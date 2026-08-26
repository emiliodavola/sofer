# Delta for CLI

## ADDED Requirements

### Requirement: --version reports the installed release version (CLI-R05)

`sofer --version` SHALL print `sofer v<version>` where `<version>` is resolved
at runtime from installed distribution metadata — never from a static constant.
The output SHALL be non-empty and PEP 440-valid, and SHALL work from an
installed console script without `uv run`.

#### Scenario: Released install reports the tag version

- GIVEN a non-editable install of a wheel built at tag `v0.3.0`
- WHEN `sofer --version` runs
- THEN stdout SHALL be `sofer v0.3.0` and the exit code SHALL be 0

#### Scenario: Dev install reports a derived version

- GIVEN a dev/editable install with no release tag at HEAD
- WHEN `sofer --version` runs
- THEN the printed version SHALL be non-empty and PEP 440-valid
- AND it SHALL NOT equal any hardcoded literal

#### Scenario: Standalone console script works

- GIVEN an installed (non-editable) console script
- WHEN `sofer --version` runs as a subprocess outside the repository
- THEN the exit code SHALL be 0 and stdout SHALL be non-empty

---

### Requirement: Document stamping uses the shared version resolver (CLI-R06)

The version stamped into generated documents (`generated.version` in
`metadata.yaml`) SHALL be produced by the SAME shared runtime resolver that
backs `--version`. The static `__version__` constant SHALL be removed; in
dev/editable contexts where installed metadata is unavailable, the resolver
SHALL fall back to a non-empty derived value.

#### Scenario: Stamped version equals the CLI version

- GIVEN a `profile` run in any install context
- WHEN the generated `metadata.yaml` is inspected
- THEN `generated.version` SHALL equal the value printed by `sofer --version`
- AND it SHALL be non-empty

#### Scenario: No static version constant remains

- GIVEN the package source
- WHEN searched for version definitions
- THEN no hardcoded `__version__` string literal SHALL exist
- AND installed-metadata lookup (with dev fallback) SHALL be the version source