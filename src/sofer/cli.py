"""
Command-line interface for sofer.

Every command is self-documenting via ``--help``.
Run ``sofer --help`` or ``sofer <command> --help``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import config
from ._formats import SUPPORTED_FORMATS
from ._version import get_version
from .checks import DatasetValidator, ValidationReport
from .codebook import generate as generate_codebook
from .codebook import generate_all as generate_all_codebooks
from .model import DatasetConfig
from .prepare import prepare as run_prepare
from .prepare import resolve_output_dir
from .profile import profile as run_profile
from .publish import publish as run_publish
from .quality import QualityValidator
from .render import render as run_render
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

    # Resolve the --max-sample default through the config module at call
    # time (post-reload), never from a frozen argparse default.
    max_sample = args.max_sample if args.max_sample is not None else config.CODEBOOK_MAX_SAMPLE

    codebook = generate_codebook(
        args.csv,
        output_path=args.output,
        max_sample=max_sample,
    )
    if not args.output:
        print(codebook)
    return 0


def _cmd_profile(args: argparse.Namespace) -> int:
    """Profile a dataset read-only and write a ``metadata.yaml`` document.

    Orchestration (delegated to :func:`sofer.profile.profile`):

        1. Detect the dataset format from its extension
           (``sofer._formats.SUPPORTED_FORMATS``).
        2. Read the dataset: CSV/TSV via ``stream_csv`` (bounded, encoding
           fallback, config delimiter/encoding); Parquet/XLSX/JSONL via
           ``codebook._read_file``.
        3. Infer a coarse storage type, a semantic type (email), and a PII
           flag per column.
        4. Assemble and write ``metadata.yaml`` next to the dataset (or to
           ``--output`` DIR when given).
        5. Report the missing human-input fields (description, license,
           source, column descriptions).

    The source dataset is never modified (PRF-03). Returns the exit code from
    :func:`sofer.profile.profile` (0 on success, 1 on unsupported format).
    """
    return run_profile(
        Path(args.dataset),
        output_dir=Path(args.output) if args.output else None,
    )


def _cmd_render(args: argparse.Namespace) -> int:
    """Render a status-annotated ``README.md`` from a ``metadata.yaml`` document.

    Orchestration (delegated to :func:`sofer.render.render`):

        1. Resolve ``metadata.yaml`` from the ``<package>`` argument — either
           the file itself or the directory containing it (RND-01).
        2. Load the document and project it into ``README.md`` markdown
           without recomputing any inference (RND-02).
        3. Write ``README.md`` next to ``metadata.yaml`` (or to ``--output``
           DIR when given).

    Inference states are rendered distinctly (RND-03): ``confirmed`` as a plain
    label, ``inferred`` as ``<type> (inferred, NN%)``, and ``unknown`` as
    ``unknown``. Returns the exit code from :func:`sofer.render.render`
    (0 on success, 1 when no ``metadata.yaml`` is found).
    """
    return run_render(
        Path(args.package),
        output_dir=Path(args.output) if args.output else None,
    )


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
    data_dir = base_dir / config.OUTPUT_DIR

    # 2. Discover supported files (exclude cache/ destination directory).
    extensions = args.ext if args.ext else None
    exclude = EXCLUSIONS | frozenset({config.OUTPUT_DIR})
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
        print(f"\n  The following files will be copied to {config.OUTPUT_DIR}/:")
        for f in discovered:
            flat = flatten_first_level(f.relative_to(base_dir))
            print(f"     → {config.OUTPUT_DIR}/{flat.as_posix()}")
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
#
# Source files -> raw/ (scan copies to cache/)

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

# Source files -> raw/ (scan copies to cache/)
# Repeat [[file]] sections for every file/directory you want to publish.
[[file]]
local = "TODO: raw/file.csv"
remote = "file.csv"

[[file]]
local = "TODO: raw/directory/"
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
    """Write a ready-to-edit TOML template and scaffold ``raw/``.

    Orchestration:

        1. ``mkdir -p RAW_DIR`` idempotently (``exist_ok=True``) before the
           TOML write — skipped only when ``--move-existing --dry-run`` is
           active (preview, no mutation).
        2. When ``--move-existing`` is set: collect depth-1 supported files
           (``SUPPORTED_FORMATS``, direct children of ``cwd``), run
           :func:`check_flatten_collisions` against existing ``raw/`` content
           before any move, honour ``--dry-run`` (preview, no ``raw/`` mkdir
           when absent, no moves), ``--force`` / ``not isatty`` guard (skip
           prompt), else prompt ``[y/N]`` and abort on ``N``, then
           :func:`shutil.move` each file into ``RAW_DIR``.
    """
    output = Path(f"{args.name}.toml")
    if output.exists():
        print(f"  X  File already exists: {output}")
        return 1

    raw_dir_name: str = config.RAW_DIR
    raw_dir_path = Path.cwd() / raw_dir_name
    move_existing: bool = bool(getattr(args, "move_existing", False))
    dry_run: bool = bool(getattr(args, "dry_run", False))
    force: bool = bool(getattr(args, "force", False))

    if not move_existing:
        # Always scaffold raw/ idempotently before TOML write (CLI-R07).
        raw_dir_path.mkdir(parents=True, exist_ok=True)
        output.write_text(_INIT_TEMPLATE.format(name=args.name), encoding="utf-8")
        print(f"  OK  Created {output}")
        print("     Edit the file and run:")
        print(f"       sofer prepare {output.name}")
        print(f"       sofer publish {output.name}")
        return 0

    # --move-existing: collect depth-1 SUPPORTED_FORMATS files in cwd.
    candidates: list[Path] = []
    for entry in Path.cwd().iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in SUPPORTED_FORMATS:
            continue
        if entry.name == output.name:
            continue
        # Exclude the template's own TOML name and already-tracked raw reuse;
        # top-level files inside cache/build/raw are not iterdir children, but
        # guard against a file literally named like those dirs (e.g. "cache").
        candidates.append(entry.resolve())
    candidates.sort()

    # Pre-move collision check against existing raw/ content.
    if candidates:
        existing: list[Path] = []
        if raw_dir_path.exists():
            for q in raw_dir_path.rglob("*"):
                if q.is_file() and q.suffix.lower() in SUPPORTED_FORMATS:
                    existing.append(q.resolve())
        base_dir = Path.cwd().resolve()
        try:
            check_flatten_collisions(candidates + existing, base_dir)
        except ValueError as exc:
            print(f"  X  {exc}", file=sys.stderr)
            return 1

    if dry_run:
        if candidates:
            print("  DRY RUN  Would move the following files:")
            for src in candidates:
                print(f"     {src.name} -> {raw_dir_name}/{src.name}")
        else:
            print("  DRY RUN  No supported files to move.")
        # Preview only: no raw/ mkdir when absent, no moves.
        output.write_text(_INIT_TEMPLATE.format(name=args.name), encoding="utf-8")
        print(f"  OK  Created {output}")
        print("     Edit the file and run:")
        print(f"       sofer prepare {output.name}")
        print(f"       sofer publish {output.name}")
        return 0

    # Non-dry-run move_existing: honour --force / isatty guard.
    is_tty = sys.stdin.isatty()
    if candidates and not force and not is_tty:
        print(
            "  !  Skipping move of existing files (non-interactive). Use --force to move.",
            file=sys.stderr,
        )
        raw_dir_path.mkdir(parents=True, exist_ok=True)
        output.write_text(_INIT_TEMPLATE.format(name=args.name), encoding="utf-8")
        print(f"  OK  Created {output}")
        print("     Edit the file and run:")
        print(f"       sofer prepare {output.name}")
        print(f"       sofer publish {output.name}")
        return 0

    if candidates and not force and is_tty:
        print(f"\n  The following files will be moved to {raw_dir_name}/:")
        for src in candidates:
            print(f"     {src.name} -> {raw_dir_name}/{src.name}")
        try:
            answer = input("\n  Continue? [y/N] ").strip().lower()
        except EOFError:
            answer = "n"
        if answer not in ("y", "yes"):
            print("  OK  Aborted move.")
            raw_dir_path.mkdir(parents=True, exist_ok=True)
            output.write_text(_INIT_TEMPLATE.format(name=args.name), encoding="utf-8")
            print(f"  OK  Created {output}")
            print("     Edit the file and run:")
            print(f"       sofer prepare {output.name}")
            print(f"       sofer publish {output.name}")
            return 0

    # Proceed: scaffold raw/ then move.
    raw_dir_path.mkdir(parents=True, exist_ok=True)
    output.write_text(_INIT_TEMPLATE.format(name=args.name), encoding="utf-8")
    print(f"  OK  Created {output}")
    for src in candidates:
        dest = raw_dir_path / src.name
        shutil.move(str(src), str(dest))
        print(f"     moved {src.name} -> {raw_dir_name}/{src.name}")
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
        version=f"sofer v{get_version()}",
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
            "local machine: universal csv/tsv/xlsx/jsonl → normalized Parquet "
            "conversion (Excel → one Parquet per sheet), cross-file schema "
            "checks, a schema report, the Dataset Card (README.md) and "
            "LICENSE, and - with --all-files - codebooks.  Set "
            "convert_to_parquet=false per [[file]] to keep the original.  This "
            "command never contacts Hugging Face and needs no credentials.\n"
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
        help=(
            "Upload the original CSV alongside the converted Parquet "
            "(hf target only; CSV-only, ignored for tsv/xlsx/jsonl)."
        ),
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
        default=None,
        help=(
            "Maximum rows to sample for analysis (default: codebook_max_sample from [tool.sofer])."
        ),
    )
    c.add_argument(
        "--all-files",
        action="store_true",
        help="Generate codebooks for every [[file]] entry in the TOML config.",
    )
    c.add_argument(
        "--config",
        default=config.DEFAULT_CONFIG_NAME,
        help=(
            "Path to the TOML config file used with --all-files (default: "
            "default_config_name from [tool.sofer])."
        ),
    )
    c.set_defaults(func=_cmd_codebook)

    # ── profile ──────────────────────────────────────────────────
    prf = sub.add_parser(
        "profile",
        help="Profile a dataset read-only and write a metadata.yaml document.",
        description=(
            "Introspect a dataset file (CSV, TSV, Parquet, Excel, or JSON "
            "Lines) read-only and generate a metadata.yaml document that "
            "records the detected schema, per-column semantic types, and "
            "possible PII findings.  The source dataset is never modified.\n"
            "\n"
            "metadata.yaml is written next to the dataset by default, or to "
            "--output DIR when given.  Missing human-input fields "
            "(description, license, source, and column descriptions) are "
            "reported after the document is written."
        ),
    )
    prf.add_argument(
        "dataset",
        help="Path to the dataset file to profile (CSV, TSV, Parquet, Excel, or JSON Lines).",
    )
    prf.add_argument(
        "--output",
        help="Output directory for metadata.yaml (default: the dataset's directory).",
    )
    prf.set_defaults(func=_cmd_profile)

    # ── render ──────────────────────────────────────────────────
    rnd = sub.add_parser(
        "render",
        help="Render a README.md from a metadata.yaml document.",
        description=(
            "Read a metadata.yaml document and render a status-annotated "
            "README.md from its contents.  The <package> argument is either "
            "the metadata.yaml file itself or the directory containing it.\n"
            "\n"
            "Inference states are rendered distinctly: confirmed as a plain "
            "label, inferred as '<type> (inferred, NN%)' with the confidence "
            "percentage, and unknown as 'unknown'.  README.md is written next "
            "to metadata.yaml by default, or to --output DIR when given.  The "
            "metadata.yaml is never modified."
        ),
    )
    rnd.add_argument(
        "package",
        help="Path to metadata.yaml, or the directory containing it.",
    )
    rnd.add_argument(
        "--output",
        help="Output directory for README.md (default: the metadata.yaml directory).",
    )
    rnd.set_defaults(func=_cmd_render)

    # ── init ──────────────────────────────────────────────────────
    i = sub.add_parser(
        "init",
        help="Create a ready-to-edit TOML configuration template and scaffold raw/.",
        description=(
            "Generate a `.toml` file with all the required structure "
            "and placeholder values (Source files -> raw/ (scan copies to cache/)) "
            "and scaffold the raw/ source directory (mkdir -p raw/, idempotent).\n"
            "\n"
            "With --move-existing: move depth-1 supported files "
            "(.csv, .tsv, .parquet, .xlsx, .jsonl) from the current directory "
            "into raw/; files inside cache/, build/, raw/, or EXCLUSIONS are "
            "never moved, subdirectories are ignored, and collisions with "
            "existing raw/ content are checked via check_flatten_collisions "
            "before any move. --dry-run previews moves without mutation "
            "(raw/ not created when absent); --force or non-interactive "
            "(not isatty) skips the [y/N] prompt, else prompt aborts on N.\n"
            "\n"
            "Pipeline: raw/ (tracked) -> cache/ (OUTPUT_DIR, gitignored) "
            "-> build/ (gitignored); scan flattens raw/DPTO.csv -> cache/DPTO.csv "
            "via flatten_first_level."
        ),
    )
    i.add_argument("name", help="Short name for the dataset.")
    i.add_argument(
        "--move-existing",
        action="store_true",
        help=(
            "Move depth-1 supported files (.csv, .tsv, .parquet, .xlsx, .jsonl) "
            "from the current directory into raw/ (SUPPORTED_FORMATS, direct "
            "children only, excluding cache/build/raw/EXCLUSIONS; "
            "check_flatten_collisions before any move)."
        ),
    )
    i.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview moves (a.csv -> raw/a.csv) without creating raw/ or moving files.",
    )
    i.add_argument(
        "--force",
        action="store_true",
        help="Skip the [y/N] prompt and move without confirmation (also skipped when not isatty).",
    )
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
        default=config.DEFAULT_CONFIG_NAME,
        help=(
            "Path to the .toml configuration file (default: default_config_name from [tool.sofer])."
        ),
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
    """Entry point (installed via ``pyproject.toml [project.scripts]``).

    Orchestration:

        1. Phase-0 bootstrap: resolve ``[tool.sofer]`` anchored on the
           current working directory (``config.reload(None)``) so argparse
           defaults such as ``default_config_name`` reflect cwd-tree
           overrides before the parser is built (TC-07).
        2. Build the parser and dispatch; dataset commands re-resolve via
           ``DatasetConfig.from_toml`` (dataset-dir anchor, TC-04/TC-05).
    """
    config.reload(None)
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
