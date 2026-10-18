# Delta for mcp-server

> **Change** `2026-10-18-fix-scan-registered-count` (issue **#345**) · branch
> `fix/345-scan-registered-count` from `dev@c68e090` · store **hybrid**.
>
> **One modified requirement, two added scenarios.** MSP-R15 gains the meaning of
> the `registered` integer in both scan envelopes.
>
> **Rule-6 resolution.** `mcp-server` has no `## Test Mapping` section
> (`openspec/test-mapping-registry.md`), so the new scenarios are unmapped and
> the registry is not edited; `scripts/check_test_mapping.py` still exits 0.

## MODIFIED Requirements

### Requirement: Scan Phase-1 move is mandatory (MSP-R15) — Modified 2026-10-18, fix-scan-registered-count

`sofer_scan_dry_run` and `sofer_scan_apply` SHALL run the Phase-1 MOVE (see MST-R06) unconditionally: no
argument SHALL allow skipping it, because `cache/` is the shared, deletion-prone staging directory and
the registered sources MUST NOT live only there. `sofer_scan_dry_run` SHALL preview the moves with no
mutation. Collisions against existing `raw/` destinations SHALL abort atomically before any move
(`registered: 0`, TOML untouched). `sofer_scan_apply` SHALL report `moved: int` in a successful envelope
(declared in `output_schema`).

`registered: int` in both scan envelopes SHALL be the number of `[[file]]` entries the merge of that
same call appended, as reported by the merge itself and never as a before/after difference of entry
counts. `[[file]]` placeholders the merge strips (`TODO:`, `raw/example*`) SHALL NOT be subtracted from
it, so on a fresh `sofer_init` tree the field SHALL equal the number of newly registered files
(`discovered` when nothing was registered before) and SHALL agree with the TOML written by the same
call. Both tools SHALL report the same value for the same tree, and an idempotent re-scan SHALL report
`registered: 0`. The field's `description` in both `output_schema` blocks SHALL state this meaning.

#### Scenario: Dry-run previews the mandatory move without mutation

- GIVEN a loose file outside `raw/`/`cache/`
- WHEN `sofer_scan_dry_run` runs with only `config`
- THEN the output SHALL show `-> raw/<rel>` and name the move as mandatory
- AND no file SHALL be moved, `raw/` SHALL NOT be scaffolded, and the TOML SHALL be untouched

#### Scenario: Collision aborts before any move

- GIVEN a loose file whose `raw/` destination already exists
- WHEN `sofer_scan_apply` runs
- THEN an `ok:false` refusal SHALL be returned naming the collision
- AND the loose file SHALL remain at its original path and the TOML SHALL be untouched

#### Scenario: There is no opt-out

- GIVEN loose supported files and no extra arguments
- WHEN `sofer_scan_apply` runs
- THEN the loose files SHALL end up under `raw/` with their tree and the envelope SHALL report `moved`
- AND no parameter SHALL exist that skips the move

#### Scenario: The init placeholders are not subtracted from the count — Added

- GIVEN a fresh `sofer_init` tree with N loose supported files and the two `raw/example*` placeholders in the TOML
- WHEN `sofer_scan_apply` runs, and separately `sofer_scan_dry_run` on a second identical tree
- THEN both SHALL report `registered: N` while the written TOML holds N `[[file]]` entries
- AND an immediate re-scan of the applied tree SHALL report `registered: 0`
