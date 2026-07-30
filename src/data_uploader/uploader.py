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

import pyarrow.csv as pc
import pyarrow.parquet as pq
from huggingface_hub import HfApi

from .model import DatasetConfig
from .repo_compliance import build_dataset_card, build_license_file, build_schema_report

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
        pq.write_table(table, parquet_path, compression="zstd")
        return parquet_path
    except Exception as exc:
        print(f"  \u26a0  {csv_path.name}: conversion failed \u2014 uploading as CSV")
        print(f"       ({exc})")
        return None


def upload(cfg: DatasetConfig, keep_csv: bool = False) -> int:
    """Upload all files declared in *cfg* to Hugging Face Hub.

    Converts CSV files to Parquet before compliance generation so the schema
    report can read native Parquet types.  Falls back to CSV when conversion
    fails.

    Args:
        cfg:      Dataset configuration.
        keep_csv: When ``True`` and a CSV was converted to Parquet, also
                  upload the original CSV as a secondary file.

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

    _ensure_repo(cfg)

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

        # Upload compliance files first (order matters for HF recognition)
        _hf_upload(cfg.repo_id, tmpdir / "README.md", "README.md", cfg.repo_type)
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

    print(f"\n{'=' * 60}")
    print(f"  Result: {ok} uploaded, {fail} failed")
    print(f"{'=' * 60}\n")
    return 0 if fail == 0 else 1
