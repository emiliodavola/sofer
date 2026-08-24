# Exploration: Fix `[tool.sofer]` config discovery anchoring (GitHub #56)

## Current State

### How discovery works today

`src/sofer/config.py`:

- `_DEFAULTS` (lines 18–68): hardcoded fallback dict with ~30 tool-wide keys
  (`schema_sample_size`, `semantic_priors`, thresholds, parquet settings,
  CSV delimiter/encoding, etc.).
- `_find_project_root()` (lines 71–78): walks up from
  `Path(__file__).resolve().parent` — **the installed package location** —
  until a `pyproject.toml` is found. Fallback: `Path.cwd()` (bare, NOT walked up).
- `_load_tool_config()` (lines 81–127): reads `[tool.sofer]` from the found
  `pyproject.toml`, merges over `_DEFAULTS`.
- Line 134: `_tool = _load_tool_config()` executes **once at module import**;
  lines 136–174 bind ~30 module-level constants (`OUTPUT_DIR`,
  `SCHEMA_SAMPLE_SIZE`, `SEMANTIC_PRIORS`, …).

### Observed failure modes (matches GitHub #56)

| Install mode | What `_find_project_root()` finds | Result |
|---|---|---|
| Editable (`uv sync`, `pip install -e .`) | sofer's **own** repo-root `pyproject.toml` (which has a populated `[tool.sofer]`, pyproject.toml:60–110) | User overrides silently ignored; dev behavior driven by sofer's own TOML |
| Regular wheel (`pip install sofer`) | Nothing near `site-packages` (hatchling ships only `src/sofer/**`; no `pyproject.toml` in the wheel) | Falls back to bare `Path.cwd()` — works **only** if the user happens to run from a directory containing a `pyproject.toml` with `[tool.sofer]`; subdirectory invocations find nothing |
| Any mode, unlucky cwd | An *unrelated* Python project's `pyproject.toml` if it contains `[tool.sofer]` | Accidental cross-project config pickup |

The wheel-layout claim was verified: `[build-system]` uses hatchling with no
force-includes, so installed layout is `site-packages/sofer/*.py` with no
`pyproject.toml` anywhere up the tree except the filesystem root.

### Consumer map — how config reaches the code

Two distinct import patterns exist (critical for the fix):

**Pattern A — `from .config import X` (value frozen at import time):**
`cli.py`, `checks.py`, `codebook.py`, `quality.py`, `profile.py`,
`prepare.py`, `publish.py`, `repo_compliance.py`, `scanner.py`,
`_csv_reader.py`.

**Pattern B — `from . import config` + `config.X` at call time (dynamic):**
`pii.py`, `semantic.py` (e.g. `pii.py:79`, `semantic.py:118–153`). These
already behave correctly under late resolution.

**Frozen-value traps (break under any lazy scheme even after import fixes):**

- `codebook.py:258` and `codebook.py:331`: `max_sample: int =
  CODEBOOK_MAX_SAMPLE` — default evaluated at function-definition time.
- `cli.py:606`: argparse `default=CODEBOOK_MAX_SAMPLE`;
  `cli.py:616`, `cli.py:707`: `default=DEFAULT_CONFIG_NAME` — evaluated at
  parser-construction time (inside `main()`, but before any reload could run
  unless ordered carefully).

### Where the dataset path enters the system

`main()` → `_cmd_*` → `_load_and_validate(args)` (cli.py:40) →
`DatasetConfig.from_toml(args.config)` (model.py:297). `from_toml` computes
`base_dir = path.parent` and stores it as `cfg._base_dir` (model.py:344–345).
So **the anchor directory is already known at exactly the right moment** —
the gap is purely that tool config was resolved earlier, without it.

Note: not every command loads a `DatasetConfig` — `sofer codebook FILE`
(single-file mode) and parts of `scan` operate without one. Those paths can
only anchor on cwd.

### Existing tests

- `tests/test_config.py`: asserts defaults/types and TOML-override merging;
  both override classes monkeypatch `sofer.config._find_project_root` with
  `lambda: tmp_path` (**zero-arg seam**) — any signature change breaks them.
- Codegraph reports `_find_project_root` itself has **no covering tests** —
  actual discovery/walk-up behavior is untested today.
- `tests/test_repo_compliance.py` RC-R09 covers `schema_sample_size`
  affecting the README footnote (via monkeypatched config), i.e. the exact
  acceptance-criteria scenario, but not the *discovery* path.

## Affected Areas

- `src/sofer/config.py` — the bug: `_find_project_root` anchors on
  `Path(__file__)`; `_load_tool_config()` runs at import time.
- All Pattern-A consumer modules listed above (mechanical import change if
  late resolution is chosen).
- `src/sofer/codebook.py` — frozen default parameters (lines 258, 331).
- `src/sofer/cli.py` — argparse defaults built from config constants;
  natural place to trigger per-invocation resolution.
- `src/sofer/model.py` — `from_toml` knows `base_dir`; alternative reload
  hook point.
- `tests/test_config.py` — monkeypatch seam signature; needs new
  discovery-behavior tests (regular-install simulation, dataset-dir
  anchoring, precedence, cwd fallback).
- `README.md:195` (`[tool.sofer]` docs) — must document the new anchoring
  rules (AGENTS.md rule 7).
- `pyproject.toml` — no structural change required; possibly comment updates.

## Approaches

### 1. Anchor-on-dataset-dir + per-invocation reload, keep constants API (RECOMMENDED)

Change `_find_project_root(start: Path | None = None)` to walk up from
*start* (the dataset TOML directory), else walk up from `Path.cwd()`, else
use `_DEFAULTS` only. Drop the `Path(__file__)` anchor entirely. Add a
module-level `config.reload(base_dir)` (or `resolve_for(base_dir)`) that
recomputes and rebinds the module constants. Call it from `main()` once the
effective `--config` path is known (and/or from `DatasetConfig.from_toml`
for library callers). Mechanically convert Pattern-A imports to
`from . import config` + attribute access; convert the two frozen default
parameters to `None` sentinels resolved at call time.

- Pros: preserves the familiar `config.X` API; single resolution point per
  process; satisfies every acceptance criterion; moderate diff; matches
  pii.py/semantic.py pattern already in the codebase; honors AGENTS.md rule 3.
- Cons: touches ~10 modules mechanically; mutating module globals is less
  pure than DI; chicken-and-egg on `--config` default (parser default for
  `default_config_name` must come from `_DEFAULTS`, not the reloaded value —
  acceptable: it is a bootstrap key like `output_dir` that logically belongs
  to "where the user runs", i.e. cwd anchoring).
- Effort: Medium.

### 2. Explicit `ToolConfig` object threaded through all consumers

Replace module constants with a dataclass loaded once per invocation and
passed down call chains explicitly.

- Pros: cleanest architecture, no global state, trivially testable.
- Cons: every consumer function signature changes (~10 modules, dozens of
  functions); far exceeds the 400-line review budget for a bugfix; high
  regression risk against 422 green tests.
- Effort: High.

### 3. Import-time only fix: reorder so config loads lazily via PEP 562 `__getattr__`

Make config constants lazy module attributes resolved on first access.

- Pros: no consumer changes at all on paper.
- Cons: does **not** work — `from .config import X` triggers first access at
  consumer-import time, still before `args` are parsed. Rejected as
  technically insufficient.
- Effort: Low (but doesn't solve the problem).

## Design-question verdicts (for sdd-design)

1. **Lazy vs pass-base-dir**: Lazy per-process resolution (Approach 1) is the
   right fit — a CLI invocation handles exactly one dataset TOML, so
   "resolve once, after the config path is known" gives per-dataset
   anchoring without threading state through dozens of signatures.
   `from_toml` is the most robust hook (covers library use too); `main()` is
   the alternative for CLI-only coverage.
2. **Precedence**: dataset-TOML-directory walk-up → cwd walk-up →
   `_DEFAULTS`. The sofer-repo `pyproject.toml` should **never** be consulted
   at runtime — it is a dev/bootstrap artifact. In editable installs the
   dataset dir usually sits outside the sofer repo, so precedence conflicts
   are rare; document that the nearest `pyproject.toml` above the dataset
   wins.
3. **Notice-on-miss**: detecting "[tool.sofer] present but undiscovered"
   requires scanning arbitrary locations — not worth it. Instead: expose
   *which* pyproject.toml was used (one line under an existing verbosity
   mechanism, e.g. `--verbose` or `SOFER_DEBUG=1`) plus README
   documentation of the anchoring rule. This satisfies "no silent failures"
   without heuristics.

## Recommendation

Approach 1. Concretely: re-anchor `_find_project_root` on a caller-supplied
start path; add a single reload entry point; convert Pattern-A imports to
attribute access; de-freeze the two default parameters and the argparse
defaults that matter; extend `test_config.py` with real discovery scenarios
(tmp_path dataset tree, simulated "installed" case with no nearby
pyproject.toml, cwd fallback, precedence). Update README §"[tool.sofer]".

## Risks

- **Missed frozen bindings**: any remaining `from .config import X` or
  default-parameter usage silently keeps old behavior — mitigated by a grep
  audit task in sdd-tasks.
- **Test seam breakage**: `test_config.py` monkeypatches `_find_project_root`
  as zero-arg; new signature requires updating those helpers.
- **Dev-workflow shift**: editable installs currently pick up sofer's own
  `[tool.sofer]`; after the fix they won't (correct, but a visible behavior
  change for maintainers — document it).
- **Chicken-and-egg on bootstrap keys** (`default_config_name`,
  `output_dir`): their overrides can only be honored via cwd anchoring;
  must be documented, not discovered.
- **Size budget**: mechanical conversion across ~10 modules may push past a
  400-line single PR; sdd-tasks should forecast chained-PR feasibility.
- **mypy/ruff gates**: run `uv run mypy src/` and full pytest matrix before
  pushing (CI lint runs mypy only under 3.13).

## Ready for Proposal

Yes. Recommended message to user: the bug is confirmed at the code level
(`Path(__file__)` anchoring + import-time resolution); the fix direction
(dataset-dir anchoring with cwd fallback and one-shot per-invocation
resolution) is viable and moderately sized; proposal should pin down the
reload hook point (main() vs from_toml) and the precedence/notice decisions
above.
