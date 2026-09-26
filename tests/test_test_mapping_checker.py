"""Behavior tests for the spec test-mapping checker (``scripts/check_test_mapping.py``).

Every test drives the checker as a **subprocess** against a temp fixture tree and
asserts observable outcomes only — exit code and the reported offender — per the
``mapping-checker`` (MC-01..MC-07) and ``test-mapping-contract`` (TMC-01..TMC-05)
capabilities. There is no ``sys.path`` mutation and no import of the script: its
CLI is the public boundary. A fake ``--collect-only-cmd`` prints a controlled
node-id set so collection is deterministic and offline; one integration test runs
the checker against the real repository tree.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CHECKER = _REPO_ROOT / "scripts" / "check_test_mapping.py"

_DUMMY_TEST = "tests/test_fake.py"

# A fake pytest: prints the node ids named by FAKE_COLLECT_OUTPUT, ignoring the
# collection flags the checker appends. Lets the tests control the collected set
# without spawning real pytest for every case.
_FAKE_COLLECT = (
    "import os\n"
    "for line in os.environ.get('FAKE_COLLECT_OUTPUT', '').splitlines():\n"
    "    if line.strip():\n"
    "        print(line)\n"
)


def _write(root: Path, rel: str, content: str) -> None:
    """Write a UTF-8 file under ``root``, creating parent directories."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _spec_with_rows(scenario: str, rows: list[str]) -> str:
    """Build a one-scenario spec with the given Test Mapping data rows."""
    return (
        "# alpha Specification\n\n"
        "## Requirements\n\n"
        "### Requirement: Alpha (X-01)\n\n"
        "Body.\n\n"
        f"#### Scenario: {scenario}\n\n"
        "- GIVEN a thing\n- WHEN it runs\n- THEN it works\n\n"
        "## Test Mapping\n\n"
        "| Req | Scenario | Verification |\n"
        "| --- | --- | --- |\n" + "\n".join(rows) + "\n"
    )


def _mapped_spec(verification: str, *, scenario: str = "Alpha scenario") -> str:
    """Build a mapped spec whose single row names ``scenario`` and ``verification``."""
    return _spec_with_rows(scenario, [f"| X-01 | {scenario} | {verification} |"])


def _two_scenario_spec(rows: list[str]) -> str:
    """Build a two-scenario spec with the given Test Mapping data rows."""
    return (
        "# alpha Specification\n\n"
        "## Requirements\n\n"
        "#### Scenario: Alpha one\n\n- GIVEN a thing\n\n"
        "#### Scenario: Alpha two\n\n- GIVEN a thing\n\n"
        "## Test Mapping\n\n"
        "| Req | Scenario | Verification |\n"
        "| --- | --- | --- |\n" + "\n".join(rows) + "\n"
    )


def _unmapped_spec() -> str:
    """Build a spec with no ``## Test Mapping`` section."""
    return (
        "# beta Specification\n\n"
        "## Requirements\n\n"
        "### Requirement: Beta (Y-01)\n\n"
        "#### Scenario: Beta scenario\n\n"
        "- GIVEN a thing\n- WHEN it runs\n- THEN it works\n"
    )


def _registry(root: Path, entries: list[tuple[str, str]]) -> None:
    """Write the registry with a ``| Spec | Reason |`` table."""
    lines = ["# Test Mapping Registry", "", "| Spec | Reason |", "| --- | --- |"]
    lines += [f"| {spec} | {reason} |" for spec, reason in entries]
    _write(root, "openspec/test-mapping-registry.md", "\n".join(lines) + "\n")


def _run_checker(
    root: Path,
    *,
    collect_output: str = "",
    args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the checker against ``root`` with a controllable fake collection."""
    fake = root / "fake_collect.py"
    fake.write_text(_FAKE_COLLECT, encoding="utf-8")
    env = {**os.environ, "FAKE_COLLECT_OUTPUT": collect_output}
    command = [
        sys.executable,
        str(_CHECKER),
        "--repo-root",
        str(root),
        "--collect-only-cmd",
        f"{sys.executable} {fake}",
        *(args or []),
    ]
    return subprocess.run(command, capture_output=True, text=True, check=False, env=env)


def _seed_baseline(
    root: Path,
    verification: str,
    *,
    collect_output: str = f"{_DUMMY_TEST}::test_one",
    registered: bool = True,
) -> str:
    """Seed one mapped spec + one unmapped spec + registry; return collect output."""
    _write(root, _DUMMY_TEST, "")
    _write(root, "openspec/specs/alpha/spec.md", _mapped_spec(verification))
    _write(root, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(root, [("beta", "declared backlog")] if registered else [])
    return collect_output


def _combined(result: subprocess.CompletedProcess[str]) -> str:
    """Return the checker's stdout+stderr for offender assertions."""
    return result.stdout + result.stderr


def test_compliant_fixture_tree_exits_zero(tmp_path: Path) -> None:
    """MC-06 S1: a compliant mapped spec + bijective registry exits 0."""
    collect = _seed_baseline(tmp_path, f"test:{_DUMMY_TEST}::test_one")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode == 0, _combined(result)


def test_heading_without_data_rows_is_unmapped(tmp_path: Path) -> None:
    """MC-01 S2: a heading with header/separator but no data row is unmapped."""
    _write(
        tmp_path,
        "openspec/specs/gamma/spec.md",
        "# gamma Specification\n\n## Test Mapping\n\n"
        "| Req | Scenario | Verification |\n| --- | --- | --- |\n",
    )
    _registry(tmp_path, [("gamma", "declared backlog")])
    result = _run_checker(tmp_path)
    assert result.returncode == 0, _combined(result)


def test_row_without_prefix_fails(tmp_path: Path) -> None:
    """TMC-01: a Verification cell with no prefix is non-compliant."""
    collect = _seed_baseline(tmp_path, _DUMMY_TEST)
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "prefix" in _combined(result)


def test_row_with_two_prefixes_fails(tmp_path: Path) -> None:
    """TMC-01: a cell carrying both prefixes is non-compliant."""
    collect = _seed_baseline(tmp_path, f"test: verify: {_DUMMY_TEST}")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "more than one evidence prefix" in _combined(result)


def test_differently_cased_prefix_fails(tmp_path: Path) -> None:
    """TMC-01: the prefix grammar is lowercase-only."""
    collect = _seed_baseline(tmp_path, f"Test:{_DUMMY_TEST}")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "prefix" in _combined(result)


def test_absolute_test_path_fails(tmp_path: Path) -> None:
    """TMC-02: an absolute path is not a repository-relative reference."""
    collect = _seed_baseline(tmp_path, f"test:/workspace/{_DUMMY_TEST}")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "repository-relative POSIX path" in _combined(result)


def test_empty_test_reference_fails(tmp_path: Path) -> None:
    """TMC-02: a ``test:`` reference SHALL be non-empty."""
    collect = _seed_baseline(tmp_path, "test:")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "empty test: reference" in _combined(result)


def test_multi_selector_test_reference_fails(tmp_path: Path) -> None:
    """TMC-02: at most one ``::`` selector is allowed."""
    collect = _seed_baseline(tmp_path, f"test:{_DUMMY_TEST}::test_a::test_b")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "more than one ::" in _combined(result)


def test_empty_verify_reference_fails(tmp_path: Path) -> None:
    """TMC-03/MC-04: an empty ``verify:`` reference is non-compliant."""
    collect = _seed_baseline(tmp_path, "verify:")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "empty verify: reference" in _combined(result)


def test_non_empty_verify_reference_passes(tmp_path: Path) -> None:
    """MC-04 S3: a non-empty ``verify:`` reference passes without resolution."""
    collect = _seed_baseline(tmp_path, "verify:Verify-phase runtime evidence — gate exit code")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode == 0, _combined(result)


def test_all_blank_row_fails(tmp_path: Path) -> None:
    """TMC-04: an all-blank row is an empty row and is non-compliant."""
    _write(
        tmp_path,
        "openspec/specs/alpha/spec.md",
        _spec_with_rows(
            "Alpha scenario", [f"| X-01 | Alpha scenario | test:{_DUMMY_TEST} |", "| | | |"]
        ),
    )
    _write(tmp_path, _DUMMY_TEST, "")
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [("beta", "declared backlog")])
    result = _run_checker(tmp_path, collect_output=f"{_DUMMY_TEST}::test_one")
    assert result.returncode != 0
    assert "empty row" in _combined(result)


def test_row_missing_verification_cell_fails(tmp_path: Path) -> None:
    """TMC-04: a data row missing its Verification content is non-compliant."""
    _write(
        tmp_path,
        "openspec/specs/alpha/spec.md",
        _spec_with_rows("Alpha scenario", ["| X-01 | Alpha scenario | |"]),
    )
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [("beta", "declared backlog")])
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    assert "empty Verification cell" in _combined(result)


def test_unmapped_scenario_fails(tmp_path: Path) -> None:
    """MC-02: a scenario with no row fails and is named."""
    _write(
        tmp_path,
        "openspec/specs/alpha/spec.md",
        _two_scenario_spec(["| X-01 | Alpha one | verify:evidence |"]),
    )
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [("beta", "declared backlog")])
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    assert "Alpha two" in _combined(result)
    assert "no mapping row" in _combined(result)


def test_doubly_mapped_scenario_fails(tmp_path: Path) -> None:
    """MC-02: a scenario named by two rows fails."""
    _write(
        tmp_path,
        "openspec/specs/alpha/spec.md",
        _two_scenario_spec(
            [
                "| X-01 | Alpha one | verify:evidence |",
                "| X-01 | Alpha one | verify:other evidence |",
                "| X-01 | Alpha two | verify:evidence |",
            ]
        ),
    )
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [("beta", "declared backlog")])
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    assert "mapped by 2 rows" in _combined(result)


def test_row_naming_unknown_scenario_fails(tmp_path: Path) -> None:
    """MC-02: a row naming a scenario that does not exist fails."""
    _write(
        tmp_path,
        "openspec/specs/alpha/spec.md",
        _spec_with_rows("Alpha scenario", ["| X-01 | Ghost scenario | verify:evidence |"]),
    )
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [("beta", "declared backlog")])
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    assert "does not exist" in _combined(result)


def test_missing_test_file_fails(tmp_path: Path) -> None:
    """MC-03: a ``test:`` row referencing a missing file fails."""
    collect = _seed_baseline(tmp_path, "test:tests/does_not_exist.py")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "does not exist" in _combined(result)


def test_uncollected_node_id_fails(tmp_path: Path) -> None:
    """MC-03: a ``::name`` not in the collected set fails."""
    _seed_baseline(tmp_path, f"test:{_DUMMY_TEST}::test_missing")
    result = _run_checker(tmp_path, collect_output=f"{_DUMMY_TEST}::test_one")
    assert result.returncode != 0
    assert "node id not collected" in _combined(result)


def test_path_only_with_zero_collected_items_fails(tmp_path: Path) -> None:
    """MC-03: a path-only reference requires at least one collected item."""
    _seed_baseline(tmp_path, f"test:{_DUMMY_TEST}")
    result = _run_checker(tmp_path, collect_output="")
    assert result.returncode != 0
    assert "collects no items" in _combined(result)


def test_unregistered_unmapped_spec_fails(tmp_path: Path) -> None:
    """MC-05: an unmapped spec absent from the registry fails."""
    collect = _seed_baseline(tmp_path, f"test:{_DUMMY_TEST}::test_one", registered=False)
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "not registered" in _combined(result)


def test_stale_registry_entry_for_mapped_spec_fails(tmp_path: Path) -> None:
    """MC-05: a registry entry for a spec that now carries a table fails."""
    _write(tmp_path, _DUMMY_TEST, "")
    _write(tmp_path, "openspec/specs/alpha/spec.md", _mapped_spec(f"test:{_DUMMY_TEST}::test_one"))
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [("alpha", "stale"), ("beta", "declared backlog")])
    result = _run_checker(tmp_path, collect_output=f"{_DUMMY_TEST}::test_one")
    assert result.returncode != 0
    assert "carries a Test Mapping table" in _combined(result)


def test_registry_entry_with_empty_reason_fails(tmp_path: Path) -> None:
    """MC-05: every registry entry SHALL carry a non-empty reason."""
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [("beta", "")])
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    assert "empty reason" in _combined(result)


def test_shell_metacharacter_reference_rejected_by_grammar(tmp_path: Path) -> None:
    """Threat Matrix: a shell-metacharacter reference fails grammar, not a shell."""
    collect = _seed_baseline(tmp_path, "test:; touch /tmp/pwned")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "repository-relative POSIX path" in _combined(result)
    assert not Path("/tmp/pwned").exists()


def test_escaping_reference_fails_containment(tmp_path: Path) -> None:
    """Threat Matrix: a ``../`` reference that escapes the repo root fails."""
    collect = _seed_baseline(tmp_path, "test:../escape.py")
    result = _run_checker(tmp_path, collect_output=collect)
    assert result.returncode != 0
    assert "escapes the repository root" in _combined(result)


def test_all_failures_reported_in_one_run(tmp_path: Path) -> None:
    """MC-06 S3: two independent violations both appear in a single run."""
    _write(tmp_path, "openspec/specs/alpha/spec.md", _mapped_spec("test:tests/does_not_exist.py"))
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [])
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    output = _combined(result)
    assert "does not exist" in output
    assert "not registered" in output


def test_real_repository_tree_is_compliant() -> None:
    """MC-06 S1 / MC-03 S4: the committed tree is clean through real collection."""
    result = subprocess.run(
        [sys.executable, str(_CHECKER)],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, _combined(result)


# ── Issue #234: escape-hatch honesty, registry policy, SCENARIO_RE pin ────────


def _spec_with_heading(heading_line: str, scenario: str) -> str:
    """Build a one-scenario mapped spec whose scenario heading is ``heading_line``."""
    return (
        "# alpha Specification\n\n"
        "## Requirements\n\n"
        f"{heading_line}\n\n"
        "- GIVEN a thing\n- WHEN it runs\n- THEN it works\n\n"
        "## Test Mapping\n\n"
        "| Req | Scenario | Verification |\n"
        "| --- | --- | --- |\n"
        f"| X-01 | {scenario} | verify:declared evidence |\n"
    )


def test_scenario_regex_matches_only_four_hash_headings(tmp_path: Path) -> None:
    """SCENARIO_RE pin: only the four-hash ``#### Scenario:`` level is a scenario heading.

    A row naming a scenario whose heading uses a different level (``###`` or
    ``#####``/``######``) must fail as a non-existent scenario, proving the
    heading is not enumerated (issue #234 AC-3).
    """
    for heading in ("### Scenario: Alpha", "##### Scenario: Alpha", "###### Scenario: Alpha"):
        case = tmp_path / f"case{heading.count('#')}"
        _write(case, "openspec/specs/alpha/spec.md", _spec_with_heading(heading, "Alpha"))
        _write(case, "openspec/specs/beta/spec.md", _unmapped_spec())
        _registry(case, [("beta", "declared backlog")])
        result = _run_checker(case)
        assert result.returncode != 0, f"{heading!r} must not be enumerated"
        assert "does not exist" in _combined(result)


def test_indented_four_hash_heading_is_enumerated(tmp_path: Path) -> None:
    """SCENARIO_RE allows leading whitespace (the coverage spec indents one heading)."""
    _write(
        tmp_path,
        "openspec/specs/alpha/spec.md",
        _spec_with_heading("    #### Scenario: Alpha", "Alpha"),
    )
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [("beta", "declared backlog")])
    result = _run_checker(tmp_path)
    assert result.returncode == 0, _combined(result)


def test_verify_rows_reported_as_declared_escape_hatch(tmp_path: Path) -> None:
    """PB-15 / issue #234: accepted ``verify:`` rows are reported as declared, non-verifiable.

    The checker must name the count, label the rows non-verifiable, and state the
    owner and review trigger — without resolving the reference.
    """
    _write(
        tmp_path,
        "openspec/specs/alpha/spec.md",
        _spec_with_rows(
            "Alpha scenario",
            ["| X-01 | Alpha scenario | verify:Verify-phase runtime evidence |"],
        ),
    )
    _write(tmp_path, "openspec/specs/beta/spec.md", _unmapped_spec())
    _registry(tmp_path, [("beta", "declared backlog")])
    result = _run_checker(tmp_path)
    assert result.returncode == 0, _combined(result)
    output = _combined(result)
    assert "verify: 1 declared evidence row(s)" in output
    assert "non-verifiable escape hatch" in output
    assert "the repository maintainer" in output
    assert "each release review" in output
