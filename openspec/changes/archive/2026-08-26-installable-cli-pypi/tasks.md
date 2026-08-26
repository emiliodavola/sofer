# Tasks: Installable CLI — release-ready packaging (hatch-vcs, metadata, docs, tests)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~450–550 |
| 400-line budget risk | High |
| Chained PRs recommended | No |
| Suggested split | Single PR to dev (2 internal commits, design D8) |
| Delivery strategy | exception-ok |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Version resolver (code + tests) | Single PR, slice 1 | `uv run pytest tests/test_metadata.py tests/test_cli.py -q` | Dev venv: `sofer --version` → `sofer v0.1.0` (pyproject still static) | Restore static `__version__` |
| 2 | Packaging + docs + packaging tests | Single PR, slice 2 | `uv run pytest tests/ -q && uv build` | `uv build` → wheel; installed-CLI `.pth` subprocess | Restore prior pyproject/workflow/docs |

## Phase 1: Version resolver (commit 1)

- [x] 1.1 Create `src/sofer/_version.py`: `get_version()` — `importlib.metadata.version("sofer")`; `PackageNotFoundError` → sentinel `0.0.0.dev0`; `lru_cache(maxsize=1)`; docstrings; no git-describe/shutil/subprocess
- [x] 1.2 `src/sofer/__init__.py`: delete `__version__ = "0.1.0"` (line 18)
- [x] 1.3 `src/sofer/cli.py`: line 14 → `from ._version import get_version`; line 462 → `version=f"sofer v{get_version()}"`
- [x] 1.4 `src/sofer/metadata.py`: line 25 import; line 177 → `field(default_factory=get_version)`; line 172 docstring
- [x] 1.5 `tests/test_metadata.py` (14/214/220): assert `get_version()` non-empty; CLI-R06 equality (`generated.version` == `--version` minus `sofer v`)
- [x] 1.6 `tests/test_cli.py::test_version` (64–69): capsys `out.strip() == f"sofer v{get_version()}"`, exit 0
- [x] 1.7 Commit-1 gate: `uv run pytest tests/ -q && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/`

## Phase 2: Packaging + workflow + docs (commit 2)

- [x] 2.1 `pyproject.toml`: `dynamic = ["version"]`, `readme`, PEP 639 `license = "MIT"` + `license-files = ["LICENSE"]`, classifiers (3.10–3.14, MIT, 4-Beta, Topic), `project.urls`, `authors`; `[tool.hatch.version] source = "vcs"`; `requires = ["hatchling", "hatch-vcs"]`
- [x] 2.2 `release.yml`: `build` job (`needs: [lint, test]`) — `uv build`, METADATA `Version:` == `${GITHUB_REF_NAME#v}`, `Classifier:`/`Project-URL:`, `entry_points.txt` `sofer = sofer.cli:main`, `licenses/LICENSE`; `release` needs `[lint, test, build]`; ci.yml UNCHANGED
- [x] 2.3 `AGENTS.md`: rule 12 rewrite (design §D5 — tag = SSOT, no bump commit); line 44 "422" → "795"
- [x] 2.4 `README.md`: `## Install` (design §D6), `## Setup` → `## Development setup`, tree line 366 + `_version.py`
- [x] 2.5 `openspec/specs/packaging/spec.md` PKG-01: stale `0.2.0.post5+g<sha>` → verified shape (`0.3.1.dev1+g<sha>` off-tag / `0.1.dev1+g<sha>` zero-tag)
- [x] 2.6 `uv sync` (adopt hatch-vcs dev version); commit-2 gate: same command as 1.7

## Phase 3: Packaging tests — `tests/test_packaging.py` (PKG-04)

- [x] 3.1 Resolver non-empty + PEP 440 regex; fallback: monkeypatch metadata to raise → sentinel, `get_version.cache_clear()`; never literal
- [x] 3.2 Source scan: `dynamic = ["version"]`, no `version =`, no `__version__`
- [x] 3.3 Build smoke: `uv build` tmp → wheel; `entry_points.txt` + METADATA via `zipfile` (first run needs network — build isolation; document, don't claim hermetic)
- [x] 3.4 Installed-CLI E2E: fresh `uv venv`; `uv pip install --python <tmp>/Scripts/python.exe --no-deps <wheel>`; `.pth` → project venv purelib (`sysconfig.get_path("purelib")`); `--help` 0; `--version` 0 + `sofer v` prefix
- [x] 3.5 Confirm `.pth` recipe on ubuntu CI runner (win32 verified; POSIX parity — flagged as apply-phase confirmation note; test written portably via `os.name`, CI confirmation pending)

## Phase 4: Scenario → test mapping (rule 6)

| Scenario | Test |
|---|---|
| PKG-01 tagged == tag | 2.2 |
| PKG-01 off-tag dev | 3.1 |
| PKG-01 no static literal | 3.2 |
| PKG-02 metadata complete | 3.3 + 2.2 |
| PKG-02 LICENSE bundled | 2.2 |
| PKG-03 entry point | 3.3 |
| PKG-03 installed CLI standalone | 3.4 |
| PKG-04 version derived | 3.1 |
| PKG-04 build smoke | 3.3 |
| PKG-04 installed-CLI | 3.4 |
| PKG-05 install docs | 2.4 |
| CLI-R05 released tag | 3.4 prefix |
| CLI-R05 dev install | 3.1 (non-empty, no literal) |
| CLI-R05 standalone script | 3.4 |
| CLI-R06 stamping equality | 1.5 |
| CLI-R06 no `__version__` | 3.2 |