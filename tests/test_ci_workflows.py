"""Static tests pinning the CI coverage gate and CodeQL workflow contracts.

Module: tests/test_ci_workflows.py

Purpose: inspect the CI/CodeQL/config/documentation surface declared by the
`ci` specification (requirements CI-01..CI-12) by parsing the repository's
workflow YAML files, `pyproject.toml`, `openspec/config.yaml`, and the docs.
Every pytest function maps 1:1 to a spec scenario (AGENTS.md rule 6): the
scenario-verifying tests are the `ci` Test Mapping rows whose verification
names a test in this module (CI-09's posture row is carried by two guards), plus
the tests owned by other capabilities or supporting this one — the two
`coverage` COV-06 guards, `test_ci_workflow_files_present`, which fails loudly
before any parse, the PB-14 hook-scope guard, the CI-07 clause-agreement guard,
which re-enforces an existing CI-07 row rather than adding one, the three
`211-test-mapping-gate` guards (rule 6 / config contract agreement, the config
context tally, and the lint-job checker step), and the three CI-12 release
lint-job parity guards. Runtime
gate exit-code evidence (CI-01 S2's local gate run, CI-08 S4's required-version
mismatch probe, and CI-09 S2's pyright gate run) is recorded in the SDD verify
report, not asserted here.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
from pathlib import Path
from typing import Any

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

# Machine-local trees the CI-09 S3 config-home walk prunes: virtualenv, dependency
# caches, coverage output and VCS metadata can all carry a third-party
# `pyrightconfig.json` that is not a repository declaration.
_SKIP_DIRS = frozenset({".git", ".venv", "node_modules", "htmlcov", ".pytest_cache", "__pycache__"})

# The analyzers whose dev pins G5 forces to be exact and lock-resolved; ruff is
# governed by its own trio guard (`test_ruff_pin_hook_rev_and_required_version_agree`).
_ANALYZER_DEV_PINS = ("mypy", "pyright")

# The ordered gate invocations every `lint` job runs; the release `lint` job
# mirrors this list exactly (CI-12). Kept in one place so the two CI-12 guards
# compare against the same contract rather than duplicating the strings.
_CI_LINT_GATE_RUNS = (
    "uv run ruff check src/ tests/ scripts/",
    "uv run ruff format --check src/ tests/",
    "uv run mypy src/ scripts/",
    "uv run pyright",
    "uv run python scripts/check_test_mapping.py",
)


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


def _declared_exact_dev_pin(name: str) -> str:
    """Extract the ``X.Y.Z`` version from a ``pyproject.toml`` dev-group exact pin.

    The single derivation shared by the analyzer pins (G5) and the pyright workflow
    scan (G3): both hold no version literal of their own, so bumping an analyzer
    edits declarations only.

    Args:
        name: The distribution name whose dev pin is read (e.g. ``mypy``).

    Returns:
        The version without its specifier — the ``X.Y.Z`` of the ``==X.Y.Z`` pin.
        A missing pin, a duplicated pin, or a non-exact specifier raises.
    """
    dev = _load_toml("pyproject.toml")["dependency-groups"]["dev"]
    pins = []
    for entry in dev:
        match = _DEV_ENTRY_RE.match(entry) if isinstance(entry, str) else None
        if match is not None and match.group("name") == name:
            pins.append(match.group("spec").strip())
    assert len(pins) == 1, f"expected exactly one {name} dev pin, found {pins}"
    exact = _EXACT_PIN_RE.match(pins[0])
    assert exact is not None, (
        f"the {name} dev pin must be an exact ==X.Y.Z specifier, got {pins[0]!r} — a floor "
        "lets `uv lock` drift the analyzer away from the version the gate runs"
    )
    return exact.group("version")


def _declared_pyright_version() -> str:
    """CI-09 S2/S4: the pyright version, derived from its exact dev-group pin.

    The workflow scan (S2) and the lock comparison (S4) both derive this value and
    the guards carry no version literal of their own, so bumping pyright edits
    declarations only.

    Returns:
        The version without its specifier — the ``X.Y.Z`` of the ``==X.Y.Z`` pin.
    """
    return _declared_exact_dev_pin("pyright")


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
    """Parse ``openspec/config.yaml`` — a committed project artifact.

    The file is tracked (issue #210, decision a) so CI-06 is enforceable in
    every checkout: a missing file fails loudly via ``_load_yaml`` instead of
    skipping.

    Returns:
        The parsed config mapping.
    """
    return _load_yaml("openspec/config.yaml")


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


def test_release_coverage_job_runs_core_100_gates() -> None:
    """CI-03 S3: release.yml coverage job invokes the COV-06 gate script.

    The release coverage job SHALL run the same
    ``bash scripts/check_core_coverage.sh`` step as ci.yml — the script
    itself, not a re-implementation — so a tag cannot publish while a core
    module sits below the AGENTS.md rule-14 100% mandate. Pins the step by
    its exact ``run`` command so it cannot silently disappear again.
    """
    release, _ = _workflow("release.yml")
    job = release.get("jobs", {}).get("coverage", {})
    assert isinstance(job, dict), "release.yml has no `coverage` job"
    assert _find_step(job, run="bash scripts/check_core_coverage.sh") is not None, (
        "the release.yml `coverage` job must contain a step whose run is exactly "
        "'bash scripts/check_core_coverage.sh' — the COV-06 per-file 100% gates "
        "(AGENTS.md rule 14), same script as ci.yml"
    )


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
    """CI-04 S4: while the repository is private, SARIF is an artifact, not an upload.

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

    The file is committed (issue #210, decision a), so this test fails loudly
    when it is absent or misdeclared — no skip on this path.
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


def test_ruff_format_hook_excludes_markdown() -> None:
    """PB-14 S1: the ruff-format hook declares its own scope and excludes Markdown."""
    config = _load_yaml(".pre-commit-config.yaml")
    hooks = [
        hook
        for repo in config["repos"]
        if repo.get("repo") == _RUFF_PRE_COMMIT_REPO
        for hook in repo.get("hooks", [])
        if hook.get("id") == "ruff-format"
    ]
    assert len(hooks) == 1, f"expected exactly one ruff-format hook entry, found {len(hooks)}"
    types_or = hooks[0].get("types_or")
    assert types_or is not None, (
        "the ruff-format hook entry must declare `types_or`: its scope is a repository "
        "declaration, not the upstream manifest default (PB-14)"
    )
    assert isinstance(types_or, list), f"`types_or` must be a list, got {types_or!r}"
    assert "markdown" not in types_or, (
        "`markdown` must not be in the ruff-format hook's `types_or`: upstream widened the "
        "manifest at 0.16.6 and the hook rewrote README.md / README_ES.md (issue #216)"
    )


def test_pyright_config_declares_the_decided_posture() -> None:
    """CI-09 S2: [tool.pyright] declares mode, scope, exclusions, interpreter, stub."""
    tool = _load_toml("pyproject.toml")["tool"]
    assert "pyright" in tool, (
        "pyproject.toml must declare a `[tool.pyright]` table: it is the single config "
        "authority for the second type gate (CI-09 S2)"
    )
    pyright = tool["pyright"]
    assert pyright["typeCheckingMode"] == "standard", (
        f"[tool.pyright] typeCheckingMode must be 'standard', got {pyright['typeCheckingMode']!r}"
    )
    include = set(pyright["include"])
    assert {"src", "scripts"} <= include, (
        f"[tool.pyright] include must cover the enforced mypy scope (src/, scripts/), got {include}"
    )
    exclude = {entry.rstrip("/") for entry in pyright["exclude"]}
    assert "tests" in exclude, (
        f"[tool.pyright] exclude must contain tests (CI-09 S1), got {pyright['exclude']}"
    )
    interpreter = _read_text(".python-version").strip()
    assert pyright["pythonVersion"] == interpreter, (
        "[tool.pyright] pythonVersion must equal the gate interpreter .python-version "
        f"({interpreter}), got {pyright['pythonVersion']!r} (CI-07's invariant)"
    )
    assert pyright["stubPath"] == "typings", (
        "[tool.pyright] stubPath must name the committed tomli stub directory, "
        f"got {pyright['stubPath']!r}"
    )
    assert pyright["reportMissingImports"] not in ("none", False), (
        "[tool.pyright] must not globally disable reportMissingImports: any rule worth "
        "binding is declared, not inherited (CI-09 S2)"
    )


def test_pyright_has_exactly_one_config_home() -> None:
    """CI-09 S3: no pyrightconfig.json exists, so [tool.pyright] stays authoritative."""
    found: list[str] = []
    saw_files = False
    for dirpath, dirnames, filenames in os.walk(_REPO_ROOT):
        dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS]
        if filenames:
            saw_files = True
        for filename in filenames:
            if filename == "pyrightconfig.json":
                found.append(str(Path(dirpath, filename).relative_to(_REPO_ROOT)))
    assert saw_files, "the config-home walk saw no files — the scan would pass vacuously"
    assert not found, (
        f"pyright prefers pyrightconfig.json over [tool.pyright]; found {found} — the table "
        "must stay the single configuration authority (CI-09 S3)"
    )


def test_ci_lint_job_runs_the_pyright_gate() -> None:
    """CI-09 S2: the lint job runs the bare gate, and no workflow pins a version."""
    ci, _ = _workflow("ci.yml")
    lint = ci.get("jobs", {}).get("lint", {})
    assert isinstance(lint, dict), "ci.yml has no `lint` job"
    assert _find_step(lint, run="uv run pyright") is not None, (
        "the ci.yml `lint` job must contain a step whose run is exactly 'uv run pyright' — "
        "bare, because [tool.pyright]'s include is the single scope authority (CI-09 S2)"
    )
    version = _declared_pyright_version()
    names = _workflow_names()
    assert names, "no workflow files found — the scan would pass vacuously"
    for name in names:
        raw = _read_text(f"{_WORKFLOW_DIR}/{name}")
        assert version not in raw, f"{name} declares the pyright version {version}"
        assert re.search(r"pyright\s*(?:==|@|>=|<=|~=|!=|>|<|=)\s*\d", raw) is None, (
            f"{name} declares a pyright version specifier"
        )


def test_ci_lint_job_runs_the_ruff_format_gate() -> None:
    """CI-11 S1: the lint job runs `ruff format --check src/ tests/` after Lint.

    Issue #194: the un-staged-file drift class — the local pre-commit
    ``ruff-format`` hook sees staged files only, so a formatting regression on
    files nobody edits is invisible to CI. The ci.yml ``lint`` job SHALL carry a
    step named ``Check formatting with ruff`` whose run is exactly
    ``uv run ruff format --check src/ tests/``, placed after the ``Lint with
    ruff`` step so it shares the installed environment. Pins the step by name
    and exact run so it cannot silently disappear.
    """
    ci, _ = _workflow("ci.yml")
    lint = ci.get("jobs", {}).get("lint", {})
    assert isinstance(lint, dict), "ci.yml has no `lint` job"
    steps = lint.get("steps", [])
    assert isinstance(steps, list), "the ci.yml `lint` job has no step list"
    lint_step = _find_step(lint, run="uv run ruff check src/ tests/ scripts/")
    format_step = _find_step(lint, run="uv run ruff format --check src/ tests/")
    assert lint_step is not None, (
        "the ci.yml `lint` job must contain the 'Lint with ruff' step "
        "'uv run ruff check src/ tests/ scripts/'"
    )
    assert format_step is not None, (
        "the ci.yml `lint` job must contain a step whose run is exactly "
        "'uv run ruff format --check src/ tests/' — the CI-11 format gate "
        "closing the issue #194 un-staged-file drift class"
    )
    assert format_step.get("name") == "Check formatting with ruff", (
        "the CI-11 step must be named 'Check formatting with ruff'"
    )
    assert steps.index(format_step) > steps.index(lint_step), (
        "the CI-11 format gate must run after the 'Lint with ruff' step, sharing "
        "the already-installed environment"
    )


def test_mypy_and_pyright_exclude_tests() -> None:
    """CI-09 S1: tests/ stays out of both type gates and the posture is documented."""
    tool = _load_toml("pyproject.toml")["tool"]
    mypy_exclude = {entry.rstrip("/") for entry in tool["mypy"]["exclude"]}
    assert "tests" in mypy_exclude, (
        f"[tool.mypy] exclude must contain tests/ (CI-09 S1), got {tool['mypy']['exclude']}"
    )

    ci, _ = _workflow("ci.yml")
    lint = ci.get("jobs", {}).get("lint", {})
    invocations = [
        str(step.get("run", ""))
        for step in lint.get("steps", [])
        if isinstance(step, dict) and "mypy" in str(step.get("run", ""))
    ]
    hooks = [
        hook
        for repo in _load_yaml(".pre-commit-config.yaml")["repos"]
        if repo.get("repo") == "local"
        for hook in repo.get("hooks", [])
        if hook.get("id") == "mypy"
    ]
    assert len(hooks) == 1, f"expected exactly one local mypy hook entry, found {len(hooks)}"
    assert hooks[0].get("entry") == "uv run mypy src/ scripts/", (
        "the local mypy hook entry must be exactly 'uv run mypy src/ scripts/', "
        f"got {hooks[0].get('entry')!r}"
    )
    invocations.append(str(hooks[0].get("entry", "")))
    assert invocations, "no mypy invocation found — the scope assertions would pass vacuously"
    for invocation in invocations:
        assert "src" in invocation and "scripts" in invocation, (
            f"every mypy invocation must name src/ and scripts/, got {invocation!r}"
        )
        assert "tests" not in invocation, (
            f"no mypy invocation may name tests/ (CI-09 S1), got {invocation!r}"
        )

    pyright = tool.get("pyright")
    assert isinstance(pyright, dict), (
        "pyproject.toml must declare a `[tool.pyright]` table before its exclude can be read "
        "(CI-09 S1)"
    )
    pyright_exclude = {entry.rstrip("/") for entry in pyright["exclude"]}
    assert "tests" in pyright_exclude, (
        f"[tool.pyright] exclude must contain tests (CI-09 S1), got {pyright['exclude']}"
    )

    contributing = _read_text("CONTRIBUTING.md")
    assert "### Type checking" in contributing, "CONTRIBUTING.md has no '### Type checking' section"
    section = contributing.split("### Type checking", 1)[1].split("### ", 1)[0]
    for required in ("uv run mypy", "uv run pyright", "tests/"):
        assert required in section, (
            f"the CONTRIBUTING.md type-checking section must state {required!r}: it is where "
            "a contributor reads the Q1 answer (CI-09 S1)"
        )

    template = _read_text(".github/PULL_REQUEST_TEMPLATE.md")
    checklist = template.split("## Checklist", 1)[1] if "## Checklist" in template else template
    assert "pyright" in checklist, (
        "the PR-template Checklist must carry the pyright item, the CI-06 S4 shape (CI-09 S1)"
    )


def test_analyzer_dev_pins_are_exact_and_match_the_lock() -> None:
    """CI-09 S4: every analyzer dev pin is exact and equals its lock resolution.

    Both sides are derived from declarations — the pin from `[dependency-groups]
    dev`, the version from `uv.lock` — so the guard holds no literal. COR-6 extends
    the single-authority discipline (D10, CI-08's ruff precedent) from pyright to
    every analyzer, so a floating range cannot move the gate's version under CI.
    """
    packages = _load_toml("uv.lock").get("package", [])
    for name in _ANALYZER_DEV_PINS:
        version = _declared_exact_dev_pin(name)
        resolved = [
            package.get("version")
            for package in packages
            if isinstance(package, dict) and package.get("name") == name
        ]
        assert resolved == [version], (
            f"uv.lock must resolve exactly one {name} package at the dev pin {version}, "
            f"got {resolved} — a pin/lock drift means the gate runs a version nobody declared"
        )


def test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates() -> None:
    """CI-09 S5: adopting pyright leaves every existing gate declaration intact."""
    ci, _ = _workflow("ci.yml")
    lint = ci.get("jobs", {}).get("lint", {})
    assert _find_step(lint, run="uv run mypy src/ scripts/") is not None, (
        "the ci.yml `lint` job must still contain the 'uv run mypy src/ scripts/' step"
    )

    config = _load_yaml(".pre-commit-config.yaml")
    entries = [
        hook.get("entry")
        for repo in config["repos"]
        if repo.get("repo") == "local"
        for hook in repo.get("hooks", [])
        if hook.get("id") == "mypy"
    ]
    assert entries == ["uv run mypy src/ scripts/"], (
        f"the local mypy hook entry must stay 'uv run mypy src/ scripts/', got {entries!r}"
    )

    for name in _workflow_names():
        raw = _read_text(f"{_WORKFLOW_DIR}/{name}")
        for literal in ("fail_under", "--fail-under"):
            assert literal not in raw, (
                f"{name} declares {literal!r}: the TOTAL coverage floor stays config-owned "
                "(CI-01, CI-09 S5)"
            )

    ruff_format_hooks = [
        hook
        for repo in config["repos"]
        if repo.get("repo") == _RUFF_PRE_COMMIT_REPO
        for hook in repo.get("hooks", [])
        if hook.get("id") == "ruff-format"
    ]
    assert len(ruff_format_hooks) == 1, (
        f"expected exactly one ruff-format hook entry, found {len(ruff_format_hooks)} (PB-14)"
    )


def test_ci07_names_the_declared_mypy_language_level() -> None:
    """CI-07: the canonical clause names the declared [tool.mypy] python_version."""
    version = _load_toml("pyproject.toml")["tool"]["mypy"]["python_version"]
    blocks = _read_text("openspec/specs/ci/spec.md").split("### Requirement: ")
    ci07 = next((block for block in blocks if "(CI-07)" in block.split("\n", 1)[0]), None)
    assert ci07 is not None, "openspec/specs/ci/spec.md has no CI-07 requirement block"
    assert f'"{version}"' in ci07, (
        f"CI-07 must name the declared [tool.mypy] python_version ({version}): the committed "
        "configuration and the canonical clause cannot diverge (issue #201)"
    )
    # The retired value is asserted as a literal on purpose: no declaration is left to
    # derive it from, and the whole point is that this string is gone. Every other
    # version in this module is derived.
    assert '"3.10"' not in ci07, (
        'CI-07 must not still declare the retired [tool.mypy] python_version "3.10": its '
        "clause and its scenario bullet were amended to the declared value (issue #201)"
    )


def test_release_test_job_mirrors_ci_os_axis_and_cli_smoke() -> None:
    """CI-10 S1/S2: the release test job mirrors CI's OS axis and the help smoke.

    Issue #209: release.yml claimed to run the same quality gates as CI while its
    ``test`` job dropped the Windows axis and the ``uv run sofer --help`` smoke
    test. The release ``test`` job SHALL declare the same ``os`` matrix as the CI
    ``test`` job and run on ``${{ matrix.os }}``, and SHALL run the CLI help smoke
    test after the full-suite step. The stale claim that the COV-06 gate was
    "tracked separately as issue #185" is gone: GitHub #185 is closed and the gate
    is shipped as CI-03.
    """
    ci, _ = _workflow("ci.yml")
    release, _ = _workflow("release.yml")
    ci_test = ci.get("jobs", {}).get("test", {})
    release_test = release.get("jobs", {}).get("test", {})
    assert isinstance(ci_test, dict), "ci.yml has no `test` job"
    assert isinstance(release_test, dict), "release.yml has no `test` job"
    assert release_test.get("runs-on") == "${{ matrix.os }}", (
        "the release `test` job must run on ${{ matrix.os }} (CI-10)"
    )
    ci_os = ci_test.get("strategy", {}).get("matrix", {}).get("os")
    release_os = release_test.get("strategy", {}).get("matrix", {}).get("os")
    assert isinstance(ci_os, list) and isinstance(release_os, list), (
        "both `test` jobs must declare an `os` matrix axis (CI-10)"
    )
    assert release_os == ci_os == ["ubuntu-latest", "windows-latest"], (
        "the release `test` job must declare the same OS axis as the CI `test` job (CI-10)"
    )
    release_steps = release_test.get("steps", [])
    run_tests = _find_step(release_test, run="uv run pytest -v")
    smoke = _find_step(release_test, run="uv run sofer --help")
    assert run_tests is not None, "the release `test` job must run the full suite (CI-10)"
    assert smoke is not None, "the release `test` job must run `uv run sofer --help` (CI-10)"
    assert smoke.get("name") == "Run CLI help smoke test"
    assert release_steps.index(smoke) > release_steps.index(run_tests), (
        "the CLI help smoke test must run after the full-suite step, matching ci.yml (CI-10)"
    )


def _lint_gate_runs(job: dict[str, Any]) -> list[str]:
    """Return a ``lint`` job's gate ``run`` commands, in step order.

    Filters the parsed steps down to the shared gate invocations (ruff, mypy,
    pyright, and the test-mapping checker), dropping setup steps (checkout,
    ``uv sync``, ``setup-uv``) so the two ``lint`` jobs can be compared directly.

    Args:
        job: A parsed ``lint`` job mapping.

    Returns:
        The ordered gate ``run`` strings found in the job.
    """
    return [
        step["run"]
        for step in job.get("steps", [])
        if isinstance(step, dict)
        and isinstance(step.get("run"), str)
        and step["run"] in _CI_LINT_GATE_RUNS
    ]


def test_release_lint_job_runs_the_ci_lint_gates() -> None:
    """CI-12 S1: the release `lint` job runs the format, pyright and mapping gates.

    Issue #233: the release header claimed CI parity while the `lint` job omitted
    three gates the CI `lint` job runs. Each SHALL be present with its exact
    invocation and SHALL keep the job's single ubuntu-latest / 3.13 axis.
    """
    release, _ = _workflow("release.yml")
    lint = release.get("jobs", {}).get("lint", {})
    assert isinstance(lint, dict), "release.yml has no `lint` job"
    for command in (
        "uv run ruff format --check src/ tests/",
        "uv run pyright",
        "uv run python scripts/check_test_mapping.py",
    ):
        assert _find_step(lint, run=command) is not None, (
            f"the release `lint` job must run exactly {command!r} (CI-12)"
        )
    assert lint.get("runs-on") == "ubuntu-latest", "the release `lint` job keeps its single OS axis"
    uv_step = _find_step(lint, uses="astral-sh/setup-uv@v10.1.0")
    assert uv_step is not None and uv_step.get("with", {}).get("python-version") == "3.13", (
        "the release `lint` job must keep its single Python axis (3.13), matching ci.yml (CI-12)"
    )


def test_release_lint_job_mirrors_ci_lint_invocations() -> None:
    """CI-12 S2: both `lint` jobs carry the same gates in the same order."""
    ci, _ = _workflow("ci.yml")
    release, _ = _workflow("release.yml")
    ci_lint = ci.get("jobs", {}).get("lint", {})
    release_lint = release.get("jobs", {}).get("lint", {})
    assert _lint_gate_runs(ci_lint) == list(_CI_LINT_GATE_RUNS), (
        "the ci.yml `lint` job gate invocations moved; update the shared contract"
    )
    assert _lint_gate_runs(release_lint) == list(_CI_LINT_GATE_RUNS), (
        "the release `lint` job must run the same gates, in the same order, as ci.yml (CI-12)"
    )


def test_release_header_states_lint_parity_without_the_stale_cov06_claim() -> None:
    """CI-12 S3: the release header states lint parity and the shipped COV-06 gate.

    The stale claim that the COV-06 gate was "tracked separately" is gone (CI-03
    owns it), and the header now states the lint-job parity.
    """
    header = _read_text(f"{_WORKFLOW_DIR}/release.yml").split("on:", 1)[0]
    assert "lint job mirrors" in header, (
        "the release header must state that the `lint` job mirrors ci.yml's lint gates (CI-12)"
    )
    assert "tracked separately" not in header, (
        "the release header must not keep the stale claim that the COV-06 gate is tracked "
        "separately (CI-12 / CI-03)"
    )


_RULE6_RE = re.compile(r"### 6\..*?(?=\n### )", re.DOTALL)
# The contract terms both normative homes must state (R6-04): the two prefixes,
# the existence/collection limit, and the registry boundary.
_CONTRACT_TERMS = ("test:", "verify:", "collected", "registry")
# Stale hand-maintained tallies #214 files: a bare count followed by the noun.
_STALE_TALLY_RE = re.compile(r"\b\d+\s+(?:tests|collected|skipped)\b|\b\d+\s+spec\s+scenarios\b")


def test_rule6_and_config_agree_on_contract_terms() -> None:
    """R6-04/R6-05: AGENTS rule 6 and config rules.specs state the same contract.

    Issue #211/#214: rule 6's unenforced absolute and its stale tally were
    replaced by the enforced contract — the ``test:``/``verify:`` prefixes, the
    existence/collection limit (not proof of exercise), the ``verify:`` escape
    hatch, and the registry boundary — plus the reproducing command alone. The
    two normative homes must agree on those contract terms, and no stale
    pass/collected/skipped triple may remain in rule 6.
    """
    match = _RULE6_RE.search(_read_text("AGENTS.md"))
    assert match is not None, "AGENTS.md rule 6 not found"
    rule6 = match.group(0)
    specs_rules = " ".join(str(entry) for entry in _openspec_config()["rules"]["specs"])
    for term in _CONTRACT_TERMS:
        assert term in rule6, f"AGENTS.md rule 6 must state the contract term {term!r}"
        assert term in specs_rules, f"config rules.specs must state the contract term {term!r}"
    assert "1766" not in rule6 and "1772" not in rule6, (
        "AGENTS.md rule 6 must not carry the stale #214 tally"
    )
    assert "uv run pytest tests/ -q" in rule6, (
        "rule 6 must keep the reproducing command as the tally's sole anchor (R6-05)"
    )


def test_verify_escape_hatch_has_owner_and_review_trigger() -> None:
    """PB-15 / issue #234: the escape hatch is non-verifiable with an owner and a trigger.

    Rule 6, ``openspec/config.yaml`` ``rules.specs``, the checker source, and the
    registry must agree: ``verify:`` is a declared, non-verifiable escape hatch
    owned by the repository maintainer and reviewed on every change to a
    ``verify:`` row / evidence class and at each release.
    """
    match = _RULE6_RE.search(_read_text("AGENTS.md"))
    assert match is not None, "AGENTS.md rule 6 not found"
    rule6 = match.group(0)
    specs_rules = " ".join(str(entry) for entry in _openspec_config()["rules"]["specs"])
    checker = _read_text("scripts/check_test_mapping.py")
    registry = _read_text("openspec/test-mapping-registry.md")
    policy_terms = (
        "non-verifiable",
        "escape hatch",
        "the repository maintainer",
        "each release review",
    )
    for label, source in (
        ("AGENTS.md rule 6", rule6),
        ("config rules.specs", specs_rules),
        ("checker docstring/constants", checker),
    ):
        for term in policy_terms:
            assert term in source, f"{label} must state {term!r} (issue #234 PB-15)"
    for term in ("permanent declared backlog", "the repository maintainer", "each release review"):
        assert term in registry, f"registry must state {term!r} (issue #234 PB-15)"


def test_config_context_has_no_stale_tally() -> None:
    """R6-06: config ``context`` carries no stale count and keeps the test command."""
    config = _openspec_config()
    context = str(config["context"])
    assert _STALE_TALLY_RE.search(context) is None, (
        "openspec/config.yaml context must not carry a stale hand-maintained tally (R6-06)"
    )
    assert config["testing"]["test_command"] == "uv run pytest tests/ -q", (
        "the reproducing command must remain declared under testing (R6-06)"
    )


def test_lint_job_runs_the_test_mapping_checker() -> None:
    """MC-07 S1: exactly one lint-job step runs the checker; no new job/axis."""
    ci, _ = _workflow("ci.yml")
    jobs = ci.get("jobs", {})
    assert isinstance(jobs, dict), "ci.yml has no `jobs` mapping"
    lint = jobs.get("lint", {})
    assert isinstance(lint, dict), "ci.yml has no `lint` job"
    checker_steps = [
        step
        for step in lint.get("steps", [])
        if isinstance(step, dict) and "check_test_mapping" in str(step.get("run", ""))
    ]
    assert len(checker_steps) == 1, (
        "the ci.yml `lint` job must contain exactly one test-mapping checker step (MC-07)"
    )
    assert checker_steps[0].get("run") == "uv run python scripts/check_test_mapping.py", (
        "the checker step must invoke scripts/check_test_mapping.py directly (MC-07)"
    )
    assert set(jobs) == {"lint", "test", "coverage"}, (
        "the checker must not add a new job or matrix axis — one step in the existing "
        f"`lint` job only (MC-07 S1), got {sorted(jobs)}"
    )
