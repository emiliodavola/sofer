# Type-gate baseline — measured evidence (parent-run, 2026-09-15)

Change: `2026-09-15-chore-type-gate-policy` (issue #201)
Branch: `chore/201-type-gate-policy` from `dev@8184ffb`
All numbers below were produced by the parent session with shell access on this branch. Configs used for measurement were temporary and removed; the tree contains only the maintainer's `pyproject.toml` edit.

## 0. Maintainer edit already in the working tree (uncommitted)

```diff
 [tool.mypy]
 python_version = "3.10"
-strict = false
+strict = true
 check_untyped_defs = true
 ignore_missing_imports = true
 warn_unused_ignores = true
```

Effect: CONTRIBUTING.md:81 ("We use **mypy** in strict mode") becomes TRUE. The drift the explore flagged is resolved by this edit — it is not a new finding.

## 1. mypy with `strict = true` — RED

```text
$ uv run mypy src/ scripts/
src\sofer\_mirror.py:77: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src\sofer\_clean.py:58: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src\sofer\_clean.py:183: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src\sofer\metadata.py:239: error: Returning Any from function declared to return "str"  [no-any-return]
src\sofer\publish.py:70: error: Module "huggingface_hub.utils" does not explicitly export attribute "RepositoryNotFoundError"  [attr-defined]
src\sofer\mcp_server.py:691: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
Found 6 errors in 5 files (checked 33 source files)
```

Context for each site:
- `_mirror.py:77` `def _is_convertible_entry(entry) -> bool:` — called at `:113` in a loop over remotes (strings).
- `_clean.py:58` `def allowed_output_remotes(cfg, keep_csv, output_dir)` and `_clean.py:183` `def clean_build(cfg, override)` — both take `cfg` deliberately unannotated ("avoid hard import cycle at module load"); `_clean.py` has no `TYPE_CHECKING` import today.
- `metadata.py:239` `return yaml.safe_dump(_plain(meta), sort_keys=True, allow_unicode=True)` — declared `-> str`.
- `publish.py:70` `from huggingface_hub.utils import RepositoryNotFoundError`.
- `mcp_server.py:691` `return _tomli.load(fh)` — declared `-> dict[str, Any]`.

**Verified public-path fix for `publish.py:70`** (on installed hf 1.25.1):

```text
$ uv run python -c "from huggingface_hub.errors import RepositoryNotFoundError; print('ok')"
ok
```

This single edit clears BOTH mypy `attr-defined` and pyright `reportPrivateImportUsage`.

## 2. pyright baselines

pyright is NOT a Python dependency (`uv run pyright` → "program not found"). It exists on this box only as a global npm install: `/c/Users/elaze/AppData/Roaming/npm/pyright`, "based on pyright 1.39.9". No `pyrightconfig.json` exists anywhere (repo, home, parents). No `[tool.pyright]`. No pyright entry in `.pre-commit-config.yaml` or `.github/workflows/`.

Measured with an explicit `{"typeCheckingMode": "<mode>"}` config placed at the REPO ROOT (removed afterwards):

| scope | basic | standard | strict | no config (default) |
|---|---|---|---|---|
| `src/` (32 files) | **10 err** / 0 warn | **11 err** / 0 warn | 578 err | 18 err / 1088 warn |
| `scripts/` | **0 err** | **0 err** | — | — |
| `tests/` (35 files) | 119 err | 119 err | — | 147 err / 13423 warn |

`scripts/` is clean in every mode → a gate over `src/ scripts/` is symmetric with `uv run mypy src/ scripts/`.

### The 11 `standard`-mode errors on `src/`

| site | rule | class |
|---|---|---|
| `_converters.py:620` | reportArgumentType | list[T] invariance (`list[_CellGetValue]` vs `list[object]`) |
| `_converters.py:650` | reportPossiblyUnboundVariable | **real smell** — see §3 |
| `cli.py:465`, `config.py:151`, `mcp_registration.py:128`, `mcp_server.py:687`, `model.py:411` | reportMissingImports | `import tomli` fallback arm (py<3.11) at the five interpreter-selection sites |
| `verification.py:66` | reportMissingImports | `datasets` (optional dependency) |
| `prepare.py:445`, `publish.py:686` | reportAttributeAccessIssue | `TextIO.reconfigure` (typeshed: on TextIOWrapper, not TextIO) |
| `publish.py:70` | reportPrivateImportUsage | same site as the mypy `attr-defined` |

The 10 `basic`-mode errors are the same list minus `_converters.py:650` — i.e. **basic misses the possibly-unbound smell**.

## 3. `_converters.py:650` — the real smell

```python
            # Clean locals for next iteration
            if "raw_rows" in locals():
                del raw_rows
```

Inside the per-sheet loop of the xlsx converter; a deliberate memory-hygiene `del` guarded by a `locals()` membership test. The guard is correct at runtime (pyright cannot model `locals()`); mypy does not flag it; `standard` mode does. Resolution is a design decision: restructure (assign `None`, or scope the parse into a helper) vs a targeted `# pyright: ignore[reportPossiblyUnboundVariable]`. `_converters.py` is NOT a rule-14 100%-coverage module.

## 4. Hard constraints (from explore, Engram #1295)

1. Adding `tomli` to the dev dependency group makes `cli.py:467` unreachable on the 3.13 gate interpreter and permanently breaks the `cli.py` COV-06 100.00% row → **rejected**. Explore recommends a single stub via `[tool.pyright] stubPath` (fallback: five per-line ignores).
2. Narrowing the win32 `sys.stdout.reconfigure` guards to `isinstance(_, io.TextIOWrapper)` would fail `tests/test_prepare.py:1626-1657` and `tests/test_publish.py:2018-2052`, which inject a duck-typed `_FakeStdout` → ignore-or-cast is the resolution.
3. pyright silently prefers `pyrightconfig.json` over `[tool.pyright]` → a guard must assert the JSON file's absence to keep one config authority.

## 5. Pin discipline precedent (#195, merged)

ruff is pinned in one place with a guard test asserting dev pin ↔ `required-version` ↔ pre-commit `rev` agreement (`tests/test_ci_workflows.py`). Pyright has no `required-version` analogue → pin is a dev dependency (`pyright==X.Y.Z`) + `uv.lock` + verify-phase runtime evidence.

## 6. Current gate surfaces

- `.github/workflows/ci.yml:6-23` (lint job): python 3.13, `uv sync`, `uv run ruff check src/ tests/ scripts/`, `uv run mypy src/ scripts/`.
- `.pre-commit-config.yaml`: ruff `--fix`; ruff-format (`types_or: [python, pyi, jupyter]`, PB-14); local mypy hook `uv run mypy src/ scripts/` (`pass_filenames: false`).
- `pyproject.toml:77-83` `[tool.mypy]`; `CONTRIBUTING.md:28` (command list) and `:79-81` (§Type checking).
- `openspec/specs/ci/spec.md`: interpreter-pin requirement ~:219-274, scenario :236, `## Test Mapping` at :380 with rows :393 (`| Req | Scenario | Verification |`).

---

## 7. Re-measurement with the PINNED version (R1 closed, 2026-09-15)

`pyright==1.1.414` was added to `[dependency-groups] dev` and `uv.lock` regenerated (this is the planned change, D10). Measurements below are from `uv run pyright` inside the project venv — the only faithful way to measure (see §7.1).

| scope | mode/config | result |
|---|---|---|
| `src/` | `standard` + `pythonVersion 3.13` | **13 errors**, 0 warnings |
| `scripts/` | same | **0 errors** |
| `tests/` | same | **119 errors** (excluded by policy) |
| `src/` | no config (default) | 11 errors |

`uv run pyright --version` → `pyright 1.1.414` (the pin is live).

### 7.1 The `uvx` artifact — why the first pinned run showed 29 errors

`uvx pyright@1.1.414 src/` reported **29 errors / 5 warnings** including `pyarrow`, `pydantic`, `fastmcp`, `dotenv`, `huggingface_hub`, `tomli_w` — i.e. every third-party import missing. Cause: `uvx` runs pyright in an isolated ephemeral environment and pyright honors the `VIRTUAL_ENV` it inherits, so it resolved imports against a venv that contains only pyright. The pinned version's real baseline is identical to the npm-measured one **once pyright runs in the project venv**. Lesson for the change: the gate MUST be invoked as `uv run pyright` (never bare `pyright`, never `uvx`), and the design should consider declaring `venvPath`/`venv` in `[tool.pyright]` so the resolution is explicit rather than inherited.

### 7.2 The `datasets` discovery — the target set is 13, not 11

With `pythonVersion = "3.13"` and the project venv, pyright RESOLVES `datasets` (installed; its runtime import currently crashes on this box via `fsspec`, which is irrelevant to static analysis) and therefore type-checks the call sites instead of reporting a missing import. That replaces the single `verification.py:66` missing-import error with **three real `reportArgumentType` errors**:

```text
verification.py:101 | reportArgumentType | Argument of type "str | NamedSplit" cannot be assigned to parameter "key" of type "str" in function "__setitem__"
verification.py:103 | reportArgumentType | (same, second assignment)
verification.py:116 | reportArgumentType | Argument of type "list[str | NamedSplit]" cannot be assigned to parameter "split_names" of type "list[str]"
```

Source: `actual_splits = list(ds.keys())` — `datasets` types `DatasetDict.keys()` as `list[str | NamedSplit]`; the code then uses the elements as `dict[str, int]` keys and passes the list as `split_names: list[str]`. Resolution: coerce once at the binding site (`actual_splits = [str(name) for name in ds.keys()]`), which is behaviour-neutral (`NamedSplit.__str__` yields the split name and `datasets` accepts the plain string for lookup).

### 7.3 Frozen resolution table (18 sites: 13 pyright + 6 mypy − 1 shared)

| # | site | gate(s) | resolution |
|---|---|---|---|
| 1 | `_mirror.py:77` | mypy | annotate the parameter (`entry: str`) |
| 2 | `_clean.py:58` | mypy | annotate `cfg: DatasetConfig` (+ `TYPE_CHECKING` import) |
| 3 | `_clean.py:183` | mypy | same pattern |
| 4 | `metadata.py:239` | mypy | make the `yaml.safe_dump` return typed (`cast`/typed local) |
| 5 | `mcp_server.py:691` | mypy | type the `_tomli.load` return for the declared `dict[str, Any]` |
| 6 | `publish.py:70` | **mypy + pyright** | `from huggingface_hub.errors import RepositoryNotFoundError` (verified on hf 1.25.1) |
| 7 | `_converters.py:620` | pyright | annotate the binding (`vals: list[object] = list(row)` at `:614`) |
| 8 | `_converters.py:650` | pyright | restructure the `if "raw_rows" in locals(): del raw_rows` block (design D6) |
| 9-13 | `cli.py:465`, `config.py:151`, `mcp_registration.py:128`, `mcp_server.py:687`, `model.py:411` | pyright | ONE committed stub via `[tool.pyright] stubPath` (D5) |
| 14-15 | `prepare.py:445`, `publish.py:686` | pyright | per-line `# pyright: ignore[reportAttributeAccessIssue]` (D7) |
| 16-18 | `verification.py:101`, `:103`, `:116` | pyright | coerce split names to `str` at the binding site (§7.2) |

Rule-14 (100% coverage) modules touched: `publish.py` (#6, #15) and `prepare.py` (#14) — every edit is comment-only, an import path, or behaviour-neutral, so the four core rows must be re-run in verify.

---

## 8. Re-measurement after the maintainer's dependency/config edits (authoritative for apply)

The maintainer edited `pyproject.toml` again during this cycle; `uv sync` was re-run. Current `[tool.mypy]` posture: `python_version = "3.11"`, `strict = true`, `check_untyped_defs = true`, `ignore_missing_imports = true`, `warn_unused_ignores = true`, `exclude = ["tests/", ".venv/"]`, plus an `[[tool.mypy.overrides]]` block for `pyarrow`, `pyarrow.*`, `datasets`, `datasets.*`. Dependency additions: runtime `datasets>=5.0.1`, `numpy<2.3`; dev `types-openpyxl`, `types-pyyaml`, `pyright==1.1.414`. mypy resolves to **2.3.0**.

### 8.1 mypy — still 6 errors, composition CHANGED

```text
$ uv run mypy src/ scripts/
src\sofer\_converters.py:620: error: Argument 1 to "append" of "list" has incompatible type "list[bool | float | ... | None]"; expected "list[object]"  [arg-type]
src\sofer\_mirror.py:77: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src\sofer\_clean.py:58: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src\sofer\_clean.py:183: error: Function is missing a type annotation for one or more parameters  [no-untyped-def]
src\sofer\publish.py:70: error: Module "huggingface_hub.utils" does not explicitly export attribute "RepositoryNotFoundError"  [attr-defined]
src\sofer\mcp_server.py:691: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
Found 6 errors in 5 files (checked 33 source files)
```

Deltas vs §1:
- **REMOVED — `metadata.py:239`**: `types-pyyaml` resolves `yaml.safe_dump` → the `no-any-return` is gone. The design's table entry #4 is retired.
- **ADDED — `_converters.py:620`**: with `python_version = "3.11"` + `types-openpyxl`, mypy now reports the SAME site pyright reports (`reportArgumentType` vs `arg-type`, both list invariance). This site becomes **dual-gate** — the third shared fix candidate alongside `publish.py:70`.
- `_mirror.py:77`, `_clean.py:58`, `_clean.py:183`, `publish.py:70`, `mcp_server.py:691` unchanged.

### 8.2 pyright — still 13 errors (pinned 1.1.414, standard + py313 + venv, scope `src/`)

Identical set to §7.2 (`_converters.py:620`, `_converters.py:650`, 5× tomli, `prepare.py:445`, `publish.py:686`, `publish.py:70`, `verification.py:101/103/116`). `scripts/` → 0 errors. `tests/` → 119 (excluded by policy).

Note: `datasets` is now a DIRECT runtime dependency, so the three `verification.py` `reportArgumentType` errors are structural (they will not revert to a missing-import error), and `verification.py`'s optional-dependency `try/except ImportError` guard becomes practically unreachable in a synced environment — its behaviour must be preserved (and remains mockable) rather than deleted.

### 8.3 Distinct apply sites: 17 (13 pyright + 6 mypy − 2 shared)

Shared: `publish.py:70` (mypy `attr-defined` + pyright `reportPrivateImportUsage`) and `_converters.py:620` (mypy `arg-type` + pyright `reportArgumentType`).

### 8.4 Suite status on this tree

```text
$ uv run pytest tests/ -q
1785 passed, 6 skipped, 1 warning in 66.87s
```

No test pins mypy's `python_version` (`grep -rn "python_version|pythonVersion" tests/*.py` → no matches), so the "3.11" value turns nothing red.

### 8.5 Maintainer decisions taken this cycle (authoritative)

1. `[tool.mypy] python_version = "3.11"` **stays**. Consequence: `openspec/specs/ci/spec.md` CI-07's clause "`[tool.mypy] python_version` SHALL remain `\"3.10\"`" is now **stale/false**. This change's earlier non-goal forbade editing CI-01..CI-08; the amendment of that single clause is being handled explicitly (see the change's tasks/design), not silently.
2. The `[[tool.mypy.overrides]]` block is **completed** with `ignore_missing_imports = true` for `pyarrow`/`pyarrow.*`/`datasets`/`datasets.*` (note: redundant today because the global `ignore_missing_imports = true` already covers them; it is kept as the maintainer asked, and is a no-op until the global key flips).
3. `datasets>=5.0.1` and `numpy<2.3` **stay in this PR**.

### 8.6 Design amendments required (supersede the frozen design where these conflict)

- Design **DC-2** claimed the tree had `ignore_missing_imports = false` and therefore needed `mypy_path = "typings"` to consume the tomli stub: **the premise is false** (`ignore_missing_imports = true`; mypy reports zero tomli diagnostics). The `mypy_path` addition is unnecessary — drop it unless apply measures otherwise.
- Design's resolution table entry for `metadata.py:239` is **retired** (§8.1).
- `_converters.py:620` is **dual-gate** and its resolution must satisfy BOTH checkers with one edit (§8.1).
- Everything else in the frozen design (D1–D13, the pyright block, the stub, guards, CI-09 text, verify plan) stands.
