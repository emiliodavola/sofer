# Design: openspec SDD-context drift guards (#258)

**Change**: `docs-openspec-context-drift`

## Decision 1 — ODD, not SDD

No `openspec/specs/**` requirement is amended. The behavior-bearing part is a static guard
in the CI-workflow guard module, which already owns several unmapped supporting guards. A new
capability requirement (e.g. a `ci` CI-15) would be over-binding for a bootstrap-file
reconciliation and would enlarge the spec surface for no enforcement gain. Resolution: ODD.

## Decision 2 — Derive every expected value from a declaration home

The guard module's discipline (CI-08/CI-13) is that a guard holds no version literal of its
own. Applied here:

- subcommands: derived from `src/sofer/cli.py` by matching the bare `sub.add_parser("…")`
  calls. The regex `\bsub\.add_parser\(` deliberately does not match `mcp_sub.add_parser(`
  (`_` is a word character, so no boundary precedes `sub` inside `mcp_sub`), which yields
  exactly the 10 **top-level** subcommands.
- tool versions: `_declared_ruff_version()`, `_declared_exact_dev_pin("mypy")`, and
  `_declared_pyright_version()` already exist in the module and read `pyproject.toml`.
- quality commands: each expected command is asserted to be a member of the module's
  `_CI_LINT_GATE_RUNS` contract before it is compared to `config.yaml`, so the config and the
  CI lint job cannot diverge. The four command strings are named in the guard because the
  config's `quality` map is itself a declaration home; the membership check keeps them from
  becoming free-floating literals.

## Decision 3 — Inventory comparison is set-based

`project.md` lists the subcommands in a human-readable order (`init, scan, validate, …`) that
is not `cli.py`'s registration order (`validate, prepare, publish, …`). The guard therefore
compares the **set** of names plus the declared count, not the sequence. This pins
missing/extra/renamed subcommands — the drift class in #258 — without freezing a descriptive
ordering.

## Guard placement

All four guards live in `tests/test_ci_workflows.py`, the module that already parses
`pyproject.toml`, `openspec/config.yaml`, and the workflows. No new test module is added.
The guards are supporting guards (unmapped), consistent with `test_ci_workflow_files_present`
and the coverage guards; the module docstring records them.

## Test strategy

| Guard | Positive | Negative control probe |
| --- | --- | --- |
| subcommand inventory | 10 names match | change project.md count to `9` → fails |
| tool versions | ruff/mypy/pyright strings present | change `mypy 2.3.1` → `mypy 2.3.0` → fails |
| pyright gate named | `uv run pyright` present | remove it → fails |
| config quality commands | each equals a CI lint gate | change formatter to `uv run ruff format` → fails |
