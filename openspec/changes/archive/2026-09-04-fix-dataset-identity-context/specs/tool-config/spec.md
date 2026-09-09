# Delta for tool-config

## MODIFIED Requirements

### Requirement: Library callers resolve via from_toml (TC-05)

`DatasetConfig.from_toml` SHALL trigger tool-config resolution using the TOML directory as anchor, so library consumers importing `sofer` directly get the same discovery behavior without going through the CLI. `from_toml` SHALL accept an optional `discovery_root: Path | None = None`: when provided, discovery SHALL be bounded by `stop_at=discovery_root` (the walk-up SHALL NOT pass it); when omitted (the CLI path), discovery SHALL remain unbounded — behavior unchanged.

(Previously: `from_toml` accepted no `discovery_root`; library loads were always unbounded.)

#### Scenario: Library load honors sibling pyproject

- GIVEN a script calls `DatasetConfig.from_toml("proj/data/dataset.toml")`
- AND `proj/pyproject.toml` sets `schema_sample_size = 250`
- THEN config constants reflect `250` after the call returns

#### Scenario: Discovery bounded by discovery_root

- GIVEN a `pyproject.toml` with `[tool.sofer]` above `discovery_root` and one inside it
- WHEN `DatasetConfig.from_toml(path, discovery_root=discovery_root)` runs
- THEN only values at or below `discovery_root` SHALL apply and the above-root overrides SHALL NOT