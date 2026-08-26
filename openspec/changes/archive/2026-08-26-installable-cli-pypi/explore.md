# Exploration: installable-cli-pypi

Issue #29 — make `sofer` installable as a standalone CLI via `pip install sofer` / `uv tool install sofer`, packaged for PyPI.

Scope of this exploration: verify the current packaging state, close the gaps to `pip install sofer` / `uv tool install sofer` / PyPI publish, recommend a versioning strategy, identify the release.yml insertion point, test needs, and risks.

## Current State

### Build system (hatchling) — WORKS
- `pyproject.toml` `[build-system]` = `requires = ["hatchling"]`, `build-backend = "hatchling.build"` (pyproject.toml:116-118).
- **`uv build` succeeds**: produces `sofer-0.1.0-py3-none-any.whl` (95 KB) + `sofer-0.1.0.tar.gz`. Verified in a sandbox out-dir.
- Hatchling **auto-detected `src/sofer`** with no `[tool.hatch.build.targets.wheel]` section. The wheel contains all 24 `sofer/*.py` modules, `sofer-0.1.0.dist-info/METADATA`, `entry_points.txt`, and `licenses/LICENSE` (hatchling's default `license-files` glob includes `LICEN[CS]E*`). No `[tool.hatch]` config is needed.
- **No package data required**: `src/sofer` is pure Python (no non-py runtime files). All tool defaults live as module constants in `config.py` (`_DEFAULTS`); the `init` template is an in-code string (`cli.py:352` `_INIT_TEMPLATE`). The wheel does not ship `pyproject.toml`, which is correct — the installed tool falls back to `config.py` defaults.

### Entry point — WORKS
- `[project.scripts]` `sofer = "sofer.cli:main"` (pyproject.toml:16-17); the wheel's `entry_points.txt` contains `[console_scripts] sofer = sofer.cli:main`.
- `cli.py:742` `def main() -> None:` → `config.reload(None)` → `_build_parser()` → `sys.exit(args.func(args))`. `if __name__ == "__main__": main()` guard present (`cli.py:760`). Exit codes propagate correctly (`--help` raises `SystemExit(0)`).
- Windows console script generated and works.

### Verified end-to-end (sandboxed, no repo mutation)
| Check | Result |
|-------|--------|
| `uv build` | ✅ wheel + sdist built |
| `uv tool install .` (isolated `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR`) | ✅ resolved 22 packages; `sofer.exe --help` exit 0; `sofer.exe --version` → `sofer v0.1.0` |
| `uv pip install --no-deps .` (fresh venv) | ✅ console script `sofer.exe` generated (traceback only because `--no-deps`; full-deps path proven by tool install) |

### Dependencies — complete, no undeclared/optional gaps
`huggingface-hub>=0.26.0`, `openpyxl>=3.1`, `pyarrow>=14.0`, `python-dotenv>=1.0.0`, `tomli>=2.0; python_version < '3.11'`, `tomli-w>=1.0`, `pyyaml>=6.0` (pyproject.toml:6-14).
- `tomli` uses a marker (`<3.11`) + the `try: import tomli / except ImportError: import tomllib` fallback (config.py:124, model.py:343, cli.py:272) — correct on 3.11+, no duplicate install.
- All heavy deps (`pyarrow`, `huggingface_hub`) ship binary wheels on PyPI and resolve normally.

### Metadata gaps for PyPI
`[project]` is missing: `readme`, `license`, `authors`, `keywords`, `classifiers`, `project.urls`. Present: `name`, `version`, `description`, `requires-python = ">=3.10"`, `dependencies`.
- `README.md` exists, is **valid UTF-8** (Hebrew `סופר` and `semántico` render correctly — earlier mojibake was console codepage only), and is PyPI-safe.
- `LICENSE` = MIT, Copyright (c) 2025 Emilio Davola; already bundled into the wheel.

### PyPI name availability
`https://pypi.org/pypi/sofer/json` returns **404** (no project with releases). Web search shows only `soferai` (Sofer.Ai SDK — a distinct name). `sofer` **appears available**; confirm definitively at publish time (see Risks).

## Versioning — DUAL SOURCE, ALREADY DRIFTED ON `main`

- Version lives in **two** places: `version = "0.1.0"` (pyproject.toml:3) AND `__version__ = "0.1.0"` (`src/sofer/__init__.py:18`). No dynamic versioning.
- **Live drift bug**: `main` has `pyproject.toml` = `0.2.0` but `src/sofer/__init__.py` = `0.1.0`. The released **v0.2.0 tag** (Aug 24) therefore prints `sofer v0.1.0` via `--version`. `sofer --version` comes from `__version__` (cli.py:462).
- Tags: `v0.1.0` (Aug 1), `v0.2.0` (Aug 24). Current `dev`/this branch = `0.1.0` in both files.
- Runtime consumers read `__version__` (e.g. `test_metadata.py:214,220` asserts generated metadata `version == __version__`). The release *process* (AGENTS.md rule 12) treats `pyproject.toml` as SSOT. Two sources, no drift test → drift already happened once.

### Options
| Option | Description | Pros | Cons | Effort |
|--------|-------------|------|------|--------|
| **A. Hatchling file version** | `[project] dynamic = ["version"]` + `[tool.hatch.version] path = "src/sofer/__init__.py"`; bump `__init__.py` on release | Single source (code); `sofer --version` can never diverge from wheel metadata; hatchling core feature | Changes documented release step; update AGENTS.md rule 12 | Low |
| B. Keep pyproject SSOT, derive `__init__` via `importlib.metadata` | `__version__ = version("sofer")` | Honors "pyproject SSOT" | Fragile in dev/editable/CI contexts (needs install); slower import | Low-Med |
| C. Status quo + drift test | Keep both static; add test asserting pyproject version == `__version__` | Minimal change | Two edit points every release; already failed once (v0.2.0) | Low |

**Recommendation: Option A.** It makes `__init__.py` the single source, and the release step becomes "bump `__version__` in `src/sofer/__init__.py`" (AGENTS.md rule 12 updated in the same change). The v0.2.0 drift is direct evidence the dual-source approach already broke.

## Release Workflow (`release.yml`)

- Trigger: `push: tags: ["v*"]`; `permissions: contents: write`.
- Jobs: `lint` (ruff + mypy, Python 3.13), `test` (matrix 3.10–3.14, `pytest -v`), `release` (`needs: [lint, test]`, `softprops/action-gh-release` with `generate_release_notes: true`).
- **GitHub Release ONLY — no PyPI publish today** (confirmed; AGENTS.md rule 12: "There is no PyPI publishing"; tag-driven).
- `ci.yml` (PR trigger) mirrors the same lint + test matrix and already runs `uv run sofer --help` as a smoke step (ci.yml:43-44).

### PyPI insertion point
Add a new `publish-pypi` job to `release.yml`, `needs: [lint, test]`, running after/parallel to `release`:
```
- uses: actions/checkout@v4
- uses: astral-sh/setup-uv@v5
- run: uv build
- run: uv publish            # OIDC trusted publishing; needs id-token: write at workflow level
```
Requires `permissions: id-token: write` (plus existing `contents: write` for release notes). Use `uv publish` (tool is already in the stack, uv 0.12.1) rather than twine.

## Gaps to Close (for #29)

1. **`[project]` metadata** (pyproject.toml): add `readme = "README.md"`, `license = "MIT"` (PEP 639) + `license-files` (or SPDX string + `license-files = ["LICENSE"]`), `classifiers` (Development Status, `License :: OSI Approved :: MIT License`, `Programming Language :: Python :: 3.10`…`3.14`, Topic), `project.urls` (Repository / Homepage / Issues), optionally `authors`.
2. **Versioning**: adopt Option A (single source from `__init__.py`) and fix the existing `main` drift. **Bump to `0.3.0` for the first PyPI release** — `dev` sits at `0.1.0`, latest GitHub release is `v0.2.0`; publishing `0.3.0` avoids re-upload confusion and marks the packaging debut (semver pre-1.0 minor bump, AGENTS.md-compatible).
3. **PyPI publish**: add the `publish-pypi` job to `release.yml` (uv build + uv publish, OIDC). One-time prerequisite: the PyPI project must exist before OIDC works — first upload is a manual API-token upload, then enable trusted publishing for `emiliodavola/sofer` on the PyPI project page.
4. **README**: add an Install section documenting `pip install sofer` and `uv tool install sofer` (AGENTS.md rule 7 — README must reflect the CLI).
5. **Tests**: add packaging/entry-point tests (below).
6. **AGENTS.md rule 12**: update "There is no PyPI publishing" and the version-bump step wording (SSOT moves to `__init__.py`).

## Testing

- **Existing (795 tests)**: `test_cli.py` covers argparse parsing, `--help`, `--version`, `upload`-removed, and `test_main_help_prints` (monkeypatched `sys.argv` + `cli.main()`). `ci.yml` runs `uv run sofer --help`. **No** subprocess/installed-script test, **no** packaging test, **no** version-consistency test.
- **Needed**:
  - Version consistency: assert `pyproject.toml version` == `sofer.__version__` (read TOML via `tomllib`) — catches drift.
  - Build smoke test: `uv build` into a temp dir (subprocess) → wheel exists → `entry_points.txt` contains `sofer = sofer.cli:main`.
  - Installed-CLI test: subprocess running the console script (`sofer --help`, exit 0) against a non-editable build — this is the literal acceptance criterion ("`sofer --help` without `uv run`").
  - Optional: `importlib.metadata.version("sofer") == sofer.__version__` when installed.
  - Add a CI/release job that installs the built wheel and runs `sofer --help` (true acceptance signal, complements the existing in-repo smoke step).

## Edge Cases / Gotchas

- **Windows console scripts**: installer-generated `sofer.exe` shim — verified working on win32 (sandboxed `uv tool install`).
- **`main()` + exit codes**: `main() -> None` calls `sys.exit(args.func(args))` — int codes propagate; argparse `SystemExit(0)` for `--help` works.
- **`config.reload(None)`** walks up from cwd to find a user `pyproject.toml` `[tool.sofer]` (issue #56). The installed global tool therefore reads the *user's* project config or falls back to `config.py` defaults — intended, and the wheel correctly ships no `pyproject.toml`.
- **`tomli`/`tomllib`**: marker `<3.11` prevents duplicate install; fallback import pattern correct in three modules.
- **Pure wheel**: `py3-none-any`; `pyarrow`/`huggingface_hub` are binary deps resolved normally from PyPI — no ABI concerns.
- **Version drift already shipped** (main v0.2.0 tag carries `__version__` 0.1.0) — the change MUST unify versioning.
- **First OIDC publish is chicken-and-egg**: trusted publishing can only be configured on an *existing* PyPI project; one manual API-token upload is required first.
- **sdist contents**: hatchling includes VCS-tracked files (tests, docs) — acceptable; optionally exclude via `[tool.hatch.build.targets.sdist] exclude` (low priority).

## Affected Areas
- `pyproject.toml` — `[project]` metadata (readme, license, classifiers, urls), versioning (dynamic + `[tool.hatch.version]`), existing `[project.scripts]`.
- `src/sofer/__init__.py` — becomes the single version source.
- `.github/workflows/release.yml` — new `publish-pypi` job + `id-token: write`.
- `.github/workflows/ci.yml` — optional installed-wheel smoke step.
- `README.md` — Install section (AGENTS.md rule 7).
- `AGENTS.md` — rule 12 wording (PyPI + version SSOT).
- `tests/` — new packaging/entry-point/version-consistency tests.
- `openspec/specs/cli/spec.md` (or a new `packaging` spec) — likely the domain for spec deltas.

## Recommendation
Proceed to **proposal**. Concrete approach: (1) add PyPI metadata to `[project]`; (2) switch to single-source versioning (hatchling file version from `__init__.py`), fix the `main` drift, release as `0.3.0`; (3) add a `publish-pypi` job to `release.yml` using `uv build` + `uv publish` with OIDC; (4) document `pip install sofer` / `uv tool install sofer` in README; (5) add ~3–4 packaging tests + a wheel-install smoke step; (6) update AGENTS.md rule 12.

## Risks
- **PyPI name availability**: Low — JSON API 404 + no conflicting package found; confirm at publish time (the similarity check with `soferai` is acceptable, but the definitive check happens when the project is created).
- **First OIDC publish requires a manual API-token upload** before trusted publishing can be enabled — operational prerequisite, not code.
- **Version drift fix touches the documented release process** (AGENTS.md rule 12) — must update docs in the same change and ensure the `__version__` bump lands in the same release commit as the tag.
- **uv publish availability**: `uv publish` exists in the installed uv (0.12.1); if a broader uv version floor is desired, pin `astral-sh/setup-uv`.

## Ready for Proposal
**Yes.** The orchestrator should tell the user: packaging already builds and installs correctly (`uv build`, `uv tool install`, console script all verified); the real work is PyPI metadata + single-source versioning (with a pre-existing drift bug on `main`) + a publish job in release.yml + tests + README install docs. First PyPI release recommended at `0.3.0`.
