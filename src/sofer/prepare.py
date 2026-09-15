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
and never requires an ``HF_TOKEN``.  CSV→Parquet conversion — the readers, the
parity checks, and the delimiter/encoding resolution — has exactly one home in
:mod:`sofer._converters` (PC-U06) and is reached through
:func:`sofer._converters.convert_file_to_parquet` with the dataset config, so a
declared ``[meta] csv_delimiter``/``csv_encoding`` governs the read.  What
remains here are the schema helpers the legacy ``uploader`` used to own (PR 4):
cross-file schema assertion, large-value warnings, and the card-dtype sanity
check.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import DatasetConfig

import pyarrow as pa
import pyarrow.parquet as pq

from . import config
from ._mirror import copy_to_mirror, parquet_remote_for
from ._parquet_helpers import _parquet_to_hf_dtype
from .checks import DatasetValidator
from .codebook import generate_all as generate_all_codebooks
from .model import resolve_doc_path
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
    # ``converted`` is keyed by *normalized* Parquet remotes; we resolve via
    # the same normalization so that accent/case variants are grouped correctly.
    from ._converters import normalize_parquet_remote

    seen: set[str] = set()
    parquet_specs: list[tuple[str, Path]] = []
    for entry in cfg.files:
        norm_key = normalize_parquet_remote(parquet_remote_for(entry.remote))
        legacy_key = str(PurePosixPath(entry.remote).with_suffix(""))
        norm_stem = norm_key.removesuffix(".parquet")
        # For xlsx multi-sheet, the entry's norm_key is the single-sheet
        # stem; we need to include all matching sheet remotes
        matching: list[str] = []
        for k in converted:
            if (
                k == norm_key
                or k == legacy_key
                or k.lower() == norm_stem.lower()
                or k.startswith(norm_stem + "__")
                or k.startswith(legacy_key + "__")
                or (k.startswith(norm_stem + "_") and k != norm_key)
                or (k.startswith(legacy_key + "_") and k != legacy_key)
            ):
                matching.append(k)
        for mk in matching:
            if mk not in seen:
                seen.add(mk)
                parquet_specs.append((mk, converted[mk][0]))

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

    first_rows = table.slice(0, min(config.REPORT_MAX_ITEMS, table.num_rows))

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
    produce: converted Parquet mirror paths (normalized), root compliance
    files, and (with ``--all-files``) the codebook index + ``codebooks/`` tree.

    For convertible entries the candidate is the **normalized** Parquet remote
    (via ``normalize_parquet_remote(parquet_remote_for(...))``); XLSX entries
    check any ``stem__*.parquet`` match in the mirror layout.

    Args:
        cfg:        Dataset configuration.
        output_dir: Destination directory being checked.
        all_files:  Whether codebooks are part of this run's output.

    Returns:
        List of existing artifact paths (empty = nothing to overwrite).
    """
    from ._converters import CONVERTIBLE_SUFFIXES, normalize_parquet_remote

    existing: list[str] = []

    for entry in cfg.files:
        if entry.recursive:
            continue  # directory trees are merged by copy_to_mirror
        suffix = PurePosixPath(entry.remote.replace("\\", "/")).suffix.lower()
        is_convertible = suffix in CONVERTIBLE_SUFFIXES
        eligible = is_convertible and bool(entry.convert_to_parquet)
        if eligible:
            normalized = normalize_parquet_remote(parquet_remote_for(entry.remote))
            if suffix == ".xlsx":
                # Any existing sheet parquet for this stem counts
                stem = PurePosixPath(normalized).stem
                parent = PurePosixPath(normalized).parent
                search_dir = output_dir / parent if str(parent) != "." else output_dir
                if search_dir.is_dir():
                    primary = sorted(search_dir.glob(f"{stem}__*.parquet"))
                    primary = [p for p in primary if p.is_file()]
                    if primary:
                        for p in primary:
                            existing.append(str(p))
                    else:
                        # Fallback for single-underscore normalized layout
                        # (mirrors _mirror.py PUB-10): _*.parquet filtered c.stem != stem
                        alt = sorted(search_dir.glob(f"{stem}_*.parquet"))
                        for p in alt:
                            if p.is_file() and p.stem != stem:
                                existing.append(str(p))
                    # Also single-sheet case
                    candidate = output_dir / PurePosixPath(normalized)
                    if candidate.exists():
                        existing.append(str(candidate))
                else:
                    candidate = output_dir / PurePosixPath(normalized)
                    if candidate.exists():
                        existing.append(str(candidate))
            else:
                candidate = output_dir / PurePosixPath(normalized)
                if candidate.exists():
                    existing.append(str(candidate))
        else:
            candidate = output_dir / entry.remote
            if candidate.exists():
                existing.append(str(candidate))

    for name in _GENERATED_ROOT_FILES:
        candidate = output_dir / name
        if candidate.exists():
            existing.append(str(candidate))

    if all_files:
        codebooks_dir = output_dir / config.CODEBOOKS_DIR
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

    # ── 2. Conversion loop — universal csv/tsv/xlsx/jsonl → Parquet (PRP-02) ──
    # Dispatcher in _converters handles per-format readers; this loop only
    # gates eligibility (convertible set + convert_to_parquet + not recursive
    # + not .parquet passthrough + local exists) and keys the result by the
    # normalized Parquet remote.  XLSX multi-sheet expands to N entries.
    from ._converters import CONVERTIBLE_SUFFIXES, convert_file_to_parquet, normalize_parquet_remote

    converted: dict[str, tuple[Path, Path, str]] = {}
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Validate case-fold collisions on normalized keys before any write (PRP-02b)
        from ._mirror import _validate_case_fold_collisions

        collision_errors = _validate_case_fold_collisions(cfg)
        if collision_errors:
            for e in collision_errors:
                print(f"  \u2717  {e}")
            return 1

        for idx, entry in enumerate(cfg.files):
            if entry.recursive:
                continue
            suffix = PurePosixPath(entry.remote.replace("\\", "/")).suffix.lower()
            if suffix == ".parquet":
                continue  # passthrough — staged as-is below
            if suffix not in CONVERTIBLE_SUFFIXES:
                continue  # non-convertible passthrough
            if not entry.convert_to_parquet:
                if entry.upload_as_csv and suffix == ".csv":
                    print(f"  i  {entry.remote}: upload_as_csv=True, skipping conversion")
                continue

            local = entry.resolve(base)
            if not local.exists():
                continue  # will be reported as NOT FOUND below

            entry_tmp = tmpdir / str(idx)
            entry_tmp.mkdir()
            dispatch_result = convert_file_to_parquet(local, entry_tmp, cfg)
            if not dispatch_result:
                # Conversion failed — warn already printed; fallback to original
                print(f"  \u26a0  {local.name}: conversion failed \u2014 staging original")
                continue
            # Single-sheet / single-file converters return {stem: path}
            # XLSX returns {stem__sheet: path} per sheet
            for stem_key, parquet_path in dispatch_result.items():
                if suffix == ".xlsx":
                    # XLSX: stem_key is already stem__sheet or stem
                    # Build normalized remote: dir(normalized) / stem_key.parquet
                    parquet_remote = parquet_remote_for(entry.remote)
                    # Replace stem with dispatch stem_key (preserves dir)
                    base_remote = PurePosixPath(parquet_remote)
                    # For multi-sheet, stem_key includes original stem prefix;
                    # derive dir + stem_key.parquet
                    normalized_remote = normalize_parquet_remote(
                        str(base_remote.parent / f"{stem_key}.parquet")
                        if str(base_remote.parent) != "."
                        else f"{stem_key}.parquet"
                    )
                else:
                    normalized_remote = normalize_parquet_remote(parquet_remote_for(entry.remote))
                converted[normalized_remote] = (parquet_path, local, entry.remote)
                print(f"  [~] {local.name} -> {PurePosixPath(normalized_remote).name}")

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
        for normalized_remote, (parquet_path, _csv_path, _orig_remote) in converted.items():
            copy_to_mirror(parquet_path, output_dir, normalized_remote)

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
            recipe_path = resolve_doc_path(cfg.recipe, base)
            if recipe_path is not None and recipe_path.exists():
                recipe_content = recipe_path.read_text(encoding="utf-8")

        study_design_content: str | None = None
        if cfg.study_design:
            study_design_path = resolve_doc_path(cfg.study_design, base)
            if study_design_path is not None and study_design_path.exists():
                study_design_content = study_design_path.read_text(encoding="utf-8")
            else:
                print(f"  \u26a0  study_design declared but not found: {cfg.study_design}")

        # Readme override — if cfg.readme is set, use that file instead of generating.
        if cfg.readme:
            readme_path = resolve_doc_path(cfg.readme, base)
            if readme_path is not None and readme_path.exists():
                print(f"  [i] Using custom README from: {readme_path}")
                card = readme_path.read_text(encoding="utf-8")
            else:
                print(f"  \u26a0  readme declared but not found: {cfg.readme} — generating card")
                card = build_dataset_card(
                    cfg,
                    schema,
                    recipe_content=recipe_content,
                    study_design_content=study_design_content,
                    row_counts=row_counts,
                    staging_dir=output_dir,
                )
        else:
            print("  [i] Generating Dataset Card \u2026")
            card = build_dataset_card(
                cfg,
                schema,
                recipe_content=recipe_content,
                study_design_content=study_design_content,
                row_counts=row_counts,
                staging_dir=output_dir,
            )

        print("  [i] Generating LICENSE \u2026")
        license_text = build_license_file(cfg.license)

        (output_dir / "README.md").write_text(card, encoding=config.OUTPUT_ENCODING)
        (output_dir / "LICENSE").write_text(license_text, encoding=config.OUTPUT_ENCODING)

        # ── 7. Stage non-converted files (opt-out, parquet passthrough, other)
        #       and recursive trees (RC-R04) ────────────────────────────
        for entry in cfg.files:
            # If this entry's normalized remote (or any sheet expansion) was
            # converted, it is already staged — skip
            norm_key = normalize_parquet_remote(parquet_remote_for(entry.remote))
            suffix = PurePosixPath(entry.remote.replace("\\", "/")).suffix.lower()
            norm_stem = norm_key.removesuffix(".parquet")
            if suffix == ".xlsx":
                is_converted = any(
                    k == norm_key
                    or k.startswith(norm_stem + "__")
                    or (k.startswith(norm_stem + "_") and k != norm_key)
                    for k in converted
                )
            else:
                is_converted = any(k == norm_key for k in converted)
            if is_converted:
                continue  # already staged as Parquet above
            local = entry.resolve(base)
            if not local.exists():
                continue  # will be reported as NOT FOUND below
            # For passthrough .parquet, copy at declared remote; for opt-out
            # convertible, keep original remote path
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

        # ── 8b. PRP-09: orphan pruning when force=True (idempotent, after staging + codebooks)
        # Allowlist is expanded_planned_remotes + compliance; dual __/_ guard is
        # inherited from expanded_planned_remotes (PUB-10).  force=False skips.
        if force:
            from ._clean import allowed_output_remotes, prune_orphans

            # keep_csv is False for prepare — the package is the build output,
            # not the hf upload set.  Any CSV originals staged via keep_csv are
            # handled at publish time; prepare owns only Parquet + passthrough.
            allowed = allowed_output_remotes(cfg, keep_csv=False, output_dir=output_dir)
            prune_orphans(output_dir, allowed)

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

        # -- 10b. Package artifact manifest (PRP-11, #122) --------
        # Single source of truth consumed by publish dry-run/confirm.
        from .manifest import MANIFEST_NAME, build_package_manifest

        (output_dir / MANIFEST_NAME).write_bytes(
            build_package_manifest(cfg, output_dir).json_bytes()
        )

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"\n{'=' * 60}")
    print(f"  Result: {len(converted)} parquet(s) generated in {output_dir}")
    print(f"{'=' * 60}\n")
    return 0
