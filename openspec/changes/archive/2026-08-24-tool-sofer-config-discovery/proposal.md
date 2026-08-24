# Proposal: Fix `[tool.sofer]` config discovery anchoring (#56)

## Intent

GitHub #56: `_find_project_root()` in `src/sofer/config.py` walks up from
`Path(__file__)` — sofer's install path — instead of the user's project or
dataset location. Editable installs silently pick up **sofer's own**
`pyproject.toml`; wheel installs find nothing near `site-packages` and fall
back to bare `cwd`, missing overrides when invoked from subdirectories. All
user `[tool.sofer]` overrides are ignored without any warning.

## Scope

### In Scope
- Re-anchor `_find_project_root(start)` on the dataset TOML directory
  (`DatasetConfig.from_toml` already computes `base_dir`); drop the
  `Path(__file__)` anchor.
- Precedence: dataset-dir walk-up → cwd walk-up → `_DEFAULTS`. Never consult
  sofer's own repo TOML at runtime.
- One per-invocation reload hook (`main()` once `--config` resolves;
  `from_toml` covers library callers).
- Convert frozen `from .config import X` consumers (~10 modules) to
  `from . import config` attribute access; de-freeze default params in
  `codebook.py:258,331` and argparse defaults in `cli.py`.
- Expose which pyproject.toml was used (`--verbose`/env flag) + README docs.

### Out of Scope
- Explicit `ToolConfig` DI object threaded through all signatures.
- Detecting "override present but undiscovered" heuristics.
- Changing any default values themselves — only *where* they are discovered.

## Capabilities

### New Capabilities
- `tool-config`: Tool-wide configuration discovery and precedence
  (dataset-dir anchoring, cwd fallback, defaults, visibility of resolved source).

### Modified Capabilities
None — no existing spec's requirements change; consumer behavior stays identical under correct discovery.

## Approach

Approach 1 from exploration: keep the module-constants API, add one reload
entry point, re-anchor discovery on caller-supplied start path. Chosen over:
(2) explicit ToolConfig threading — cleanest but exceeds review budget for a
bugfix; (3) PEP 562 lazy attrs — rejected, `from .config import X` still
freezes at import time before args are parsed.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/config.py` | Modified | New signature, reload hook, precedence |
| Pattern-A modules (cli, checks, codebook, quality, profile, prepare, publish, repo_compliance, scanner, _csv_reader) | Modified | Mechanical frozen-import → attribute access |
| `src/sofer/codebook.py`, `cli.py` | Modified | De-freeze default params / argparse defaults |
| `tests/test_config.py` | Modified | Zero-arg monkeypatch seam updated; new discovery tests |
| `README.md` | Modified | Document anchoring rules |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Missed frozen binding keeps old behavior | Med | Grep audit task in sdd-tasks |
| Test seam breakage (zero-arg monkeypatch) | High | Update helpers first |
| Maintainer editable-install behavior shift | Certain | Document in README/release notes |
| Bootstrap keys (`default_config_name`) cwd-only | Low | Document limitation |

**Forecast**: ~400–600 changed lines across ~13 files — exceeds the 2000-line
review budget? No; but exceeds a 400-line single PR. Chained PRs recommended.

## Rollback Plan

Single revert of the change branch restores import-time constants; no data,
schema, or CLI-surface migrations involved.

## Dependencies

- None external. Gates: `uv run mypy src/`, full pytest matrix (422 tests green).

## Success Criteria

- [ ] User `[tool.sofer]` next to dataset TOML is honored in all install modes
- [ ] sofer's own repo TOML never consulted at runtime
- [ ] Discovery behavior covered by new tests (dataset-dir, cwd fallback, precedence)
- [ ] README documents anchoring rules; resolved pyproject visible via verbosity flag
