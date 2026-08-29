# Proposal: fix-quality-encoding-xlsx

## Intent

`QualityValidator.run()` runs `encoding_validation` + `stream_csv` on every `[[file]]` without a format guard. Binary `.xlsx`/`.parquet`/`.jsonl` fail UTF-8 decode, emit `fail` findings, and block `sofer publish`. `prepare.py` gates on suffix; quality must align to CSV/TSV-only.

## Scope

### In Scope
- `TEXT_SUFFIXES = {".csv",".tsv"}` + `is_text_eligible(path)` in `src/sofer/_formats.py`
- Guard `QualityValidator.run()` loop to skip non-eligible files; defensive early-returns in `_check_encoding_validation()` and `_process_file()`
- Fix `ran_checks` so skipped binary-only datasets do not show spurious "ran"
- Delta spec for `data-quality` §4.9: scope all P0 checks to CSV/TSV, clarify UTF-8-only chain, add binary-skipped scenarios
- Tests for `.xlsx`/`.parquet`/`.jsonl` skipped, `.tsv` included, case-insensitive, no-extension skipped, `ran_checks` correctness

### Out of Scope
- Re-adding `latin-1`/`cp1252` to `ENCODING_FALLBACKS`
- Magic-byte / NUL sniffing
- Config-driven allowlist (`[tool.sofer] quality_eligible_suffixes`)
- Changes to `prepare.py` staging or `repo_compliance.py`
- Compressed CSVs (`.csv.gz`)

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `data-quality`: scope §4.9 and all P0 checks to CSV/TSV; add binary-skip scenarios; document UTF-8-only enforcement

## Approach

Suffix allowlist via `_formats.py` (exploration Approach 1). `TEXT_SUFFIXES: frozenset[str]` + `is_text_eligible` on `path.suffix.lower()`. In `run()`: `if not is_text_eligible(resolved): continue` after `exists`/`is_dir`. Guards in helpers for direct-call safety. No `[tool.sofer]` key — invariant, not preference. Keep `ENCODING_FALLBACKS = ["utf-8-sig","utf-8"]`; `ValueError` stays as safety net for mislabeled `.csv`. `.csv.gz` → `.gz` → skipped via `.suffix`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/_formats.py` | Modified | Add `TEXT_SUFFIXES` + `is_text_eligible()` |
| `src/sofer/quality.py` | Modified | Guard `run()`; guards in helpers; fix `ran_checks` |
| `openspec/specs/data-quality/spec.md` | Modified (delta) | Scope §4.9 + P0 checks to CSV/TSV |
| `tests/test_quality.py` | Modified | Skipped-binary + `.tsv` + `ran_checks` cases |
| `src/sofer/_csv_reader.py` | Referenced | Unchanged; UTF-8-only stays |
| `src/sofer/prepare.py` | Referenced | Pattern source; no change |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Forgetting `.tsv` | Low | Constant + explicit `.tsv` test |
| Case sensitivity (`.XLSX`) | Med | `.suffix.lower()`; upper-case tests |
| `ran_checks` wrong on xlsx-only dataset | Med | Only add to `ran_checks` when eligible; test binary-only |
| Mislabeled `.csv` with ZIP bytes fails | Low | Intended; `ValueError` safety net |

## Rollback Plan

Revert single commit on `fix/quality-encoding-xlsx`. No migration or data cleanup. Gate reverts to prior binary-failing behavior.

## Dependencies

- None. No new dependency, no config, no README sync.

## Success Criteria

- [ ] `sofer publish --target local` with 2 `.xlsx`: 0 failed quality findings
- [ ] `.csv`/`.tsv` still fully checked (encoding + streaming unchanged)
- [ ] `.xlsx`/`.parquet`/`.jsonl` (any case) emit no `encoding_validation` finding
- [ ] `uv run pytest tests/ -q` and `uv run mypy src/` pass
