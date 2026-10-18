# Delta for scan

> **Change** `2026-10-18-fix-scan-registered-count` (issue **#345**) · branch
> `fix/345-scan-registered-count` from `dev@c68e090` · store **hybrid**.
>
> **One modified requirement, two added scenarios.** SCN-04 gains the reporting
> rule: the printed count is the number of `[[file]]` entries the merge of that
> run appended, so it never disagrees with the TOML the same run writes.
>
> **Rule-6 resolution.** `scan` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md:41`), so the new scenarios are unmapped and
> the registry is not edited; `scripts/check_test_mapping.py` still exits 0.

## MODIFIED Requirements

### Requirement: CLI Interface (SCN-04) — Modified 2026-10-18, fix-scan-registered-count

The system MUST provide `sofer scan [config.toml] [--dry-run] [--force] [--ext .ext]`.
Default config SHALL be `dataset.toml` in the current directory. `--dry-run`
MUST report without filesystem changes. `--force` MUST skip the confirmation
prompt. Exit code 0 on success, 1 on error.

The reported registration count SHALL be the number of `[[file]]` entries the
merge of that same run appended — measured by the merge itself, never as a
before/after difference of entry counts: `[[file]]` placeholders that the merge
strips (`TODO:`, `raw/example*`) SHALL NOT be subtracted from the count, because
they were never part of the merged list. `Registered N new [[file]] entry(s).`
SHALL therefore agree with the TOML the same run writes, and an idempotent
re-scan over unchanged inputs SHALL report `0`.

#### Scenario: Default config and interactive confirm

- GIVEN `dataset.toml` in the working directory
- WHEN `sofer scan` is called
- THEN `dataset.toml` SHALL be used as config
- AND the user SHALL be prompted before files are copied

#### Scenario: --force skips confirmation

- GIVEN discovered files and `dataset.toml`
- WHEN `sofer scan --force` is called
- THEN files SHALL be copied without prompting

#### Scenario: Explicit config path

- GIVEN `my-project/config.toml` exists
- WHEN `sofer scan my-project/config.toml` is called
- THEN that file SHALL be used as the TOML source

#### Scenario: The count matches the TOML on an init-scaffolded tree — Added

- GIVEN a TOML carrying the two `sofer init` placeholders (`local = "raw/example.csv"`, `local = "raw/example/"`) and N loose supported files
- WHEN `sofer scan --force` runs
- THEN it SHALL print `Registered N new [[file]] entry(s).`
- AND the written TOML SHALL hold N `[[file]]` entries, with no placeholder left

#### Scenario: A re-scan reports zero — Added

- GIVEN a TOML already holding every discovered file's entry
- WHEN `sofer scan --force` runs again
- THEN it SHALL print `All discovered files already registered (idempotent).`
- AND no `<details>`-free count other than zero SHALL be reported
