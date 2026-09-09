# Design: Fix multisheet profile/render (all xlsx sheets)

## Technical Approach

Extend `generate_all_profiles` (PRF-05) and `generate_all_renders` (RND-04) from 1:1 per `[[file]]` to 1:N for `.xlsx` N>1, mirroring `codebook.generate_all` and `prepare` (`stem__sheet`). Single-sheet and non-xlsx stay suffix-less. Reuse `codebook._read_xlsx_sheets` and `_converters.sanitize_sheet_name` + `seen _{n}` dedup. Helpers `_profile_output_for_rel`/`_render_output_for_rel` anchor on `cfg._base_dir.resolve()` + `OUTPUT_DIR`/`PROFILE_DIR`/`RENDER_DIR`. Normalized collision `re.sub(r"__+","_",path)` makes `a__ventas≈a_ventas`; partial-write then `ValueError ::sheet`. Containment via `_validate_output_targets`, Option B anchoring.

## Architecture Decisions

### Decision: 1:N files vs `sheets[]` aggregation

| Option | Tradeoff | Decision |
|--------|----------|----------|
| 1:N `stem__sheet` | Parity with codebook/prepare; flat Metadata; no schema break | **Chosen** |
| `sheets[]` in Metadata | Changes Metadata/card/publish; high churn | Rejected |

### Decision: Reuse `_read_xlsx_sheets` + `sanitize_sheet_name`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Reuse verbatim | Single pipeline; fixes propagate; DRY | **Chosen** |
| Duplicate reader | Drift risk; violates one-module-per-concern | Rejected |

Pipeline: `lower→NFKD→ascii→space->_→[^a-z0-9_-]->_→__+->_→strip→empty→sheet`. Dedup `seen:dict[str,int]` emits `base, base_2, base_3` as in `_converters._convert_xlsx_to_parquet:394` and `codebook._read_xlsx_sheets:162`.

### Decision: Helpers `_profile_output_for_rel` / `_render_output_for_rel`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Extract helpers + `_normalize_collision_key` | DRY `PurePath.suffixes` (last suffix only); testable | **Chosen** |
| Inline logic | Duplicates across profile/render | Rejected |

Mirrors `codebook._codebook_output_for_rel` / `_normalize_codebook_collision_key`.

### Decision: Collision key `__+ → _`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `re.sub(r"__+","_",path.as_posix())` | Catches `a__ventas` vs `a_ventas` aliasing | **Chosen** |
| Exact match | Misses alias; inconsistent with codebook/prepare | Rejected |

Error names sources as `<rel>::<sanitized>`.

### Decision: Partial-write-then-ValueError

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Write non-colliding, then `ValueError` | Matches codebook:737; preserves progress | **Chosen** |
| Atomic abort | Loses valid outputs; diverges from precedent | Rejected |

### Decision: Anchoring `base_dir.resolve()` + Option B

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `base_dir=cfg._base_dir.resolve(); data_dir=base_dir/OUTPUT_DIR; write_root=base_dir/output if relative else out.resolve()` | CWD-independent; matches profile:182/render:124/codebook:514 | **Chosen** |
| CWD-relative | Breaks under `monkeypatch.chdir`; violates spec | Rejected |

Single-sheet guard: `len==1 → sheet=None` (no suffix), byte-identical to `next(iter(sheets))`.

## Data Flow

```
dataset.toml → DatasetConfig.from_toml → cfg(_base_dir, files)
        ↓
base_dir.resolve() + data_dir(=base_dir/OUTPUT_DIR)
        ↓
entries = [(local=resolve(base_dir), suffix) if exists+format]
        ↓
for each: rel_stem = relative_to(data_dir) if inside else relative_to(base_dir)
  ├─ non-xlsx → expanded += (local, None, helper(profiles_dir, rel_stem, None))
  └─ .xlsx → sheets=_read_xlsx_sheets(path) // sanitize+seen
        ├─ len==1 → expanded += (local, first_key, helper(...,None))
        └─ len>1  → for s in sheets: helper(...,s) → stem__s
        ↓
collision_map: normalize(out)=re.sub(__+→_ ) → [sources]
colliding = {(local,sheet) where len>1}
generate: skip colliding; read per-sheet (or load metadata), write
        ↓
if colliding: print "X Collision: ..." + raise ValueError(::sheet) // partial-write
else: return generated
```

Render sources `metadata.yaml` from `profiles_dir` under same `write_root`; skips missing with warning. MCP checks `_validate_output_targets` before writes.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/profile.py` | Modify | Add `_profile_output_for_rel`, `_normalize_profile_collision_key`; 1:N via `_read_xlsx_sheets`/`sanitize_sheet_name`/`seen`; collision `__+→_` + partial-write |
| `src/sofer/render.py` | Modify | Add `_render_output_for_rel`; same 1:N parity; resolve metadata from `profiles_dir`; skip missing |
| `src/sofer/_converters.py` | Reuse | `sanitize_sheet_name` unchanged |
| `src/sofer/codebook.py` | Reuse | `_read_xlsx_sheets` pattern reference |
| `src/sofer/config.py` | Reuse | `PROFILE_DIR`/`RENDER_DIR`/`OUTPUT_DIR` |
| `src/sofer/cli.py` | No-op | Already delegates `ValueError→exit1` |
| `src/sofer/mcp_server.py` | Indirect | Inherits via `_validate_output_targets` + bounded reload |
| `tests/test_profile.py` | Modify | 2-sheet openpyxl batch + collision tests |
| `tests/test_render.py` | Modify | 2-sheet render + dedup + collision tests |

## Interfaces / Contracts

```python
def _profile_output_for_rel(dir: Path, rel: Path, sheet: str | None) -> Path:
    # (dir/rel).with_suffix(last→.metadata.yaml) ; sheet→ stem__sheet
def _render_output_for_rel(dir: Path, rel: Path, sheet: str | None) -> Path: ...
def _normalize_collision_key(p: Path) -> str:
    return re.sub(r"__+", "_", p.as_posix())
# generate_all_profiles(cfg, output_dir?) -> list[str]  # ValueError after partial-write
# generate_all_renders(cfg, output_dir?) -> list[str]   # skips missing metadata
```

Sanitization verbatim: `lower→NFKD→ascii→space->_→[^a-z0-9_-]->_→__+->_→strip→"sheet"`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `sanitize_sheet_name("DATA GOT Año")→data_got_ano`, `""→sheet`, dedup `Ventas/VENTAS→ventas, ventas_2` | Direct helper calls |
| Unit | helpers with `Labels/etiquetas_a.csv`, `cache` vs outside, `profile_dir` override | `restore_tool_config` + `config.reload` |
| Integration | 2-sheet `report.xlsx` Sales/Inventory → `report__sales`+`__inventory` correct schema/rows; 1-sheet stays suffix-less byte-identical | openpyxl wb + `DatasetConfig` + `generate_all_*` |
| Integration | Collision `a__ventas::Ventas` vs `a_ventas.csv` → ValueError `::Ventas`, partial-write `ok.csv` kept | Assert files + stderr |
| Integration | Option B absolute/relative (`rel/out` anchored to base_dir via `chdir`), `docs/profiles`, `[[file]]` fail-fast, missing metadata skip | Temp trees + `monkeypatch.chdir` |
| Contract | CLI exit1 + MCP `_validate_output_targets` rejects escaping `profile_dir` | `cli._cmd_profile(Namespace)` + `sofer_profile(all_files=True)` |

No hardcoded `";"`/`"utf-8-sig"` outside `config.py`.

## Migration / Rollout

No migration. Derived artifacts only; single-sheet stable. Rollback: `git revert` profile/render; delete `*__*.metadata.yaml`/`*__*.README.md` if needed.

## Open Questions

- None blocking. openpyxl already required.
