# Delta for tool-config

## MODIFIED Requirements

### Requirement: README documents discovery rules (TC-09)

The deep `[tool.sofer]` reference SHALL reside in `docs/configuration.md`, which SHALL document the anchoring rules, the precedence order (dataset dir → cwd → defaults), the cwd-only limitation for bootstrap keys, and the behavior shift for editable installs of sofer itself. The README SHALL keep a short summary of the `[tool.sofer]` section, SHALL link to `docs/configuration.md` for the full reference, and SHALL NOT duplicate the deep reference in the README body. The README SHALL retain a one-line `SOFER_VERBOSE` troubleshooting pointer.
(Previously: the README itself carried the full `[tool.sofer]` reference section, including discovery rules, precedence, bootstrap-key caveat, and editable-install notes.)

#### Scenario: Docs cover precedence and maintainer shift

- GIVEN a reader consults `docs/configuration.md`
- THEN they find the three-step precedence, the bootstrap-key caveat, and a note that sofer's own repo TOML no longer applies at runtime

#### Scenario: README points to the authoritative reference

- GIVEN a user reading `README.md` looks for `[tool.sofer]` details
- WHEN they reach the configuration summary
- THEN the README links to `docs/configuration.md`
- AND the README body does not carry the full deep reference

#### Scenario: SOFER_VERBOSE pointer survives extraction

- GIVEN the deep config reference has moved to `docs/configuration.md`
- WHEN a user troubleshoots verbosity from the README
- THEN the README keeps a one-line `SOFER_VERBOSE` pointer
- AND the pointer indicates where the full explanation lives