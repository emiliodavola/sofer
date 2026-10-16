"""Static contract guard for the per-file coverage policy (COV-01/03/06).

Skip-if-absent local read + static scans only: the enforcement of the four core
100% rows lives in the CI per-file gates (COV-06), and the three ≥90 floors and
TOTAL are verify-phase runtime evidence (COV-01/02) — measured percentages are
never pytest-asserted here beyond the sanctioned local ``.coverage`` read when
the data file is present (skips on a clean checkout).

The sanctioned read asserts only on a database this process can vouch for
(issue #305): it must exist, no measurement may be in flight, and it must be at
least as new as every file it measured.  Residual limitation, named rather than
hidden: a ``coverage run`` over a *subset* of the suite also leaves a fresh,
complete-looking database, and coverage data records no provenance about which
tests ran (mitigated only by the measured-files check below).
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

_CORE_MODULES = ("cli.py", "scanner.py", "prepare.py", "publish.py")

_FLOOR_MODULES = ("profile.py", "mcp_registration.py", "verification.py")


def _vouch_for_coverage_data(
    data_file: Path,
    measured: list[str],
    env: Mapping[str, str],
) -> str | None:
    """Return why the guard cannot vouch for *data_file*, or ``None``.

    The guard may only assert on a database attributable to the current tree
    (issue #305), which requires three conditions in order:

    1. the file exists — a clean checkout has nothing to assert on;
    2. the measurement is not in flight: ``coverage run`` sets ``COVERAGE_RUN``
       and flushes its data only at process exit, so during the run the file on
       disk belongs to a previous run;
    3. the database is at least as new as every file it measured (``>=`` because
       filesystem timestamps have limited granularity), and none of the measured
       paths has disappeared.

    Args:
        data_file: Candidate ``.coverage`` database.
        measured:  Paths the database measured (empty before it is loaded).
        env:       Environment to read ``COVERAGE_RUN`` from.

    Returns:
        A skip reason naming the failed condition, or ``None`` when the database
        may be asserted on.
    """
    if not data_file.exists():
        return "no local .coverage data file (clean checkout — CI measurement is the arbiter)"
    if env.get("COVERAGE_RUN"):
        return (
            "coverage run in progress: its data file is flushed at process exit, "
            "so the file on disk is not this run's"
        )

    db_mtime = data_file.stat().st_mtime
    for path_str in measured:
        measured_path = Path(path_str)
        if not measured_path.exists():
            return f"stale coverage database: it measured {path_str}, which no longer exists"
        if measured_path.stat().st_mtime > db_mtime:
            return (
                "stale coverage database: it is older than a file it measured "
                f"({measured_path.name}) — run `uv run coverage run -m pytest` "
                "for current numbers"
            )
    return None


def test_core_modules_contain_no_pragma_tokens() -> None:
    """COV-03/06: zero pragma tokens in the four core modules (full-text scan).

    Catches both ``# pragma: no cover`` and ``#pragma: no cover`` spellings —
    the token scan spans the whole file, not just the diff.
    """
    for name in _CORE_MODULES:
        text = (_REPO_ROOT / "src" / "sofer" / name).read_text(encoding="utf-8")
        assert re.search(r"#\s*pragma:\s*no cover", text, re.IGNORECASE) is None, (
            f"pragma token found in src/sofer/{name}"
        )


@pytest.mark.skipif(
    not (_REPO_ROOT / ".coverage").exists(),
    reason="no local .coverage data file (clean checkout — CI measurement is the arbiter)",
)
def test_three_floor_modules_and_total_meet_90_when_data_file_present() -> None:
    """COV-01/02: when a local, vouchable .coverage data file exists, the three
    floor rows and TOTAL must meet the 90% bar (read-only, best-effort
    regression pin).

    The guard asserts only on data it can attribute to the current tree (#305): a
    missing file, a measurement in flight, or a database older than the files it
    measured is skipped with a named reason instead of failing on numbers that
    describe a different tree.  An empty or partial mid-run database is treated
    as absent → the guard skips rather than failing on transient state
    (COV-01-S3).
    """
    import coverage

    data_file = _REPO_ROOT / ".coverage"
    reason = _vouch_for_coverage_data(data_file, [], os.environ)
    if reason is not None:
        pytest.skip(reason)

    cov = coverage.Coverage(data_file=str(data_file))
    cov.load()
    data = cov.get_data()
    measured = data.measured_files()
    if not measured:
        pytest.skip("empty/partial coverage database — treated as absent")

    reason = _vouch_for_coverage_data(data_file, measured, os.environ)
    if reason is not None:
        pytest.skip(reason)

    def pct(suffix: str | None) -> float | None:
        """Executed-statement percentage over matching measured files.

        *suffix* is ``None`` to aggregate every ``src/sofer`` module (the TOTAL
        row); a module filename suffix selects one file. ``None`` result means
        no measured file matched — a partial mid-run database, which the guard
        treats as absent (skip) rather than failing.
        """
        if suffix is None:
            matches = [m for m in measured if "/src/sofer/" in m.replace("\\", "/")]
        else:
            matches = [m for m in measured if m.replace("\\", "/").endswith(suffix)]
        if not matches:
            return None
        total = 0
        executed = 0
        for m in matches:
            _, executed_lines, _excluded, missing_lines, _fmt = cov.analysis2(m)
            total += len(executed_lines) + len(missing_lines)
            executed += len(executed_lines)
        return (executed / total) * 100.0 if total else None

    for name in _FLOOR_MODULES:
        value = pct(f"src/sofer/{name}")
        if value is None:
            pytest.skip(f"partial database: src/sofer/{name} not measured yet")
        assert value >= 90.0, f"src/sofer/{name} measured {value:.1f}% locally (< 90)"

    value = pct(None)
    if value is None:
        pytest.skip("partial database: no src/sofer files measured yet")
    assert value >= 90.0, f"TOTAL measured {value:.1f}% locally (< 90)"


def test_gate_machinery_bounded() -> None:
    """COV-03: the gate machinery is bounded — config floor intact, no XML or
    third-party coverage references in the workflows."""
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r"fail_under\s*=\s*90\s*$", pyproject, re.MULTILINE) is not None
    for workflow in ("ci.yml", "release.yml"):
        raw = (_REPO_ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8").lower()
        assert "coverage xml" not in raw
        assert "codecov" not in raw
        assert "coveralls" not in raw


def _pinned_file(tmp_path: Path, name: str, mtime: float) -> Path:
    """Write *name* under *tmp_path* with an exact mtime and return it."""
    path = tmp_path / name
    path.write_text("x = 1\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path


def test_vouch_rejects_missing_data_file(tmp_path):
    """A clean checkout has nothing to assert on (COV-01-S3)."""
    reason = _vouch_for_coverage_data(tmp_path / ".coverage", [], {})
    assert reason is not None
    assert "no local .coverage" in reason


def test_vouch_rejects_in_flight_measurement(tmp_path):
    """Under `coverage run` the file on disk is not this run's (D1)."""
    db = _pinned_file(tmp_path, ".coverage", 2000.0)
    source = _pinned_file(tmp_path, "mod.py", 1000.0)
    reason = _vouch_for_coverage_data(db, [str(source)], {"COVERAGE_RUN": "true"})
    assert reason is not None
    assert "coverage run in progress" in reason


def test_vouch_rejects_stale_database(tmp_path):
    """The live false positive of #305: the numbers predate the sources."""
    db = _pinned_file(tmp_path, ".coverage", 1000.0)
    source = _pinned_file(tmp_path, "mod.py", 2000.0)
    reason = _vouch_for_coverage_data(db, [str(source)], {})
    assert reason is not None
    assert "stale coverage database" in reason
    assert "mod.py" in reason


def test_vouch_rejects_measured_path_that_vanished(tmp_path):
    """A deleted source file makes the database unattributable."""
    db = _pinned_file(tmp_path, ".coverage", 2000.0)
    reason = _vouch_for_coverage_data(db, [str(tmp_path / "gone.py")], {})
    assert reason is not None
    assert "no longer exists" in reason


def test_vouch_accepts_database_as_new_as_its_files(tmp_path):
    """Equal mtimes are accepted (filesystem timestamp granularity)."""
    source = _pinned_file(tmp_path, "mod.py", 1000.0)
    db = _pinned_file(tmp_path, ".coverage", 1000.0)
    assert _vouch_for_coverage_data(db, [str(source)], {}) is None


def test_vouch_accepts_database_newer_than_its_files(tmp_path):
    """A database produced after its sources may be asserted on."""
    source = _pinned_file(tmp_path, "mod.py", 1000.0)
    db = _pinned_file(tmp_path, ".coverage", 3000.0)
    assert _vouch_for_coverage_data(db, [str(source)], {}) is None
