"""Measure the peak memory and wall time of a real ``sofer validate`` run.

Issue #306's verification gap: #290 bounded every per-row accumulator in the
quality scan, and the delivered evidence was **structural** — identical
accumulator sizes after 100 and after 3 000 rows, and a ``tracemalloc``-measured
~143 B per tracked duplicate row. No run reported what the fixed code costs on a
large corpus, so the issue's acceptance ("validate/prepare can now run on
multi-GB datasets") was asserted rather than shown.

This script produces the end-to-end number. It generates a synthetic corpus in a
temporary directory and measures the same run twice:

1. **In process, under ``tracemalloc``** — the peak Python allocation of the
   whole validation pass, plus wall time. Always available (stdlib).
2. **As a subprocess, sampling its process subtree** — peak RSS plus wall time,
   reported **only when the sampler passes a self-calibration** (below). The
   subtree matters because ``sys.executable`` need not be the process that does
   the work (see :func:`_rss_bytes_of_tree`).

The self-calibration matters and is not ceremony: on the Windows host this was
first developed on, the sampler reported 5.2 MiB for every child, including one
that had touched a 300 MiB allocation. The platform code was not at fault, and
the constant was not a stale counter: ``sys.executable`` in a uv-managed venv is
a launcher that spawns the real interpreter as its child, so the sampler was
reading an idle trampoline while the memory sat one hop below it. The sampler
therefore measures the whole process subtree before comparing anything, and it
still refuses to publish a number its calibration has not accepted.

Both quality configurations of the issue's step 3 are measured, so the output
shows the knobs move the number rather than only that one number exists.

Deliberately outside the CI matrix: a multi-GB run does not belong in a
three-minute job. Run it by hand and record the output as evidence.

Usage::

    uv run python scripts/measure_quality_scan_rss.py --rows 5000000
    uv run python scripts/measure_quality_scan_rss.py --rows 5000000 --keep

The corpus is removed unless ``--keep`` is passed.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

# ── Corpus shape ──────────────────────────────────────────────────────────────
# Rows per CSV chunk. The corpus is written in chunks so generating it does not
# itself need unbounded memory.
CHUNK_ROWS: int = 100_000

COLUMNS: tuple[str, ...] = (
    "id",
    "region",
    "district",
    "household_size",
    "income",
    "notes",
)

# Deliberately repeated values so the `duplicates` check has real per-row hashing
# to do — it is the accumulator the cap bounds.
DUPLICATE_EVERY: int = 17

REGIONS: tuple[str, ...] = ("north", "south", "east", "west", "central")

# A second file with a different schema, exercising the mixed-schema card path
# (#292/#304) alongside the quality scan.
SECOND_COLUMNS: tuple[str, ...] = ("code", "label", "amount")

SECOND_ROWS: int = 50_000

# Sampling interval for the child's resident set.
RSS_SAMPLE_SECONDS: float = 0.05

# How many process hops the subtree reading follows. One hop is what a uv venv's
# launcher needs; the bound exists so an unforeseen process tree cannot turn a
# 20 Hz sampler into an unbounded one.
RSS_TREE_MAX_DEPTH: int = 4

# Toolhelp32 snapshot flag for the process list (winbase.h).
TH32CS_SNAPPROCESS: int = 0x00000002

# The `[tool.sofer]` ``quality_max_dup_tracking`` default that the "defaults"
# case measures, restated as a constant so the case does not silently follow a
# developer's own pyproject.
DEFAULT_DUP_CAP: int = 1_000_000

# A cap below the corpus's distinct-row-hash count (~294 000 at 5 M rows), paired
# with the *default* full-scan policy. The first and third cases cannot show
# whether the cap bounds the peak — the shipped 1 000 000 cap is never reached on
# this corpus shape, so both of them measure an uncapped hash table (issue #317,
# item 1). This case is what makes the two default-policy peaks comparable.
BOUND_DUP_CAP: int = 100_000

# The lowered cap used by the bounded case. Small enough that the `duplicates`
# finding is marked partial and the hash table stays tiny.
LOWERED_DUP_CAP: int = 10_000

# ── Sampler self-calibration ──────────────────────────────────────────────────
# A child that TOUCHES this many mebibytes must be reported at no less than
# CALIBRATION_MIN_RATIO of it, or the sampler is declared unreliable.
CALIBRATION_MIB: int = 200
CALIBRATION_MIN_RATIO: float = 0.5

DATASET_TOML: str = """\
[dataset]
name = "{name}"
repo_id = "example/{name}"
repo_type = "dataset"
private = true
build_dir = "build"

[meta]
description = "Synthetic corpus for the bounded-scan memory measurement (issue #306)"
license = "MIT"
confidential = false
source = "sofer measurement harness"

[[file]]
local = "raw/{first}"
remote = "{first}"

[[file]]
local = "raw/{second}"
remote = "{second}"
"""

PYPROJECT_TOML: str = """\
[tool.sofer]
quality_full_scan = "{full_scan}"
quality_max_dup_tracking = {dup_cap}
"""


def _rss_bytes(pid: int) -> int | None:
    """Return the resident set size of *pid* in bytes, or ``None``.

    Three platform paths, tried in order, with no dependency added: Linux and
    WSL read ``/proc/<pid>/statm``; Windows calls ``GetProcessMemoryInfo``
    through :mod:`ctypes`; anything else shells out to ``ps``. ``None`` means the
    platform cannot report it. The caller MUST calibrate before trusting a value
    (see :func:`_sampler_is_trustworthy`).

    Args:
        pid: Process id to sample.

    Returns:
        Resident bytes, or ``None`` when unavailable.
    """
    statm = Path(f"/proc/{pid}/statm")
    try:
        if statm.exists():
            pages = int(statm.read_text(encoding="ascii").split()[1])
            sysconf = getattr(os, "sysconf", None)
            if sysconf is None:  # pragma: no cover - non-POSIX host
                return None
            return int(pages * sysconf("SC_PAGE_SIZE"))
    except (OSError, ValueError):
        return None

    windll = getattr(__import__("ctypes"), "windll", None)
    if windll is not None:  # pragma: no cover - Windows-only path
        try:
            import ctypes
            from ctypes import wintypes

            class _Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            handle = windll.kernel32.OpenProcess(0x0400 | 0x1000, False, pid)
            if not handle:
                return None
            try:
                counters = _Counters()
                counters.cb = ctypes.sizeof(counters)
                if not windll.psapi.GetProcessMemoryInfo(
                    handle, ctypes.byref(counters), counters.cb
                ):
                    return None
                return int(counters.WorkingSetSize)
            finally:
                windll.kernel32.CloseHandle(handle)
        except (OSError, AttributeError):
            return None

    try:
        out = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except OSError:
        return None
    if not out.isdigit():
        return None
    return int(out) * 1024


def _windows_child_pids(pid: int) -> list[int]:
    """Return *pid*'s direct children through a Toolhelp32 process snapshot.

    Args:
        pid: Parent process id.

    Returns:
        The children's process ids, or ``[]`` on a host without the Windows API
        or when the snapshot cannot be taken.
    """
    windll = getattr(__import__("ctypes"), "windll", None)
    if windll is None:  # pragma: no cover - non-Windows host
        return []
    import ctypes
    from ctypes import wintypes

    class _ProcessEntry32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    kernel32 = windll.kernel32
    # HANDLE is pointer-sized: without these two lines ctypes truncates it to a
    # 32-bit int, which happens to work for small handle values and is therefore
    # a trap rather than a visible defect.
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (0, None, ctypes.c_void_p(-1).value):  # pragma: no cover - API failure
        return []
    entry = _ProcessEntry32()
    entry.dwSize = ctypes.sizeof(_ProcessEntry32)
    children: list[int] = []
    try:
        present = kernel32.Process32First(snapshot, ctypes.byref(entry))
        while present:
            if entry.th32ParentProcessID == pid:
                children.append(int(entry.th32ProcessID))
            present = kernel32.Process32Next(snapshot, ctypes.byref(entry))
    except (OSError, AttributeError):  # pragma: no cover - API failure
        return []
    finally:
        kernel32.CloseHandle(snapshot)
    return children


def _child_pids(pid: int) -> list[int]:
    """Return the direct children of *pid*, using this host's cheapest reader.

    Child enumeration is the one part of the subtree measurement with no portable
    stdlib answer, and the script adds no dependency, so each host gets the
    smallest interface that answers it: ``/proc`` on Linux and WSL, a Toolhelp32
    snapshot on Windows (see :func:`_windows_child_pids`), and nothing
    elsewhere. ``[]`` means "no known descendants" — which is exactly what the
    sampler assumed before it walked subtrees at all.

    Args:
        pid: Process id whose children to list.

    Returns:
        The direct children's process ids, possibly empty.
    """
    proc_children = Path(f"/proc/{pid}/task/{pid}/children")
    try:
        if proc_children.is_file():
            return [int(token) for token in proc_children.read_text(encoding="ascii").split()]
    except (OSError, ValueError):
        return []
    return _windows_child_pids(pid)


def _rss_bytes_of_tree(pid: int) -> int | None:
    """Return the resident set of *pid* plus its descendants, in bytes.

    The process a measurement spawns is not always the process that does the
    work: a ``sys.executable`` inside a uv-managed venv is a launcher whose child
    is the real interpreter. Summing the subtree makes the reading independent of
    whether that hop exists, instead of encoding one platform's launcher shape
    into the measurement.

    The walk is bounded by :data:`RSS_TREE_MAX_DEPTH` and stops as soon as a
    level reports no children.

    Args:
        pid: Root process id of the subtree.

    Returns:
        Total resident bytes, or ``None`` when the root itself cannot be read.
        A descendant that cannot be read is skipped rather than failing the
        whole measurement.
    """
    root = _rss_bytes(pid)
    if root is None:
        return None
    total = root
    frontier = [pid]
    for _ in range(RSS_TREE_MAX_DEPTH):
        descendants: list[int] = []
        for parent in frontier:
            descendants.extend(_child_pids(parent))
        if not descendants:
            break
        for descendant in descendants:
            reading = _rss_bytes(descendant)
            if reading is not None:
                total += reading
        frontier = descendants
    return total


def _peak_rss_of(code: str, seconds: float) -> int | None:
    """Run *code* in a child and return the highest RSS sampled from its tree.

    Args:
        code: Python source for the child.
        seconds: How long to keep sampling.

    Returns:
        Peak resident bytes of the child and its descendants, or ``None`` when
        the sampler could not read it.
    """
    child = subprocess.Popen([sys.executable, "-c", code])
    peak = 0
    deadline = time.perf_counter() + seconds
    try:
        while child.poll() is None and time.perf_counter() < deadline:
            current = _rss_bytes_of_tree(child.pid)
            if current is None:
                return None
            peak = max(peak, current)
            time.sleep(RSS_SAMPLE_SECONDS)
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()
    return peak or None


def _sampler_is_trustworthy() -> tuple[bool, int, int]:
    """Check the RSS sampler against a child whose footprint is known.

    Returns:
        ``(trustworthy, reported_bytes, expected_bytes)``. The child touches
        :data:`CALIBRATION_MIB` of memory; a sampler that reports less than
        :data:`CALIBRATION_MIN_RATIO` of that is declared unreliable and no RSS
        number is published.
    """
    mib = CALIBRATION_MIB
    code = (
        "import time\n"
        f"b = bytearray({mib} * 1024 * 1024)\n"
        "for i in range(0, len(b), 4096):\n"
        "    b[i] = 1\n"
        "time.sleep(3)\n"
    )
    reported = _peak_rss_of(code, seconds=4.0)
    expected = mib * 1024 * 1024
    if reported is None:
        return False, 0, expected
    return reported >= int(expected * CALIBRATION_MIN_RATIO), reported, expected


def _write_csv(path: Path, columns: tuple[str, ...], rows: int, *, dup_every: int) -> None:
    """Write *rows* synthetic data rows to *path* in memory-bounded chunks.

    Args:
        path: Destination CSV (semicolon-delimited, like sofer's own defaults).
        columns: Header columns. :data:`COLUMNS` selects the primary shape.
        rows: How many data rows to write.
        dup_every: Every *dup_every*-th row repeats the current bucket's values,
            so the duplicate hash table has real entries.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    primary = columns is COLUMNS
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=";", lineterminator="\n")
        writer.writerow(columns)
        chunk: list[list[str]] = []
        for i in range(rows):
            bucket = i - (i % dup_every)
            if primary:
                chunk.append(
                    [
                        str(bucket),
                        REGIONS[(bucket // dup_every) % len(REGIONS)],
                        f"d{bucket % 1_000}",
                        str(1 + bucket % 9),
                        str(1_000 + bucket % 5_000),
                        f"note {bucket % 97}",
                    ]
                )
            else:
                chunk.append([f"c{bucket}", f"label {bucket % 31}", str(bucket % 7_000)])
            if len(chunk) >= CHUNK_ROWS:
                writer.writerows(chunk)
                chunk.clear()
        writer.writerows(chunk)


def _build_corpus(root: Path, rows: int) -> tuple[Path, Path, Path]:
    """Generate the corpus, the dataset TOML and the tool-config home.

    Returns:
        ``(config_path, corpus_dir, pyproject_path)``.
    """
    corpus = root / "corpus"
    first, second = "households.csv", "codes.csv"
    _write_csv(corpus / "raw" / first, COLUMNS, rows, dup_every=DUPLICATE_EVERY)
    _write_csv(corpus / "raw" / second, SECOND_COLUMNS, SECOND_ROWS, dup_every=DUPLICATE_EVERY)
    config = corpus / "dataset.toml"
    config.write_text(
        DATASET_TOML.format(name="memory_probe", first=first, second=second), encoding="utf-8"
    )
    return config, corpus, corpus / "pyproject.toml"


def _in_process_run(
    config_path: Path, corpus: Path, *, full_scan: str, dup_cap: int
) -> dict[str, Any]:
    """Validate the corpus in this process under ``tracemalloc``.

    Mirrors the CLI's own validate sequence (``DatasetConfig.from_toml`` →
    ``DatasetValidator.run_all`` → ``QualityValidator.run``), with the tool-config
    discovery anchored at the corpus so the case's ``[tool.sofer]`` values apply.

    Args:
        config_path: Dataset TOML path.
        corpus: Directory anchoring ``[tool.sofer]`` discovery.
        full_scan: ``quality_full_scan`` value for this case.
        dup_cap: ``quality_max_dup_tracking`` value for this case.

    Returns:
        ``{"peak_bytes", "seconds", "quality_results"}``.
    """
    sofer_config = importlib.import_module("sofer.config")
    model = importlib.import_module("sofer.model")
    checks = importlib.import_module("sofer.checks")
    quality = importlib.import_module("sofer.quality")

    (corpus / "pyproject.toml").write_text(
        PYPROJECT_TOML.format(full_scan=full_scan, dup_cap=dup_cap), encoding="utf-8"
    )
    sofer_config.reload(start=str(corpus))
    try:
        tracemalloc.start()
        started = time.perf_counter()
        cfg = model.DatasetConfig.from_toml(str(config_path))
        errors = cfg.validate()
        if errors:
            raise RuntimeError(f"corpus config invalid: {errors[0]}")
        report = checks.DatasetValidator(cfg).run_all()
        quality_report = quality.QualityValidator(cfg).run()
        elapsed = time.perf_counter() - started
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    finally:
        sofer_config.reload()
    return {
        "peak_bytes": peak,
        "tm_seconds": elapsed,
        "quality_results": len(quality_report.quality_results),
        "ran_checks": len(report.ran_checks),
    }


def _subprocess_run(
    config_path: Path, corpus: Path, *, full_scan: str, dup_cap: int
) -> dict[str, Any]:
    """Run ``sofer validate`` as a subprocess, sampling its tree's RSS.

    The reading covers the spawned process and its descendants, because
    ``sys.executable`` need not be the interpreter that does the work (see
    :func:`_rss_bytes_of_tree`).

    Args:
        config_path: Dataset TOML path.
        corpus: Working directory for the child (so discovery anchors there).
        full_scan: ``quality_full_scan`` value for this case.
        dup_cap: ``quality_max_dup_tracking`` value for this case.

    Returns:
        ``{"exit_code", "seconds", "peak_rss_bytes"}``.
    """
    (corpus / "pyproject.toml").write_text(
        PYPROJECT_TOML.format(full_scan=full_scan, dup_cap=dup_cap), encoding="utf-8"
    )
    started = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "-m", "sofer.cli", "validate", str(config_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(corpus),
    )
    peak = 0
    while proc.poll() is None:
        current = _rss_bytes_of_tree(proc.pid)
        if current is None:
            proc.kill()
            proc.communicate()
            return {
                "exit_code": -1,
                "seconds": time.perf_counter() - started,
                "peak_rss_bytes": None,
            }
        peak = max(peak, current)
        time.sleep(RSS_SAMPLE_SECONDS)
    elapsed = time.perf_counter() - started
    proc.communicate()
    return {
        "exit_code": proc.returncode,
        "seconds": elapsed,
        "peak_rss_bytes": peak or None,
    }


def _mib(value: object) -> str:
    """Render a byte count as mebibytes, or ``n/a``."""
    return f"{int(value) / (1024 * 1024):.1f}" if isinstance(value, int) and value else "n/a"


def main(argv: list[str] | None = None) -> int:
    """Generate the corpus, run both cases, print the measurement table.

    Args:
        argv: Argument vector without the program name.

    Returns:
        ``0`` when every case ran, ``1`` when a validation run exited non-zero.
    """
    parser = argparse.ArgumentParser(
        description="Measure peak memory and wall time of a real `sofer validate` run."
    )
    parser.add_argument(
        "--rows", type=int, default=5_000_000, help="Rows in the primary CSV (default: 5000000)."
    )
    parser.add_argument(
        "--keep", action="store_true", help="Keep the corpus directory instead of removing it."
    )
    parser.add_argument(
        "--corpus-dir", default=None, help="Corpus directory (default: a temporary directory)."
    )
    parser.add_argument(
        "--skip-rss",
        action="store_true",
        help="Skip the subprocess RSS pass entirely (in-process tracemalloc only).",
    )
    args = parser.parse_args(argv)

    root = Path(args.corpus_dir) if args.corpus_dir else Path(tempfile.mkdtemp(prefix="sofer-rss-"))
    root.mkdir(parents=True, exist_ok=True)
    try:
        config, corpus, _pyproject = _build_corpus(root, args.rows)
        primary = corpus / "raw" / "households.csv"
        print(f"corpus: {primary}")
        print(
            f"shape:  {args.rows:,} rows x {len(COLUMNS)} columns "
            f"({primary.stat().st_size / (1024 * 1024):.1f} MiB)"
        )
        print(f"        + {SECOND_ROWS:,} rows x {len(SECOND_COLUMNS)} columns (second schema)")
        print(f"        duplicate value every {DUPLICATE_EVERY} rows")
        print()

        rss_ok = False
        reported = expected = 0
        if not args.skip_rss:
            rss_ok, reported, expected = _sampler_is_trustworthy()
            verdict = "trustworthy" if rss_ok else "UNRELIABLE"
            print(
                f"rss sampler calibration: {verdict} "
                f"(a child holding {expected / (1024 * 1024):.0f} MiB was reported at "
                f"{reported / (1024 * 1024):.1f} MiB)"
            )
            if not rss_ok:
                print(
                    "  note: no RSS number will be printed — a sampler that cannot see a\n"
                    "        known 200 MiB child cannot be trusted to measure a real run.\n"
                )
        print()

        cases: list[tuple[str, str, int]] = [
            ("defaults (fail check forces the full scan)", "auto", DEFAULT_DUP_CAP),
            ("default policy, cap reached", "auto", BOUND_DUP_CAP),
            ("bounded knobs", "never", LOWERED_DUP_CAP),
        ]
        rows: list[dict[str, Any]] = []
        for label, full_scan, dup_cap in cases:
            print(f"running: {label} ...", flush=True)
            inproc = _in_process_run(config, corpus, full_scan=full_scan, dup_cap=dup_cap)
            sub = (
                {"exit_code": None, "seconds": None, "peak_rss_bytes": None}
                if not rss_ok
                else _subprocess_run(config, corpus, full_scan=full_scan, dup_cap=dup_cap)
            )
            rows.append(
                {"label": label, "full_scan": full_scan, "dup_cap": dup_cap, **inproc, **sub}
            )

        print()
        print(
            f"{'case':<44} {'tm peak MiB':>12} {'tm sec':>7} {'rss exit':>8} "
            f"{'peak RSS MiB':>13} {'rss sec':>8}"
        )
        print("-" * 100)
        for row in rows:
            rss_seconds = row["seconds"]
            rss_text = "n/a" if rss_seconds is None else f"{rss_seconds:.1f}"
            print(
                f"{row['label']:<44} {_mib(row['peak_bytes']):>12} "
                f"{row['tm_seconds']:>7.1f} {row['exit_code']!s:>8} "
                f"{_mib(row['peak_rss_bytes']):>13} {rss_text:>8}"
            )
        print()
        print("knobs per case (quality_full_scan / quality_max_dup_tracking):")
        for row in rows:
            print(f"  {row['label']}: {row['full_scan']} / {row['dup_cap']:,}")
        print()
        print("tm peak MiB = peak Python allocation of the in-process pass (tracemalloc).")
        if rss_ok:
            print("peak RSS MiB = highest resident set sampled from the child process.")
        else:
            print("peak RSS MiB = not measured: the sampler failed its self-calibration.")
        bad = [r for r in rows if r["exit_code"] not in (None, 0)]
        if bad:
            print(f"\nX  a validation run exited non-zero: {[r['exit_code'] for r in bad]}")
            return 1
        return 0
    finally:
        if args.keep:
            print(f"\ncorpus kept at {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
