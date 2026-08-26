# Proposal: Installable CLI — release-ready packaging (hatch-vcs, metadata, docs, tests)

## Intent

Make `sofer` release-ready as a standalone installable CLI (`pip install sofer` / `uv tool install sofer`, issue #29) WITHOUT publishing to PyPI yet. Packaging already builds and installs correctly (verified in exploration: `uv build`, `uv tool install`, console script on win32). The real gaps: PyPI metadata, versioning — dual-source already drifted (v0.2.0 tag ships `__version__=0.1.0`) — README install docs, and packaging tests.

## Scope

### In Scope
- hatch-vcs tag-driven versioning: `[project] dynamic = ["version"]` + `[tool.hatch.version] source = "vcs"`, add `hatch-vcs` to `[build-system] requires`; remove static `version` / `__version__`; `sofer --version` derives from the release tag (never lies on released wheels).
- Complete `[project]` metadata: `readme`, `license` + `license-files`, `classifiers` (Py 3.10–3.14, MIT, Dev Status, Topic), `project.urls`, `authors`. LICENSE already bundled by hatchling default.
- README Install section: `pip install sofer` / `uv tool install sofer`.
- AGENTS.md rule 12 update: version SSOT moves to the release tag (hatch-vcs); "no PyPI publishing" wording retained; version-bump step wording replaced.
- Packaging tests: version-consistency (build-time derived), build smoke (`uv build` → wheel → `entry_points.txt`), installed-CLI subprocess (`sofer --help` exit 0; `--version` non-empty — never a hardcoded literal).
- release.yml: validate the built wheel + entry points in the quality-gate path; NO publish job.

### Out of Scope
- PyPI publish job, OIDC / API-token setup, actual publishing (user decision).
- Changing the CLI interface; Docker; choosing the first release version number (tag decides at release time).

## Capabilities

### New Capabilities
- `packaging`: distribution contract — build system, metadata, tag-driven versioning, entry points, installability. No existing domain fits (`publish` = HF Hub delivery; `cli` = command surface). New spec is warranted: release-readiness is an ongoing contract that future release work (actual PyPI publishing) will extend. Not small enough to document in the change folder only.

### Modified Capabilities
- `cli`: ADDED requirement CLI-R05 — `sofer --version` output derives from the installed release tag (no static constant), format `sofer v<version>`. Delta spec in the change folder.

## Approach

- pyproject.toml: `dynamic = ["version"]`, `[tool.hatch.version] source = "vcs"`, build-system `requires = ["hatchling", "hatch-vcs"]`; static `version` removed.
- `src/sofer/__init__.py`: drop static `__version__`; runtime version resolved via `importlib.metadata` (used by `cli.py --version` and `metadata.py` document stamping) — exact mechanism in design.
- Metadata block per exploration (README.md valid UTF-8, MIT LICENSE already bundled).
- release.yml: build wheel + assert entry point in lint/test path (tag-triggered, no publish, no `id-token`).
- Tests updated in same change (existing `test_metadata.py` asserts `version == __version__`).
- README + AGENTS.md rules 7/12 updated in same change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `pyproject.toml` | Modified | Version dynamic + hatch-vcs, metadata additions, build-system |
| `src/sofer/__init__.py` | Modified | Static `__version__` removed/derived |
| `src/sofer/cli.py` | Modified | `--version` resolves installed metadata |
| `src/sofer/metadata.py` | Modified | Generator version stamping source |
| `.github/workflows/release.yml` | Modified | Wheel build + entry-point validation; no publish |
| `.github/workflows/ci.yml` | Modified | Optional wheel-install smoke step |
| `README.md` | Modified | Install section |
| `AGENTS.md` | Modified | Rule 12 version SSOT wording |
| `tests/` | Added | Packaging tests (version-consistency, build smoke, installed CLI) |
| `openspec/specs/packaging/spec.md` | New | Packaging capability spec |
| `openspec/changes/installable-cli-pypi/specs/cli/spec.md` | New | CLI delta (CLI-R05) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Runtime version resolution fragile in dev/editable contexts | Med | `importlib.metadata` with fallback; tests assert non-empty |
| hatch-vcs emits dev versions (`0.1.devN+gHASH`) off-tag | Low | Documented; tests never assert a literal |
| Removing `__version__` breaks `metadata.py` document stamping | Med | Shared version resolver; metadata tests updated in same change |
| Old "bump pyproject" release habit persists | Low | AGENTS.md rule 12 documents tag-as-SSOT |

## Rollback Plan

Revert versioning changes (pyproject.toml, `__init__.py`, `cli.py`, `metadata.py`) to static `version`/`__version__`; restore previous release.yml / README / AGENTS.md. Pure config/code revert — no data migration; hatch-vcs never mutates git, tags unaffected.

## Dependencies

- `hatch-vcs` build dependency (resolved from PyPI by build isolation).
- No PyPI project needed (publishing out of scope).

## Success Criteria

- [ ] `uv build` at a tag produces wheel dist-info METADATA version == tag.
- [ ] `uv tool install .` → `sofer --help` exit 0; `sofer --version` matches installed metadata.
- [ ] Packaging tests pass: version-consistency, build smoke, installed-CLI subprocess (`uv run pytest tests/ -q`).
- [ ] README documents both install paths; AGENTS.md rule 12 reflects tag SSOT.
- [ ] Wheel METADATA contains readme, license + license-files, classifiers, urls, authors.

Estimated size: Medium — ~450–550 changed lines (packaging tests + spec files dominate); near the 400-line review budget, flag in sdd-tasks.