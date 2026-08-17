# Design: sofer v2 — metadata core (Fase A)

## Technical Approach

Additive vertical slice: `metadata.yaml` becomes the dataset-documentation source of truth. A new read-only `profile` command generates it from a dataset file; a new `render` command produces a status-annotated `README.md` from it. The existing `build_dataset_card` path is untouched, so two render paths coexist until a later phase unifies them. Detectors are plugin-style (base class + registry, mirroring `_formats.py`), stdlib-only (PyYAML already a dependency). Confidence = `match_rate × prior`, rounded to `confidence_round_digits` (default 4) before storing; priors/thresholds read from `[tool.sofer]` config — no magic numbers (AGENTS.md rule 1). CSV is read through the existing bounded `_csv_reader.stream_csv` (encoding fallback, config delimiter/encoding); non-CSV formats reuse `codebook._read_file`.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Semantic vs PII split | Two hierarchies: `SemanticDetector` ("what kind of data") vs `PiiDetector` ("is it sensitive") | Orthogonal questions — an email column is both `type=email` and `possible_pii`. Merging forces each detector to answer both or neither; a future non-PII type (e.g. `datetime`) has no PII signal. Single-purpose, composable. |
| Prior source | `prior` resolved from `config.SEMANTIC_PRIORS[name]` at detect-time, not a class attribute | Rule 1 — a hardcoded float can't be overridden by TOML and needs a code edit to recalibrate (empirical calibration is out of scope). Config resolution = one source of truth. |
| `InferenceStatus` location | `model.py` (mirrors `QUALITY_CHECK_NAMES`) | Frozen 3-value vocabulary (MTA-04) consumed by `semantic.py` (Detection.status), `metadata.py` (serialization), `render.py` (display). `model.py` already hosts `QUALITY_CHECK_NAMES`; living there avoids semantic↔metadata↔render cross-imports. |
| metadata.yaml = truth | README rendered only; `build_dataset_card` untouched | One deterministic, round-trippable machine-readable doc (MTA-03); render is pure projection. Card path frozen until unification. |
| Reader reuse | CSV via `_csv_reader.stream_csv`; non-CSV (Parquet/XLSX/JSONL) via `codebook._read_file`; coarse type via `codebook.infer_column_type` | No new readers (rule 4). `stream_csv` is bounded (`max_sample`), has encoding fallback (`utf-8-sig → utf-8`), and reads delimiter/encoding from `CSV_DELIMITER`/`CSV_ENCODING` (rule 3). `_read_file` full-loads into memory with no encoding fallback or delimiter sniffing, so it is used ONLY for non-CSV formats — never for CSV/TSV. |
| Email regex sharing | `_patterns.py` holding `EMAIL_PATTERN` | Both detectors need the regex — one definition, no duplication (rule 4), no semantic↔pii import. |
| PII confidence | same `match_rate × SEMANTIC_PRIORS["email"]` | One prior, one formula, two lenses — deterministic, no second magic number. |

## Data Flow

```
profile:  dataset ──detect format(_formats)──→ CSV: stream_csv (bounded, enc fallback)
                                               non-CSV: _read_file ──→ per column:
            infer_column_type (coarse) ─→ infer_semantic_types (all detectors → list[Detection])
                                       ─→ infer_pii_types (all detectors → list[PiiDetection])
          ──assemble Metadata──→ write metadata.yaml (sort_keys=True) ──→ report missing_fields
render:   metadata.yaml ──load──→ README.md (confirmed plain | inferred "email (inferred, 78%)" | unknown "unknown")
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_patterns.py` | Create | `EMAIL_PATTERN` shared regex |
| `src/sofer/semantic.py` | Create | `SemanticDetector` ABC, `Detection`, `EmailDetector`, `infer_semantic_types`, `infer_status` |
| `src/sofer/pii.py` | Create | `PiiDetector` ABC, `PiiDetection`, `EmailPiiDetector`, `infer_pii_types` |
| `src/sofer/metadata.py` | Create | `METADATA_VERSION` constant, schema dataclasses, `serialize`/`load`, `missing_fields` |
| `src/sofer/profile.py` | Create | `profile(dataset_path, output_dir)` orchestrator (CSV via `stream_csv`) |
| `src/sofer/render.py` | Create | `render(metadata_path, output_dir)` |
| `src/sofer/model.py` | Modify | Add `InferenceStatus` (additive) |
| `src/sofer/config.py` | Modify | `_DEFAULTS` += `semantic_priors`, `confirm_threshold`, `min_threshold`, `detect_threshold`, `confidence_round_digits`, `profile_max_sample` + constants; dict-type validation for `semantic_priors` |
| `src/sofer/cli.py` | Modify | `profile` + `render` subparsers, `_cmd_profile`/`_cmd_render` |
| `pyproject.toml` | Modify | Mirror new `[tool.sofer]` keys |
| `README.md` | Modify | Document profile/render (rule 7) |

## Interfaces / Contracts

```python
METADATA_VERSION: str = "1"            # metadata.py module constant (MTA-02)

class InferenceStatus(str, Enum): CONFIRMED="confirmed"; INFERRED="inferred"; UNKNOWN="unknown"

@dataclass(frozen=True)
class Detection:
    type: str; match_rate: float; confidence: float; status: InferenceStatus
    # confidence = round(match_rate × prior, CONFIDENCE_ROUND_DIGITS)

class SemanticDetector(ABC):
    name: str; pattern: re.Pattern[str]
    @property
    def prior(self) -> float:
        try: return SEMANTIC_PRIORS[self.name]
        except KeyError as e:
            raise ValueError(f"no semantic prior configured for detector '{self.name}'") from e
    @abstractmethod
    def detect(self, values: list[str]) -> Detection | None: ...
    # returns None when match_rate < DETECT_THRESHOLD; match_rate counts non-missing values only

def infer_semantic_types(values: list[str]) -> list[Detection]: ...  # runs all detectors
def infer_status(confidence: float) -> InferenceStatus: ...           # ≥CONFIRM / ≥MIN / else

@dataclass(frozen=True)
class PiiDetection:
    label: str; confidence: float; note: str = "possible_pii"   # serializes to {label, confidence, note} (PII-02)

class PiiDetector(ABC):
    def detect(self, values: list[str]) -> PiiDetection | None: ...

def infer_pii_types(values: list[str]) -> list[PiiDetection]: ...  # runs all PII detectors (mirrors infer_semantic_types)

def profile(dataset_path: Path, output_dir: Path | None = None) -> int: ...
def render(metadata_path: Path, output_dir: Path | None = None) -> int: ...
def serialize(meta: Metadata) -> str: ...   # yaml.safe_dump(sort_keys=True)
def load(path: Path) -> Metadata: ...
```

Defaults: `semantic_priors={"email": 0.98}` (distinctive `@`+TLD structure ⇒ match-rate near 1.0), `confirm_threshold=0.8`, `min_threshold=0.5`, `detect_threshold=0.5` (spec canonical STI-04/STI-01 values), `confidence_round_digits=4`, `profile_max_sample=100_000` (matches `codebook_max_sample`). `METADATA_VERSION = "1"` is a module constant in `metadata.py` (MTA-02), not a config key.

## Testing Strategy

Strict TDD; 562 existing tests untouched. New flat `tests/` files using `tmp_path`.

| Layer | Coverage | Approach |
|-------|----------|-----------|
| Unit | STI-01..06 | `test_semantic.py`: contract, Detection shape, confidence `round(0.8×0.9, 4) = 0.72` asserted with `pytest.approx` (config override), match_rate denominator excludes missing, `detect_threshold` → `None` boundary, status boundaries, email match/no-match |
| Unit | PII-01..04 | `test_pii.py`: finding shape, note always `possible_pii`, `infer_pii_types` aggregation, flag/no-flag |
| Unit | MTA-01..06 | `test_metadata.py`: skeleton, per-column contract, `metadata_version == METADATA_VERSION`, byte-identical serialize, round-trip, enum, read-only |
| Unit | RND-01..03 | `test_render.py`: confirmed plain / `email (inferred, 78%)` / `unknown` |
| Integration | PRF-01..04 | `test_profile.py`: CSV→metadata.yaml next to dataset, email + possible_pii, missing_fields, unsupported-format exit 1, source bytes unchanged |
| CLI | CLI-R03/R04 | `test_cli.py`: profile/render in `--help`, dispatch, help accuracy |

## Migration / Rollout

No data migration. Additive modules + constants + two subparsers; revert = drop the chain per-WU. `build_dataset_card`/`build_schema_report` signatures untouched (562 green).

## Work-Unit Breakdown (chained PRs)

Forecast ~1150 source + ~600 test lines ≫ 400-line budget.

- **Decision needed before apply: No**
- **Chained PRs recommended: Yes**
- **400-line budget risk: High**

| WU | Contents | Green proof |
|----|----------|-------------|
| WU1 | `config.py` (priors/thresholds/sample/rounding + `semantic_priors` dict-type validation) + `model.py` `InferenceStatus` + `pyproject.toml` | config/model tests; 562 pass |
| WU2 | `_patterns.py` + `semantic.py` + `test_semantic.py` | new tests |
| WU3 | `pii.py` (imports `_patterns`, adds `infer_pii_types`) + `test_pii.py` | new tests |
| WU4 | `metadata.py` (+ `METADATA_VERSION`) + `test_metadata.py` | new tests |
| WU5 | `profile.py` + `_cmd_profile` + `test_profile.py` + CLI | new tests |
| WU6 | `render.py` + `_cmd_render` + `test_render.py` + README | new tests |

Each WU: one PR targeting the previous WU's branch (feature-branch chain); autonomous, independently green and revertable.

## Open Questions

None — both resolved during design review:

- `--format` flag: **deferred**. Fase A supports only `yaml`; `profile`/`render` assume YAML and expose no `--format` flag. Introduce the flag only when a second serialization format is added (avoids a dead flag).
- `metadata_version`: resolved to the module constant `METADATA_VERSION = "1"` in `metadata.py` (MTA-02), never an inline literal.
