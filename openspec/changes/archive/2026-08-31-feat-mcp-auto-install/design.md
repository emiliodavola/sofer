# Design: feat-mcp-auto-install

## Technical Approach

Promote `fastmcp>=3.4,<4` to `[project].dependencies`; keep `mcp = ["fastmcp>=3.4,<4"]` as one-minor alias. Regenerate `uv.lock` (moves `fastmcp` to unconditional `dependencies`). Retain degraded guard in `src/sofer/mcp_server.py:55-57` with corrected PEP 508 `sofer[mcp] @ URL` for both `pip` and `uv tool`. Fix `README.md`/`README_ES.md` Install + AI/MCP blocks same commit (AGENTS.md sec13). Spec deltas `mcp-server` MSP-R02/R12 and `packaging` PKG-06 already capture contract.

## Architecture Decisions

### Decision: Dependency placement

| Option | Tradeoff | Decision |
|---|---|---|
| Promote to `dependencies`, keep alias | Out-of-box `sofer-mcp`, backward compat; +~10 MB / 8 pkgs | **Chosen** |
| Docs-only (keep optional) | Lean but `sofer-mcp` still crashes; reporter rejected | Rejected |
| Two distributions | Clean split but doubles release/docs for ~10 MB | Rejected |
| Runtime wrapper auto-install | Mutates env, breaks offline, violates MSP-R01 | Rejected |
| Vendoring | Violates AGENTS.md sec9, supply-chain lag | Rejected |

Rationale: reporter prefers automatic install; cost marginal vs `pyarrow` 40 MB.

### Decision: Guard retention

| Option | Tradeoff | Decision |
|---|---|---|
| Keep guard, update message | Covers `--no-deps`/corrupt wheel | **Chosen** |
| Remove guard | Raw `ModuleNotFoundError` on degraded install | Rejected |

Rationale: 3 lines, `pragma: no cover` via `sys.modules` monkeypatch; unreachable on correct install.

### Decision: Lock and build

| Option | Tradeoff | Decision |
|---|---|---|
| `uv lock` + `uv build` after edit | Hatchling renders unconditional `Requires-Dist`; enforces identical pin in 3 places | **Chosen** |
| Manual `uv.lock` edit | Error-prone, drift | Rejected |

Pin appears in `dependencies`, `optional-dependencies.mcp`, `dependency-groups.dev` — identical string.

## Data Flow

```
pip/uv install
  -> wheel METADATA: Requires-Dist: fastmcp>=3.4,<4  (no marker)
                     Provides-Extra: mcp / Requires-Dist: fastmcp>=3.4,<4; extra == 'mcp' (alias)
  -> pip install "sofer @ git+...@vX.Y.Z"               => fastmcp installed => sofer-mcp --help ok
  -> pip install "sofer[mcp] @ git+...@vX.Y.Z"          => same wheel + alias marker (redundant, valid)
  -> --no-deps / corrupt                                 => guard ImportError with pip+uv+PEP508 hint

uv tool install "sofer @ git+...@vX.Y.Z" --force        => isolated tool env, same
uvx --from "git+...@vX.Y.Z" --with "sofer[mcp]" sofer-mcp --help => transient alias
```

`[project.scripts] sofer-mcp = "sofer.mcp_server:main"` resolves without extra.

## File Changes

| File | Action | Description | Est. lines |
|---|---|---|---|
| `pyproject.toml` | Modify | Add `fastmcp>=3.4,<4` to `dependencies`; keep alias | +2 |
| `uv.lock` | Modify | Regenerated (~30 lines) | ~30 |
| `src/sofer/mcp_server.py:55-57` | Modify | Guard message: `pip` + `uv tool` + `sofer[mcp] @ git+...` (not `git+...[mcp]`) | ~4 |
| `README.md` | Modify | Install canonical `sofer @` + alias note; AI/MCP fix 444 + flip to included by default; add `uv tool`/`uvx --with` | ~27 |
| `README_ES.md` | Modify | Mirror README.md same commit; ES prose, EN commands | ~27 |
| `tests/test_mcp_server.py` | Modify | Invert `TestImportWithoutExtra`; assert unconditional `Requires-Dist` | ~10 |

Total ~100 lines — well under 2000 budget; single PR.

## Interfaces / Contracts

**pyproject.toml** — hatchling auto-renders `METADATA`:

```toml
dependencies = ["huggingface-hub>=0.26.0", "openpyxl>=3.1", "pyarrow>=14.0",
  "python-dotenv>=1.0.0", "tomli>=2.0; python_version < '3.11'", "tomli-w>=1.0", "pyyaml>=6.0",
  "fastmcp>=3.4,<4"]
[project.optional-dependencies]
mcp = ["fastmcp>=3.4,<4"]
[dependency-groups]
dev = ["pytest>=8.0", "ruff>=0.9.0", "mypy>=1.15.0", "pre-commit>=4.0.0", "fastmcp>=3.4,<4"]
```

Wheel: `Requires-Dist: fastmcp>=3.4,<4` + `Provides-Extra: mcp`.

**Guard** — degraded-only, correct PEP 508, never `git+...[mcp]`:

```python
raise ImportError(
    "sofer's MCP server requires 'fastmcp' - install with: "
    "pip install 'sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z' "
    "or uv tool install 'sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z' --force "
    "/ uvx --from git+https://github.com/emiliodavola/sofer.git@vX.Y.Z --with 'sofer[mcp]' sofer-mcp --help"
) from _exc
```

**READMEs** — canonical `pip install "sofer @ git+...@vX.Y.Z"` / `uv tool install "sofer @ git+...@vX.Y.Z"` + alias note; `uvx --from "git+...@vX.Y.Z" --with "sofer[mcp]" sofer-mcp --help`; intro: "included by default — `[mcp]` is now an alias."

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Lean install imports `fastmcp`/`sofer.mcp_server`; guard mentions pip+uv+`sofer[mcp] @` | `python -c "import fastmcp"` + `sys.modules` monkeypatch |
| Integration | `uv tool install "sofer @ git+..." --force` => `sofer-mcp --help` ok; alias also works | Smoke + `uv run pytest tests/test_mcp_server.py tests/test_mcp_registration.py -q` |
| Wheel | `Requires-Dist` unconditional, `Provides-Extra` present, `entry_points.txt` has `sofer-mcp` | `hatchling build -t wheel` then METADATA checks (`TestWheelPackaging`) |

Edge: lean +10 MB justified vs `pyarrow`; pin drift avoided via identical string; `README_ES` same commit per sec13; `release.yml` METADATA version check covers version.

## Migration / Rollout

No migration. Single commit; alias keeps `pip install "sofer[mcp]"` valid. `uv tool upgrade` may need re-install (document in notes). Rollback: revert `pyproject.toml`, guard, READMEs, `uv lock`.

## Open Questions

- None blocking. Optional: extend `release.yml` to assert both `sofer` and `sofer-mcp` entry points.
