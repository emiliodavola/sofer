# Design: Installable CLI — release-ready packaging (hatch-vcs, metadata, docs, tests)

## Technical Approach

Single-source versioning: the git tag is the version SSOT (PKG-01). At build time `hatch-vcs` stamps the tag-derived version into wheel METADATA; at runtime a shared resolver (`src/sofer/_version.py`) reads installed metadata via `importlib.metadata` — so `sofer --version` and `generated.version` (CLI-R05/CLI-R06) can never drift from the wheel. The static `version = "0.1.0"` (`pyproject.toml:3`) and `__version__ = "0.1.0"` (`__init__.py:18`) are removed — the dual-source drift bug (v0.2.0 tag shipping `0.1.0`) is structurally eliminated. Complete `[project]` metadata (PKG-02), a wheel-verification job in `release.yml` (no publish), README install docs (PKG-05), AGENTS.md rule 12 rewrite, and packaging tests (PKG-04) land in the same change.

## Architecture Decisions

### D1: Version resolver — `src/sofer/_version.py`

**Choice**: New private module with `get_version() -> str`: `importlib.metadata.version("sofer")` primary; on `PackageNotFoundError`, deterministic PEP 440-valid sentinel `0.0.0.dev0` ("unknown build" marker) — **no `git describe` normalization** (hatch-vcs's setuptools-scm derivation is documented, not reimplemented, so the fallback never pretends to match a built wheel). `functools.lru_cache(maxsize=1)` (one resolution per process; CLI + metadata stamping agree).
**Alternatives**: (a) exploration's Option A — `[tool.hatch.version] path = __init__.py` file version — rejected: keeps a static literal in `src/` (violates PKG-01 "no static version literal in package source") and still needs a manual bump each release; (b) static `__version__` + drift test (Option C) — rejected: two edit points, already failed once; (c) `packaging` library for validation — rejected: not a declared dependency (AGENTS.md rule 9), both producers are PEP 440-conformant by construction.
**Rationale**: `importlib.metadata` reads exactly what the wheel declares (hatch-vcs stamped) — "never lies on released wheels"; editable installs under `uv sync` also register dist-info, so dev contexts resolve via the primary path (CLI-R06 scenario 2: "dev/editable install" → hatch-vcs dev version, never a literal). The sentinel covers bare-source-tree execution (no install) and signal-less environments; it is a *marker*, not the distribution version — tests never compare against it (PKG-04). **Actual hatch-vcs output (verified on real wheels)**: off-tag builds are `NEXT.devN+g<sha>` — v0.3.0 + 1 commit ships `0.3.1.dev1+g<sha>` — and zero-tag checkouts (like this branch: no reachable tags) ship `0.1.devN+g<sha>`. The resolver does NOT reproduce these shapes, so a bare-tree run does NOT report what a build at that commit would ship; only installed metadata is authoritative. Full contract in Interfaces/Contracts.

### D2: `--version` output format

**Choice**: Keep `sofer v<version>` (CLI-R05 scenario 1 asserts exactly `sofer v0.3.0`). `cli.py:462` becomes `version=f"sofer v{get_version()}"`; argparse `action="version"` already prints to stdout and exits 0. `main()` dispatch and the `__main__` guard (cli.py:742/760) untouched.
**Alternatives**: bare `<version>` or `sofer <version>` — rejected: changes the CLI surface (out of scope) and breaks the spec scenario.
**Rationale**: Zero interface change; only the version source moves.

### D3: pyproject.toml — dynamic version + metadata

**Choice**: Remove static `version`; add `dynamic = ["version"]` + `[tool.hatch.version] source = "vcs"`; add `hatch-vcs` to `[build-system].requires`; add `readme`, PEP 639 `license = "MIT"` + `license-files = ["LICENSE"]`, `classifiers` (3.10–3.14, MIT, Dev Status 4-Beta, Topic), `project.urls` (github.com/emiliodavola/sofer), `authors = [{ name = "Emilio Davola" }]` (from LICENSE copyright). No `[tool.hatch.build.targets.wheel]` section — hatchling auto-detects the `src/sofer` layout (verified in exploration; unchanged by hatch-vcs).
**Alternatives**: legacy `license = {text = "MIT"}` — rejected: deprecated by PEP 639; SPDX string is the current standard.
**Rationale**: Exact block in Interfaces/Contracts. `Development Status :: 4 - Beta` fits pre-1.0 with a stable CLI and 795 passing tests. No release-version number is chosen (out of scope — tag decides).

### D4: release.yml — wheel validation job; ci.yml unchanged

**Choice**: New `build` job in `release.yml`, `needs: [lint, test]`; `release` job gains `needs: [lint, test, build]`. The job runs `uv build`, then asserts (a) wheel METADATA `Version:` equals the pushed tag (`${GITHUB_REF_NAME#v}`) — PKG-01 "tagged build matches the tag"; (b) `entry_points.txt` contains `sofer = sofer.cli:main` — PKG-03; (c) `licenses/LICENSE` bundled — PKG-02; (d) METADATA contains `Classifier:` and `Project-URL:` lines — PKG-02 "metadata complete" scenario (dedicated step below). **ci.yml gets no change — and it exists**: `.github/workflows/ci.yml` is the PR workflow (lint + 5-version test matrix + a `uv run sofer --help` smoke step at ci.yml:43-44); `.github/workflows/release.yml` is the tag workflow (lint + test + release). The proposal's "`.github/workflows/ci.yml` | Modified | Optional wheel-install smoke step" row is superseded: the installed-CLI/entry-point paths are covered by the PKG-04 pytest suite per matrix cell, and the wheel-validation job lives in release.yml because its assertions need a tag (PR builds have none).
**Alternatives**: build step inside the `lint` job — rejected: conflates concerns and runs before tests; adding the job to `ci.yml` — rejected: PR builds have no tag, so the METADATA==tag assertion cannot run there.
**Rationale**: Tag-only facts belong in the tag-triggered workflow; everything else is already exercised per-matrix-cell by tests. Exact YAML in Interfaces/Contracts.

### D5: AGENTS.md rule 12 rewrite

**Choice**: Replace step 2 ("Bump version in pyproject.toml on main — SSOT") with "no bump anywhere — the tag is the SSOT"; step 3 drops the `chore(release): bump version` commit (version lives in the tag; `--follow-tags` pushes the tag on the merge commit); keep "no PyPI publishing", mypy-3.13, never-move-a-tag, and branch-flow rules verbatim. Exact replacement text in Interfaces/Contracts.
**Rationale**: The old step is now obsolete (no static version field exists to bump) and is the documented root of the drift habit.

### D6: README Install section

**Choice**: New `## Install` section immediately after the tagline blockquote (before `## Why`), documenting `pip install sofer` and `uv tool install sofer`, plus "`sofer --version` always matches the release tag". `## Setup` retitled `## Development setup` (its content is dev-oriented). Architecture tree line 366 (`__init__.py  # Version + public API`) updated and `_version.py` added. Exact text in Interfaces/Contracts.
**Alternatives**: after `## Why` — rejected: install is the first thing a new reader needs.
**Rationale**: AGENTS.md rule 7 — README reflects the CLI; the Install section is the acceptance surface for PKG-05.

### D7: Test rework + new packaging tests

**Choice**: `tests/test_metadata.py:14/214/220` switch `__version__` → `get_version()` (import `sofer._version`), assert non-empty, and add a CLI-R06 equality test (`generated.version` == `--version` output stripped of `sofer v`). `tests/test_cli.py` `test_version` asserts `out.strip() == f"sofer v{get_version()}"` + exit 0 (capsys). New `tests/test_packaging.py`: (1) resolver non-empty + PEP 440 regex; (2) `pyproject.toml` has `dynamic = ["version"]` and no static `version =`; (3) `__init__.py` contains no `__version__`; (4) fallback — monkeypatch `importlib.metadata.version` to raise → sentinel returned, non-empty + PEP 440-valid, with `get_version.cache_clear()` (no git/subprocess branch exists to fake); (5) build smoke — `uv build` into tmp, wheel exists, `entry_points.txt` via stdlib `zipfile`, METADATA contains `Classifier:` and `Project-URL:` lines (PKG-02) — note `uv build` is NOT network-free: the first run's build isolation fetches `hatch-vcs`/`setuptools-scm` from the index, uv caches thereafter; (6) installed-CLI subprocess — wheel built; fresh `uv venv <tmp-venv>`; `uv pip install --python <tmp-venv>/Scripts/python.exe --no-deps <wheel>`; then a `.pth` file in the tmp venv's site-packages pointing at the project venv's purelib (`sysconfig.get_path("purelib")` of the project venv python — portable across win32 `Lib\site-packages` / POSIX `lib/pythonX.Y/site-packages`). NOT `uv venv --system-site-packages --python .venv/.../python.exe`: verified on uv 0.12.1/win32 that uv de-references a venv interpreter to its base (empty site-packages), so `sofer --help` crashes on `import pyarrow`; the `.pth` indirection reuses the project venv's deps hermeticly (offline, no shared-env mutation) while proving the wheel's entry point runs standalone. Run console script (`Scripts/sofer.exe` win32 / `bin/sofer` POSIX): `--help` → 0; `--version` → 0, non-empty, and starts with `sofer v` (CLI-R05 prefix — exact `sofer v0.3.0` is NOT assertable here: a non-tag commit ships the hatch-vcs dev version (zero-tag → `0.1.devN+g<sha>`), and PKG-04 forbids literals; exactness is the release.yml METADATA==tag job's job).
**Alternatives**: installed-CLI test with full `uv pip install` dep resolution — rejected: network + slow per matrix cell; `uv venv --system-site-packages --python <project-venv>` (gate-review suggestion) — rejected after empirical verification on uv 0.12.1/win32: uv bases the new venv on the venv interpreter's *base* (de-referencing), so `--system-site-packages` exposes empty site-packages and the installed CLI crashes on import; the `.pth` indirection is the hermetic equivalent.
**Rationale**: Every PKG-01..05 + CLI-R05/06 scenario maps to a test (AGENTS.md rule 6).

### D8: Rollback boundary + work-unit commit split

**Choice**: Two independently green commits (each passes `uv run pytest tests/ -q`):
1. **Version resolver** (code): `_version.py` + `__init__.py` (drop `__version__`) + `cli.py` + `metadata.py` + reworked `test_metadata.py`/`test_cli.py`. Green because pyproject still declares static `0.1.0` → `importlib.metadata` returns it → tests pass. Revert = restore static `__version__`.
2. **Packaging + docs**: `pyproject.toml` + `release.yml` + `AGENTS.md` + `README.md` + `tests/test_packaging.py`; re-run `uv sync` (pick up hatch-vcs dev version) before the green check. Revert = restore prior pyproject/workflow/docs.
**Alternatives**: single commit — rejected: ~450–550 lines, near/over the 400-line review budget; the split isolates the behavior change (1) from the packaging surface (2).
**Rationale**: Each slice is reviewable, independently verifiable, and trivially revertible; hatch-vcs never mutates git, tags unaffected (proposal rollback plan).

## Data Flow

    Build time (release tag pushed):
      git tag v0.3.0 ──▶ hatch-vcs ──▶ wheel METADATA Version: 0.3.0
                                          wheel entry_points.txt: sofer = sofer.cli:main
                                          wheel licenses/LICENSE (hatchling default glob)

    Runtime (installed console script):
      sofer --version ──▶ cli.py ──▶ get_version()
      profile ──▶ GeneratedMetadata.version (default_factory) ──▶ get_version()
                                     │
        get_version(): importlib.metadata.version("sofer")  ◀── dist-info (wheel/editable)
                       │ PackageNotFoundError (bare source tree)
                       └── sentinel "0.0.0.dev0" (marker — never asserted, never
                                                 claimed to match the wheel; no
                                                 git-describe path)

    hatch-vcs shapes at build time (verified on real wheels): off-tag
    `NEXT.devN+g<sha>` (v0.3.0 + 1 commit → `0.3.1.dev1+g<sha>`); zero-tag
    `0.1.devN+g<sha>` (this branch). The runtime resolver does not reproduce them.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_version.py` | Create | Shared runtime version resolver (`get_version`) — see Interfaces/Contracts |
| `src/sofer/__init__.py` | Modify | Remove `__version__ = "0.1.0"` (line 18); docstring-only module |
| `src/sofer/cli.py` | Modify | Line 14 import → `from ._version import get_version`; line 462 → `version=f"sofer v{get_version()}"` |
| `src/sofer/metadata.py` | Modify | Line 25 import; line 177 → `version: str = field(default_factory=get_version)`; line 172 docstring |
| `pyproject.toml` | Modify | `dynamic = ["version"]`, hatch-vcs, metadata block (exact below) |
| `.github/workflows/release.yml` | Modify | New `build` job + `release` needs (exact below) |
| `AGENTS.md` | Modify | Rule 12 rewrite (exact below) |
| `README.md` | Modify | `## Install` section, `## Setup` → `## Development setup`, Architecture tree |
| `tests/test_metadata.py` | Modify | `get_version()` assertions + CLI-R06 equality test |
| `tests/test_cli.py` | Modify | `test_version` asserts `sofer v{get_version()}` |
| `tests/test_packaging.py` | Create | PKG-04 tests: resolver, source scan, build smoke, installed-CLI subprocess |

Note: `src/sofer/profile.py` needs no change — `GeneratedMetadata(timestamp=...)` (line 119) inherits the new `default_factory`.

## Interfaces / Contracts

### `src/sofer/_version.py` (contract)

```python
"""Runtime resolution of the sofer distribution version.

Single source for ``sofer --version`` and the version stamped into generated
documents (``generated.version``). The distribution version is derived from
the git release tag by hatch-vcs at build time; this module resolves it at
runtime. Never raises, never returns an empty string.

The git fallback is intentionally NOT a reproduction of hatch-vcs. Actual
hatch-vcs shapes (verified on built wheels): off-tag ``NEXT.devN+g<sha>``
(v0.3.0 + 1 commit ships ``0.3.1.dev1+g<sha>``); zero-tag ``0.1.devN+g<sha>``
(a checkout with no reachable tags). A bare-tree run therefore does NOT
report what a build at that commit would ship — only installed metadata is
authoritative. The fallback is a marker, never compared against wheel output.
"""

from __future__ import annotations

import importlib.metadata
from functools import lru_cache

# Distribution name registered in pyproject.toml [project] — a name, not a version.
_DISTRIBUTION_NAME = "sofer"
# Marker for environments with no version signal (not installed). This is NOT
# the distribution version — it is an "unknown build" sentinel in the
# setuptools-scm convention; tests never compare against it (PKG-04).
_UNKNOWN_VERSION = "0.0.0.dev0"


@lru_cache(maxsize=1)
def get_version() -> str:
    """Return the sofer version: non-empty and PEP 440-valid, never raises.

    Resolution order:
      1. Installed distribution metadata (importlib.metadata) — the
         hatch-vcs-derived version stamped at build/install time. Covers
         released wheels (tag) and editable installs (dev version).
      2. ``_UNKNOWN_VERSION`` when the distribution is not installed (bare
         source tree or signal-less environment) — a deterministic marker,
         not a claim about what a build would ship.
    """
```

No git-describe normalization exists. When the distribution is not installed, `get_version()` returns `_UNKNOWN_VERSION` (`0.0.0.dev0`) — deterministic, non-empty, PEP 440-valid. All failure paths (metadata lookup raising) return the sentinel; the function never raises and never returns an empty string. The actual hatch-vcs derivation (setuptools-scm) is deliberately not reimplemented: reproducing `NEXT.devN+g<sha>` / `0.1.devN+g<sha>` would require running setuptools-scm itself, and the fallback's output is never compared to wheel metadata (tests assert non-empty + PEP 440 only, PKG-04).

### `pyproject.toml` — `[project]` replacement

```toml
[project]
name = "sofer"
dynamic = ["version"]
description = "Publish any dataset to Hugging Face Hub with built-in validation and data-sharing standards."
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
license-files = ["LICENSE"]
authors = [{ name = "Emilio Davola" }]
classifiers = [
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Topic :: Scientific/Engineering",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
dependencies = [  # unchanged: huggingface-hub, openpyxl, pyarrow, python-dotenv, tomli (marker), tomli-w, pyyaml
]
```

Plus (elsewhere in the file):

```toml
[project.urls]
Homepage = "https://github.com/emiliodavola/sofer"
Repository = "https://github.com/emiliodavola/sofer"
Issues = "https://github.com/emiliodavola/sofer/issues"

[tool.hatch.version]
source = "vcs"

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"
```

### `.github/workflows/release.yml` — added job

```yaml
  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.13"
      - name: Install dependencies
        run: uv sync
      - name: Build distribution
        run: uv build --out-dir dist
      - name: Verify wheel METADATA version matches the tag
        run: |
          WHEEL=$(ls dist/sofer-*.whl)
          VERSION=$(unzip -p "$WHEEL" 'sofer-*.dist-info/METADATA' | sed -n 's/^Version: //p')
          test "$VERSION" = "${GITHUB_REF_NAME#v}"
      - name: Verify wheel METADATA completeness (PKG-02)
        run: |
          WHEEL=$(ls dist/sofer-*.whl)
          unzip -p "$WHEEL" 'sofer-*.dist-info/METADATA' > metadata.txt
          grep -q '^Classifier:' metadata.txt
          grep -q '^Project-URL:' metadata.txt
      - name: Verify console-script entry point
        run: |
          WHEEL=$(ls dist/sofer-*.whl)
          unzip -p "$WHEEL" '*/entry_points.txt' | grep -q 'sofer = sofer.cli:main'
      - name: Verify LICENSE bundled
        run: |
          WHEEL=$(ls dist/sofer-*.whl)
          unzip -l "$WHEEL" | grep -q 'licenses/LICENSE'
```

`release` job: `needs: [lint, test, build]`. No publish job, no `id-token` (out of scope). The job runs on ubuntu-latest where network is available; the first `uv sync` / `uv build` fetches build deps (hatch-vcs) from the index, cached by uv thereafter.

### `AGENTS.md` rule 12 — exact replacement (lines 76–89)

```markdown
### 12. Release process
Releases are **tag-driven and automated** by `.github/workflows/release.yml`: pushing a `v*` tag runs lint + the full test matrix + a wheel-build validation job, then creates a GitHub Release with auto-generated notes. There is no PyPI publishing.

Cutting a release:
1. Sync `main` with `dev`: `git checkout main && git merge --no-ff dev`. Note: `main` is **not** a fast-forward of `dev` (release PR merge commits live on `main`), so always use `--no-ff`.
2. Do **not** bump a version anywhere: the version is derived from the tag at build time (hatch-vcs, `[tool.hatch.version] source = "vcs"`). The tag is the single source of truth — `pyproject.toml` has no static `version` field and there is no `__version__` constant.
3. Create an annotated tag on the merge commit (`git tag -a vX.Y.Z -m "sofer vX.Y.Z"`) and push with `git push origin main --follow-tags`.
4. Verify: `gh run list --workflow=release.yml` must go green (including the wheel-build job asserting the wheel METADATA version equals the tag); the release appears under GitHub Releases with notes generated from commits/PRs since the previous tag.

Rules:
- Versioning is semver; pre-1.0 minor bumps (0.x) may carry breaking changes — document them in the release notes (e.g. v0.2.0 removed the `upload` subcommand). The shipped version always equals the tag: `vX.Y.Z` installs as `sofer vX.Y.Z` via `--version`, resolved at runtime from installed metadata (never a static constant).
- **Never move or delete a pushed tag** unless the release job never ran (e.g. quality gates failed before publishing); in that case fix on `dev`, merge to `main`, delete the tag locally and remotely, and re-tag.
- The workflow's lint job intentionally runs mypy only under Python 3.13, mirroring CI. Do not add mypy to the version matrix: under 3.10 the `import tomli as tomllib` fallback triggers `no-redef` errors (known latent issue in `model.py`, `config.py`, `cli.py`).
- Branch flow: all work lands on `dev` first; `main` receives changes only via merges from `dev` (typically at release time).
```

### `README.md` — Install section (insert after the tagline blockquote, before `## Why`)

```markdown
## Install

sofer is a standalone CLI — install it once, run it anywhere:

```bash
pip install sofer
# or, with uv (isolated tool install):
uv tool install sofer
```

Then run `sofer --help`. `sofer --version` always matches the release tag
(e.g. `v0.3.0` installs as `sofer v0.3.0`).
```

Rename `## Setup` → `## Development setup` (content unchanged). Architecture tree: `__init__.py  # Version + public API` → `__init__.py  # Package docstring + public API`; add `_version.py  # Runtime version resolution (installed metadata + dev fallback)`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `get_version()` non-empty + PEP 440 (never literal) | `tests/test_packaging.py` — regex assert |
| Unit | Fallback (metadata raises) | monkeypatch `importlib.metadata.version` + `get_version.cache_clear()` → sentinel, non-empty, PEP 440-valid |
| Unit | No static version literal anywhere | source scan: `pyproject.toml` has `dynamic = ["version"]`, no `version =`; `__init__.py` has no `__version__` |
| Unit | CLI-R06 stamping equality | `test_metadata.py` — `generated.version` == `get_version()` == `--version` output stripped of `sofer v` |
| Integration | Build smoke | `uv build` subprocess → wheel exists → `entry_points.txt` + METADATA `Classifier:`/`Project-URL:` via `zipfile` (first run needs network for build isolation; uv cache thereafter) |
| E2E | Installed-CLI subprocess | wheel → fresh `uv venv` + `--no-deps` install + `.pth` to project venv purelib → console script `--help` exit 0; `--version` exit 0, non-empty, starts with `sofer v` |

Green gate per commit: `uv run pytest tests/ -q` + `uv run mypy src/` + `uv run ruff check src/ tests/`.

## Migration / Rollout

No migration. Two-commit rollout (D8); each commit independently revertible — commit 1 revert restores static `__version__`, commit 2 revert restores the prior pyproject/workflow/docs. hatch-vcs never mutates git; existing tags (`v0.1.0`, `v0.2.0`) untouched. Note: after commit 2 lands, contributors must re-run `uv sync` so the editable install picks up the hatch-vcs-derived version.

## Open Questions

- None blocking. (Apply-phase notes: confirm hatchling on the resolved uv version accepts PEP 639 `license-files`; uv 0.12.1 verified to ship both `uv venv --system-site-packages` and `--python` flags; the exact PEP 440 regex used in the resolver test is an apply detail; confirm the `.pth` E2E recipe on the ubuntu CI runner — uv's venv-interpreter de-referencing is platform-independent interpreter resolution, so it is expected identical on POSIX, but only win32 was verified. Stale items to fix during apply, out of this design's edit scope: `openspec/specs/packaging/spec.md` PKG-01 still carries the example `0.2.0.post5+g<sha>` (update to the verified `NEXT.devN+g<sha>`), and `AGENTS.md:44` still quotes the old "422 tests" count — the suite is 795.)