"""Static contract guard for the per-file coverage policy (COV-01/03/06).

Skip-if-absent local read + static scans only: the enforcement of the four core
100% rows lives in the CI per-file gates (COV-06), and the three ≥90 floors and
TOTAL are verify-phase runtime evidence (COV-01/02) — measured percentages are
never pytest-asserted here beyond the sanctioned local ``.coverage`` read when
the data file is present (skips on a clean checkout).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

_CORE_MODULES = ("cli.py", "scanner.py", "prepare.py", "publish.py")

_FLOOR_MODULES = ("profile.py", "mcp_registration.py", "verification.py")


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
    """COV-01/02: when a local .coverage data file exists, the three floor rows
    and TOTAL must meet the 90% bar (read-only, best-effort regression pin).

    An empty or partial mid-run database is treated as absent → the guard skips
    rather than failing on transient state (COV-01-S3).
    """
    import coverage

    cov = coverage.Coverage(data_file=str(_REPO_ROOT / ".coverage"))
    cov.load()
    data = cov.get_data()
    measured = data.measured_files()
    if not measured:
        pytest.skip("empty/partial coverage database — treated as absent")

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
