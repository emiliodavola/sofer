"""
Command-line interface for sofer.

Every command is self-documenting via ``--help``.
Run ``sofer --help`` or ``sofer <command> --help``.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
from pathlib import Path
from typing import Any, cast

from . import _toml, config, failure_report, mcp_doctor, mcp_registration, meta_edit
from ._formats import SUPPORTED_FORMATS
from ._version import get_version
from .checks import DatasetValidator, ValidationReport, meta_placeholder_warnings
from .codebook import generate as generate_codebook
from .codebook import generate_all as generate_all_codebooks
from .execution_context import resolve_dataset_root, validate_identity
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
    check_raw_collisions,
    collect_init_moves,
    copy_files,
    discover_files,
    format_stale_cache_warning,
    merge_entries,
    move_to_raw,
    registration_path,
    stale_cache_registrations,
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


def _positive_seconds(text: str) -> int:
    """Argparse type for a positive whole number of seconds.

    Used by ``sofer mcp add``'s host-timeout flags (issues #287, #296). A
    non-positive host deadline would make the registered server unusable —
    exactly the failure the flags exist to prevent — so argparse rejects it
    with exit 2 and a usage message instead of writing it into the config.

    Args:
        text: Raw command-line value.

    Returns:
        The parsed positive integer.

    Raises:
        argparse.ArgumentTypeError: When *text* is not a whole number, or is
            less than 1.
    """
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected a whole number of seconds, got {text!r}"
        ) from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be a positive number of seconds, got {value}")
    return value


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
        3. When ``--clean`` is given and delivery succeeded (``fail==0``,
           quality passed, not ``--dry-run``), delete the resolved build
           directory (``resolve_output_dir(cfg, --output)``) and, with
           ``--clean-cache``/``--all``, the tool-wide ``cache/``
           (``cfg._base_dir / config.OUTPUT_DIR``, sibling-shared).
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
        clean=getattr(args, "clean", False),
        clean_cache=getattr(args, "clean_cache", False),
    )


def _cmd_codebook(args: argparse.Namespace) -> int:
    """Generate a markdown codebook for one file or all files in the config.

    Without ``--all-files``: analyse *FILE* and print the codebook to
    stdout (or write to ``--output``).  The resolved tool-wide
    ``config.CSV_DELIMITER`` / ``config.CSV_ENCODING`` are read at call time
    (module-constant reads, resolved by ``main()``'s single ``config.reload``
    before dispatch), so the invocation's ``[tool.sofer]`` values reach
    ``codebook.generate`` — whose dialect parameters are now required keyword
    arguments with no literal default (issue #260) — the
    same source ``sofer_codebook`` uses (MSP-R10).  An unreadable input
    (``ValueError`` from an exhausted encoding chain, ``LookupError`` from an
    unknown codec name) prints ``Error: <message>`` on stderr and returns 1 —
    never an uncaught traceback.  With ``--all-files``: read every
    ``[[file]]`` entry from the TOML and write one codebook per file
    under the package ``build_dir`` (``--output`` overrides it), plus a
    root index — mirroring where ``sofer_codebook_all`` and ``publish``
    collect codebooks.

    ``--delimiter`` / ``--encoding`` are additive overrides (issue #204): when
    supplied they win over the applicable tier (single-file: the tool-wide
    values above; ``--all-files``: the dataset ``[meta]``), and when omitted
    the resolution is exactly today's.  A supplied override is echoed on
    stderr (``_echo_explicit_dialect``).
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
        _echo_explicit_dialect(args)
        try:
            generate_all_codebooks(
                cfg,
                output_dir=resolve_output_dir(cfg, args.output),
                delimiter=getattr(args, "delimiter", None),
                encoding=getattr(args, "encoding", None),
                max_sample=args.max_sample,
            )
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

    # Resolve the delimiter/encoding through the config module at call time,
    # exactly like ``max_sample`` above (TC-04): the single reload in
    # ``main()`` has already run, so these observe this invocation's
    # ``[tool.sofer]`` values — the same source ``sofer_codebook`` passes
    # (MSP-R10).  ``codebook.generate`` now takes the dialect as required
    # keyword arguments (issue #260), so these are the only values it can use;
    # an explicit ``--delimiter`` / ``--encoding`` wins over the configured
    # value (CB-R12).
    delimiter = getattr(args, "delimiter", None)
    if delimiter is None:
        delimiter = config.CSV_DELIMITER
    encoding = getattr(args, "encoding", None)
    if encoding is None:
        encoding = config.CSV_ENCODING

    # Anchor a relative --output to the input file's parent (MSP-R10): the
    # codebook lands next to the analysed file, never in an unrelated cwd.
    output_path = args.output
    if output_path:
        out = Path(output_path)
        if not out.is_absolute():
            out = Path(args.csv).parent / out
        output_path = str(out)

    # Same diagnostic contract as the --all-files sibling above: an unreadable
    # input (decode exhaustion is a ``ValueError``) or an unknown codec name
    # (``LookupError``, reachable while TC-13 accepts any non-empty string)
    # becomes one ``Error: …`` line on stderr with exit 1 — never a traceback.
    _echo_explicit_dialect(args)
    try:
        codebook = generate_codebook(
            args.csv,
            output_path=output_path,
            delimiter=delimiter,
            encoding=encoding,
            max_sample=max_sample,
        )
    except (ValueError, LookupError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if not args.output:
        print(codebook)
    return 0


def _cmd_profile(args: argparse.Namespace) -> int:
    """Profile a dataset read-only and write a ``metadata.yaml`` document.

    Orchestration (delegated to :func:`sofer.profile.profile` / ``generate_all_profiles``):

        1. Single-file (default): detect format, read dataset, infer types/PII,
           assemble ``metadata.yaml`` next to the dataset (or in ``--output``),
           with ``FileExistsError`` guard gated by ``--force`` (PRF-06).
        2. Batch (``--all-files``): load ``[[file]]`` entries from the TOML
           (``DatasetConfig.from_toml``; fail fast when none), derive
           ``rel_stem`` via ``relative_to(data_dir)``/``base_dir`` +
           ``PurePath.suffixes``, write each
           ``<write_root>/profiles/<rel_stem>.metadata.yaml`` via
           ``config.PROFILE_DIR``, write non-colliding first then raise
           ``ValueError`` for collisions, honour Option B ``--output``
           anchoring to ``cfg._base_dir``.

    The source dataset is never modified (PRF-03). Returns the exit code from
    the domain function (0 on success, 1 on error). A missing destination
    guard without ``--force`` surfaces ``FileExistsError`` as exit 1 with a
    ``use --force to overwrite`` hint.

    ``--delimiter`` / ``--encoding`` are additive overrides (issue #204): when
    supplied they win over the resolved ``config.CSV_*`` values, and when
    omitted the resolution is exactly today's.  A supplied override is echoed
    on stderr (``_echo_explicit_dialect``).
    """
    if getattr(args, "all_files", False):
        # Positional ``dataset`` is the TOML path when --all-files is set;
        # --config overrides when explicitly provided.
        config_path_raw = getattr(args, "config", None)
        dataset_raw = getattr(args, "dataset", None)
        # Determine effective TOML path: explicit --config wins when non-default
        toml_arg: str | None = None
        if config_path_raw is not None and str(config_path_raw) != config.DEFAULT_CONFIG_NAME:
            toml_arg = str(config_path_raw)
        elif dataset_raw is not None:
            toml_arg = str(dataset_raw)
        else:
            toml_arg = (
                str(config_path_raw) if config_path_raw is not None else config.DEFAULT_CONFIG_NAME
            )
        try:
            cfg = DatasetConfig.from_toml(toml_arg)
        except Exception as exc:
            print(f"Error: Failed to read TOML: {exc}", file=sys.stderr)
            return 1
        validation_errors = cfg.validate()
        if validation_errors:
            for err in validation_errors:
                print(f"Error: {err}", file=sys.stderr)
            return 1
        if not cfg.files:
            print("Error: No [[file]] entries found in configuration.", file=sys.stderr)
            return 1
        from .profile import generate_all_profiles as _gen_all

        _echo_explicit_dialect(args)
        try:
            _gen_all(
                cfg,
                output_dir=args.output,
                delimiter=getattr(args, "delimiter", None),
                encoding=getattr(args, "encoding", None),
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    if not getattr(args, "dataset", None):
        print("Error: Must specify a dataset file or use --all-files.", file=sys.stderr)
        return 1
    # Anchor a relative --output to the dataset's parent (MSP-R10): the
    # metadata.yaml lands next to the profiled file, never in an unrelated cwd.
    output_dir = Path(args.output) if args.output else None
    if output_dir is not None and not output_dir.is_absolute():
        output_dir = Path(args.dataset).parent / output_dir
    _echo_explicit_dialect(args)
    try:
        return run_profile(
            Path(args.dataset),
            output_dir=output_dir,
            force=bool(getattr(args, "force", False)),
            delimiter=getattr(args, "delimiter", None),
            encoding=getattr(args, "encoding", None),
        )
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _cmd_render(args: argparse.Namespace) -> int:
    """Render a status-annotated ``README.md`` from a ``metadata.yaml`` document.

    Orchestration (delegated to :func:`sofer.render.render` / ``generate_all_renders``):

        1. Single-file (default): resolve ``metadata.yaml`` from ``<package>``
           (file or directory, RND-01), load and project into ``README.md``
           without recomputing inference (RND-02), write next to metadata
           (or to ``--output``) with ``FileExistsError`` guard gated by
           ``--force`` (RND-05).
        2. Batch (``--all-files``): iterate ``[[file]]`` entries, resolve each
           entry's ``metadata.yaml`` under ``profile_dir``, write
           ``<write_root>/renders/<rel_stem>.README.md`` via ``config.RENDER_DIR``,
           skip missing metadata, collision map + partial-write-then-ValueError,
           Option B anchoring.

    Inference states are rendered distinctly (RND-03): ``confirmed`` as a plain
    label, ``inferred`` as ``<type> (inferred, NN%)``, and ``unknown`` as
    ``unknown``. Returns the exit code from the domain function
    (0 on success, 1 when no ``metadata.yaml`` is found or guard triggers).
    """
    if getattr(args, "all_files", False):
        config_path_raw = getattr(args, "config", None)
        package_raw = getattr(args, "package", None)
        toml_arg: str | None = None
        if config_path_raw is not None and str(config_path_raw) != config.DEFAULT_CONFIG_NAME:
            toml_arg = str(config_path_raw)
        elif package_raw is not None:
            toml_arg = str(package_raw)
        else:
            toml_arg = (
                str(config_path_raw) if config_path_raw is not None else config.DEFAULT_CONFIG_NAME
            )
        try:
            cfg = DatasetConfig.from_toml(toml_arg)
        except Exception as exc:
            print(f"Error: Failed to read TOML: {exc}", file=sys.stderr)
            return 1
        validation_errors = cfg.validate()
        if validation_errors:
            for err in validation_errors:
                print(f"Error: {err}", file=sys.stderr)
            return 1
        if not cfg.files:
            print("Error: No [[file]] entries found in configuration.", file=sys.stderr)
            return 1
        from .render import generate_all_renders as _gen_all_renders

        try:
            _gen_all_renders(cfg, output_dir=args.output)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    if not getattr(args, "package", None):
        print("Error: Must specify a package path or use --all-files.", file=sys.stderr)
        return 1
    # Anchor a relative --output to the package dir-or-file (MSP-R10): the
    # README.md lands next to metadata.yaml, never in an unrelated cwd.
    output_dir = Path(args.output) if args.output else None
    if output_dir is not None and not output_dir.is_absolute():
        pkg = Path(args.package)
        output_dir = (pkg if pkg.is_dir() else pkg.parent) / output_dir
    try:
        return run_render(
            Path(args.package),
            output_dir=output_dir,
            force=bool(getattr(args, "force", False)),
        )
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _cmd_report_failure(args: argparse.Namespace) -> int:
    """Send a persisted failure report through ``gh`` (CLI-R14, issue #244).

    Reads the JSON document written by the assisted failure reporter, retries
    the same delivery path, and prints the created issue URL on success. When
    ``gh`` is still missing, unauthenticated, or offline it re-emits the triple
    safety net (saved path, retry command, manual URL, ``gh auth login``) and
    keeps the file, so no reportable failure is ever lost.

    Args:
        args: Parsed CLI arguments (must expose ``file``).

    Returns:
        ``0`` when the issue was created, ``1`` otherwise.
    """
    return failure_report.send_persisted_report(Path(args.file))


def _cmd_scan(args: argparse.Namespace) -> int:
    """MOVE loose files to ``raw/`` then copy ``raw/`` → ``cache/``.

    Orchestration (SCN-07):

        Phase 1 — MOVE loose files preserving ``relative_to(base_dir)`` tree:

            1. Discover loose supported files outside ``raw/``/``cache/``/
               ``EXCLUSIONS`` (5 exts via ``SUPPORTED_FORMATS``).
            2. ``mkdir -p raw/`` (skip on ``--dry-run``).
            3. Pre-flight ``check_raw_collisions`` — atomic abort, exit 1,
               no mutation when any ``raw/<rel>`` already exists.
            4. Gate on ``--dry-run`` (preview ``-> raw/<rel>``, no mutation),
               ``--force`` (skip prompt), else ``[y/N]`` prompt — ``N`` aborts
               atomically before first move, TOML untouched.
            5. ``move_to_raw`` — ``mkdir -p`` parents, ``shutil.move``,
               no flatten.

        Phase 2 — copy ``raw/`` → ``cache/`` (keyed relative to ``raw/``):

            6. Discover files excluding ``cache/``/``EXCLUSIONS``,
               ``check_flatten_collisions``, ``merge_entries``,
               ``copy_files`` (``raw/DPTO.csv`` → ``cache/DPTO.csv`` via
               :func:`registration_path` + ``shutil.copy2``), ``write_toml``.

    Atomicity: collision or ``N``/``--dry-run`` leaves TOML and moved files
    untouched — no partial moves. Phase 2 copies files first and writes the
    TOML last via an atomic :func:`write_toml` (temp + ``os.replace``), so a
    TOML write failure cannot corrupt the config; the documented recovery is
    a plain re-run with ``--force`` (the cache copy is overwritten and the
    TOML re-registered, SCN-08).
    """
    config_path = Path(args.config).resolve()

    if not config_path.exists():
        print(f"  X  Config file not found: {config_path}", file=sys.stderr)
        return 1

    # 1. Load raw TOML (parser resolved once in `sofer._toml`, #192).
    try:
        with open(config_path, "rb") as fh:
            raw_toml = _toml.load(fh)
    except Exception as exc:
        print(f"  X  Failed to read TOML: {exc}", file=sys.stderr)
        return 1

    base_dir = config_path.parent.resolve()
    data_dir = base_dir / config.OUTPUT_DIR
    raw_dir = base_dir / config.RAW_DIR
    extensions = args.ext if args.ext else None

    # ── Phase 1: MOVE loose files → raw/ ─────────────────────────────
    exclude_move = EXCLUSIONS | frozenset({config.RAW_DIR, config.OUTPUT_DIR})
    candidates = discover_files(base_dir, extensions, exclude_dirs=exclude_move)

    if candidates:
        # 1a. Ensure raw/ exists (skip on dry-run — no FS mutation).
        if not args.dry_run:
            raw_dir.mkdir(parents=True, exist_ok=True)

        # 1b. Pre-flight collision check — atomic abort before any move.
        try:
            check_raw_collisions(candidates, raw_dir, base_dir)
        except ValueError as exc:
            print(f"  X  {exc}", file=sys.stderr)
            return 1

        # 1c. Dry-run preview for MOVE — no mutation, no P2.
        if args.dry_run:
            print("  DRY RUN  Would move the following files:")
            for src in candidates:
                rel = src.relative_to(base_dir)
                print(f"     -> raw/{rel.as_posix()}")
            return 0

        # 1d. Prompt gate — single gate for the MOVE phase.
        if not args.force:
            print(f"\n  The following files will be moved to {config.RAW_DIR}/:")
            for src in candidates:
                rel = src.relative_to(base_dir)
                print(f"     -> raw/{rel.as_posix()}")
            try:
                answer = input("\n  Continue? [y/N] ").strip().lower()
            except EOFError:
                answer = "n"
            if answer not in ("y", "yes"):
                print("  OK  Aborted.")
                return 0

        # 1e. Execute MOVE — preserving relative_to tree.
        try:
            moved = move_to_raw(candidates, base_dir, raw_dir, dry_run=False)
        except Exception as exc:
            print(f"  X  Failed to move to raw/: {exc}", file=sys.stderr)
            return 1

        for _src, dest in moved:
            print(f"     OK  {dest.relative_to(base_dir).as_posix()}")

    else:
        # No loose files — honor --dry-run for P2 later, but don't exit yet.
        if args.dry_run and not candidates:
            # Still need to honor dry-run semantics for P2 — fall through to P2
            # with dry_run=True so P2 reports without mutation. Don't return yet.
            pass

    # If Phase 1 had candidates and we are here, we already handled dry-run
    # (returned) and executed moves. For dry-run with candidates we never reach
    # here. For the atomic dry-run case with candidates, P2 must NOT run — already
    # returned. For the no-candidate dry-run case, P2 will report correctly.

    # Dry-run with candidates already returned; if we are in dry-run and had
    # candidates, we wouldn't be here. But if dry_run and candidates non-empty,
    # we returned above. So if dry_run is True here, it means no candidates.
    # However to keep atomic semantics simple: if args.dry_run and candidates:
    # we returned. So remaining dry_run case is no-candidate.

    # ── Phase 2: discover → check_flatten → merge → copy → write ─────
    exclude_cache = EXCLUSIONS | frozenset({config.OUTPUT_DIR})
    discovered = discover_files(base_dir, extensions, exclude_dirs=exclude_cache)

    # Stale-registration report (#339/D5): name cache/-only entries whose raw/
    # source is missing, without rewriting them. Reported before the early
    # return so a config whose only entries are stale still says so.
    for line in format_stale_cache_warning(
        stale_cache_registrations(raw_toml.get("file", []), base_dir),
        config.REPORT_MAX_ITEMS,
    ):
        print(line)

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

    # 4. Confirm with the user before copying when Phase 1 had no candidates
    #    and thus no prompt yet; when Phase 1 moved files, the gate already
    #    passed so skip a second prompt.
    if not candidates and not args.dry_run and not args.force:
        print(f"\n  The following files will be copied to {config.OUTPUT_DIR}/:")
        for f in discovered:
            flat = registration_path(f, base_dir, raw_dir)
            print(f"     -> {config.OUTPUT_DIR}/{flat.as_posix()}")
        try:
            answer = input("\n  Continue? [y/N] ").strip().lower()
        except EOFError:
            answer = "n"
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
        if copied:
            print("  DRY RUN  Would copy the following files:")
            for _src, dest in copied:
                print(f"     -> {dest.relative_to(base_dir).as_posix()}")
        else:
            print(
                "  DRY RUN  Nothing to copy — all files already present in the"
                f" artifact cache ({config.OUTPUT_DIR}/, idempotent)."
            )
        if new_count:
            print(f"  DRY RUN  Would register {new_count} new [[file]] entry(s).")
        else:
            print("  DRY RUN  All discovered files already registered (idempotent).")
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
            print(
                "  i  Re-run with --force to recover (cache/ copies are already in place).",
                file=sys.stderr,
            )
            return 1
        # Registration is only truthful AFTER the copy and the TOML write have
        # both succeeded — a partial failure must never report a registration.
        if new_count:
            print(f"  OK  Registered {new_count} new [[file]] entry(s).")
        else:
            print("  OK  All discovered files already registered (idempotent).")

    return 0


def _cmd_mcp_add(args: argparse.Namespace) -> int:
    """Register ``sofer-mcp`` with the selected agent(s).

    Orchestration:

        1. Expand ``--agent all`` to the registry agents (``mcp_registration.AGENT_NAMES``).
        2. Resolve the desired ``cwd`` (``--cwd`` or ``Path.cwd()``) to an
           absolute path via ``Path.resolve()`` and require it to be an
           **existing directory** via ``mcp_registration.validate_cwd`` —
           fail with exit 1 and a path message when it is not. A tree outside
           the home and the process cwd is accepted and named by
           ``mcp_registration.outside_root_warning`` instead of being refused
           (issue #274).
        3. For each agent: when opencode is selected and known env keys are
           present, print an informational stderr warning naming the dropped
           env NAMES (never values) and pointing at the README alternative.
           Informational only — it never changes the exit code or stdout.
        4. For each agent: probe native delegation via
           ``mcp_registration.probe_native`` (``which`` + ``mcp --help``
           timeout 3s); when available, try ``delegate_add`` first — on
           success skip file-edit. Delegation is fidelity-gated (#167, #232):
           when the native CLI cannot forward the same env NAMES, scope and
           timeouts as the file edit, ``delegate_add`` declines without
           spawning, a stderr warning names the reason (``env forwarding`` /
           ``project scope`` / ``timeout``, NAMES only), and the file-edit path
           runs; any other native failure (raise or non-zero exit) falls back
           with the generic message.
        5. File-edit path: ``resolve_config_path`` → ``single_scope_note``
           (a single-scope agent under ``--scope project`` prints the
           substitution to stderr here, before the read/merge/dry-run branch) →
           ``read_config`` (unreadable/malformed → print to stderr, return 1,
           no backup/write) → ``build_entry`` (absolute cwd, env forwarding per
           agent, host timeout keys per agent) → ``merge`` (normalize Codex
           command string/array, preserve other servers, no write when
           unchanged) → ``--dry-run`` guard (no mutation) → ``backup`` (single
           ``.bak`` copy2 overwrite) → ``atomic_write`` (tmp in same dir +
           ``os.replace``).
        6. Aggregate per-agent exit codes — exit 0 iff all succeed else 1.

        Env forwarding: ``HF_TOKEN``/``SOFER_MCP_APPROVAL_PHRASE`` are collected
        from ``os.environ``; Codex receives an ``env_vars`` allow-list, Gemini,
        Pi and Hermes receive an ``env`` name list (NAMES only — values are
        never persisted; Pi and Hermes use the ``${KEY}`` form they interpolate),
        opencode receives no env. When opencode (or the opencode member of
        ``all``) is chosen with known env keys present, the step-3 warning is
        printed once per run and names the variables that cannot be forwarded.

        Host timeouts (issues #287, #296): the entry carries the host's
        per-request and connect/startup deadlines so a cold start (16-32 s
        measured) and a long call (~680 s ``prepare`` measured) do not fail
        against a host default and look like a broken registration. The values
        default to ``[tool.sofer] mcp_request_timeout_seconds`` /
        ``mcp_connect_timeout_seconds``, are overridable per invocation, and are
        omitted entirely by ``--no-timeout``. The key name and the unit come
        from the adapter; an agent whose entry accepts none is named on stderr
        by ``mcp_registration.dropped_timeout_note``.
    """
    # Expand agent
    raw_agent: str = getattr(args, "agent")
    agents: list[str] = list(mcp_registration.AGENT_NAMES) if raw_agent == "all" else [raw_agent]
    scope: str = getattr(args, "scope", "user")
    _scope = cast(mcp_registration.Scope, scope)
    cwd_raw: str | None = getattr(args, "cwd", None)
    dry_run: bool = bool(getattr(args, "dry_run", False))
    user_config: str | None = getattr(args, "user_config", None)

    # Host timeouts for the entry (issues #287, #296). Values default to the
    # live [tool.sofer] keys (AGENTS.md rule 1 — never a literal here), the
    # flags override per invocation, and --no-timeout writes none at all.
    timeouts: mcp_registration.Timeouts | None
    if bool(getattr(args, "no_timeout", False)):
        timeouts = None
    else:
        raw_request = getattr(args, "timeout", None)
        raw_connect = getattr(args, "connect_timeout", None)
        timeouts = mcp_registration.Timeouts(
            request_seconds=(
                config.MCP_REQUEST_TIMEOUT_SECONDS if raw_request is None else raw_request
            ),
            connect_seconds=(
                config.MCP_CONNECT_TIMEOUT_SECONDS if raw_connect is None else raw_connect
            ),
        )

    # `--user-config` names ONE file, so it is ambiguous for `--agent all`
    # (each agent has its own config). Reject before any write (issue #274).
    if user_config is not None and user_config.strip() and getattr(args, "agent") == "all":
        print(
            "  X  --user-config cannot be combined with --agent all: each agent "
            "has its own config file",
            file=sys.stderr,
        )
        return 1

    # Informational: `$HOME` and the account home can disagree, and the agent may
    # read its config from the latter — so a successful write can be a silent
    # no-op. Naming both homes is what removes the silence (issue #274).
    if scope == "user":
        mismatch = mcp_registration.home_mismatch_warning()
        if mismatch is not None:
            print(mismatch, file=sys.stderr)

    # Resolve desired cwd for the entry (absolute, contained)
    if cwd_raw is not None:
        cwd_resolved = Path(cwd_raw).resolve()
    else:
        cwd_resolved = Path.cwd().resolve()

    # ``--cwd`` must be an existing directory. The rule is existence, not
    # containment (issue #274): the previous home/process-cwd gate refused
    # legitimate trees and still accepted a nonexistent path under either root.
    if not mcp_registration.validate_cwd(cwd_resolved):
        print(
            f"  X  --cwd {cwd_resolved} is not an existing directory",
            file=sys.stderr,
        )
        return 1

    # Informational: an explicit --cwd is the caller's declaration, so an
    # unusual tree is accepted and named rather than refused (issue #274).
    outside_warning = mcp_registration.outside_root_warning(cwd_resolved)
    if outside_warning is not None:
        print(outside_warning, file=sys.stderr)

    env = mcp_registration.collect_env()
    overall = 0

    for agent in agents:
        # Informational env-drop warning (names only, never values)
        dropped = mcp_registration.dropped_env_keys(agent, env)
        if dropped:
            print(
                f"  !  {agent} registration receives no env: {', '.join(dropped)} "
                "not forwarded. See README for the launcher environment or an explicit "
                "'environment' literal in opencode.json.",
                file=sys.stderr,
            )
        # Informational timeout-drop note for a host whose entry accepts none.
        timeout_note = mcp_registration.dropped_timeout_note(agent, timeouts)
        if timeout_note is not None:
            print(timeout_note, file=sys.stderr)
        # Prefer native delegation for codex/gemini — but only when it is
        # faithful (#167, #232). A decline warns with the reason and falls back.
        if mcp_registration.probe_native(agent, timeout=3.0):
            try:
                delegated = mcp_registration.delegate_add(
                    agent, cwd_resolved, list(env.keys()), _scope, timeouts
                )
            except Exception:
                delegated = False
                native_error = True
            else:
                native_error = False
            if delegated:
                print(f"  OK  {agent} delegated via native mcp add")
                continue
            reasons = (
                []
                if native_error
                else mcp_registration.native_delegation_decline_reasons(
                    agent, list(env.keys()), _scope, timeouts
                )
            )
            if reasons:
                # Name the escape hatch only when it actually restores delegation.
                # Measured (issue #321): with no env key present the reasons are
                # exactly ["timeout"] and --no-timeout clears them, but with an
                # env key present they are ["env forwarding", "timeout"] and
                # the flag removes only the second, so the hint would point at a
                # flag that changes nothing.
                hint = (
                    "; pass --no-timeout to keep native delegation at the cost of the deadlines"
                    if reasons == ["timeout"]
                    else ""
                )
                print(
                    f"  !  {agent} native mcp add cannot express "
                    f"{', '.join(reasons)}; falling back to file edit{hint}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"  !  {agent} native delegation failed, falling back to file edit",
                    file=sys.stderr,
                )

        # File-edit fallback — project scope anchors on the resolved cwd; user
        # scope ignores the anchor and resolves under Path.home().
        anchor = cwd_resolved if scope == "project" else None
        path = mcp_registration.resolve_config_path(agent, _scope, anchor, user_config)
        # Single-scope agents (Hermes) have no project file: name the
        # substitution on stderr before the read/merge/dry-run branch so
        # ``--dry-run`` sees it too (issue #272).
        note = mcp_registration.single_scope_note(agent, _scope, path)
        if note is not None:
            print(note, file=sys.stderr)

        try:
            existing, _fmt = mcp_registration.read_config(path)
        except Exception as exc:
            print(f"  X  {agent} config unreadable ({path}): {exc}", file=sys.stderr)
            overall = 1
            continue

        desired = mcp_registration.build_entry(agent, cwd_resolved, env, timeouts)
        new_doc, changed = mcp_registration.merge(agent, existing, desired)
        if not changed:
            print(f"  OK  {agent} already registered (idempotent)")
            continue
        if dry_run:
            print(f"  DRY RUN  Would register {agent} at {path}")
            continue
        # Backup before first mutation
        try:
            mcp_registration.backup(path)
        except Exception as exc:
            print(f"  X  {agent} backup failed: {exc}", file=sys.stderr)
            overall = 1
            continue
        # Atomic write — fmt from adapter (preserve agent's expected format)
        fmt_expected = mcp_registration.ADAPTERS[agent]["fmt"]
        try:
            mcp_registration.atomic_write(path, new_doc, fmt_expected)
        except Exception as exc:
            print(f"  X  {agent} write failed: {exc}", file=sys.stderr)
            overall = 1
            continue
        print(f"  OK  {agent} registered at {path}")

    return overall


def _cmd_mcp_remove(args: argparse.Namespace) -> int:
    """Remove ``sofer-mcp`` from the selected agent(s).

    Orchestration mirrors :func:`_cmd_mcp_add` without ``--cwd``:

        1. Expand ``--agent all``.
        2. For each agent: probe native ``delegate_remove`` first;
           on success skip file-edit. Fidelity-gated like ``add`` (#232):
           when the native CLI cannot express the requested scope,
           ``delegate_remove`` declines, a stderr warning names ``project
           scope``, and the file-edit path runs; any other native failure
           falls back with the generic message.
        3. File-edit: ``resolve_config_path`` → ``single_scope_note``
           (a single-scope agent under ``--scope project`` prints the
           substitution to stderr here, before the read/dry-run branch) →
           ``read_config`` (unreadable → exit 1, no backup/write) →
           ``remove_entry`` (preserve other servers, no write when absent) →
           ``--dry-run`` guard → ``backup`` → ``atomic_write``.
        4. Aggregate exit codes — 0 iff all succeed else 1.

    No ``--cwd`` flag exists on remove (CLI-R09: only add accepts cwd).
    """
    raw_agent: str = getattr(args, "agent")
    agents: list[str] = list(mcp_registration.AGENT_NAMES) if raw_agent == "all" else [raw_agent]
    scope: str = getattr(args, "scope", "user")
    dry_run: bool = bool(getattr(args, "dry_run", False))
    user_config: str | None = getattr(args, "user_config", None)
    overall = 0

    # `--user-config` names ONE file, so it is ambiguous for `--agent all`
    # (each agent has its own config). Reject before any write (issue #274).
    if user_config is not None and user_config.strip() and getattr(args, "agent") == "all":
        print(
            "  X  --user-config cannot be combined with --agent all: each agent "
            "has its own config file",
            file=sys.stderr,
        )
        return 1

    # Informational, same contract as `add` (issue #274).
    if scope == "user":
        mismatch = mcp_registration.home_mismatch_warning()
        if mismatch is not None:
            print(mismatch, file=sys.stderr)

    for agent in agents:
        _scope = cast(mcp_registration.Scope, scope)
        if mcp_registration.probe_native(agent, timeout=3.0):
            try:
                delegated = mcp_registration.delegate_remove(agent, _scope)
            except Exception:
                delegated = False
                native_error = True
            else:
                native_error = False
            if delegated:
                print(f"  OK  {agent} delegated remove via native mcp remove")
                continue
            reasons = (
                []
                if native_error
                else mcp_registration.native_delegation_decline_reasons(agent, [], _scope)
            )
            if reasons:
                print(
                    f"  !  {agent} native mcp remove cannot express "
                    f"{', '.join(reasons)}; falling back to file edit",
                    file=sys.stderr,
                )
            else:
                print(
                    f"  !  {agent} native remove failed, falling back to file edit",
                    file=sys.stderr,
                )

        path = mcp_registration.resolve_config_path(agent, _scope, None, user_config)
        # Same single-scope note as ``add``: name the substitution before the
        # read/dry-run branch so ``--dry-run`` sees it too (issue #272).
        note = mcp_registration.single_scope_note(agent, _scope, path)
        if note is not None:
            print(note, file=sys.stderr)
        try:
            existing, _fmt2 = mcp_registration.read_config(path)
        except Exception as exc:
            print(f"  X  {agent} config unreadable ({path}): {exc}", file=sys.stderr)
            overall = 1
            continue

        new_doc, changed = mcp_registration.remove_entry(agent, existing)
        if not changed:
            print(f"  OK  {agent} already absent (idempotent)")
            continue
        if dry_run:
            print(f"  DRY RUN  Would remove {agent} at {path}")
            continue
        try:
            mcp_registration.backup(path)
        except Exception as exc:
            print(f"  X  {agent} backup failed: {exc}", file=sys.stderr)
            overall = 1
            continue
        fmt_expected = mcp_registration.ADAPTERS[agent]["fmt"]
        try:
            mcp_registration.atomic_write(path, new_doc, fmt_expected)
        except Exception as exc:
            print(f"  X  {agent} write failed: {exc}", file=sys.stderr)
            overall = 1
            continue
        print(f"  OK  {agent} removed from {path}")

    return overall


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
repo_id = "{user}/{name}"
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
local = "raw/example.csv"
remote = "file.csv"

[[file]]
local = "raw/example/"
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


def _cmd_mcp_doctor(args: argparse.Namespace) -> int:
    """Measure the real ``sofer-mcp`` cold start and report it against the written deadline.

    Orchestration:

        1. Resolve the entry point: the ``sofer-mcp`` console script when it is on
           ``PATH``, else the module entry point (issue #322).
        2. Measure the stdio ``initialize`` round trip, using the configured
           ``[tool.sofer] mcp_connect_timeout_seconds`` as the budget - the same
           value ``mcp add`` writes, never a literal here (AGENTS.md rule 1).
        3. Collate the per-agent rows from ``timeout_entry_keys``, so the report
           cannot disagree with what registration writes, and repeat
           ``dropped_timeout_note`` for an agent whose schema accepts no key.
        4. Print the report and return 0 even when the measurement exceeds the
           budget - the same informational contract as the timeout and env-drop
           notes. Only "nothing could be measured" returns 1. This command never
           reads a config file and never writes one.

    Args:
        args: Parsed arguments carrying ``--agent`` and ``--json``.

    Returns:
        0 when a launch was measured (whatever it measured), else 1.
    """
    raw_agent: str | None = getattr(args, "agent", None)
    agents: list[str] = (
        list(mcp_registration.AGENT_NAMES) if raw_agent in (None, "all") else [raw_agent]
    )
    as_json = bool(getattr(args, "json", False))
    timeouts = mcp_registration.Timeouts(
        request_seconds=config.MCP_REQUEST_TIMEOUT_SECONDS,
        connect_seconds=config.MCP_CONNECT_TIMEOUT_SECONDS,
    )
    measurement = mcp_doctor.measure(
        mcp_doctor.resolve_entry_point(),
        timeout_seconds=float(config.MCP_CONNECT_TIMEOUT_SECONDS),
    )
    report = mcp_doctor.build_report(
        agents,
        measurement=measurement,
        timeouts=timeouts,
        budget_seconds=config.MCP_CONNECT_TIMEOUT_SECONDS,
    )
    exit_code = 0 if measurement.ok else 1
    if as_json:
        print(mcp_doctor.render_json(report, exit_code=exit_code))
    elif measurement.ok:
        print(mcp_doctor.render_human(report))
    else:
        print(mcp_doctor.render_human(report), file=sys.stderr)
    return exit_code


def _cmd_meta_check(args: argparse.Namespace) -> int:
    """Report the ``[meta]`` fields that still carry an ``init`` placeholder.

    Orchestration:

        1. Load the dataset TOML with :meth:`DatasetConfig.from_toml`, the same
           dataset-directory anchor every other dataset command uses.
        2. Reuse :func:`sofer.checks.meta_placeholder_warnings` — the very
           implementation ``sofer_validate`` calls — so the query and the
           validator cannot disagree about what a placeholder is.
        3. Print one line per warning, or a single ``OK`` line when there are
           none. Informational by contract (maintainer decision D6): the exit
           code is 0 either way, exactly like the warning it reports, because a
           non-zero exit here would make this query stricter than the run it
           queries. Only "the config could not be read" exits 1.

    Args:
        args: Parsed arguments carrying ``config`` and ``--json``.

    Returns:
        0 when the config was read (whatever it reports), else 1.
    """
    path: str = args.config
    try:
        cfg = DatasetConfig.from_toml(path)
    except Exception as exc:
        print(f"  X  cannot read {path}: {exc}", file=sys.stderr)
        return 1
    warnings = meta_placeholder_warnings(cfg)
    if bool(getattr(args, "json", False)):
        print(
            json.dumps(
                {
                    "ok": True,
                    "exit_code": 0,
                    "message": f"{len(warnings)} [meta] placeholder warning(s)",
                    "placeholders": len(warnings),
                    "warnings": warnings,
                },
                ensure_ascii=False,
            )
        )
        return 0
    if warnings:
        for warning in warnings:
            print(f"  !  {warning}")
    else:
        print(f"  OK  {path}: no [meta] placeholders")
    return 0


def _cmd_meta_set(args: argparse.Namespace) -> int:
    """Write the given ``[meta]`` keys into the dataset TOML.

    Orchestration:

        1. Read every ``--set KEY=VALUE`` into a typed mapping with
           :func:`sofer.meta_edit.parse_meta_value` — the registry kind decides
           how the text is read (maintainer decision D9). An argument without
           ``=``, a blank key, an unknown key and an unreadable boolean are all
           refused before anything is touched (argparse guarantees at least one
           ``--set``).
        2. Load the dataset TOML (dataset-directory anchor) so an unreadable or
           invalid config fails before the write, and so the build-tree note
           below can use the resolved ``build_dir``.
        3. Apply the edit with :func:`sofer.meta_edit.set_meta`: it touches only
           the ``[meta]`` table, preserves every other byte, commits with an
           atomic replace, and refuses rather than writing a document it cannot
           parse back. ``--dry-run`` computes and verifies the edit and writes
           nothing.
        4. Report the keys written and the keys already holding the requested
           value; a build tree that predates the write is named on stderr and
           never changes the exit code (maintainer decision D7). A refusal exits
           1 with nothing written.

    Args:
        args: Parsed arguments carrying ``config``, ``assignments``,
            ``--dry-run`` and ``--json``.

    Returns:
        0 on success (including a no-op), else 1.
    """
    values: dict[str, Any] = {}
    for entry in list(getattr(args, "assignments", [])):
        key, separator, raw = entry.partition("=")
        if not separator or not key.strip():
            print(f"  X  --set expects KEY=VALUE, got {entry!r}", file=sys.stderr)
            return 1
        try:
            values[key.strip()] = meta_edit.parse_meta_value(key.strip(), raw)
        except meta_edit.MetaEditError as exc:
            print(f"  X  {exc}", file=sys.stderr)
            return 1

    path: str = args.config
    dry_run = bool(getattr(args, "dry_run", False))
    try:
        cfg = DatasetConfig.from_toml(path)
    except Exception as exc:
        print(f"  X  cannot read {path}: {exc}", file=sys.stderr)
        return 1
    try:
        result = meta_edit.set_meta(path, values, dry_run=dry_run)
    except meta_edit.MetaEditError as exc:
        print(f"  X  {exc}", file=sys.stderr)
        return 1

    written = ", ".join(result.written)
    if bool(getattr(args, "json", False)):
        # CLI-R10: the machine-readable line is the ONLY stdout the command
        # writes, so a consumer can parse it without stripping human prose.
        print(
            json.dumps(
                {
                    "ok": True,
                    "exit_code": 0,
                    "message": (
                        (f"would write: {written}" if dry_run else f"wrote: {written}")
                        if result.changed
                        else "already up to date"
                    ),
                    "dry_run": result.dry_run,
                    "changed": result.changed,
                    "written": list(result.written),
                    "unchanged": list(result.unchanged),
                },
                ensure_ascii=False,
            )
        )
    else:
        if dry_run:
            print(f"  DRY RUN  {path}: would write {written or 'nothing'}")
        elif result.changed:
            print(f"  OK  {path}: wrote {written}")
        else:
            print(f"  OK  {path}: already up to date")
        if not dry_run and result.unchanged:
            print(f"  i  unchanged: {', '.join(result.unchanged)}")
    note = meta_edit.build_predates_write(cfg, path)
    if note is not None:
        print(note, file=sys.stderr)
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    """Write a ready-to-edit TOML template and scaffold ``raw/``.

    Orchestration:

        1. Validate the identity pre-write via :func:`validate_identity`
           (INIT-05 / CLI-R07): a missing/blank/placeholder/unsafe ``name``
           or ``user`` prints each error to stderr and exits 1 — neither
           the TOML nor ``raw/`` is created.
        2. Resolve the dataset root — no bound, so the live working
           directory (:func:`resolve_dataset_root` mode (a)) — and derive
           ``<root>/<name>.toml`` and ``<root>/RAW_DIR`` from it; refuse to
           overwrite an existing TOML.
        3. Write the TOML FIRST, then ``mkdir -p RAW_DIR`` idempotently
           (``exist_ok=True``) — a TOML write failure never leaves an orphan
           ``raw/`` (no partial state). Both steps are skipped under
           ``--dry-run`` in BOTH branches (preview only, no mutation),
           matching the MCP ``sofer_init`` no-mutation semantics.
        4. When ``--move-existing`` is set: collect depth-1 supported files
           (``SUPPORTED_FORMATS``, direct children of the dataset root), run
           :func:`check_flatten_collisions` against existing ``raw/`` content
           before any move, honour ``--dry-run`` (preview: no TOML, no
           ``raw/`` mkdir when absent, no moves), ``--force`` / ``not
           isatty`` guard (skip prompt), else prompt ``[y/N]`` and abort on
           ``N``, then :func:`shutil.move` each file into ``RAW_DIR``.
    """
    errors = validate_identity(args.name, getattr(args, "user", None))
    if errors:
        for err in errors:
            print(f"  X  {err}", file=sys.stderr)
        return 1

    dataset_root = resolve_dataset_root(None, live_cwd=Path.cwd().resolve())
    output = dataset_root / f"{args.name}.toml"
    if output.exists():
        print(f"  X  File already exists: {output}")
        return 1

    raw_dir_name: str = config.RAW_DIR
    raw_dir_path = dataset_root / raw_dir_name
    move_existing: bool = bool(getattr(args, "move_existing", False))
    dry_run: bool = bool(getattr(args, "dry_run", False))
    force: bool = bool(getattr(args, "force", False))
    user_val: str = args.user
    toml_text = _INIT_TEMPLATE.format(name=args.name, user=user_val)

    if not move_existing:
        if dry_run:
            # No-mutation preview (CLI-R07 / MCP parity): neither the TOML
            # nor raw/ is created.
            print(f"  DRY RUN  Would create {output.name}")
            print(f"  DRY RUN  Would scaffold {raw_dir_name}")
            return 0
        # TOML write BEFORE the raw/ scaffold: a write failure never leaves
        # an orphan raw/ (no partial state, INIT-05 robustness).
        output.write_text(toml_text, encoding="utf-8")
        raw_dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  OK  Created {output}")
        print("     Edit the file and run:")
        print(f"       sofer prepare {output.name}")
        print(f"       sofer publish {output.name}")
        return 0

    # --move-existing: collect depth-1 SUPPORTED_FORMATS files in the dataset
    # root (shared helper, AGENTS.md rule 4).
    candidates, existing = collect_init_moves(dataset_root, output.name, raw_dir_path)

    # Pre-move collision check against existing raw/ content.
    if candidates:
        base_dir = dataset_root
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
        # Preview only — dry_run performs NO filesystem writes (CLI-R07
        # no-mutation contract): neither the TOML nor raw/ is created, no
        # moves, matching the MCP sofer_init no-mutation semantics.
        print(f"  DRY RUN  Would create {output.name}")
        print(f"  DRY RUN  Would scaffold {raw_dir_name}")
        return 0

    # Non-dry-run move_existing: honour --force / isatty guard.
    is_tty = sys.stdin.isatty()
    if candidates and not force and not is_tty:
        print(
            "  !  Skipping move of existing files (non-interactive). Use --force to move.",
            file=sys.stderr,
        )
        output.write_text(toml_text, encoding="utf-8")
        raw_dir_path.mkdir(parents=True, exist_ok=True)
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
            output.write_text(toml_text, encoding="utf-8")
            raw_dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  OK  Created {output}")
            print("     Edit the file and run:")
            print(f"       sofer prepare {output.name}")
            print(f"       sofer publish {output.name}")
            return 0

    # Proceed: write the TOML, then scaffold raw/ and move.
    output.write_text(toml_text, encoding="utf-8")
    raw_dir_path.mkdir(parents=True, exist_ok=True)
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


def _add_dialect_args(parser: argparse.ArgumentParser) -> None:
    """Add the optional explicit CSV dialect flags (issue #204).

    Both default to ``None`` ("not supplied"), so the omitted path reuses the
    exact config resolution the command already performs — the override is
    additive and byte-identical when unused.  When supplied, the explicit value
    wins over the configured one; the encoding still fronts the shared
    ``utf-8-sig → utf-8`` fallback chain in ``_csv_reader.stream_csv``.

    Args:
        parser: The ``codebook`` or ``profile`` subparser to extend.
    """
    parser.add_argument(
        "--delimiter",
        default=None,
        help=(
            "Explicit CSV field delimiter for this invocation; wins over the "
            "configured csv_delimiter. Omitted = configured value (applies to "
            ".csv only; .tsv stays tab-delimited)."
        ),
    )
    parser.add_argument(
        "--encoding",
        default=None,
        help=(
            "Explicit CSV encoding for this invocation; wins over the configured "
            "csv_encoding. Omitted = configured value (applies to .csv and .tsv)."
        ),
    )


def _echo_explicit_dialect(args: argparse.Namespace) -> None:
    """Echo a supplied ``--delimiter`` / ``--encoding`` on stderr (issue #204).

    Traceability contract: when the caller states a dialect explicitly, the
    command names what was supplied. Only the supplied keys are listed, so an
    omitted flag is never reported as if it had been chosen. stderr is used so
    the single-file codebook's stdout stays pure markdown.

    Args:
        args: Parsed CLI namespace carrying ``delimiter`` / ``encoding``.
    """
    parts: list[str] = []
    delimiter = getattr(args, "delimiter", None)
    if delimiter is not None:
        parts.append(f"delimiter={delimiter!r}")
    encoding = getattr(args, "encoding", None)
    if encoding is not None:
        parts.append(f"encoding={encoding!r}")
    if parts:
        print(f"  i  Explicit dialect: {' '.join(parts)}", file=sys.stderr)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sofer",
        description=(
            "Prepare and publish datasets to Hugging Face Hub with built-in "
            "validation.\n"
            "\n"
            "Every dataset is configured via a TOML file.  Run:\n"
            "  sofer init my-dataset --user myuser # create a template\n"
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
            "local machine: universal csv/tsv/xlsx/jsonl -> normalized Parquet "
            "conversion (Excel -> one Parquet per sheet), cross-file schema "
            "checks, a schema report, the Dataset Card (README.md) and "
            "LICENSE, and - with --all-files - codebooks.  Set "
            "convert_to_parquet=false per [[file]] to keep the original.  This "
            "command never contacts Hugging Face and needs no credentials.\n"
            "\n"
            "Conversion never changes a value: a zero-padded code column "
            '("001", "02") is forced to string instead of being inferred as '
            'a number, and declaring column_types = { COL = "string" } on the '
            "[[file]] entry makes that intent explicit.  If a value would still "
            "be altered, the run reports the column and the declaration that "
            "fixes it, delivers nothing for that file, and exits 1.\n"
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
    pb.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Delete the build directory after a successful publish (PUB-11). "
            "Build-only by default; has no effect on --dry-run, quality-gate block, "
            "or upload failure. Respects --output override via resolve_output_dir."
        ),
    )
    pb.add_argument(
        "--clean-cache",
        "--all",
        dest="clean_cache",
        action="store_true",
        help=(
            "Also delete cache/ (tool-wide OUTPUT_DIR at cfg._base_dir/cache, "
            "shared across datasets) when used with --clean. Requires explicit "
            "opt-in; warn: sibling datasets share cache/."
        ),
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
            "in the TOML configuration, written under the package build_dir/.\n"
            "\n"
            "--delimiter / --encoding override the resolved CSV dialect for "
            "this invocation: the explicit value wins over the configured one, "
            "and omitting both keeps the current behaviour."
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
    _add_dialect_args(c)
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
            "Single-file: metadata.yaml is written next to the dataset by "
            "default, or to --output DIR when given. Without --force an "
            "existing destination raises FileExistsError with hint "
            "'use --force to overwrite <path>'.\n"
            "\n"
            "Batch (--all-files): positional DATASET is the TOML file "
            "containing [[file]] entries (also via --config). Each entry is "
            "profiled into <write_root>/profiles/<rel_stem>.metadata.yaml "
            "where <rel_stem> is relative to cache/ (OUTPUT_DIR) or the TOML "
            "directory and only the last suffix is replaced. Relative "
            "--output anchors to the TOML directory (Option B); writes never "
            "mutate cache/ when --output is given. TOML without [[file]] "
            "fails fast. Collisions write non-colliding first then raise "
            "ValueError.\n"
            "\n"
            "--delimiter / --encoding override the resolved CSV dialect for "
            "this invocation: the explicit value wins over the configured one, "
            "and omitting both keeps the current behaviour."
        ),
    )
    prf.add_argument(
        "dataset",
        nargs="?",
        help="Path to the dataset file to profile (CSV, TSV, Parquet, Excel, or JSON Lines). "
        "With --all-files, path to the TOML configuration file containing [[file]] entries.",
    )
    prf.add_argument(
        "--output",
        help="Output directory for metadata.yaml (default: the dataset's directory). "
        "With --all-files, directory for profiles/<rel_stem>.metadata.yaml (Option B).",
    )
    prf.add_argument(
        "--all-files",
        action="store_true",
        help="Profile every [[file]] entry in the TOML config (requires [[file]]).",
    )
    prf.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing metadata.yaml without error "
        "(single-file; hint: use --force to overwrite).",
    )
    prf.add_argument(
        "--config",
        default=config.DEFAULT_CONFIG_NAME,
        help="Path to the TOML config file used with --all-files "
        "(default: default_config_name from [tool.sofer]).",
    )
    _add_dialect_args(prf)
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
            "Single-file: README.md is written next to metadata.yaml by "
            "default, or to --output DIR when given. Without --force an "
            "existing destination raises FileExistsError with hint "
            "'use --force to overwrite <path>'.\n"
            "\n"
            "Batch (--all-files): positional PACKAGE is the TOML file "
            "containing [[file]] entries (also via --config). Each entry's "
            "metadata.yaml under <write_root>/profiles/<rel_stem>.metadata.yaml "
            "is rendered into <write_root>/renders/<rel_stem>.README.md "
            "where <rel_stem> mirrors profile. Missing metadata.yaml entries "
            "are skipped. Relative --output anchors to the TOML directory "
            "(Option B). TOML without [[file]] fails fast. Collisions raise "
            "ValueError after partial write."
        ),
    )
    rnd.add_argument(
        "package",
        nargs="?",
        help="Path to metadata.yaml, or the directory containing it. "
        "With --all-files, path to the TOML configuration file containing [[file]] entries.",
    )
    rnd.add_argument(
        "--output",
        help="Output directory for README.md (default: the metadata.yaml directory). "
        "With --all-files, directory for renders/<rel_stem>.README.md (Option B).",
    )
    rnd.add_argument(
        "--all-files",
        action="store_true",
        help="Render every [[file]] entry in the TOML config (requires [[file]]).",
    )
    rnd.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing README.md without error "
        "(single-file; hint: use --force to overwrite).",
    )
    rnd.add_argument(
        "--config",
        default=config.DEFAULT_CONFIG_NAME,
        help="Path to the TOML config file used with --all-files "
        "(default: default_config_name from [tool.sofer]).",
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
            "before any move. --dry-run performs no writes in either branch "
            "(no <name>.toml, no raw/, no moves); --force or non-interactive "
            "(not isatty) skips the [y/N] prompt, else prompt aborts on N.\n"
            "\n"
            "Pipeline: raw/ (tracked) -> cache/ (OUTPUT_DIR, gitignored) "
            "-> build/ (gitignored); scan keys raw/DPTO.csv -> cache/DPTO.csv "
            "via registration_path."
        ),
    )
    i.add_argument("name", help="Short name for the dataset.")
    i.add_argument(
        "--user",
        required=True,
        help=(
            "Hugging Face username or organization for repo_id "
            "(e.g. --user myuser -> repo_id 'myuser/<name>'). Required: "
            "a missing --user exits 2, and placeholder (YOUR_USER) or "
            "unsafe values are rejected with exit 1 before any write."
        ),
    )
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
        help=(
            "Preview without writing any files: no <name>.toml, no raw/, no "
            "moves — for plain init and --move-existing alike."
        ),
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
            "Move loose data files to raw/ preserving tree, then copy "
            "raw/ -> cache/ flattened and register in TOML."
        ),
        description=(
            "Two-phase scan for the raw/ -> cache/ -> build/ pipeline.\n"
            "\n"
            "Phase 1 — MOVE to raw/: discover supported files outside "
            "raw/, cache/, and EXCLUSIONS (.git, __pycache__, .venv, "
            "node_modules, dist, build), then MOVE each loose file to "
            "raw/<relative_to(base_dir)> via shutil.move preserving the "
            "full tree (mkdir -p raw/ if missing, mkdir -p parents). "
            "Collision against existing raw/<rel> fails atomically before "
            "any move. --dry-run prints '-> raw/<rel>' with no mutation; "
            "--force skips the [y/N] prompt, else prompt aborts on N with "
            "no partial moves or TOML write.\n"
            "\n"
            "Phase 2 — COPY raw/ -> cache/: recursively scan (excluding "
            "cache/ and EXCLUSIONS), key each file by its path relative to "
            "raw/ (raw/DPTO.csv -> cache/DPTO.csv, raw/Labels/x.csv -> "
            "cache/Labels/x.csv), register new files as "
            "[[file]] entries in the TOML, and copy them into the cache/ "
            "directory via registration_path + shutil.copy2. Keying on raw/ "
            "is what makes a re-scan idempotent whatever the layout."
            "\n"
            "Running scan twice is safe — already-registered files are "
            "skipped (idempotent TOML and cache/)."
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
        help=(
            "Preview without mutation: Phase 1 prints '-> raw/<rel>' for "
            "each loose file; Phase 2 prints copy preview. No raw/ mkdir, "
            "no moves, no cache writes, no TOML update."
        ),
    )
    s.add_argument(
        "--force",
        action="store_true",
        help=(
            "Skip the [y/N] prompt and overwrite existing cache/ files; "
            "also skips the MOVE prompt (atomic: collision still fails "
            "before any move)."
        ),
    )
    s.add_argument(
        "--ext",
        action="append",
        choices=list(SUPPORTED_FORMATS.keys()),
        help="Only scan for files with these extensions (repeatable). "
        "When omitted, all supported formats are included.",
    )
    s.set_defaults(func=_cmd_scan)

    # ── mcp ───────────────────────────────────────────────────────
    mcp = sub.add_parser(
        "mcp",
        help="Register sofer-mcp with AI agents (opencode, codex, gemini, pi, hermes).",
        description=(
            "Register or remove the ``sofer-mcp`` MCP server from AI agent "
            "configurations. Supports ``opencode`` (opencode.json), ``codex`` "
            "(config.toml), ``gemini`` (settings.json), ``pi`` (mcp.json) and "
            "``hermes`` (config.yaml) with idempotent merge, backup to ``.bak``, "
            "atomic write, and per-agent env forwarding. Use ``--agent all`` to "
            "target every agent."
        ),
    )
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=True)

    mcp_add = mcp_sub.add_parser(
        "add",
        help="Register sofer-mcp with the selected agent(s).",
        description=(
            "Register ``sofer-mcp`` in the agent config file. Creates the "
            "config when missing, merges idempotently when present, preserves "
            "other servers, backs up the original to ``.bak`` (single file, "
            "overwrites), and writes atomically via tmp+os.replace. "
            "``--cwd`` sets the server's working directory (absolute; it must "
            "be an existing directory, and a tree outside the home is accepted "
            "with a warning naming it). ``--user-config`` states the user-scope "
            "config file explicitly - it wins over the adapter's env override and "
            "the home default, and it is rejected with ``--agent all``. A YAML "
            "config edit preserves the rest of the document (comments, key order, "
            "unrelated keys); a TOML edit may strip comments. "
            "Env: codex, gemini, pi and hermes receive env forwarding (names only, "
            "values never written; gemini uses $KEY references, pi and hermes use "
            "${KEY} references); opencode entries carry no "
            "environment, and a warning is printed on stderr when HF_TOKEN or "
            "SOFER_MCP_APPROVAL_PHRASE are set with --agent opencode (or all). "
            "hermes reads a single user-scope config, so --scope project resolves "
            "to that same file and the substitution is named on stderr. "
            "Native codex/gemini delegation is used only when it can forward the "
            "same env NAMES, scope and timeouts as the file edit; otherwise the "
            "config file is edited and a warning naming the reason is printed on "
            "stderr. "
            "Host timeouts (issues #287, #296): a first launch of sofer-mcp can "
            "take tens of seconds while its imports warm up, and a tool call on a "
            "large dataset can run for minutes, so the entry carries the host's "
            "per-request and connect/startup deadlines (--timeout / "
            "--connect-timeout, or --no-timeout to omit them). The key name, the "
            "unit and which budget a key carries are per agent: opencode's single "
            "scalar `timeout` is its connect budget in milliseconds. An agent "
            "whose schema accepts no timeout key is named on stderr."
        ),
    )
    mcp_add.add_argument(
        "--agent",
        choices=[*mcp_registration.AGENT_NAMES, "all"],
        required=True,
        help="Target agent or 'all' for every agent.",
    )
    mcp_add.add_argument(
        "--scope",
        choices=["user", "project"],
        default="user",
        help="Config scope: 'user' (home directory) or 'project' (current directory).",
    )
    mcp_add.add_argument(
        "--cwd",
        help=(
            "Working directory for the MCP server (absolute, must be an existing "
            "directory; a tree outside the home is accepted with a warning)."
        ),
    )
    mcp_add.add_argument(
        "--user-config",
        help=(
            "Explicit user-scope config FILE for the selected agent; wins over the "
            "adapter's env override and the home default. Rejected with --agent all."
        ),
    )
    mcp_add.add_argument(
        "--timeout",
        type=_positive_seconds,
        default=None,
        help=(
            "Per-request (tool call) deadline in seconds written into the entry. "
            "Default: [tool.sofer] mcp_request_timeout_seconds."
        ),
    )
    mcp_add.add_argument(
        "--connect-timeout",
        type=_positive_seconds,
        default=None,
        help=(
            "Initial-connection / cold-start deadline in seconds written into the "
            "entry. Default: [tool.sofer] mcp_connect_timeout_seconds."
        ),
    )
    mcp_add.add_argument(
        "--no-timeout",
        action="store_true",
        help=(
            "Omit the timeout keys entirely, restoring the pre-#287/#296 entry "
            "shape. For codex and gemini this is also the only path where sofer "
            "does not rewrite the config file: with the timeouts, native "
            "delegation declines and the file edit rewrites the whole document."
        ),
    )
    mcp_add.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing — no file or .bak is created.",
    )
    mcp_add.set_defaults(func=_cmd_mcp_add)

    mcp_remove = mcp_sub.add_parser(
        "remove",
        help="Remove sofer-mcp from the selected agent(s).",
        description=(
            "Remove the ``sofer`` entry idempotently. Preserves other "
            "servers, backs up before edit, and does no write when the entry "
            "is already absent. A YAML config edit preserves the rest of the "
            "document, while a TOML edit may strip comments. hermes reads a "
            "single user-scope config, so --scope project resolves to that "
            "same file and the substitution is named on stderr. Prefers native "
            "``mcp remove`` only when it can "
            "express the requested scope; otherwise it edits the config file "
            "and prints a warning naming the reason on stderr."
        ),
    )
    mcp_remove.add_argument(
        "--agent",
        choices=[*mcp_registration.AGENT_NAMES, "all"],
        required=True,
        help="Target agent or 'all' for every agent.",
    )
    mcp_remove.add_argument(
        "--scope",
        choices=["user", "project"],
        default="user",
        help="Config scope: 'user' (home directory) or 'project' (current directory).",
    )
    mcp_remove.add_argument(
        "--user-config",
        help=(
            "Explicit user-scope config FILE for the selected agent; wins over the "
            "adapter's env override and the home default. Rejected with --agent all."
        ),
    )
    mcp_remove.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing — no file or .bak is created.",
    )
    mcp_remove.set_defaults(func=_cmd_mcp_remove)

    mcp_doctor_parser = mcp_sub.add_parser(
        "doctor",
        help="Measure the real sofer-mcp cold start and print the deadline to configure.",
        description=(
            "Measure the real launch: spawn ``sofer-mcp`` (or the module entry "
            "point when the console script is not on PATH) and time the stdio "
            "``initialize`` round trip, which is what a host's connect/startup "
            "deadline covers - import timing measures the wrong thing. Prints the "
            "measured milliseconds beside the per-agent entry key and the value "
            "``sofer mcp add`` would write, so the two can be compared. The budget "
            "is ``[tool.sofer] mcp_connect_timeout_seconds``. Informational: "
            "exceeding the budget never changes the exit code, because a slow "
            "machine is not a broken registration. Reads and writes nothing."
        ),
    )
    mcp_doctor_parser.add_argument(
        "--agent",
        choices=[*mcp_registration.AGENT_NAMES, "all"],
        default=None,
        help="Report one agent's entry key instead of every registered agent.",
    )
    mcp_doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the machine-readable status line as stable JSON (CLI-R10).",
    )
    mcp_doctor_parser.set_defaults(func=_cmd_mcp_doctor)

    # ── meta ──────────────────────────────────────────────────────
    meta = sub.add_parser(
        "meta",
        help="Read and fill the dataset [meta] block (init placeholders, card values).",
        description=(
            "Read and write the dataset TOML's ``[meta]`` table. ``check`` "
            "reports which fields still carry a ``sofer init`` placeholder, the "
            "same warning ``sofer validate`` prints, queryable on demand. "
            "``set`` writes the keys it is given into ``[meta]``, preserving "
            "every other key, every comment and the rest of the document. "
            "The dataset TOML is the only file touched, and both surfaces mirror "
            "the ``sofer_meta_check`` / ``sofer_meta_set`` MCP tools."
        ),
    )
    meta_sub = meta.add_subparsers(dest="meta_command", required=True)

    meta_check = meta_sub.add_parser(
        "check",
        help="Report the [meta] fields still carrying an init placeholder (read-only).",
        description=(
            "Print one line per ``[meta]`` field that is empty or still starts "
            "with a ``meta_placeholder_prefixes`` value (``[tool.sofer]``, "
            "case-insensitive), plus one for placeholder ``tags``. Read-only: "
            "no file is written. Informational: the exit code is 0 whatever it "
            "reports, exactly like the warning ``sofer validate`` prints "
            "(issue #288's decision); only an unreadable config exits 1."
        ),
    )
    meta_check.add_argument(
        "config",
        help="Path to the dataset .toml configuration file to inspect.",
    )
    meta_check.add_argument(
        "--json",
        action="store_true",
        help=(
            "Emit the machine-readable status line as stable JSON (CLI-R10): "
            "ok, exit_code, message, placeholders, warnings."
        ),
    )
    meta_check.set_defaults(func=_cmd_meta_check)

    meta_set = meta_sub.add_parser(
        "set",
        help="Write [meta] keys into the dataset TOML, preserving everything else.",
        description=(
            "Write the given ``[meta]`` keys into the dataset TOML. Only the "
            "``[meta]`` table changes: other keys, comments, blank lines and "
            "every unrelated table survive byte for byte. The write is atomic "
            "(tmp + os.replace) and the edited document is parsed back before "
            "it replaces the file, so a refusal - an unknown key, a value of "
            "the wrong kind, a document that would not parse - writes nothing. "
            "``--set KEY=VALUE`` reads VALUE per the key's kind: text verbatim, "
            "a list as comma-separated items (``--set tags=a,b``, empty for "
            "``[]``), and a flag as ``true``/``false``. Re-running with the "
            "values the file already holds writes nothing. A ``build/`` tree "
            "that predates the write is named on stderr - the Dataset Card and "
            "LICENSE there still carry the old values until ``sofer prepare`` "
            "runs again."
        ),
    )
    meta_set.add_argument(
        "config",
        help="Path to the dataset .toml configuration file to edit.",
    )
    meta_set.add_argument(
        "--set",
        dest="assignments",
        action="append",
        required=True,
        metavar="KEY=VALUE",
        help=(
            "A [meta] key to write (repeatable), e.g. --set description='What it "
            "is' --set license=MIT --set source='Some org' --set tags=a,b. The "
            "value is read per the key's kind: text verbatim, a list as "
            "comma-separated items, a flag as true/false."
        ),
    )
    meta_set.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Compute and verify the edit, report the keys it would write, and "
            "leave the file untouched."
        ),
    )
    meta_set.add_argument(
        "--json",
        action="store_true",
        help=(
            "Emit the machine-readable status line as stable JSON (CLI-R10): "
            "ok, exit_code, message, dry_run, changed, written, unchanged."
        ),
    )
    meta_set.set_defaults(func=_cmd_meta_set)

    # ── report-failure ────────────────────────────────────────────
    rf = sub.add_parser(
        "report-failure",
        help="Retry sending a previously saved failure report through gh.",
        description=(
            "Send a failure report that the assisted reporter persisted to "
            "disk (one JSON file per failure under the sofer state directory, "
            "e.g. ~/.local/state/sofer/failure-reports/).  The report captures "
            "the command, its arguments, the error and traceback, and the "
            "sofer/Python/platform versions - never dataset contents, secret "
            "values, or un-anonymized home paths.  On success this prints the "
            "created GitHub issue URL.  If gh is still missing, unauthenticated, "
            "or offline it prints the saved path, this retry command, the "
            "manual github.com/<repo>/issues/new URL, and 'gh auth login'."
        ),
    )
    rf.add_argument(
        "file",
        help="Path to a persisted failure report (JSON) to send.",
    )
    rf.set_defaults(func=_cmd_report_failure)

    return parser


def _configure_console_streams() -> None:
    """Reconfigure the console text streams to substitute unencodable text (CLI-R11).

    Called as the FIRST statement of :func:`main`, ahead of ``config.reload`` and
    ``_build_parser``: argparse resolves ``sys.stdout`` at call time, so a guard placed
    after the parser is built would leave ``--help`` unfixed, and the ``config.reload``
    verbose line (a resolved path interpolated into an f-string) would stay exposed.
    Each stream is reconfigured *in place* with ``errors=config.CONSOLE_ERRORS``; the
    stream objects are never swapped or replaced, so stream identity -- and therefore the
    ``io.StringIO`` capture interleaving in :func:`sofer.mcp_server._capture_output` --
    is preserved.

    Defensive by construction (CLI-R11): a stream that cannot be reconfigured in place is
    left untouched and this function SHALL NOT raise. Two cases are skipped explicitly:
    a stream that is not an :class:`io.TextIOWrapper` (an in-memory capture object such as
    :class:`io.StringIO`, a foreign capture stream, or ``None``) and a real wrapper that
    refuses reconfiguration (a closed or detached buffer, or an ``OSError`` from the
    implicit flush when the stream's reader is gone).

    Returns:
        ``None``.  The only observable effect is the error handler of the process's
        ``sys.stdout`` / ``sys.stderr`` objects, which are the same objects on return.
    """
    for stream in (sys.stdout, sys.stderr):
        if not isinstance(stream, io.TextIOWrapper):
            continue
        try:
            stream.reconfigure(errors=config.CONSOLE_ERRORS)
        except (ValueError, OSError):
            continue


def main() -> None:
    """Entry point (installed via ``pyproject.toml [project.scripts]``).

    Orchestration:

        0. Console encoding guard: reconfigure ``sys.stdout``/``sys.stderr``
           in place so a character the active console encoding cannot
           represent is substituted rather than aborting the command
           (CLI-R11). Runs first so argparse's ``--help`` output and the
           ``config.reload`` verbose line are covered too.
        1. Phase-0 bootstrap: resolve ``[tool.sofer]`` anchored on the
           current working directory (``config.reload(None)``) so argparse
           defaults such as ``default_config_name`` reflect cwd-tree
           overrides before the parser is built (TC-07).
        2. Build the parser and dispatch; dataset commands re-resolve via
           ``DatasetConfig.from_toml`` (dataset-dir anchor, TC-04/TC-05).
        3. An uncaught command exception is handed to
           :func:`sofer.failure_report.report_cli_failure`, which re-prints the
           traceback and, on an interactive terminal only, offers to file a
           confidential GitHub issue (CLI-R13). The process still exits ``1``.

    ``SystemExit`` (argparse) and ``KeyboardInterrupt`` are never intercepted.
    """
    _configure_console_streams()
    config.reload(None)
    parser = _build_parser()
    args = parser.parse_args()
    try:
        exit_code = args.func(args)
    except Exception as exc:
        failure_report.report_cli_failure(sys.argv[1:], exc)
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
