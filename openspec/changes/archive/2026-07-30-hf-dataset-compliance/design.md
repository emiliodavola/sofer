# Design: HF Dataset Compliance

## Technical Approach

Add 7 optional `[meta]` fields to `DatasetConfig`, then create `repo_compliance.py` with three pure functions that generate a HF-standard Dataset Card (`README.md`), a `LICENSE` file, and a column schema report. Wire these into `uploader.upload()` before pushing data files — compliance artifacts land first so the repo is standard-compliant from its first commit.

All new fields default to empty/zero values; `.get()` in `from_toml()` ensures zero breakage for existing configs.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| `ColumnSchema` location | Inside `repo_compliance.py` | In `model.py` | Schema is an output of compliance, not a config model field |
| YAML frontmatter | `PyYAML yaml.safe_dump()` from filtered dict | String templates, `tomli_w.dumps()` | `tomli_w.dumps()` outputs TOML (`=`) syntax, not YAML (`:`) — HF frontmatter parser requires valid YAML. `PyYAML` is a standard choice available as a transitive dependency in most ML/Python environments |
| License templates | Inline `dict[str, str]` in module + descriptive fallback for non-SPDX | Standalone `.txt` files | Colocated with lookup; no file-discovery at runtime; non-SPDX values produce a descriptive LICENSE file instead of crashing |
| Schema inference | Promote `codebook._infer_type` to public `codebook.infer_column_type` | Import private `_infer_type`, Reimplement | Importing private functions is fragile; promote to a stable public API shared by both `codebook.py` and `repo_compliance.py` |
| CSV delimiter | Configurable `csv_delimiter` field (default `";"`) accepted as `build_schema_report` parameter; `csv.Sniffer` fallback | Hardcoded `";"` | Some datasets use `","` or `"\t"`; explicit config with Sniffer fallback avoids silent parsing errors |
| Staging | `tempfile.mkdtemp()` → write → upload → cleanup | Write directly to repo dir | No leftover artifacts on disk; reliable cleanup via `try/finally` |
| Upload ordering | `README.md` → `LICENSE` → data files | Unordered | HF recognises the repo as a dataset immediately |
| Existing `readme` field | Unchanged (separate concern) | Merge with Dataset Card | User-supplied readme != generated Dataset Card |

## Data Flow

```
TOML config → DatasetConfig.from_toml()
                    ↓
             DatasetConfig.validate()            ← unchanged
                    ↓
             build_schema_report(cfg)            ← reads CSVs locally
                    ↓
            ColumnSchema[]  ←─── infer_column_type (public API in codebook)
                    ↓
             build_dataset_card(cfg, schema)     ← returns README.md str
                    ↓
             build_license_file(cfg.license)     ← returns LICENSE str
                    ↓
             tempfile.mkdtemp() → write README.md + LICENSE
                    ↓
             huggingface-cli upload (README.md → LICENSE → data files)
                    ↓
             tempdir cleanup (try/finally)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/model.py` | Modify | Add 6 `[meta]` fields + `csv_delimiter` to `DatasetConfig`; reuse existing `source` field instead of adding `source_organization`; extend `from_toml()` with `.get()` calls |
| `src/sofer/repo_compliance.py` | Create | `build_dataset_card()`, `build_license_file()`, `build_schema_report()`, `ColumnSchema` dataclass, `_LICENSE_TEMPLATES` dict |
| `src/sofer/uploader.py` | Modify | Call compliance after `_ensure_repo()`, pre-load recipe content, write to tempdir, upload compliance files before data files |
| `tests/test_repo_compliance.py` | Create | Unit tests for all 3 functions + integration mock test for upload ordering |

No changes: `cli.py`, `checks.py`, `__init__.py`.  Updated: `codebook.py` (promote `_infer_type` to public `infer_column_type`); `pyproject.toml` (replace `tomli-w` with `PyYAML`).

## Interfaces / Contracts

```python
@dataclass
class ColumnSchema:
    name: str
    dtype: str           # "numeric" | "categorical/text" | "mixed (mostly numeric)" | "unknown"
    nullable: bool
    example: str
    unique: int
    missing: float       # 0.0–100.0

def build_schema_report(cfg: DatasetConfig, csv_delimiter: str | None = None, csv_encoding: str = "utf-8-sig") -> list[ColumnSchema]
def build_dataset_card(cfg: DatasetConfig, schema: list[ColumnSchema], recipe_content: str | None = None) -> str
def build_license_file(license_id: str) -> str   # fallback text for unknown SPDX
```

### New `DatasetConfig` fields

| Field | Type | Default (`from_toml`) | Frontmatter key |
|-------|------|----------------------|-----------------|
| `language` | `list[str]` | `field(default_factory=list)` | `language` |
| `pretty_name` | `str` | `""` | `pretty_name` |
| `task_categories` | `list[str]` | `field(default_factory=list)` | `task_categories` |
| `size_categories` | `str` | `""` | `size_categories` |
| `citation` | `str` | `""` | (body only) |
| `collection_method` | `str` | `""` | (body only) |
| `csv_delimiter` | `str` | `";"` | (not in frontmatter) |
| `csv_encoding` | `str` | `"utf-8-sig"` | (not in frontmatter) |

### Upload orchestration (pseudocode)

```
def upload(cfg):
    _ensure_repo(cfg)
    schema = build_schema_report(cfg, csv_delimiter=cfg.csv_delimiter, csv_encoding=cfg.csv_encoding)
    recipe_content = _read_file(cfg.recipe) if cfg.recipe else None
    readme  = build_dataset_card(cfg, schema, recipe_content=recipe_content)
    license = build_license_file(cfg.license)
    tmpdir = tempfile.mkdtemp()
    try:
        (tmpdir / "README.md").write_text(readme)
        (tmpdir / "LICENSE").write_text(license)
        _hf_upload(tmpdir / "README.md", "README.md")
        _hf_upload(tmpdir / "LICENSE", "LICENSE")
        for entry in cfg.files:             # existing loop
            _hf_upload(entry.resolve(...), entry.remote)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `build_dataset_card` | Full meta, minimal meta, empty schema, recipe inlined, recipe missing, all sections present |
| Unit | `build_license_file` | 7 known SPDX → correct text; non-SPDX → descriptive fallback; empty/restricted → generic fallback |
| Unit | `build_schema_report` | Single CSV, multi-CSV, missing values, file-not-found skip, column name collisions |
| Unit | `ColumnSchema` | Field types, defaults |
| Integration | `upload()` compliance wiring | Mock 3 functions; verify call order, tempdir cleanup, exception propagation |

Coverage targets: ≥90% branch in `repo_compliance.py`, ≥80% in modified upload path.

## Migration / Rollout

No migration required. Old TOML files produce minimal Dataset Cards and a fallback LICENSE. Re-running `upload` on an existing repo regenerates the compliance artifacts — no-op on data files.

## Open Questions

None.
