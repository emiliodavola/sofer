# ODD feature: writable `[[file]]` registration surface (#344)

Branch: `feat/344-file-entry-tool` (stacked on `fix/343-root-discoverability`). Delivery: one PR assigned to the maintainer. Test runner: `uv run pytest tests/ -q`.

## Specs

- **S1** — `sofer_init`'s template advertises `[[file]]` keys that no MCP tool can write: `recursive`, `upload_as_csv`/`convert_to_parquet`, `include_in_schema`, and `column_types` (the last one is actively recommended by `sofer_validate`'s zero-padded-code warning). Issue #344 asks for one of: a tool that writes `[[file]]` entries; `scan_apply` grouping directories; or the template/README dropping the advertised shape.
- **S2** — Chosen shape (option A of the issue): a `sofer_file_set(config, entries, dry_run=False)` tool, symmetric with `sofer_meta_set`, that REPLACES the `[[file]]` array and preserves every other key, table and comment.
- **S3** — Accepted keys: `local` (required), `remote` (required), `recursive`, `convert_to_parquet`, `upload_as_csv`, `include_in_schema` (booleans), `column_types` (`{column = "string"}` restricted to `config.COLUMN_TYPES_SUPPORTED`). Unknown key or wrong kind → `CONFIG_ERROR`, nothing written, naming the accepted set.
- **S4** — Every `local` resolves under the containment root and exists (directory for `recursive`, file otherwise); every `remote` is safe and unique; a recursive entry's remote folder must not contain another entry's remote (the double-registration the folder shape makes easy); `entries=[]` is refused while entries exist.
- **S5** — Atomic write, parse + round-trip verification before commit, idempotent when the file already holds the entries, `dry_run` writes nothing. Continuation: `sofer_validate`. The roster grows from 18 to 19 callables.

## Tasks

- T1 (inline) — `src/sofer/file_edit.py`: registry, `normalize_entries`, surgical region finder, renderer, `set_files`; shared `_toml.atomic_write_text` extracted from `meta_edit`. Evidence: `tests/test_file_edit.py::TestApplyFileEdit` green.
- T2 (inline) — `sofer_file_set` tool + `_validate_file_set_entries` (containment/existence/uniqueness/collision) + registration/schema. Evidence: `tests/test_file_edit.py::TestSoferFileSet` green.
- T3 (inline) — registry, instructions, roster/schema tests (18 → 19), README/README_ES, spec MSP-R03 + MSP-R22.
- T4 — full suite, mypy/pyright/ruff, commit.

## Log

- **L1** (user, verbatim): "1. sincronizá dev, podá las ramas locales 2. revisá los issues pendiente, no confies espontanemante en ellos, armate un roadmap de implementación 3. creá una rama para cada issue y luego cuando pushees creá un PR asignado a mi 4. usá ODD (de acuerdo a la complejidad), no uses SDD"
- **L2** (issue #344, verbatim excerpt): "No MCP tool can write a `[[file]]` entry — the template's own `recursive = true` shape is unreachable". The issue's comment adds `column_types` as a third unreachable key.
- **L3** (decision): option A — a dedicated setter. It is the least behaviour-changing option (scan output stays flat, which the reporter judged strictly better for their corpus) and follows the `sofer_meta_set` precedent. Documented in the spec as MSP-R22.
- **L4** (verification): focused MCP suite green (403 passed, 3 skipped) after the roster update; `tests/test_file_edit.py` 14 passed; `tests/test_workflow.py` green.
