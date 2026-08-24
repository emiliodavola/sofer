# Design: Fix `[tool.sofer]` config discovery anchoring (#56)

## Technical Approach

Approach 1 from exploration: keep the module-constants API, add one reload
entry point (`config.reload(start)`), re-anchor discovery on a caller-supplied
start path, and de-freeze every binding that captures config at import/def
time. Resolution happens in two phases per CLI invocation: Phase 0 (cwd
anchor, before parser construction — serves bootstrap keys, TC-07) and
Phase 1 (dataset-TOML-dir anchor, inside `DatasetConfig.from_toml` — serves
everything else, TC-04/TC-05). Import time performs **zero** filesystem
access; constants initialize from `_DEFAULTS` only (hardens TC-03).

## Architecture Decisions

### AD-1: Discovery signature and semantics

| Option | Tradeoff | Decision |
|---|---|---|
| `_find_project_root(start=None) -> Path \| None`, stop at first `pyproject.toml` | Predictable, ecosystem-conventional (ruff/pytest), enables TC-08 reporting | **Chosen** |
| Walk past section-less `pyproject.toml` | Surprising long-range pickups; diverges from tooling convention | Rejected |
| Return bare `Path.cwd()` fallback (status quo shape) | Cannot distinguish "defaults" from "cwd file found" → breaks TC-08 | Rejected |

Exact contract: walk `[start_dir, *start_dir.parents]` (start dir **included**
— fixes today's exclusion of the anchor itself); `start=None` → anchor on
`Path.cwd()`; no hit up to filesystem root → `None`. The `Path(__file__)`
anchor is deleted. A found `pyproject.toml` without `[tool.sofer]` is
selected but contributes nothing → `_DEFAULTS` values (documented, not
heuristically re-walked).

### AD-2: Reload hook placement, single-fire, thread posture

`config.reload(start: str | Path | None = None) -> None` recomputes the
merged dict and rebinds all module constants; records `config.SOURCE_PATH`.

| Concern | Design |
|---|---|
| Phase 0 (bootstrap, TC-07) | `main()` calls `reload(None)` **before** `_build_parser()`; argparse then reads cwd-resolved `config.DEFAULT_CONFIG_NAME` |
| Phase 1 (dataset, TC-04/05) | `DatasetConfig.from_toml` calls `reload(base_dir)` right after computing `base_dir`, before validation — the only dataset-anchored call site |
| "Exactly one" guarantee | **Structural ownership**, not a latch: Phase 1 has exactly one call site (`from_toml`); `main()` never passes the dataset path. Enforced by a grep-audit task + a test asserting reload-call count via monkeypatched counter |
| Accidental double-fire | Harmless by construction: resolution is a pure function of (anchor, filesystem); no hidden skip-state that would break tests rewriting a TOML at the same path |
| Thread safety | Merged dict built fully, then attributes swapped under a `threading.Lock`; concurrent readers see old-or-new complete state, never a partial mix |

Alternatives rejected: reload only in `main()` (misses library callers,
TC-05); latch/skip-if-same-anchor memoization (hidden state, complicates
repeat reloads in tests).

### AD-3: De-freezing mechanics

| Frozen binding | Conversion |
|---|---|
| `from .config import X` in ~10 modules (cli, checks, codebook, quality, profile, prepare, publish, repo_compliance, scanner, _csv_reader) | `from . import config` + `config.X` at call time — matches the existing `pii.py`/`semantic.py` precedent (AGENTS.md rule 10) |
| `codebook.generate(..., max_sample=CODEBOOK_MAX_SAMPLE)` (:258/:331 region) | `max_sample: int \| None = None` sentinel, resolved in body: `config.CODEBOOK_MAX_SAMPLE if max_sample is None` |
| `cli.py` `--max-sample` (:606) | `default=None`; `_cmd_codebook` resolves through `config.CODEBOOK_MAX_SAMPLE` post-Phase-1 |
| `cli.py` `--config` (:616) / `scan` config (:707) | `default=config.DEFAULT_CONFIG_NAME` evaluated inside `_build_parser()` **after** Phase 0 — correct bootstrap-key semantics |

No backward-compat aliases for `from .config import X`: those imports are the
bug vector; keeping them invites regression. Internal API — breaking is
acceptable. Rejected: PEP 562 lazy attrs (still freezes on `from`-import);
explicit `ToolConfig` DI object (out of scope/budget).

### AD-4: Bootstrap keys (TC-07)

Bootstrap set: `default_config_name` (needed at parser construction) and
`output_dir` (needed by scan/init before a dataset TOML is validated). Both
resolve via cwd walk-up in Phase 0. After Phase 1 they are rebound like any
other key — documented behavior: the cwd-only limitation applies to the
pre-config window; once a dataset TOML loads, dataset-dir overrides apply.
This is documentation, not heuristic resolution, per the requirement.

### AD-5: Resolved-source visibility (TC-08)

Env var `SOFER_VERBOSE=1` → `reload()` writes one line to **stderr**:
`[tool.sofer] source: {absolute pyproject path}` or
`[tool.sofer] source: built-in defaults`. Chosen over a global `--verbose`
flag: zero parser surface churn across 8 subcommands, and it also works for
library callers. Stdout is untouched; silent by default.

## Data Flow

```
import sofer            main()                       DatasetConfig.from_toml
     │                      │                                  │
constants = _DEFAULTS ──► reload(None)  ──parser──► args ──► reload(base_dir)
(no fs access)         cwd walk-up                     dataset-dir walk-up → cwd walk-up
                       SOURCE_PATH=cwd-file|None       SOURCE_PATH=dataset-file|cwd-file|None
                            │                                  │
                     bootstrap keys honored          all consumers read config.X live
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/config.py` | Modify | New `_find_project_root(start)`, `_discover` precedence, `reload()`, `SOURCE_PATH`, lock; import binds from `_DEFAULTS` only |
| `src/sofer/model.py` | Modify | `from_toml` calls `config.reload(base_dir)` after `base_dir = path.parent` |
| `src/sofer/cli.py` | Modify | Phase-0 reload in `main()`; argparse default de-freeze (:606,:616,:707); import conversion |
| `src/sofer/checks.py`, `quality.py`, `profile.py`, `prepare.py`, `publish.py`, `repo_compliance.py`, `scanner.py`, `_csv_reader.py` | Modify | Mechanical `from .config import X` → attribute access |
| `src/sofer/codebook.py` | Modify | Import conversion + `max_sample` sentinel (:258,:331) |
| `tests/test_config.py` | Modify | Seam updated to `lambda start=None: ...`; new discovery/precedence/reload tests |
| `tests/conftest.py` | Create | `pytree` fixture helper building tmp `pyproject.toml` layouts |
| `README.md` | Modify | §[tool.sofer]: anchoring rules, precedence, bootstrap caveat, editable-install shift, `SOFER_VERBOSE` (AGENTS.md rule 7) |

## Interfaces / Contracts

```python
# config.py
def reload(start: str | Path | None = None) -> None:
    """Re-resolve [tool.sofer] and rebind module constants.

    start=None anchors on Path.cwd(); a dataset dir anchors Phase 1.
    Records SOURCE_PATH (None => built-in defaults). Emits one stderr
    line when SOFER_VERBOSE is truthy.
    """

def _find_project_root(start: str | Path | None = None) -> Path | None: ...
SOURCE_PATH: Path | None  # module-level, rebound by reload()
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (TC-01) | Start-path injection; walk-up includes start dir; `Path(__file__)` never consulted | `tmp_path` trees + `reload(tmp_path)`; editable-install simulation (package dir outside tree) |
| Unit (TC-02) | Dataset-dir beats cwd; nothing found → `_DEFAULTS` | Two nested tmp trees with conflicting `schema_sample_size`; empty-tree case |
| Unit (TC-03) | Section-less pyproject stops walk → defaults | pyproject with only `[project]` above the tree |
| Unit (TC-06) | Post-reload visibility through `generate(max_sample=None)`, argparse-free handlers, repeated-import consistency | Call functions after `reload()` with mutated TOML |
| Integration (TC-04) | Exactly one Phase-1 reload per invocation | Monkeypatched reload counter around `main([...])`; single-file `codebook FILE` path anchors cwd |
| Integration (TC-05) | Library `from_toml` triggers reload | Direct `DatasetConfig.from_toml` on tmp tree, assert `config.SCHEMA_SAMPLE_SIZE` |
| Unit (TC-07) | cwd pyproject supplies `default_config_name` | `reload(None)` + parser default inspection |
| Integration (TC-08) | stderr line present/absent; abs path vs defaults message | capsys capture with/without `SOFER_VERBOSE` |
| Regression | Existing suites stay green; seam migration | `uv run pytest tests/ -q` (422 baseline); `test_config.py` monkeypatches become `lambda start=None: tmp_path` |

## Migration / Rollout

No data/schema migration. Behavior shifts documented in README + release
notes: maintainers' editable installs no longer pick up sofer's own
`[tool.sofer]` at runtime (use a user-project pyproject instead). Rollback =
single revert.

## PR Slicing Forecast

**Single PR** (delivery_strategy=auto-forecast, budget 2000 lines).
~550–650 changed lines across ~13 files — mostly mechanical conversions.
Guards: `Decision needed before apply: No` · `Chained PRs recommended: No` ·
`2000-line budget risk: Low`. Commit sequencing inside the PR: (1) config.py
+ test seam migration, (2) consumer conversion + de-freeze, (3) hooks +
visibility + README.

## Open Questions

- [x] None blocking. Noted nuance: `output_dir` is bootstrap-adjacent — its
      cwd-only limitation holds only until Phase 1 rebinds it; README will
      state this explicitly.
