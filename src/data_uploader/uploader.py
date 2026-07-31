"""
Upload engine.

Uploads files to Hugging Face Hub using the ``huggingface_hub`` Python API
directly (not via the deprecated ``huggingface-cli``).
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pc
import pyarrow.parquet as pq
from huggingface_hub import HfApi

from .model import DatasetConfig
from .repo_compliance import build_dataset_card, build_license_file, build_schema_report
from .splits import detect_splits, validate_layout, validate_split_mapping
from .verification import VerificationReport, _print_verification_report, verify_load_dataset

_api = HfApi()


def _ensure_repo(cfg: DatasetConfig) -> None:
    """Create the HF repository if it doesn't exist (idempotent)."""
    try:
        _api.create_repo(
            repo_id=cfg.repo_id,
            repo_type=cfg.repo_type,
            private=cfg.private,
            exist_ok=True,
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "already exists" in msg:
            print(f"  i  Repository already exists: {cfg.repo_id}")
        else:
            print(f"  \u26a0  {exc}")


def _hf_upload(
    repo_id: str,
    local_path: str | Path,
    remote_path: str,
    repo_type: str,
) -> bool:
    """Upload a single file to Hugging Face Hub.

    Uses ``HfApi.upload_file()``.
    """
    label = Path(local_path).name
    print(f"  \u2191  {label}  \u2192  {remote_path}")
    try:
        _api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=remote_path,
            repo_id=repo_id,
            repo_type=repo_type,
        )
        print(f"  \u2713  {label}")
        return True
    except Exception as exc:
        print(f"  \u2717  {exc}")
        return False


def _sniff_csv_delimiter(csv_path: Path) -> str:
    """Heuristic delimiter detection: pick ``;`` or ``,`` based on first line."""
    try:
        first = csv_path.read_text(encoding="utf-8-sig").splitlines()[0]
        semi = first.count(";")
        comma = first.count(",")
        return ";" if semi > comma else ","
    except Exception:
        return ";"


def _convert_to_parquet(csv_path: Path, staging_dir: Path) -> Path | None:
    """Convert a CSV file to Parquet in *staging_dir*.

    Args:
        csv_path:    Path to the original CSV file.
        staging_dir: Temporary directory for the converted file.

    Returns:
        Path to the converted Parquet file on success,
        ``None`` on conversion failure (warning already printed).

    Behaviour:
        1. Sniff the delimiter (``;`` or ``,``) from the first line.
        2. Read CSV via ``pyarrow.csv.read_csv(csv_path)``.
        3. Write via ``pyarrow.parquet.write_table(table, parquet_path,
           compression='zstd')``.
        4. Return the Parquet path.
        5. On any exception, print a warning and return ``None``.
    """
    try:
        delimiter = _sniff_csv_delimiter(csv_path)
        parse_opts = pc.ParseOptions(delimiter=delimiter)
        table = pc.read_csv(csv_path, parse_options=parse_opts)
        parquet_path = staging_dir / f"{csv_path.stem}.parquet"
        pq.write_table(
            table,
            parquet_path,
            compression="zstd",
            write_page_index=True,
            row_group_size=100_000,
        )

        # ── Size check: warn if >500 MB ──────────────────────────────────
        size_mb = parquet_path.stat().st_size / (1024 * 1024)
        if size_mb > 500:
            print(
                f"  \u26a0  {parquet_path.name}: {size_mb:.1f} MB (>500 MB). "
                f"Consider sharding into smaller files for better "
                f"Dataset Viewer performance."
            )

        return parquet_path
    except Exception as exc:
        print(f"  \u26a0  {csv_path.name}: conversion failed \u2014 uploading as CSV")
        print(f"       ({exc})")
        return None


def _validate_remote_paths(cfg: DatasetConfig) -> list[str]:
    """Validate that every ``FileEntry.remote`` is a file path, not a directory.

    A remote path ending with ``/`` (or ``\\``) that is not declared as
    ``recursive`` is considered invalid.

    Returns:
        A list of error messages (empty = all paths are valid).
    """
    errors: list[str] = []
    for i, entry in enumerate(cfg.files):
        stripped = entry.remote.rstrip("/").rstrip("\\")
        # Directory path detected — trailing slash removed something
        if stripped != entry.remote and not entry.recursive:
            errors.append(
                f"File entry {i + 1}: remote='{entry.remote}' looks like a "
                f"directory path (trailing slash). Set recursive=true if this "
                f"is a directory, or provide a valid file path."
            )
        # Empty path after stripping
        if not stripped:
            errors.append(f"File entry {i + 1}: remote='{entry.remote}' is not a valid file path.")
    return errors


def _inspect_repo(cfg: DatasetConfig) -> list[str]:
    """Query the HF repo and return a list of existing remote file paths.

    Returns an empty list when the repo does not exist yet, the network
    is unavailable, or the call otherwise fails — the upload will create
    whatever files are needed.
    """
    try:
        existing = _api.list_repo_files(repo_id=cfg.repo_id, repo_type=cfg.repo_type)
        return list(existing)
    except Exception:
        return []


def _repo_diff_summary(
    cfg: DatasetConfig,
    existing_files: list[str],
    keep_csv: bool,
) -> str:
    """Build a human-readable diff of what will be added vs modified.

    Args:
        cfg:            Dataset configuration.
        existing_files: Files already in the repo (from :func:`_inspect_repo`).
        keep_csv:       Whether original CSVs will be uploaded alongside Parquet.

    Returns:
        A multiline string suitable for printing.
    """
    existing_set = {f.lower() for f in existing_files}

    # Build the list of planned uploads
    planned: list[str] = []

    # Compliance files
    planned.append("README.md")
    planned.append("LICENSE")

    # Data files
    for entry in cfg.files:
        remote_lower = entry.remote.lower()
        if entry.recursive:
            planned.append(f"{entry.remote}*")  # directory — can't list contents
        elif remote_lower.endswith(".csv") and not entry.upload_as_csv:
            stem = Path(entry.remote).stem
            planned.append(f"{stem}.parquet")
            if keep_csv:
                planned.append(entry.remote)
        else:
            planned.append(entry.remote)

    new = [p for p in planned if p.lower() not in existing_set]
    modified = [p for p in planned if p.lower() in existing_set]

    lines: list[str] = []
    lines.append("  Repo inspection:")
    if not existing_files:
        lines.append("    (repo is empty or does not exist yet)")
    else:
        lines.append(f"    {len(existing_files)} file(s) already in repo")

    if new:
        lines.append(f"    + {len(new)} file(s) will be ADDED:")
        for f in new[:10]:
            lines.append(f"      + {f}")
        if len(new) > 10:
            lines.append(f"      … and {len(new) - 10} more")

    if modified:
        lines.append(f"    ~ {len(modified)} file(s) will be OVERWRITTEN:")
        for f in modified[:5]:
            lines.append(f"      ~ {f}")
        if len(modified) > 5:
            lines.append(f"      … and {len(modified) - 5} more")

    return "\n".join(lines)


def _check_overwrite_protection(
    existing_files: list[str],
    force: bool,
) -> set[str]:
    """Check whether README.md / LICENSE already exist and gate overwrites.

    When *force* is ``True``, skip the check entirely.

    In interactive mode: warn and ask for confirmation per file.
    In non-interactive mode: warn and skip the protected files.

    Returns:
        Set of filenames that SHOULD be skipped (protected).
    """
    if force:
        return set()

    protected: set[str] = set()
    existing_set = {f.lower() for f in existing_files}
    interactive = sys.stdin.isatty()

    for filename in ("README.md", "LICENSE"):
        if filename.lower() in existing_set:
            if interactive:
                try:
                    answer = input(
                        f"  ⚠  {filename} already exists in the repo. Overwrite? [y/N]: "
                    )
                    if answer.strip().lower() not in ("y", "yes"):
                        print(f"  i  {filename}: skipped (protected by user)")
                        protected.add(filename.lower())
                except (EOFError, KeyboardInterrupt):
                    print(f"\n  i  {filename}: skipped (non-interactive input)")
                    protected.add(filename.lower())
            else:
                print(
                    f"  ⚠  {filename} already exists in the repo. "
                    f"Skipping overwrite (non-interactive mode — use --force to override)."
                )
                protected.add(filename.lower())

    return protected


def _assert_cross_file_schema(
    converted: dict[str, tuple[Path, Path, str]],
    cfg: DatasetConfig,
) -> list[str]:
    """Assert every file in a split has identical column names and dtypes.

    Groups converted Parquet files by detected split and compares
    schemas within each split.  Returns a list of human-readable error
    messages (empty = all splits are consistent).
    """
    errors: list[str] = []

    # ── Build (parquet_remote, parquet_path) pairs, de-duped by stem ──────
    seen: set[str] = set()
    parquet_specs: list[tuple[str, Path]] = []
    for entry in cfg.files:
        stem = Path(entry.remote).stem
        if stem in converted and stem not in seen:
            seen.add(stem)
            parquet_remote = f"{stem}.parquet"
            parquet_specs.append((parquet_remote, converted[stem][0]))

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

    # ── Compare schemas within each multi-file split ──────────────────────
    for split_name, files in split_files.items():
        if len(files) < 2:
            continue

        ref_remote, ref_path = files[0]
        try:
            ref_schema = pq.read_schema(ref_path)
        except Exception as exc:
            errors.append(f"Failed to read schema of '{ref_remote}': {exc}")
            continue

        ref_cols = set(ref_schema.names)
        ref_types: dict[str, object] = {
            name: ref_schema.field(name).type for name in ref_schema.names
        }

        for remote, path in files[1:]:
            try:
                schema = pq.read_schema(path)
            except Exception as exc:
                errors.append(f"Failed to read schema of '{remote}': {exc}")
                continue

            cols = set(schema.names)
            types = {name: schema.field(name).type for name in schema.names}

            # -- column name mismatch --
            if cols != ref_cols:
                missing = sorted(ref_cols - cols)
                extra = sorted(cols - ref_cols)
                detail_parts: list[str] = []
                if missing:
                    detail_parts.append(f"missing: {missing}")
                if extra:
                    detail_parts.append(f"extra: {extra}")
                errors.append(
                    f"Schema mismatch in split '{split_name}': "
                    f"'{ref_remote}' columns={sorted(ref_cols)}, "
                    f"'{remote}' columns={sorted(cols)} "
                    f"({' ; '.join(detail_parts)})"
                )
                continue

            # -- dtype mismatch (only when column names are identical) --
            common = sorted(cols & ref_cols)
            diffs = []
            for col in common:
                if str(types[col]) != str(ref_types[col]):
                    diffs.append(f"{col}: {ref_types[col]} vs {types[col]}")
            if diffs:
                errors.append(
                    f"Schema mismatch in split '{split_name}': "
                    f"'{ref_remote}' and '{remote}' differ in dtypes "
                    f"({' ; '.join(diffs)})"
                )

    return errors


def _check_large_values(
    parquet_path: Path,
    max_bytes: int = 10_240,
) -> list[str]:
    """Emit warnings for string columns whose first-10-row values exceed
    *max_bytes*, which can trigger ``TooBigContentError`` in the Hugging
    Face Dataset Viewer.

    Args:
        parquet_path: Path to the Parquet file.
        max_bytes:    Byte-size threshold (default 10 KB).

    Returns:
        A list of ``"⚠ …"`` warning strings (empty = no large values found).
    """
    warnings: list[str] = []
    fname = parquet_path.name

    try:
        table = pq.read_table(parquet_path)
    except Exception:
        return warnings  # can't read — skip silently

    first_rows = table.slice(0, min(10, table.num_rows))

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


def upload(
    cfg: DatasetConfig,
    keep_csv: bool = False,
    force: bool = False,
    dry_run: bool = False,
    verify_load: bool = False,
) -> int:
    """Upload all files declared in *cfg* to Hugging Face Hub.

    Converts CSV files to Parquet before compliance generation so the schema
    report can read native Parquet types.  Falls back to CSV when conversion
    fails.

    Args:
        cfg:         Dataset configuration.
        keep_csv:    When ``True`` and a CSV was converted to Parquet, also
                     upload the original CSV as a secondary file.
        force:       When ``True``, skip the README.md / LICENSE overwrite
                     protection prompt and overwrite unconditionally.
        dry_run:     When ``True``, show the repo diff and split report but
                     do not upload any files.
        verify_load: When ``True``, run ``datasets.load_dataset()`` against
                     the staged files to verify end-to-end loadability.
                     With ``--dry-run``, stages the files for verification
                     and then cleans up.

    Returns:
        Exit code (0 = success, 1 = one or more uploads failed).
    """
    print(f"\n{'=' * 60}")
    print(f"  Dataset:   {cfg.name}")
    print(f"  Target:    {cfg.repo_id}")
    print(f"  Type:      {cfg.repo_type}")
    print(f"  Private:   {cfg.private}")
    print(f"  File entries: {len(cfg.files)}")
    print(f"{'=' * 60}\n")

    # Ensure UTF-8 output for Unicode characters on Windows
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # ── 0. Remote path validation (before any network calls) ────────────
    path_errors = _validate_remote_paths(cfg)
    if path_errors:
        print("  \u2717  Remote path errors:")
        for e in path_errors:
            print(f"     {e}")
        print()
        return 1

    _ensure_repo(cfg)

    # ── 0b. Pre-upload repo inspection ─────────────────────────────────
    existing_files = _inspect_repo(cfg)
    diff_summary = _repo_diff_summary(cfg, existing_files, keep_csv)
    print(diff_summary)
    print()

    # ── 0c. Overwrite protection for README.md / LICENSE ───────────────
    protected = _check_overwrite_protection(existing_files, force)

    # ── 0d. Planned remotes (used by dry-run and verification) ──────────
    planned_remotes: list[str] = []
    for entry in cfg.files:
        if entry.recursive:
            planned_remotes.append(entry.remote.rstrip("/\\"))
        elif entry.remote.lower().endswith(".csv") and not entry.upload_as_csv:
            stem = Path(entry.remote).stem
            planned_remotes.append(f"{stem}.parquet")
            if keep_csv:
                planned_remotes.append(entry.remote)
        else:
            planned_remotes.append(entry.remote)

    # ── 0e. Split mapping validation (always run before upload) ─────────
    _print_split_mapping_validation(planned_remotes)

    # ── 0f. Dry-run: stop here UNLESS verify_load is requested ─────────
    if dry_run and not verify_load:
        # Show split detection for dry-run
        simulated = existing_files + planned_remotes
        report = detect_splits(simulated)
        _print_split_report(report)
        print(f"\n{'=' * 60}")
        print("  Dry-run complete — no files uploaded.")
        print(f"{'=' * 60}\n")
        return 0

    # ── Staging (wraps everything for cleanup) ───────────────────────────
    tmpdir = Path(tempfile.mkdtemp())
    try:
        base = cfg._base_dir if cfg._base_dir else Path.cwd()

        # ── 1. Conversion loop — CSV → Parquet ──────────────────────────
        # Map: remote stem → (parquet_path, original_csv_path, original_remote)
        converted: dict[str, tuple[Path, Path, str]] = {}

        for entry in cfg.files:
            remote_lower = entry.remote.lower()
            if entry.recursive or not remote_lower.endswith(".csv"):
                continue
            if entry.upload_as_csv:
                print(f"  i  {entry.remote}: upload_as_csv=True, skipping conversion")
                continue

            local = entry.resolve(base)
            if not local.exists():
                continue  # will be reported as NOT FOUND in the upload loop

            result = _convert_to_parquet(local, tmpdir)
            if result is not None:
                stem = Path(entry.remote).stem
                converted[stem] = (result, local, entry.remote)
                print(f"  [~] {local.name} -> {result.name}")

        # ── 1b. Cross-file schema assertion per split ──────────────────
        schema_errors = _assert_cross_file_schema(converted, cfg)
        if schema_errors:
            print("\n  \u2717  Cross-file schema assertion FAILED:")
            for e in schema_errors:
                print(f"     {e}")
            print()
            return 1

        # ── 1c. Large-value check on converted Parquet files ───────────
        for _stem, (_parquet_path, _csv_path, _orig_remote) in converted.items():
            large_warnings = _check_large_values(_parquet_path)
            for w in large_warnings:
                print(f"  \u26a0  {w}")

        # ── 2. Compliance generation (reads Parquet when available) ─────
        print("  [i] Building schema report \u2026")
        schema = build_schema_report(
            cfg,
            csv_delimiter=cfg.csv_delimiter,
            csv_encoding=cfg.csv_encoding,
            staging_dir=tmpdir if converted else None,
        )

        recipe_content: str | None = None
        if cfg.recipe:
            recipe_path = Path(cfg.recipe)
            if recipe_path.exists():
                recipe_content = recipe_path.read_text(encoding="utf-8")

        print("  [i] Generating Dataset Card \u2026")
        card = build_dataset_card(cfg, schema, recipe_content=recipe_content)
        print("  [i] Generating LICENSE \u2026")
        license_text = build_license_file(cfg.license)

        (tmpdir / "README.md").write_text(card, encoding="utf-8")
        (tmpdir / "LICENSE").write_text(license_text, encoding="utf-8")

        # ── 2b. load_dataset() verification (optional) ────────────────────
        verification: VerificationReport | None = None
        if verify_load:
            verification = verify_load_dataset(tmpdir, cfg)
            _print_verification_report(verification)

        # ── If dry-run with verify_load: stop here ────────────────────────
        if dry_run:
            simulated = existing_files + planned_remotes
            report = detect_splits(simulated)
            _print_split_report(report)
            print(f"\n{'=' * 60}")
            print("  Dry-run complete — no files uploaded.")
            if verify_load:
                status = "passed" if verification and verification.passed else "failed"
                print(f"  Verification: {status}")
            print(f"{'=' * 60}\n")
            return 0

        # Upload compliance files (respect overwrite protection)
        if "readme.md" not in protected:
            _hf_upload(cfg.repo_id, tmpdir / "README.md", "README.md", cfg.repo_type)
        if "license" not in protected:
            _hf_upload(cfg.repo_id, tmpdir / "LICENSE", "LICENSE", cfg.repo_type)

        # ── 3. Upload data files ────────────────────────────────────────
        ok = 0
        fail = 0

        for entry in cfg.files:
            local = entry.resolve(base)
            remote = entry.remote

            if not local.exists():
                print(f"  \u2717  NOT FOUND: {local}")
                fail += 1
                continue

            # Determine if this entry was converted to Parquet
            entry_stem = Path(entry.remote).stem
            is_converted = entry_stem in converted and not entry.recursive

            if is_converted:
                parquet_path, csv_path, original_remote = converted[entry_stem]
                parquet_remote = f"{entry_stem}.parquet"

                # Upload the Parquet version (from staging dir)
                if _hf_upload(cfg.repo_id, parquet_path, parquet_remote, cfg.repo_type):
                    ok += 1
                else:
                    fail += 1

                # If keep_csv, also upload the original CSV
                if keep_csv:
                    if _hf_upload(cfg.repo_id, csv_path, original_remote, cfg.repo_type):
                        ok += 1
                    else:
                        fail += 1
            else:
                # Upload original file (CSV with upload_as_csv, .parquet, or other)
                if _hf_upload(cfg.repo_id, local, remote, cfg.repo_type):
                    ok += 1
                else:
                    fail += 1

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # ── 4. Post-upload split report ────────────────────────────────────
    updated_files = _inspect_repo(cfg)
    if updated_files:
        report = detect_splits(updated_files)
        _print_split_report(report)

    # ── 4b. Upload summary with warnings ───────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  Result: {ok} uploaded, {fail} failed")

    if verify_load and verification is not None:
        status = "\u2713  PASSED" if verification.passed else "\u2717  FAILED"
        print(f"  load_dataset() verification: {status}")

    print(f"{'=' * 60}\n")
    return 0 if fail == 0 else 1


def _print_split_report(report: object) -> None:
    """Print a human-readable split detection summary."""
    from .splits import SplitReport

    if not isinstance(report, SplitReport):
        return

    if not report.splits:
        return

    print("\n  Split detection:")
    for s in report.splits:
        print(f"    [{s.name}] {len(s.files)} file(s)")
        for f in s.files[:5]:
            print(f"      - {f}")
        if len(s.files) > 5:
            print(f"      … and {len(s.files) - 5} more")

    if report.unclassified:
        print(f"    [?] {len(report.unclassified)} file(s) unclassified")

    for w in report.warnings:
        print(f"    ⚠  {w}")

    # Layout validation
    layout_warnings = validate_layout(
        [f for s in report.splits for f in s.files] + report.unclassified
    )
    for w in layout_warnings:
        print(f"    ⚠  {w}")


def _print_split_mapping_validation(remotes: list[str]) -> None:
    """Print split mapping compatibility warnings for the planned upload."""
    mapping_warnings = validate_split_mapping(remotes)
    if mapping_warnings:
        print("\n  Split mapping validation:")
        for w in mapping_warnings:
            print(f"    ⚠  {w}")
