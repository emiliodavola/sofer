"""
Command-line interface for data-uploader.

Every command is self-documenting via ``--help``.
Run ``data-uploader --help`` or ``data-uploader <command> --help``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from ._formats import SUPPORTED_FORMATS
from .checks import DatasetValidator
from .codebook import generate as generate_codebook
from .model import DatasetConfig
from .quality import QualityValidator
from .scanner import (
    EXCLUSIONS,
    copy_files,
    discover_files,
    merge_entries,
    write_toml,
)
from .uploader import upload as run_upload

# ── command implementations ────────────────────────────────────────────


def _cmd_validate(args: argparse.Namespace) -> int:
    cfg = DatasetConfig.from_toml(args.config)

    # validate the configuration itself
    config_errors = cfg.validate()
    if config_errors:
        print("\n  X  Configuration errors:")
        for e in config_errors:
            print(f"     X  {e}")
        return 1

    # validate the actual data on disk
    validator = DatasetValidator(cfg)
    report = validator.run_all()

    # quality checks
    quality = QualityValidator(cfg)
    quality_report = quality.run()
    report.quality_results = quality_report.quality_results

    report.print_summary()
    return 0 if report.passed else 1


def _cmd_upload(args: argparse.Namespace) -> int:
    cfg = DatasetConfig.from_toml(args.config)

    config_errors = cfg.validate()
    if config_errors:
        print("\n  \u2717  Configuration errors \u2014 fix before uploading:")
        for e in config_errors:
            print(f"     \u2717  {e}")
        return 1

    validator = DatasetValidator(cfg)
    report = validator.run_all()

    # quality checks
    quality = QualityValidator(cfg)
    quality_report = quality.run()
    report.quality_results = quality_report.quality_results

    return run_upload(
        cfg,
        keep_csv=args.keep_csv,
        force=args.force,
        dry_run=args.dry_run,
        verify_load=args.verify_load,
        quality_report=report,
    )


def _cmd_codebook(args: argparse.Namespace) -> int:
    codebook = generate_codebook(
        args.csv,
        output_path=args.output,
        max_sample=args.max_sample,
    )
    if not args.output:
        print(codebook)
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    """Discover data files, register them in TOML, and copy to ``data/``."""
    config_path = Path(args.config).resolve()

    if not config_path.exists():
        print(f"  X  Config file not found: {config_path}", file=sys.stderr)
        return 1

    # 1. Load raw TOML.
    try:
        import tomli as _tomli
    except ImportError:
        import tomllib as _tomli

    try:
        with open(config_path, "rb") as fh:
            raw_toml = _tomli.load(fh)
    except Exception as exc:
        print(f"  X  Failed to read TOML: {exc}", file=sys.stderr)
        return 1

    base_dir = config_path.parent.resolve()
    data_dir = base_dir / "data"

    # 2. Discover supported files (exclude data/ destination directory).
    extensions = args.ext if args.ext else None
    exclude = EXCLUSIONS | frozenset({"data"})
    discovered = discover_files(base_dir, extensions, exclude_dirs=exclude)

    if not discovered:
        print("  OK  No supported files found.")
        return 0

    # 3. Merge new entries into the raw TOML dict.
    before_count = len(raw_toml.get("file", []))
    raw_toml = merge_entries(discovered, raw_toml, base_dir, data_dir)
    after_count = len(raw_toml.get("file", []))
    new_count = after_count - before_count

    print(f"  OK  Discovered {len(discovered)} supported file(s).")
    if new_count:
        print(f"  OK  Registered {new_count} new [[file]] entry(s).")
    else:
        print("  OK  All discovered files already registered (idempotent).")

    # 4. Confirm with the user before copying (unless --force or --dry-run).
    if not args.dry_run and not args.force:
        print("\n  The following files will be copied to data/:")
        for f in discovered:
            print(f"     → data/{f.relative_to(base_dir)}")
        answer = input("\n  Continue? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("  OK  Aborted.")
            return 0

    # 5. Copy files to data/.
    try:
        copied = copy_files(discovered, base_dir, data_dir, dry_run=args.dry_run, force=args.force)
    except FileExistsError as exc:
        print(f"  X  {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("  DRY RUN  Would copy the following files:")
        for _src, dest in copied:
            print(f"     → {dest.relative_to(base_dir)}")
    else:
        for _src, dest in copied:
            print(f"     OK  {dest.relative_to(base_dir)}")

    # 6. Write TOML (skip on dry-run — no disk mutation at all).
    if not args.dry_run:
        try:
            write_toml(raw_toml, config_path)
            print(f"  OK  Updated {config_path.name}")
        except Exception as exc:
            print(f"  X  Failed to write TOML: {exc}", file=sys.stderr)
            return 1

    return 0


_INIT_TEMPLATE = """\
# Configuration for: {name}
# Generated by ``data-uploader init {name}``
#
# Usage:
#   data-uploader validate {name}.toml
#   data-uploader upload   {name}.toml

[dataset]
name = "{name}"
repo_id = "YOUR_USER/{name}"
repo_type = "dataset"
private = true

[meta]
description = "TODO: short description"
license = "TODO: MIT / restricted / …"
confidential = false
source = "TODO: organisation name"
tags = ["TODO: tag1", "TODO: tag2"]

# Repeat [[file]] sections for every file/directory you want to upload.
[[file]]
local = "TODO: path/to/file.csv"
remote = "file.csv"

[[file]]
local = "TODO: path/to/directory/"
remote = "subfolder/"
recursive = true

# Optional data-sharing documentation (recommended):
# [meta]
# language = ["en"]
# pretty_name = "TODO: human-readable name"
# task_categories = ["tabular-classification"]
# size_categories = "1K<n<10K"
# citation = "TODO: BibTeX or citation"
# collection_method = "TODO: survey / admin / sensor / ..."
# csv_delimiter = ";"
# readme = "README.md"
# codebook = "codebook.md"
# study_design = "study_design.md"
# recipe = "recipe.R"

# Validation thresholds (adjust as needed).
[[check]]
min_files = 1
min_total_size_mb = 0.0

# Verify that a CSV has the expected columns.
# [[check]]
# columns = "file.csv"
# expected = ["col_a", "col_b", "col_c"]

# Quality checks run automatically with sensible defaults.
# Uncomment and customise to override severity or thresholds:
# [[quality]]
# check = "duplicates"
# severity = "fail"
#
# [[quality]]
# check = "null_profiling"
# max_null_pct = 15.0
# columns = ["age", "income"]
#
# [[quality]]
# check = "value_range"
# columns = ["age"]
# min = 0
# max = 120
"""


def _cmd_init(args: argparse.Namespace) -> int:
    """Write a ready-to-edit TOML template to disk."""
    output = Path(f"{args.name}.toml")
    if output.exists():
        print(f"  X  File already exists: {output}")
        return 1
    output.write_text(_INIT_TEMPLATE.format(name=args.name), encoding="utf-8")
    print(f"  OK  Created {output}")
    print("     Edit the file and run:")
    print(f"       data-uploader validate {output.name}")
    print(f"       data-uploader upload   {output.name}")
    return 0


# ── argument parser ───────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-uploader",
        description=(
            "Publish datasets to Hugging Face Hub with built-in validation.\n"
            "\n"
            "Every dataset is configured via a TOML file.  Run:\n"
            "  data-uploader init my-dataset     # create a template\n"
            "  data-uploader validate dataset.toml  # check data locally\n"
            "  data-uploader upload dataset.toml    # upload to HF"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"data-uploader v{__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── validate ──────────────────────────────────────────────────
    v = sub.add_parser(
        "validate",
        help="Check that the local data matches the TOML configuration.",
        description=(
            "Read a TOML configuration, verify that every file exists, "
            "check minimum size and column requirements, and print "
            "a validation report.  Does NOT contact Hugging Face."
        ),
    )
    v.add_argument("config", help="Path to the .toml configuration file.")
    v.set_defaults(func=_cmd_validate)

    # ── upload ────────────────────────────────────────────────────
    u = sub.add_parser(
        "upload",
        help="Validate the dataset, then upload everything to HF.",
        description=(
            "Run all validations first; abort if any check fails. "
            "On success, upload every declared file to the HF repository. "
            "The repository is created automatically if it doesn't exist."
        ),
    )
    u.add_argument("config", help="Path to the .toml configuration file.")
    u.add_argument(
        "--keep-csv",
        action="store_true",
        help="Upload the original CSV alongside the converted Parquet",
    )
    u.add_argument(
        "--force",
        action="store_true",
        help="Skip README.md / LICENSE overwrite confirmation and overwrite unconditionally.",
    )
    u.add_argument(
        "--dry-run",
        action="store_true",
        help="Show repo diff and split report without uploading any files.",
    )
    u.add_argument(
        "--verify-load",
        action="store_true",
        help="Test end-to-end loadability with datasets.load_dataset() after staging.",
    )
    u.set_defaults(func=_cmd_upload)

    # ── codebook ──────────────────────────────────────────────────
    c = sub.add_parser(
        "codebook",
        help="Generate a markdown codebook from a CSV file.",
        description=(
            "Analyse a CSV file and produce a human-readable codebook "
            "that lists every column, its inferred type, unique count, "
            "missing percentage, and a sample value."
        ),
    )
    c.add_argument("csv", help="Path to the CSV file.")
    c.add_argument(
        "-o",
        "--output",
        help="Output file path (default: print to stdout).",
    )
    c.add_argument(
        "--max-sample",
        type=int,
        default=100_000,
        help="Maximum rows to sample for analysis (default: 100 000).",
    )
    c.set_defaults(func=_cmd_codebook)

    # ── init ──────────────────────────────────────────────────────
    i = sub.add_parser(
        "init",
        help="Create a ready-to-edit TOML configuration template.",
        description=(
            "Generate a `.toml` file with all the required structure "
            "and placeholder values.  Edit it to match your data, then "
            "run ``data-uploader validate``."
        ),
    )
    i.add_argument("name", help="Short name for the dataset.")
    i.set_defaults(func=_cmd_init)

    # ── scan ───────────────────────────────────────────────────────
    s = sub.add_parser(
        "scan",
        help="Discover data files and register them in the TOML config.",
        description=(
            "Recursively scan the config file's directory for supported "
            "data formats (.csv, .tsv, .parquet, .xlsx, .jsonl), register "
            "new files as [[file]] entries in the TOML, and copy them into "
            "the data/ directory preserving subdirectory structure.\n"
            "\n"
            "Running scan twice is safe — already-registered files are "
            "skipped."
        ),
    )
    s.add_argument(
        "config",
        nargs="?",
        default="dataset.toml",
        help="Path to the .toml configuration file (default: dataset.toml).",
    )
    s.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done without modifying the disk or TOML.",
    )
    s.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files in data/ without raising an error.",
    )
    s.add_argument(
        "--ext",
        action="append",
        choices=list(SUPPORTED_FORMATS.keys()),
        help="Only scan for files with these extensions (repeatable). "
        "When omitted, all supported formats are included.",
    )
    s.set_defaults(func=_cmd_scan)

    return parser


def main() -> None:
    """Entry point (installed via ``pyproject.toml [project.scripts]``)."""
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
