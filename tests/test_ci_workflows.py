"""Static tests pinning the CI coverage gate and CodeQL workflow contracts.

Module: tests/test_ci_workflows.py

Purpose: inspect the CI/CodeQL/config/documentation surface declared by the
`ci` specification (requirements CI-01..CI-08) by parsing the repository's
workflow YAML files, `pyproject.toml`, `openspec/config.yaml`, and the docs.
Every pytest function maps 1:1 to a spec scenario (AGENTS.md rule 6): the
scenario-verifying tests are the 18 `ci` Test Mapping rows whose verification
names a test in this module, plus four tests owned by other capabilities or
supporting this one — the two `coverage` COV-06 guards, the CodeQL
private-window guard, and `test_ci_workflow_files_present`, which fails loudly
before any parse. Runtime gate exit-code evidence (CI-01 S2's local gate run and
CI-08 S4's required-version mismatch probe) is recorded in the SDD verify
report, not asserted here.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]  # tests/ -> repo root

_WORKFLOW_DIR = ".github/workflows"


def _read_text(rel: str) -> str:
    """Read a repository file (utf-8) relative to the repo root.

    Args:
        rel: Repo-root-relative path, forward slashes.

    Returns:
        The file contents as text; a missing file raises loudly.
    """
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _load_yaml(rel: str) -> dict[str, Any]:
    """Parse a repository YAML file with ``yaml.safe_load``.

    Args:
        rel: Repo-root-relative path, forward slashes.

    Returns:
        The parsed mapping (workflow/config documents are top-level maps).
    """
    return yaml.safe_load(_read_text(rel))


def _load_toml(rel: str) -> dict[str, Any]:
    """Parse a repository TOML file with ``tomllib`` (``tomli`` on Python 3.10).

    Resolves the TOML parser via ``importlib`` (stdlib ``tomllib`` on
    Python 3.11+, the marker-only ``tomli`` backport below) instead of a
    static fallback import, so static analysis never has to resolve
    ``tomli`` inside a 3.11+ venv where it is not installed. Same intent
    as the ``tests/test_cli.py`` fallback pattern.

    Args:
        rel: Repo-root-relative path, forward slashes.

    Returns:
        The parsed TOML document as a nested mapping.
    """
    parser = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")
    return parser.loads(_read_text(rel))


def _as_list(value: Any) -> list[Any]:
    """Normalize a GitHub ``needs`` value (single string, list, or absent).

    Args:
        value: A job's ``needs`` entry as parsed from YAML.

    Returns:
        The value as a list (``[]`` when absent, ``[str]`` when scalar).
    """
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


_RUFF_PRE_COMMIT_REPO = "https://github.com/astral-sh/ruff-pre-commit"
_DEV_ENTRY_RE = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<spec>[<>=!~].*)$")
_EXACT_PIN_RE = re.compile(r"^==(?P<version>\d+\.\d+\.\d+)$")


def _declared_ruff_version() -> str:
    """Extract the ``X.Y.Z`` version from the ``pyproject.toml`` dev-group ruff pin.

    CI-08's single source of the ruff version: all three declarations the guards
    compare are derived from this value and the guards carry no version literal of
    their own, so bumping ruff edits declarations only.

    Returns:
        The version without its specifier — the ``X.Y.Z`` of the ``==X.Y.Z`` pin.
    """
    dev = _load_toml("pyproject.toml")["dependency-groups"]["dev"]
    pins = []
    for entry in dev:
        match = _DEV_ENTRY_RE.match(entry) if isinstance(entry, str) else None
        if match is not None and match.group("name") == "ruff":
            pins.append(match.group("spec").strip())
    assert len(pins) == 1, f"expected exactly one ruff dev pin, found {pins}"
    exact = _EXACT_PIN_RE.match(pins[0])
    assert exact is not None, (
        f"the ruff dev pin must be an exact ==X.Y.Z specifier, got {pins[0]!r} — a floor "
        "lets `uv lock` drift the formatter away from the version the hook runs, which is "
        "exactly how the ambient binary drifted from the pre-commit rev"
    )
    return exact.group("version")


def _workflow(rel: str) -> tuple[dict[str, Any], str]:
    """Return ``(parsed YAML, raw text)`` for a workflow under the workflows dir.

    Args:
        rel: Workflow file name (e.g. ``ci.yml``).

    Returns:
        A tuple of the parsed top-level mapping and the raw file text.
    """
    path = f"{_WORKFLOW_DIR}/{rel}"
    return _load_yaml(path), _read_text(path)


def _triggers(wf: dict[Any, Any]) -> dict[str, Any]:
    """Resolve a workflow's trigger map, normalizing the YAML 1.1 ``on`` key.

    PyYAML (YAML 1.1) parses the bare top-level ``on`` key as boolean ``True``,
    so ``yaml.safe_load`` yields ``{True: {...}}``; this helper owns that
    normalization in exactly one place (``wf.get("on", wf.get(True))``). The
    mapping is typed with ``Any`` keys because the whole point is that parsed
    YAML may legitimately carry a boolean key.

    Args:
        wf: The parsed workflow mapping.

    Returns:
        The trigger mapping (an empty dict when no triggers are present).
    """
    triggers = wf.get("on", wf.get(True))
    return triggers if isinstance(triggers, dict) else {}


def _workflow_names() -> tuple[str, ...]:
    """List the workflow file names under ``.github/workflows``, sorted.

    Returns:
        A sorted tuple of ``*.yml`` file names present in the workflows dir.
    """
    workflows = (_REPO_ROOT / _WORKFLOW_DIR).glob("*.yml")
    return tuple(sorted(path.name for path in workflows))


def _coverage_jobs() -> list[dict[str, Any]]:
    """Collect the ``coverage`` job mapping from ci.yml and release.yml.

    Both workflows carry an identical job shape (shared definition in the
    design); only the release one declares ``needs``.

    Returns:
        A list of the parsed ``coverage`` job mappings (one per workflow).
    """
    jobs: list[dict[str, Any]] = []
    for name in ("ci.yml", "release.yml"):
        wf, _ = _workflow(name)
        job = wf.get("jobs", {}).get("coverage")
        if isinstance(job, dict):
            jobs.append(job)
    return jobs


def _find_step(
    job: dict[str, Any], *, run: str | None = None, uses: str | None = None
) -> dict[str, Any] | None:
    """Find a job step by its ``run`` command or ``uses`` action reference.

    Args:
        job: A parsed GitHub Actions job mapping.
        run: Optional exact ``run`` command to match.
        uses: Optional exact ``uses`` reference to match.

    Returns:
        The first matching step mapping, or None when no step matches.
    """
    for step in job.get("steps", []):
        if not isinstance(step, dict):
            continue
        if run is not None and step.get("run") == run:
            return step
        if uses is not None and step.get("uses") == uses:
            return step
    return None


def _openspec_config() -> dict[str, Any]:
    """Parse ``openspec/config.yaml`` — gitignored SDD-local state.

    The file is listed in ``.gitignore`` (SDD generated artifact) and may be
    absent from CI checkouts, so the test skips when it is missing; the values
    asserted here are recorded as working-tree evidence by the SDD verify
    phase. Correct under both the tracked and untracked readings (D5 note).

    Returns:
        The parsed config mapping.
    """
    path = _REPO_ROOT / "openspec" / "config.yaml"
    if not path.exists():
        pytest.skip(
            "openspec/config.yaml is absent (gitignored SDD state); "
            "asserting its values is the local SDD verify phase's job"
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_ci_workflow_files_present() -> None:
    """Supporting guard: the three workflow files exist before any parse."""
    required = {"ci.yml", "release.yml", "codeql.yml"}
    assert required.issubset(set(_workflow_names()))


def test_pyproject_declares_coverage_fail_under_90() -> None:
    """CI-01 S1: pyproject.toml declares the 90% floor next to show_missing."""
    coverage_report = _load_toml("pyproject.toml")["tool"]["coverage"]["report"]
    assert coverage_report["fail_under"] == 90


def test_coverage_job_gates_core_modules_at_100() -> None:
    """COV-06: the four core modules are gated at 100 via the gate script.

    Reads ``scripts/check_core_coverage.sh`` and the ``ci.yml`` coverage job:
    (a) each of the four ``src/sofer/<file>.py`` paths is paired with
    ``--fail-under=100 -m`` in the script, and the script is referenced by a
    coverage-job step; (b) no ``--fail-under`` value other than 100 appears in
    the script or either workflow; (c) the config-key spelling ``fail_under``
    (underscore) appears in neither. The TOTAL floor stays config-owned
    (``test_pyproject_declares_coverage_fail_under_90``).
    """
    script = _read_text("scripts/check_core_coverage.sh")
    # The script drives the four modules through a single loop; assert the loop
    # roster and the scoped invocation shape (one home for the four 100 gates).
    assert "for f in cli scanner prepare publish" in script
    assert '--include="src/sofer/${f}.py" --fail-under=100 -m' in script
    for module in ("cli", "scanner", "prepare", "publish"):
        assert module in script
    assert "bash scripts/check_core_coverage.sh" in _read_text(f"{_WORKFLOW_DIR}/ci.yml")
    for raw in (
        script,
        _read_text(f"{_WORKFLOW_DIR}/ci.yml"),
        _read_text(f"{_WORKFLOW_DIR}/release.yml"),
    ):
        assert "fail_under" not in raw
        for match in re.findall(r"--fail-under=[0-9]+", raw):
            assert match == "--fail-under=100", f"non-100 floor literal {match}"


def test_agents_md_declares_core_100_mandate() -> None:
    """COV-06: AGENTS.md rule 14 names the modules, the 100% mandate, and the
    pragma ban."""
    rule14 = re.search(r"### 14\..*?(?=\n### 15\.|\Z)", _read_text("AGENTS.md"), re.DOTALL)
    assert rule14 is not None, "AGENTS.md rule 14 not found"
    text = rule14.group(0)
    for module in ("cli.py", "scanner.py", "prepare.py", "publish.py"):
        assert module in text
    assert "100.00%" in text
    assert re.search(r"#\s*pragma:\s*no\s*cover", text, re.IGNORECASE) is not None


def test_coverage_gate_is_config_driven_without_cli_floor() -> None:
    """CI-01 S2 (TOTAL gate only): no floor literal or flag in the workflows.

    The *TOTAL* gate is config-driven: the raw text of ci.yml and release.yml
    must not contain ``fail_under``, ``--fail-under``, or ``fail-under`` — the
    TOTAL floor lives only in ``pyproject.toml`` and is read by coverage.py
    itself. The documented exception is the COV-06 per-file 100% machinery:
    the four scoped invocations live in ``scripts/check_core_coverage.sh``
    (asserted by ``test_coverage_job_gates_core_modules_at_100``), never as
    flags or config keys in the workflows. The TOTAL report step stays the
    flag-free ``uv run coverage report -m``.
    """
    for name in ("ci.yml", "release.yml"):
        raw = _read_text(f"{_WORKFLOW_DIR}/{name}")
        assert "--fail-under" not in raw
        assert "fail_under" not in raw
        assert "fail-under" not in raw
    for job in _coverage_jobs():
        assert _find_step(job, run="uv run coverage report -m") is not None
    # Pinned added assertion: the TOTAL report step in every coverage job is
    # exactly the flag-free invocation (COV-06 gate script stays out of the
    # workflow text and never replaces this step).
    for job in _coverage_jobs():
        steps = job.get("steps", [])
        assert any(
            s.get("run") == "uv run coverage report -m"
            and "--fail-under" not in str(s.get("run", ""))
            and "bash scripts/check_core_coverage.sh" not in str(s.get("run", ""))
            for s in steps
        )


def test_coverage_report_honors_show_missing() -> None:
    """CI-01 S3: show_missing is set in config and the report step uses -m."""
    coverage_report = _load_toml("pyproject.toml")["tool"]["coverage"]["report"]
    assert coverage_report["show_missing"] is True
    for job in _coverage_jobs():
        assert _find_step(job, run="uv run coverage report -m") is not None


def test_coverage_jobs_generate_and_upload_htmlcov() -> None:
    """CI-02 S1: every coverage job runs ``coverage html`` and uploads htmlcov."""
    assert len(_coverage_jobs()) == 2  # ci.yml + release.yml
    for job in _coverage_jobs():
        assert _find_step(job, run="uv run coverage html") is not None
        upload = _find_step(job, uses="actions/upload-artifact@v7")
        assert upload is not None
        assert upload.get("with", {}).get("name") == "coverage-html"
        assert upload.get("with", {}).get("path") == "htmlcov"


def test_coverage_report_step_lists_missing_lines() -> None:
    """CI-02 S2: the report step is exactly `coverage report -m` in both jobs."""
    for job in _coverage_jobs():
        assert _find_step(job, run="uv run coverage report -m") is not None


def test_no_xml_codecov_or_badge_references_in_workflows() -> None:
    """CI-02 S3: self-hosted evidence only — no XML, Codecov, or badges."""
    for name in ("ci.yml", "release.yml"):
        raw = _read_text(f"{_WORKFLOW_DIR}/{name}").lower()
        for marker in ("coverage xml", "codecov", "coveralls", "badge"):
            assert marker not in raw


def test_release_is_gated_on_the_coverage_job() -> None:
    """CI-03 S1: release.yml build/citation-check/release all need coverage."""
    release, _ = _workflow("release.yml")
    jobs = release.get("jobs", {})
    assert "coverage" in jobs
    assert _as_list(jobs["coverage"].get("needs")) == ["lint", "test"]
    assert "coverage" in _as_list(jobs["build"].get("needs"))
    assert _as_list(jobs["citation-check"].get("needs")) == ["coverage"]
    assert "coverage" in _as_list(jobs["release"].get("needs"))


def test_codeql_has_push_pr_and_weekly_triggers() -> None:
    """CI-04 S1: push/PR on main+dev and a single weekly cron schedule."""
    codeql, _ = _workflow("codeql.yml")
    triggers = _triggers(codeql)
    assert triggers.get("push", {}).get("branches") == ["main", "dev"]
    assert triggers.get("pull_request", {}).get("branches") == ["main", "dev"]
    schedules = triggers.get("schedule", [])
    assert len(schedules) == 1
    cron = schedules[0].get("cron", "")
    assert re.fullmatch(r"\d+ \d+ \* \* \d+", cron) is not None


def test_codeql_pull_request_targets_dev() -> None:
    """CI-04 S2: pull requests to dev are scanned alongside main."""
    codeql, _ = _workflow("codeql.yml")
    pr_branches = _triggers(codeql).get("pull_request", {}).get("branches", [])
    assert set(pr_branches) == {"main", "dev"}


def test_codeql_security_write_permission_and_python() -> None:
    """CI-04 S3: security-events write + python init + analyze@v3 step.

    The spec's "the analyze step SHALL declare ``languages: python``" wording
    is resolved at the intent level (design D3): ``languages`` is an ``init``
    parameter in canonical CodeQL, so this asserts the init declaration, the
    write permission, and that an analyze step exists.
    """
    codeql, _ = _workflow("codeql.yml")
    assert codeql.get("permissions") == {
        "actions": "read",
        "contents": "read",
        "security-events": "write",
    }
    analyze_job = codeql.get("jobs", {}).get("analyze", {})
    init = _find_step(analyze_job, uses="github/codeql-action/init@v4")
    assert init is not None
    assert init.get("with", {}).get("languages") == "python"
    assert _find_step(analyze_job, uses="github/codeql-action/analyze@v4") is not None


def test_codeql_init_references_config_file() -> None:
    """CI-05 S1: init passes the Advanced-Setup config file and languages."""
    codeql, _ = _workflow("codeql.yml")
    init = _find_step(
        codeql.get("jobs", {}).get("analyze", {}),
        uses="github/codeql-action/init@v4",
    )
    assert init is not None
    assert init.get("with", {}).get("config-file") == "./.github/codeql/config.yml"
    assert init.get("with", {}).get("languages") == "python"


def test_codeql_private_window_publishes_sarif_artifact_without_upload() -> None:
    """While the repository is private, SARIF is an artifact, not an upload.

    Code scanning cannot be enabled on a private repository without GitHub Code
    Security, so uploading SARIF to the Security tab would fail every run. The
    analyze step therefore sets ``upload: never`` and the SARIF is published as
    a workflow artifact instead. When the repository becomes public, ``upload``
    goes back to ``always`` and this test must change with it.
    """
    codeql, _ = _workflow("codeql.yml")
    analyze_job = codeql.get("jobs", {}).get("analyze", {})
    analyze = _find_step(analyze_job, uses="github/codeql-action/analyze@v4")
    assert analyze is not None
    assert analyze.get("with", {}).get("upload") == "never"
    artifact = _find_step(analyze_job, uses="actions/upload-artifact@v7")
    assert artifact is not None
    assert artifact.get("with", {}).get("name") == "codeql-sarif"
    assert artifact.get("with", {}).get("path") == "codeql-results/*.sarif"


def test_codeql_paths_ignore_covers_non_code_trees() -> None:
    """CI-05 S2: paths-ignore covers non-code trees, never src/sofer/."""
    config = _load_yaml(".github/codeql/config.yml")
    paths_ignore = config.get("paths-ignore", [])
    for required in ("docs/", ".github/", "openspec/"):
        assert required in paths_ignore
    assert "src/sofer/" not in paths_ignore


def test_openspec_config_declares_coverage_available_at_90() -> None:
    """CI-06 S1: openspec/config.yaml declares coverage available at 90.

    Skips when the (gitignored) file is absent — see ``_openspec_config``.
    """
    config = _openspec_config()
    assert config["testing"]["coverage"]["available"] is True
    assert config["testing"]["coverage"]["command"] == "uv run coverage run -m pytest"
    assert config["rules"]["verify"][-1]["coverage_threshold"] == 90


def test_contributing_documents_coverage_floor() -> None:
    """CI-06 S2: CONTRIBUTING.md documents the floor and both commands."""
    text = _read_text("CONTRIBUTING.md")
    assert "90%" in text
    assert "uv run coverage run -m pytest" in text
    assert "uv run coverage report -m" in text
    assert "no drop in coverage" not in text


def test_pr_template_has_coverage_checklist_item() -> None:
    """CI-06 S4: the PR template checklist has the coverage item and README_ES item."""
    text = _read_text(".github/PULL_REQUEST_TEMPLATE.md")
    checklist = text.split("## Checklist", 1)[1] if "## Checklist" in text else text
    assert "Coverage gate met" in checklist
    assert "README_ES.md updated" in checklist


def test_ruff_pin_hook_rev_and_required_version_agree() -> None:
    """CI-08 S1: the dev pin, required-version, and the hook rev name one version."""
    version = _declared_ruff_version()
    required = _load_toml("pyproject.toml")["tool"]["ruff"]["required-version"]
    assert required == f"=={version}", f"required-version must be '=={version}', got {required!r}"
    config = _load_yaml(".pre-commit-config.yaml")
    revs = [
        repo.get("rev") for repo in config["repos"] if repo.get("repo") == _RUFF_PRE_COMMIT_REPO
    ]
    assert revs == [f"v{version}"], f"ruff-pre-commit rev must be 'v{version}', got {revs!r}"


def test_workflows_do_not_declare_a_ruff_version() -> None:
    """CI-08 S2: the version reaches CI through uv.lock, never through a workflow."""
    version = _declared_ruff_version()
    names = _workflow_names()
    assert names, "no workflow files found — the scan would pass vacuously"
    for name in names:
        raw = _read_text(f"{_WORKFLOW_DIR}/{name}")
        assert version not in raw, f"{name} declares the ruff version {version}"
        assert re.search(r"ruff\s*(?:==|@|>=|<=|~=|!=|>|<|=)\s*\d", raw) is None, (
            f"{name} declares a ruff version specifier"
        )


def test_contributing_names_the_declared_ruff_version() -> None:
    """CI-08 S3: the Code style section names the version the pin declares."""
    version = _declared_ruff_version()
    text = _read_text("CONTRIBUTING.md")
    assert "### Code style" in text, "CONTRIBUTING.md has no '### Code style' section"
    section = text.split("### Code style", 1)[1].split("### ", 1)[0]
    assert re.search(rf"(?<![\d.]){re.escape(version)}(?![\d.])", section), (
        f"the Code style section must name ruff {version}"
    )
