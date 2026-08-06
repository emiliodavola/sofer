"""
Command-line interface for sofer.

Every command is self-documenting via ``--help``.
Run ``sofer --help`` or ``sofer <command> --help``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from ._formats import SUPPORTED_FORMATS
from .checks import DatasetValidator, ValidationReport
from .codebook import generate as generate_codebook
from .codebook import generate_all as generate_all_codebooks
from .config import DEFAULT_CONFIG_NAME, OUTPUT_DIR
from .model import DatasetConfig
from .prepare import prepare as run_prepare
from .prepare import resolve_output_dir
from .publish import publish as run_publish
from .quality import QualityValidator
from .scanner import (
    EXCLUSIONS,
    check_flatten_collisions,
    copy_files,
    discover_files,
    flatten_first_level,
    merge_entries,
    write_toml,
)

# ── command implementations ────────────────────────────────────────────


def _load_and_validate(
    args: argparse.Namespace,
    verb: str,
    *,
    run_checks: bool = True,
) -> tuple[DatasetConfig | None, ValidationReport | None]:
    """Load the TOML config and run the structural + quality checks (shared).

    This is the common prologue of ``validate``, ``prepare``, and
    ``publish``: it loads the :class:`DatasetConfig`, validates the
    configuration itself, runs :class:`DatasetValidator`, and (unless
    *run_checks* is ``False``) runs :class:`QualityValidator`, merging its
    results into the report.

    Args:
        args:        Parsed CLI arguments (must expose ``config``).
        verb:        Gerund used in the configuration-error message
                     (e.g. ``"preparing"`` -> "fix before preparing").
        run_checks:  When ``False``, skip the validators entirely
                     (``--no-checks``).

    Returns:
        ``(cfg, report)`` — ``cfg`` is ``None`` (and ``report`` is ``None``)
        when the configuration itself has errors and the caller should exit 1.
    """
    cfg = DatasetConfig.from_toml(args.config)

    config_errors = cfg.validate()
    if config_errors:
        print(f"\n  \u2717  Configuration errors \u2014 fix before {verb}:")
        for e in config_errors:
            print(f"     \u2717  {e}")
        return None, None

    if not run_checks:
        return cfg, None

    validator = DatasetValidator(cfg)
    report = validator.run_all()

    quality = QualityValidator(cfg)
    quality_report = quality.run()
    report.quality_results = quality_report.quality_results
    report.ran_checks = quality_report.ran_checks

    return cfg, report


def _cmd_validate(args: argparse.Namespace) -> int:
    """Validate the local dataset against its TOML configuration and quality checks.

    Runs the shared :func:`_load_and_validate` prologue (config load,
    :class:`DatasetValidator`, :class:`QualityValidator`), prints the
    summary report, and returns 0 when all checks pass, 1 otherwise.
    """
    cfg, report = _load_and_validate(args, verb="checking")
    if cfg is None or report is None:
        return 1

    report.print_summary()
    return 0 if report.passed else 1


def _cmd_prepare(args: argparse.Namespace) -> int:
    """Validate the config, then generate the full dataset package locally.

    Full flow:
        1. Run the shared :func:`_load_and_validate` prologue
           (``--no-checks`` skips the validators — the checks inside
           :func:`sofer.prepare.prepare` are gated by the same flag).
        2. Resolve the output directory (``--output`` or ``[dataset] build_dir``).
        3. Run :func:`sofer.prepare.prepare` — CSV→Parquet conversion,
           cross-file schema assertion, schema report, Dataset Card + LICENSE,
           codebooks (``--all-files``), NOT FOUND report, optional
           ``--verify``.  Zero network calls; ``--force`` allows overwriting
           existing artifacts.
    """
    cfg, _report = _load_and_validate(args, verb="preparing", run_checks=not args.no_checks)
    if cfg is None:
        return 1

    output_dir = resolve_output_dir(cfg, args.output)
    return run_prepare(
        cfg,
        output_dir,
        all_files=args.all_files,
        no_checks=args.no_checks,
        force=args.force,
        verify=args.verify,
    )


def _cmd_publish(args: argparse.Namespace) -> int:
    """Validate the config, then deliver the prepared package to a target.

    Full flow:
        1. Run the shared :func:`_load_and_validate` prologue — the quality
           report it produces is the publish quality gate.
        2. Deliver the prepared package: ``--target hf`` ensures the HF
           repository, gates on the quality report, prints a diff summary,
           and pushes the package in a single ``upload_folder`` call;
           ``--target local`` copies the package to ``--output`` with no
           network access.  Stale or missing artifacts trigger ``prepare``
           automatically; ``--dry-run`` only prints the diff and split
           report.
    """
    cfg, report = _load_and_validate(args, verb="publishing")
    if cfg is None or report is None:
        return 1

    return run_publish(
        cfg,
        target=args.target,
        output_dir=args.output,
        force=args.force,
        keep_csv=args.keep_csv,
        dry_run=args.dry_run,
        quality_report=report,
    )


def _cmd_codebook(args: argparse.Namespace) -> int:
    """Generate a markdown codebook for one file or all files in the config.

    Without ``--all-files``: analyse *FILE* and print the codebook to
    stdout (or write to ``--output``).  With ``--all-files``: read every
    ``[[file]]`` entry from the TOML and write one codebook per file
    under ``cache/codebooks/``, plus a root index.
    """
    if args.all_files:
        if args.csv:
            print(
                "Error: --all-files cannot be used with a positional file argument.",
                file=sys.stderr,
            )
            return 1
        try:
            cfg = DatasetConfig.from_toml(args.config)
        except Exception as exc:
            print(f"Error: Failed to read TOML: {exc}", file=sys.stderr)
            return 1
        validation_errors = cfg.validate()
        if validation_errors:
            for err in validation_errors:
                print(f"Error: {err}", file=sys.stderr)
            return 1
        try:
            generate_all_codebooks(cfg)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    if not args.csv:
        print(
            "Error: Must specify a FILE or use --all-files.",
            file=sys.stderr,
        )
        return 1

    codebook = generate_codebook(
        args.csv,
        output_path=args.output,
        max_sample=args.max_sample,
    )
    if not args.output:
        print(codebook)
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    """Discover data files, register them in TOML, and copy to ``cache/``."""
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
    data_dir = base_dir / OUTPUT_DIR

    # 2. Discover supported files (exclude cache/ destination directory).
    extensions = args.ext if args.ext else None
    exclude = EXCLUSIONS | frozenset({OUTPUT_DIR})
    discovered = discover_files(base_dir, extensions, exclude_dirs=exclude)

    if not discovered:
        print("  OK  No supported files found.")
        return 0

    # 2a. Check for flatten collisions BEFORE any copy or merge.
    try:
        check_flatten_collisions(discovered, base_dir)
    except ValueError as exc:
        print(f"  X  {exc}", file=sys.stderr)
        return 1

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
        print(f"\n  The following files will be copied to {OUTPUT_DIR}/:")
        for f in discovered:
            flat = flatten_first_level(f.relative_to(base_dir))
            print(f"     → {OUTPUT_DIR}/{flat.as_posix()}")
        answer = input("\n  Continue? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("  OK  Aborted.")
            return 0

    # 5. Copy files to cache/.
    try:
        copied = copy_files(discovered, base_dir, data_dir, dry_run=args.dry_run, force=args.force)
    except FileExistsError as exc:
        print(f"  X  {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("  DRY RUN  Would copy the following files:")
        for _src, dest in copied:
            print(f"     → {dest.relative_to(base_dir).as_posix()}")
    else:
        for _src, dest in copied:
            print(f"     OK  {dest.relative_to(base_dir).as_posix()}")

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
# Generated by ``sofer init {name}``
#
# Usage:
#   sofer prepare {name}.toml   # generate the package locally (build/)
#   sofer publish {name}.toml   # deliver to HF Hub or a local dir
#   sofer validate {name}.toml  # check data integrity + quality

[dataset]
name = "{name}"
repo_id = "YOUR_USER/{name}"
repo_type = "dataset"
private = true
build_dir = "build"

[meta]
description = "TODO: short description"
license = "TODO: MIT / restricted / …"
confidential = false
source = "TODO: organisation name"
tags = ["TODO: tag1", "TODO: tag2"]

# Repeat [[file]] sections for every file/directory you want to publish.
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
    print(f"       sofer prepare {output.name}")
    print(f"       sofer publish {output.name}")
    return 0


# ── argument parser ───────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sofer",
        description=(
            "Prepare and publish datasets to Hugging Face Hub with built-in "
            "validation.\n"
            "\n"
            "Every dataset is configured via a TOML file.  Run:\n"
            "  sofer init my-dataset      # create a template\n"
            "  sofer prepare dataset.toml # generate the package locally (build/)\n"
            "  sofer publish dataset.toml # deliver to HF Hub or a local dir"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"sofer v{__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── validate ──────────────────────────────────────────────────
    v = sub.add_parser(
        "validate",
        help="Check that the local data matches the TOML configuration and passes quality checks.",
        description=(
            "Read a TOML configuration, verify that every file exists, "
            "check minimum size and column requirements, run streaming "
            "quality checks (duplicates, nulls, encoding, corrupt rows, "
            "and more), and print a validation report.  Does NOT contact "
            "Hugging Face."
        ),
    )
    v.add_argument("config", help="Path to the .toml configuration file.")
    v.set_defaults(func=_cmd_validate)

    # ── prepare ───────────────────────────────────────────────────
    p = sub.add_parser(
        "prepare",
        help="Generate the full dataset package locally (Parquet, card, LICENSE, codebooks).",
        description=(
            "Generate every artifact that makes up a dataset package on the "
            "local machine: CSV-to-Parquet conversion, cross-file schema "
            "checks, a schema report, the Dataset Card (README.md) and "
            "LICENSE, and - with --all-files - codebooks.  This command "
            "never contacts Hugging Face and needs no credentials.\n"
            "\n"
            "Artifacts are written to --output DIR (default: the dataset's "
            "[dataset] build_dir, usually build/).  Existing generated "
            "artifacts block the run unless --force is given."
        ),
    )
    p.add_argument("config", help="Path to the .toml configuration file.")
    p.add_argument(
        "--output",
        help="Output directory (default: [dataset] build_dir from the TOML, usually build/).",
    )
    p.add_argument(
        "--all-files",
        action="store_true",
        help="Also generate per-file codebooks directly into the output directory.",
    )
    p.add_argument(
        "--no-checks",
        action="store_true",
        help=(
            "Skip the structural and quality validation report "
            "(checks run by default, non-blocking)."
        ),
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing generated artifacts in the output directory.",
    )
    p.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Run datasets.load_dataset() against the generated package and "
            "print PASSED/FAILED (non-blocking)."
        ),
    )
    p.set_defaults(func=_cmd_prepare)

    # ── publish ───────────────────────────────────────────────────
    pb = sub.add_parser(
        "publish",
        help="Deliver a prepared dataset package to Hugging Face Hub or a local directory.",
        description=(
            "Deliver the prepared dataset package to --target.  The default "
            "target 'hf' ensures the repository exists, gates on the quality "
            "report, prints a diff summary, and pushes the package in a "
            "single upload_folder call.  The 'local' target copies the "
            "package to --output with no network access (default: the "
            "package stays in place).  Missing or stale artifacts trigger "
            "prepare first; --dry-run prints the diff and split report "
            "without preparing, copying, or touching the network."
        ),
    )
    pb.add_argument("config", help="Path to the .toml configuration file.")
    pb.add_argument(
        "--target",
        choices=["hf", "local"],
        default="hf",
        help=(
            "Delivery target: 'hf' (Hugging Face Hub, default) or 'local' "
            "(copy the package to --output)."
        ),
    )
    pb.add_argument(
        "--output",
        help=(
            "hf: override the prepare output directory (default: the "
            "dataset's [dataset] build_dir).  local: destination directory "
            "for the package copy."
        ),
    )
    pb.add_argument(
        "--force",
        action="store_true",
        help="Skip overwrite protection and overwrite remote files unconditionally.",
    )
    pb.add_argument(
        "--keep-csv",
        action="store_true",
        help="Upload the original CSV alongside the converted Parquet (hf target only).",
    )
    pb.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the repo diff and split report without preparing or uploading.",
    )
    pb.set_defaults(func=_cmd_publish)

    # ── codebook ──────────────────────────────────────────────────
    c = sub.add_parser(
        "codebook",
        help="Generate a markdown codebook from a data file.",
        description=(
            "Analyse a data file (CSV, TSV, Parquet, Excel, or JSON Lines) "
            "and produce a human-readable codebook that lists every column, "
            "its inferred type, unique count, missing percentage, "
            "and a sample value.\n"
            "\n"
            "Use --all-files to generate one codebook per [[file]] entry "
            "in the TOML configuration, written under cache/codebooks/."
        ),
    )
    c.add_argument(
        "csv",
        nargs="?",
        metavar="FILE",
        help="Path to the data file (CSV, TSV, Parquet, Excel, or JSON Lines).",
    )
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
    c.add_argument(
        "--all-files",
        action="store_true",
        help="Generate codebooks for every [[file]] entry in the TOML config.",
    )
    c.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help="Path to the TOML config file (used with --all-files, default: dataset.toml).",
    )
    c.set_defaults(func=_cmd_codebook)

    # ── init ──────────────────────────────────────────────────────
    i = sub.add_parser(
        "init",
        help="Create a ready-to-edit TOML configuration template.",
        description=(
            "Generate a `.toml` file with all the required structure "
            "and placeholder values.  Edit it to match your data, then "
            "run ``sofer validate``."
        ),
    )
    i.add_argument("name", help="Short name for the dataset.")
    i.set_defaults(func=_cmd_init)

    # ── scan ───────────────────────────────────────────────────────
    s = sub.add_parser(
        "scan",
        help=(
            "Discover data files, flatten directory structure, "
            "and register them in the TOML config."
        ),
        description=(
            "Recursively scan the config file's directory for supported "
            "data formats (.csv, .tsv, .parquet, .xlsx, .jsonl), flatten "
            "the first path segment (raw/DPTO.csv → cache/DPTO.csv), register "
            "new files as [[file]] entries in the TOML, and copy them into "
            "the cache/ directory.\n"
            "\n"
            "Running scan twice is safe — already-registered files are "
            "skipped."
        ),
    )
    s.add_argument(
        "config",
        nargs="?",
        default=DEFAULT_CONFIG_NAME,
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
        help="Overwrite existing files in cache/ without raising an error.",
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
