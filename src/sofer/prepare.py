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
and never requires an ``HF_TOKEN``.  Conversion helpers are imported from
``uploader.py`` unchanged and will be moved here when the uploader is
retired (PR 4).
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import DatasetConfig

from ._mirror import copy_to_mirror
from .checks import DatasetValidator
from .codebook import generate_all as generate_all_codebooks
from .config import CODEBOOKS_DIR, DEFAULT_CONFIG_NAME, OUTPUT_ENCODING
from .quality import QualityValidator
from .repo_compliance import (
    build_dataset_card,
    build_license_file,
    build_schema_report,
)
from .uploader import (
    _assert_cross_file_schema,
    _check_large_values,
    _convert_to_parquet,
)
from .verification import _print_verification_report, verify_load_dataset

# Files that count as "generated artifacts" for the PRP-07 overwrite check.
_GENERATED_ROOT_FILES: tuple[str, ...] = ("README.md", "LICENSE", "codebook.md")


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
        schema = build_schema_report(
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
                )
        else:
            print("  [i] Generating Dataset Card \u2026")
            card = build_dataset_card(
                cfg,
                schema,
                recipe_content=recipe_content,
                study_design_content=study_design_content,
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
                f"  i  Run `sofer codebook --all-files --config {DEFAULT_CONFIG_NAME}` "
                f"to generate codebooks.",
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
