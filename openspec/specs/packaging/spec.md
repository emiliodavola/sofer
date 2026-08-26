# Packaging Specification

## Purpose

Distribution contract for `sofer` as an installable CLI: build system, tag-driven
versioning, PyPI metadata, console-script entry point, and release-readiness
tests. PyPI publishing is out of scope; the `publish` domain covers Hub delivery,
not PyPI distribution.

## Requirements

### Requirement: Tag-driven versioning (PKG-01)

The distribution version SHALL be derived from the git release tag at build time
via hatch-vcs. `pyproject.toml` SHALL declare `version` as dynamic with
`[tool.hatch.version] source = "vcs"`, and `hatch-vcs` SHALL be a build
dependency. The release tag SHALL be the single source of truth; no static
version literal SHALL exist in `pyproject.toml` or package source. Tagged builds
SHALL ship a version equal to the tag; off-tag builds SHALL produce a non-empty,
PEP 440-valid dev version (e.g. `0.3.1.dev1+g<sha>` — v0.3.0 plus one commit;
a checkout with no reachable tags ships `0.1.dev1+g<sha>`). The documented
release process (AGENTS.md rule 12) SHALL treat the tag as the version source.

#### Scenario: Tagged build matches the tag

- GIVEN a checkout at release tag `v0.3.0`
- WHEN `uv build` runs
- THEN the wheel METADATA Version SHALL equal `0.3.0`

#### Scenario: Off-tag build derives a dev version

- GIVEN a commit ahead of the last tag
- WHEN `uv build` runs
- THEN the version SHALL be non-empty and PEP 440-valid, based on the last tag

#### Scenario: No static version literal

- GIVEN the repository source
- WHEN the version declaration is located
- THEN `pyproject.toml` SHALL NOT contain a static `version =` literal
- AND no `__version__` string constant SHALL exist in package source

---

### Requirement: Complete distribution metadata (PKG-02)

`[project]` SHALL declare `readme`, SPDX `license` with `license-files`,
`classifiers` covering Python 3.10–3.14 and MIT, `project.urls`, and `authors`.
The built wheel SHALL embed the README, the MIT LICENSE, and the classifiers.

#### Scenario: Wheel metadata is complete

- GIVEN a built wheel
- WHEN its METADATA is inspected
- THEN readme, license, license-files, classifiers (3.10–3.14, MIT), urls, and
  authors SHALL be present

#### Scenario: LICENSE is bundled

- GIVEN a built wheel
- WHEN its `licenses/` directory is inspected
- THEN the MIT LICENSE SHALL be present

---

### Requirement: Installability and entry point (PKG-03)

The build SHALL produce a pure wheel (`py3-none-any`) exposing console script
`sofer = sofer.cli:main`. Installing the built artifact via pip or
`uv tool install` SHALL provide a working `sofer` command that runs without
`uv run`.

#### Scenario: Entry point present in wheel

- GIVEN a built wheel
- WHEN `entry_points.txt` is inspected
- THEN it SHALL contain `sofer = sofer.cli:main`

#### Scenario: Installed CLI runs standalone

- GIVEN a non-editable install of the built artifact
- WHEN the installed `sofer --help` runs as a subprocess
- THEN the exit code SHALL be 0

---

### Requirement: Release-readiness tests (PKG-04)

The test suite SHALL include packaging tests: version non-empty and never a
hardcoded literal; a build smoke test (`uv build` → wheel exists → entry point
present); and an installed-CLI subprocess test.

#### Scenario: Version is derived, never literal

- GIVEN the tests run in any context (dev, CI, tagged)
- WHEN the resolved version is asserted
- THEN it SHALL be non-empty and PEP 440-valid
- AND no assertion SHALL compare against a hardcoded literal

#### Scenario: Build smoke test

- GIVEN the repository at any commit
- WHEN `uv build` runs into a temp directory via subprocess
- THEN a wheel SHALL exist and its `entry_points.txt` SHALL contain the console
  script

#### Scenario: Installed-CLI subprocess test

- GIVEN the wheel installed non-editable
- WHEN `sofer --help` and `sofer --version` run via subprocess
- THEN both SHALL exit 0, and `--version` output SHALL be non-empty

---

### Requirement: Install documentation (PKG-05)

The README SHALL document `pip install sofer` and `uv tool install sofer` as
install paths.

#### Scenario: README documents both install paths

- GIVEN the README
- WHEN its install section is inspected
- THEN `pip install sofer` SHALL be documented
- AND `uv tool install sofer` SHALL be documented