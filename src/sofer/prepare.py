"""
Local dataset generation pipeline (offline).

``prepare`` turns a ``DatasetConfig`` into a complete, self-contained
dataset package inside a single output directory (the *mirror layout*):
CSV-to-Parquet conversion, cross-file schema assertion, large-value
warnings, a schema report, a Dataset Card (``README.md``), a ``LICENSE``,
and — with ``--all-files`` — per-file codebooks written directly into the
output directory (Option B, never the shared ``cache/``).

Orchestration flow (mirrors the generation half of the legacy
``uploader.upload``, minus every network step):

    1. Resolve the output directory (``cfg._base_dir / build_dir`` unless
       overridden via ``--output``).
    2. Unless ``--force``, refuse to run when generated artifacts already
       exist in the output directory (PRP-07).
    3. Unless ``--no-checks``, run the structural and quality validators and
       print their report — failures never block generation (PRP-05).
    4. Convert every eligible CSV entry to Parquet at its remote-relative
       path inside the output directory (PRP-02); ``upload_as_csv`` entries
       and non-CSV files are staged as-is instead.
    5. Assert cross-file schema consistency (exit 1 on mismatch), then warn
       on large string values.
    6. Build the schema report against the output directory (so the card
       carries native Parquet types), generate the Dataset Card and the
       LICENSE file at the output root (PRP-03).
    7. Stage non-converted files and ``recursive=true`` trees into the
       mirror layout via :func:`sofer._mirror.copy_to_mirror` (RC-R04).
    8. With ``--all-files``, generate codebooks directly into the output
       directory via ``codebook.generate_all(cfg, output_dir=...)``
       (PRP-04, Option B); without it, print an advisory only.
    9. Report NOT FOUND entries (advisory, non-blocking).
   10. With ``--verify``, run ``datasets.load_dataset()`` against the
       generated package and print PASSED/FAILED — the exit code stays 0
       regardless (PRP-08).

This module performs ZERO network calls: it never imports ``huggingface_hub``
and never requires an ``HF_TOKEN``.  The conversion / schema helpers that the
legacy ``uploader`` used to own now live here (PR 4): CSV→Parquet conversion
with parity checks, delimiter sniffing, cross-file schema assertion, large
value warnings, and the card-dtype sanity check.
"""

from __future__ import annotations

import csv as csv_module
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import DatasetConfig

import pyarrow as pa
import pyarrow.csv as pc
import pyarrow.parquet as pq

from ._mirror import copy_to_mirror
from ._parquet_helpers import _parquet_to_hf_dtype
from .checks import DatasetValidator
from .codebook import generate_all as generate_all_codebooks
from .config import (
    CODEBOOKS_DIR,
    OUTPUT_ENCODING,
    PARQUET_COMPRESSION,
    PARQUET_ROW_GROUP_SIZE,
    PARQUET_SHARD_WARNING_MB,
    REPORT_MAX_ITEMS,
    SNIFF_DELIMITERS,
)
from .quality import QualityValidator
from .repo_compliance import (
    ColumnSchema,
    build_dataset_card,
    build_license_file,
    build_schema_report_with_rows,
)
from .splits import detect_splits
from .verification import _print_verification_report, verify_load_dataset

# Files that count as "generated artifacts" for the PRP-07 overwrite check.
_GENERATED_ROOT_FILES: tuple[str, ...] = ("README.md", "LICENSE", "codebook.md")


# ── CSV → Parquet conversion helpers (moved from uploader.py, PR 4) ────────────


def _sniff_csv_delimiter(csv_path: Path) -> str:
    """Heuristic delimiter detection from the first line.

    Counts ``;``, ``,``, and ``\\t`` **outside double-quoted fields** so that
    quoted values like ``"a,b"`` do not sway the count.  Falls back to ``;``
    when the file cannot be read.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        The detected delimiter (``";"``, ``","``, or ``"\\t"``).
    """
    try:
        first = csv_path.read_text(encoding="utf-8-sig").splitlines()[0]
        counts = _count_delimiters_outside_quotes(first)
        semi = counts.get(";", 0)
        comma = counts.get(",", 0)
        tab = counts.get("\t", 0)
        best = max(semi, comma, tab)
        if best == 0:
            return ";"
        # Prefer whichever delimiter appears most often
        if semi == best:
            return ";"
        if tab == best:
            return "\t"
        return ","
    except Exception:
        return ";"


def _count_delimiters_outside_quotes(line: str) -> dict[str, int]:
    """Count occurrences of ``;``, ``,``, and ``\\t`` outside double-quoted spans.

    Args:
        line: A single line of CSV text.

    Returns:
        ``{delimiter: count}`` for every delimiter in :data:`SNIFF_DELIMITERS`.
    """
    counts: dict[str, int] = {d: 0 for d in SNIFF_DELIMITERS}
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
            continue
        if in_quotes:
            continue
        if ch in counts:
            counts[ch] += 1
    return counts


def _cast_null_columns_to_string(table: pa.Table) -> pa.Table:
    """Cast any column whose Arrow type is ``null`` to ``string``.

    pyarrow infers the ``null`` type when a column contains only missing
    values.  Downstream consumers (the schema report, Hugging Face Dataset
    Viewer) handle ``string`` gracefully; ``null`` confuses them.

    Args:
        table: Table produced by ``pyarrow.csv.read_csv``.

    Returns:
        A copy of *table* with all-null columns cast to ``string``.
    """
    for field_idx, field in enumerate(table.schema):
        if pa.types.is_null(field.type):
            col = table.column(field_idx)
            table = table.set_column(field_idx, field.name, col.cast(pa.string()))
    return table


def _read_csv_raw_values(
    csv_path: Path,
    delimiter: str,
) -> tuple[list[str], list[list[str]]] | None:
    """Read a CSV file into header and rows using Python's csv module.

    Args:
        csv_path:  Path to the CSV file.
        delimiter: Field delimiter (e.g. ``";"``).

    Returns:
        ``(header, rows)`` where *rows* is a list of lists of raw strings,
        or ``None`` if the file cannot be read.
    """
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv_module.reader(fh, delimiter=delimiter)
            try:
                header = next(reader)
            except StopIteration:
                return ([], [])
            rows = [row for row in reader]
            return (header, rows)
    except Exception:
        return None


def _check_conversion_parity(
    csv_path: Path,
    delimiter: str,
    table: pa.Table,
) -> tuple[bool, list[str]]:
    """Assert row count, column count, and column names match CSV ↔ Parquet.

    Args:
        csv_path:  Original CSV file.
        delimiter: Field delimiter used to read *csv_path*.
        table:     Parquet table produced from *csv_path*.

    Returns:
        ``(ok, warnings)`` where *ok* is ``False`` when a hard parity
        violation is detected (conversion should fail), and *warnings* is a
        list of human-readable messages about value alterations
        (non-blocking).
    """
    raw = _read_csv_raw_values(csv_path, delimiter)
    if raw is None:
        return (False, ["Cannot read CSV for parity check"])

    csv_header, csv_rows = raw
    csv_row_count = len(csv_rows)
    csv_col_count = len(csv_header)
    parquet_row_count = table.num_rows
    parquet_col_names = table.column_names

    # ── Hard parity checks (fail conversion on mismatch) ─────────────────
    if csv_row_count != parquet_row_count:
        print(
            f"  \u26a0  PARITY FAIL: row count mismatch — "
            f"CSV={csv_row_count}, Parquet={parquet_row_count}"
        )
        return (False, [])

    if csv_col_count != len(parquet_col_names):
        print(
            f"  \u26a0  PARITY FAIL: column count mismatch — "
            f"CSV={csv_col_count}, Parquet={len(parquet_col_names)}"
        )
        return (False, [])

    if csv_header != parquet_col_names:
        print(
            f"  \u26a0  PARITY FAIL: column names diverge — "
            f"CSV={csv_header}, Parquet={parquet_col_names}"
        )
        return (False, [])

    # ── Soft value parity check (warning only) ───────────────────────────
    warnings: list[str] = []
    for col_idx, col_name in enumerate(csv_header):
        # Build CSV value set (string-normalized)
        csv_values: set[str] = set()
        for row in csv_rows:
            if col_idx < len(row):
                csv_values.add(row[col_idx].strip())

        # Build Parquet value set (string-ified)
        parquet_col = table.column(col_idx)
        parquet_values: set[str] = set()
        for i in range(parquet_col.length()):
            val = parquet_col[i].as_py()
            if val is None:
                parquet_values.add("")
            else:
                parquet_values.add(str(val).strip())

        # Detect any value present in CSV but missing from Parquet after
        # stringification — this catches leading-zero stripping, comma
        # decimals, and other type-coercion artefacts.
        altered = csv_values - parquet_values
        if altered:
            first = sorted(altered)[0]
            warnings.append(
                f"  [!] VALUE ALTERED: column '{col_name}' — "
                f"e.g. '{first}' changed after type inference"
            )

    for w in warnings:
        print(w)

    return (True, warnings)


def _convert_to_parquet(
    csv_path: Path,
    staging_dir: Path,
    delimiter: str | None = None,
) -> Path | None:
    """Convert a CSV file to Parquet in *staging_dir*.

    Args:
        csv_path:    Path to the original CSV file.
        staging_dir: Temporary directory for the converted file.
        delimiter:   Explicit CSV delimiter.  When ``None`` (default), the
                     delimiter is sniffed from the first line via
                     :func:`_sniff_csv_delimiter`.

    Returns:
        Path to the converted Parquet file on success,
        ``None`` on conversion failure (warning already printed).
    """
    try:
        if delimiter is None:
            delimiter = _sniff_csv_delimiter(csv_path)
        parse_opts = pc.ParseOptions(delimiter=delimiter)
        table = pc.read_csv(csv_path, parse_options=parse_opts)
        parquet_path = staging_dir / f"{csv_path.stem}.parquet"

        # ── Row / column / value parity ───────────────────────────────────
        parity_ok, _parity_warnings = _check_conversion_parity(csv_path, delimiter, table)
        if not parity_ok:
            return None

        # ── All-null column handling ──────────────────────────────────────
        # pyarrow infers `null` type for columns where every value is missing;
        # cast those to `string` so the schema report renders them correctly.
        table = _cast_null_columns_to_string(table)

        pq.write_table(
            table,
            parquet_path,
            compression=PARQUET_COMPRESSION,
            write_page_index=True,
            row_group_size=PARQUET_ROW_GROUP_SIZE,
        )

        # ── Size check: warn when the shard exceeds the threshold ─────────
        size_mb = parquet_path.stat().st_size / (1024 * 1024)
        if size_mb > PARQUET_SHARD_WARNING_MB:
            print(
                f"  \u26a0  {parquet_path.name}: {size_mb:.1f} MB "
                f"(> {PARQUET_SHARD_WARNING_MB} MB). Consider sharding into "
                f"smaller files for better Dataset Viewer performance."
            )

        return parquet_path
    except Exception as exc:
        print(f"  \u26a0  {csv_path.name}: conversion failed \u2014 uploading as CSV")
        print(f"       ({exc})")
        return None


def _assert_cross_file_schema(
    converted: dict[str, tuple[Path, Path, str]],
    cfg: DatasetConfig,
) -> list[str]:
    """Assert every file in a split has identical column names and dtypes.

    Groups converted Parquet files by detected split and compares schemas
    within each split.  Files that share the exact same column names are
    assumed to be the same logical table (e.g. train/test splits) and are
    checked for dtype consistency; standalone tables with unique column sets
    are skipped.

    Args:
        converted: Map ``remote_key → (parquet_path, csv_path, original_remote)``
                   from the conversion step.
        cfg:       Dataset configuration (honours ``skip_cross_file_schema``).

    Returns:
        A list of human-readable error messages (empty = all splits are
        consistent).
    """
    errors: list[str] = []

    # ── Honour skip flag for multi-table / relational datasets ────────────
    if cfg.skip_cross_file_schema:
        print("  [i] Skipping cross-file schema check (skip_cross_file_schema=true)")
        return errors

    # ── Build (parquet_remote, parquet_path) pairs, de-duped by remote_key ──
    seen: set[str] = set()
    parquet_specs: list[tuple[str, Path]] = []
    for entry in cfg.files:
        remote_key = str(PurePosixPath(entry.remote).with_suffix(""))
        if remote_key in converted and remote_key not in seen:
            seen.add(remote_key)
            parquet_remote = str(PurePosixPath(entry.remote).with_suffix(".parquet"))
            parquet_specs.append((parquet_remote, converted[remote_key][0]))

    if len(parquet_specs) < 2:
        return errors  # nothing to compare

    # ── Detect splits from planned remote paths ───────────────────────────
    remotes = [spec[0] for spec in parquet_specs]
    report = detect_splits(remotes)

    if not report.splits:
        return errors

    # ── Build split → file mapping ────────────────────────────────────────
    split_files: dict[str, list[tuple[str, Path]]] = {}
    for remote, path in parquet_specs:
        for s in report.splits:
            if remote in s.files:
                split_files.setdefault(s.name, []).append((remote, path))
                break

    if not split_files:
        return errors

    # ── Group files by column name sets; only check groups with 2+ files ──
    for split_name, files in split_files.items():
        if len(files) < 2:
            continue

        # Read schemas and group by sorted column names.
        from collections import defaultdict

        col_groups: dict[tuple[str, ...], list[tuple[str, dict[str, object]]]] = defaultdict(list)
        for remote, path in files:
            try:
                schema = pq.read_schema(path)
            except Exception as exc:
                errors.append(f"Failed to read schema of '{remote}': {exc}")
                continue
            cols_key = tuple(sorted(schema.names))
            types = {name: schema.field(name).type for name in schema.names}
            col_groups[cols_key].append((remote, types))

        # Only validate groups with 2+ files (same-table variants).
        for cols_key, group in col_groups.items():
            if len(group) < 2:
                continue

            ref_remote, ref_types = group[0]
            for remote, types in group[1:]:
                diffs = []
                for col in cols_key:
                    if str(types[col]) != str(ref_types[col]):
                        diffs.append(f"{col}: {ref_types[col]} vs {types[col]}")
                if diffs:
                    cols_list = sorted(cols_key)
                    errors.append(
                        f"Schema mismatch in split '{split_name}': "
                        f"'{ref_remote}' and '{remote}' differ in dtypes "
                        f"({' ; '.join(diffs)}) — shared columns: {cols_list}"
                    )

    return errors


def _check_large_values(
    parquet_path: Path,
    max_bytes: int = 10_240,
) -> list[str]:
    """Emit warnings for string columns whose first-row values exceed *max_bytes*.

    Values above the threshold can trigger ``TooBigContentError`` in the
    Hugging Face Dataset Viewer.

    Args:
        parquet_path: Path to the Parquet file.
        max_bytes:    Byte-size threshold (default 10 KB).

    Returns:
        A list of ``"[!] …"`` warning strings (empty = no large values found).
    """
    warnings: list[str] = []
    fname = parquet_path.name

    try:
        table = pq.read_table(parquet_path)
    except Exception:
        return warnings  # can't read — skip silently

    first_rows = table.slice(0, min(REPORT_MAX_ITEMS, table.num_rows))

    for col_idx in range(first_rows.num_columns):
        field = first_rows.schema.field(col_idx)
        if not (pa.types.is_string(field.type) or pa.types.is_large_string(field.type)):
            continue

        col_data = first_rows.column(col_idx)
        for row_idx in range(col_data.length()):
            val = col_data[row_idx].as_py()
            if val is None:
                continue
            byte_len = len(val.encode("utf-8"))
            if byte_len > max_bytes:
                warnings.append(
                    f"{fname}: column '{field.name}' row {row_idx} is "
                    f"{byte_len} bytes (>10 KB). Consider moving large "
                    f"payloads to separate files to avoid "
                    f"TooBigContentError in the Dataset Viewer."
                )
                break  # one warning per column is enough

    return warnings


def _assert_card_dtypes_match_parquet(
    schema: list[ColumnSchema],
    converted: dict[str, tuple[Path, Path, str]],
) -> None:
    """Sanity-check that the schema report's hf_dtype matches the Parquet files.

    At minimum: no ``float64`` in the card when the actual Parquet column
    is ``int64`` (or any integral type).  This catches drift where the card
    falls back to a loose ``float64`` default even though the Parquet
    schema carries a precise integer type.

    Args:
        schema:    The schema report from :func:`build_schema_report`.
        converted: Map ``remote_key → (parquet_path, csv_path, original_remote)``
                   from the conversion step.
    """
    _integral_types = frozenset({"int8", "int16", "int32", "int64"})

    # Build remote_key→parquet_path lookup
    parquet_by_key: dict[str, Path] = {key: p for key, (p, _c, _r) in converted.items()}

    mismatches: list[str] = []

    for col in schema:
        if "::" in col.name:
            continue  # skip disambiguated pseudo-columns
        if col.hf_dtype is None or col.hf_dtype != "float64":
            continue  # only flag suspect float64 entries

        # Find which Parquet file this column belongs to
        for remote_key, parquet_path in parquet_by_key.items():
            try:
                pf = pq.ParquetFile(parquet_path)
                names = pf.schema_arrow.names
                if col.name not in names:
                    continue
                field_idx = names.index(col.name)
                pa_type = pf.schema_arrow.field(field_idx).type
                actual = _parquet_to_hf_dtype(pa_type)
                if actual is not None and actual in _integral_types:
                    mismatches.append(
                        f"Column '{col.name}' card dtype=float64 but "
                        f"Parquet '{remote_key}.parquet' has {actual} — "
                        f"mismatch may indicate schema-source drift."
                    )
                    break  # one mismatch per column is enough
            except Exception:
                continue

    if mismatches:
        for m in mismatches:
            print(f"  \u26a0  SCHEMA ASSERTION: {m}")


def resolve_output_dir(cfg: DatasetConfig, override: str | None) -> Path:
    """Resolve the artifact destination directory for *cfg*.

    The default is the dataset's own ``build_dir`` (``[dataset] build_dir``
    in the TOML, default ``"build"``) anchored to the config directory —
    NOT the tool-wide ``OUTPUT_DIR``.  ``--output`` overrides the TOML value
    for this run without touching it.

    Args:
        cfg:      Dataset configuration.
        override: ``--output`` value (``None`` = use ``cfg.build_dir``).

    Returns:
        Absolute output directory path.
    """
    base = cfg._base_dir if cfg._base_dir else Path.cwd()
    name = override or cfg.build_dir
    out = Path(name)
    if not out.is_absolute():
        out = base / out
    return out.resolve()


def _check_local_overwrite(cfg: DatasetConfig, output_dir: Path, all_files: bool) -> list[str]:
    """Return the generated artifacts that already exist in *output_dir*.

    Used by PRP-07: without ``--force``, ``prepare`` refuses to overwrite
    existing generated artifacts.  The set checked matches what a run would
    produce: converted Parquet mirror paths, root compliance files, and
    (with ``--all-files``) the codebook index + ``codebooks/`` tree.

    Args:
        cfg:        Dataset configuration.
        output_dir: Destination directory being checked.
        all_files:  Whether codebooks are part of this run's output.

    Returns:
        List of existing artifact paths (empty = nothing to overwrite).
    """
    existing: list[str] = []

    for entry in cfg.files:
        if entry.recursive:
            continue  # directory trees are merged by copy_to_mirror
        remote_lower = entry.remote.lower()
        if remote_lower.endswith(".csv") and not entry.upload_as_csv:
            candidate = output_dir / PurePosixPath(entry.remote).with_suffix(".parquet")
        else:
            candidate = output_dir / entry.remote
        if candidate.exists():
            existing.append(str(candidate))

    for name in _GENERATED_ROOT_FILES:
        candidate = output_dir / name
        if candidate.exists():
            existing.append(str(candidate))

    if all_files:
        codebooks_dir = output_dir / CODEBOOKS_DIR
        if codebooks_dir.exists():
            existing.append(str(codebooks_dir))

    return existing


def prepare(
    cfg: DatasetConfig,
    output_dir: Path,
    all_files: bool = False,
    no_checks: bool = False,
    force: bool = False,
    verify: bool = False,
) -> int:
    """Generate the complete dataset package for *cfg* into *output_dir*.

    Full flow — see the module docstring for the orchestration walk-through.

    Args:
        cfg:        Dataset configuration.
        output_dir: Destination directory (mirror layout root).  Use
                    :func:`resolve_output_dir` to derive it from the CLI.
        all_files:  When ``True``, generate per-file codebooks directly into
                    ``output_dir`` (Option B).  When ``False``, print an
                    advisory only.
        no_checks:  When ``True``, skip the DatasetValidator / QualityValidator
                    run entirely.  Default runs them non-blocking (report only).
        force:      When ``True``, overwrite existing generated artifacts.
                    Without it, existing artifacts block the run (exit 1).
        verify:     When ``True``, run ``datasets.load_dataset()`` against the
                    generated package and print PASSED/FAILED (non-blocking).

    Returns:
        Exit code: ``0`` on success, ``1`` on overwrite refusal, cross-file
        schema failure, or codebook generation failure.
    """
    print(f"\n{'=' * 60}")
    print(f"  Dataset:   {cfg.name}")
    print(f"  Output:    {output_dir}")
    print(f"  File entries: {len(cfg.files)}")
    print(f"{'=' * 60}\n")

    # Ensure UTF-8 output for Unicode characters on Windows.
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    base = cfg._base_dir if cfg._base_dir else Path.cwd()

    # ── 0. Overwrite protection (PRP-07) ────────────────────────────────
    if not force:
        existing = _check_local_overwrite(cfg, output_dir, all_files)
        if existing:
            print("  \u2717  Refusing to overwrite existing generated artifacts:")
            for path in sorted(existing):
                print(f"     {path}")
            print("     Re-run with --force to regenerate and overwrite.")
            print()
            return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Checks (PRP-05) — non-blocking, report only ─────────────────
    if not no_checks:
        validator = DatasetValidator(cfg)
        report = validator.run_all()
        quality = QualityValidator(cfg)
        quality_report = quality.run()
        report.quality_results = quality_report.quality_results
        report.ran_checks = quality_report.ran_checks
        report.print_summary()

    # ── 2. Conversion loop — CSV → Parquet (PRP-02) ────────────────────
    # Conversion writes flat stem-named parquets into per-entry temp
    # subdirs (same-stem files in different remote dirs must not collide),
    # then each is staged to its remote-relative mirror path.
    converted: dict[str, tuple[Path, Path, str]] = {}
    tmpdir = Path(tempfile.mkdtemp())
    try:
        for idx, entry in enumerate(cfg.files):
            remote_lower = entry.remote.lower()
            if entry.recursive:
                continue
            if remote_lower.endswith(".csv") or remote_lower.endswith(".parquet"):
                pass  # eligible for conversion
            else:
                continue
            if entry.upload_as_csv:
                print(f"  i  {entry.remote}: upload_as_csv=True, skipping conversion")
                continue

            local = entry.resolve(base)
            if not local.exists():
                continue  # will be reported as NOT FOUND below

            entry_tmp = tmpdir / str(idx)
            entry_tmp.mkdir()
            result = _convert_to_parquet(local, entry_tmp, delimiter=cfg.csv_delimiter)
            if result is not None:
                # Use the full remote path (without extension) as the key so
                # that data/PROV/train and data/DPTO/train stay distinct.
                remote_key = str(PurePosixPath(entry.remote).with_suffix(""))
                converted[remote_key] = (result, local, entry.remote)
                print(f"  [~] {local.name} -> {result.name}")

        # ── 3. Cross-file schema assertion (per split) ─────────────────
        schema_errors = _assert_cross_file_schema(converted, cfg)
        if schema_errors:
            print("\n  \u2717  Cross-file schema assertion FAILED:")
            for e in schema_errors:
                print(f"     {e}")
            print()
            return 1

        # ── 4. Large-value check on converted Parquet files ────────────
        for _stem, (parquet_path, _csv_path, _orig_remote) in converted.items():
            for w in _check_large_values(parquet_path):
                print(f"  \u26a0  {w}")

        # ── 5. Stage converted Parquet files into the mirror layout ────
        for remote_key, (parquet_path, _csv_path, original_remote) in converted.items():
            parquet_remote = str(PurePosixPath(original_remote).with_suffix(".parquet"))
            copy_to_mirror(parquet_path, output_dir, parquet_remote)

        # ── 6. Schema report + Dataset Card + LICENSE (PRP-03) ─────────
        print("  [i] Building schema report \u2026")
        schema, row_counts = build_schema_report_with_rows(
            cfg,
            csv_delimiter=cfg.csv_delimiter,
            csv_encoding=cfg.csv_encoding,
            staging_dir=output_dir,
        )

        recipe_content: str | None = None
        if cfg.recipe:
            recipe_path = Path(cfg.recipe)
            if recipe_path.exists():
                recipe_content = recipe_path.read_text(encoding="utf-8")

        study_design_content: str | None = None
        if cfg.study_design:
            study_design_path = Path(cfg.study_design)
            if study_design_path.exists():
                study_design_content = study_design_path.read_text(encoding="utf-8")
            else:
                print(f"  \u26a0  study_design declared but not found: {cfg.study_design}")

        # Readme override — if cfg.readme is set, use that file instead of generating.
        if cfg.readme:
            readme_path = Path(cfg.readme)
            if readme_path.exists():
                print(f"  [i] Using custom README from: {cfg.readme}")
                card = readme_path.read_text(encoding="utf-8")
            else:
                print(f"  \u26a0  readme declared but not found: {cfg.readme} — generating card")
                card = build_dataset_card(
                    cfg,
                    schema,
                    recipe_content=recipe_content,
                    study_design_content=study_design_content,
                    row_counts=row_counts,
                )
        else:
            print("  [i] Generating Dataset Card \u2026")
            card = build_dataset_card(
                cfg,
                schema,
                recipe_content=recipe_content,
                study_design_content=study_design_content,
                row_counts=row_counts,
            )

        print("  [i] Generating LICENSE \u2026")
        license_text = build_license_file(cfg.license)

        (output_dir / "README.md").write_text(card, encoding=OUTPUT_ENCODING)
        (output_dir / "LICENSE").write_text(license_text, encoding=OUTPUT_ENCODING)

        # ── 7. Stage non-converted files (upload_as_csv, parquet, other)
        #       and recursive trees (RC-R04) ────────────────────────────
        for entry in cfg.files:
            remote_key = str(PurePosixPath(entry.remote).with_suffix(""))
            if remote_key in converted:
                continue  # already staged as Parquet above
            local = entry.resolve(base)
            if not local.exists():
                continue  # will be reported as NOT FOUND below
            copy_to_mirror(local, output_dir, entry.remote)

        # ── 8. Codebooks (PRP-04) — Option B: directly into output_dir ─
        if all_files:
            try:
                generate_all_codebooks(cfg, output_dir=str(output_dir))
            except ValueError as exc:
                print(f"  \u2717  Codebook generation failed: {exc}", file=sys.stderr)
                return 1
        else:
            print(
                "  i  Re-run with --all-files to generate codebooks into the output directory.",
                file=sys.stderr,
            )

        # ── 9. Report NOT FOUND files ──────────────────────────────────
        not_found: list[str] = []
        for entry in cfg.files:
            local = entry.resolve(base)
            if not local.exists():
                not_found.append(str(local))
        if not_found:
            for nf in not_found:
                print(f"  \u2717  NOT FOUND: {nf}")

        # ── 10. Optional load verification (PRP-08) — non-blocking ─────
        if verify:
            verification = verify_load_dataset(output_dir, cfg)
            _print_verification_report(verification)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"\n{'=' * 60}")
    print(f"  Result: {len(converted)} parquet(s) generated in {output_dir}")
    print(f"{'=' * 60}\n")
    return 0
