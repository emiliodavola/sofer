# Delta for scan

> **Change** `2026-10-17-fix-scan-move-raw-mandatory` (issue **#339**) · branch
> `fix/339-scan-move-raw-mandatory` from `dev@ec511e7` · store **hybrid**.
>
> **Three modified requirements, four added scenarios.** SCN-01 and SCN-02 gain
> the keying rule (`registration_path`); SCN-07 gains the mandatory-move clause
> and the tracked-source clause that `validate`/`prepare` enforce.
>
> **Rule-6 resolution.** `scan` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md:41`), so the new scenarios are unmapped and
> the registry is not edited; `scripts/check_test_mapping.py` still exits 0.

## MODIFIED Requirements

### SCN-01 File Discovery — Modified 2026-10-17, fix-scan-move-raw-mandatory

`registration_path` SHALL key each file relative to the root that owns it —
`raw/` for a file under `raw/`, the dataset root otherwise — so the same file
keys identically whether it is discovered loose or under `raw/`.
`flatten_first_level` stays the helper for the raw/-rooted case it names.

#### Scenario: Key independent of the discovery layout — Added

- GIVEN a loose `Labels/x.csv` and, in a second run, its post-move `raw/Labels/x.csv`
- WHEN each is registered
- THEN both SHALL key `Labels/x.csv` (`local = "cache/Labels/x.csv"`, `remote = "Labels/x.csv"`)

### SCN-02 TOML Merge — Modified 2026-10-17, fix-scan-move-raw-mandatory

The merge SHALL register `local = "cache/<key>"` and `remote = "<key>"` where
`<key>` is `registration_path`. Dedup by resolved absolute path and `remote`, and
the existing preservation, flattened-paths and root-file scenarios are unchanged.

#### Scenario: Nested tree keys identically loose and under raw — Added

- GIVEN a loose `Labels/x.csv`
- WHEN scan moves it and registers it
- THEN `raw/Labels/x.csv` and `cache/Labels/x.csv` SHALL exist and the TOML SHALL carry `remote = "Labels/x.csv"` — not `x.csv`
- AND a second scan over the same tree SHALL register no new `[[file]]` entry

### SCN-07 Source Layout and Move-to-Raw — Modified 2026-10-17, fix-scan-move-raw-mandatory

The MOVE SHALL NOT be optional: it MUST run on every scan surface — the CLI and
both MCP scan tools — with no opt-in flag that can skip it, because `cache/` is
the shared, deletion-prone staging directory and the registered sources MUST NOT
live only there.

The system MUST refuse a `[[file]]` entry whose `local` resolves under `cache/`
while `raw/` holds no corresponding source (`raw/<path relative to cache/>`):
`validate` and `prepare` MUST report it as an error naming the expected `raw/`
path and the repair, and both scan adapters MUST report it without rewriting the
config.

#### Scenario: MCP scan moves without an opt-in flag — Added

- GIVEN a dataset TOML and a loose `loose.csv` outside `raw/`, with no `raw/` directory
- WHEN `sofer_scan_apply` runs with only `config`
- THEN `raw/loose.csv` and `cache/loose.csv` SHALL exist, `loose.csv` SHALL NOT remain in the root, and the TOML SHALL carry `local = "cache/loose.csv"`

#### Scenario: MCP dry-run previews the mandatory move without mutating — Added

- GIVEN a dataset TOML and a loose `loose.csv`
- WHEN `sofer_scan_dry_run` runs with only `config`
- THEN the output SHALL list `raw/loose.csv` and name the move as mandatory
- AND no file SHALL be moved, no `raw/` SHALL be created, no `cache/` write, TOML unchanged

#### Scenario: Cache-only registration with no raw source is refused — Added

- GIVEN `[[file]] local = "cache/x.csv"` and no `raw/x.csv`
- WHEN `sofer_validate` runs
- THEN it SHALL report an error naming `raw/x.csv` and exit 1
- AND `sofer_scan_apply` SHALL report the same entry without rewriting the TOML
