# Spec delta: fix-residual-parity

> Delta for requirement `codebook`. The canonical `openspec/specs/codebook/spec.md`
> carries CB-R01..CB-R09; this change adds CB-R10, mirroring the existing
> requirement/scenario block format.

## NEW Requirements

### Requirement: generate_all max_sample threading (CB-R10)

> Added by change `fix-residual-parity` (closes #155).

`codebook.generate_all` SHALL accept `max_sample: int | None = None` and SHALL
thread it into EVERY per-file codebook it emits — single-format files,
empty/headerless placeholders, and single-sheet and per-sheet `.xlsx` outputs
(CB-R09). `None` SHALL resolve to `config.CODEBOOK_MAX_SAMPLE` (from
`[tool.sofer] codebook_max_sample`, default `100_000`) at call time inside
`_build_markdown` — the same per-call resolution the single-file path uses
(CB-R08); no frozen literal. Each codebook SHALL analyse
`n = min(total_rows, max_sample)` rows and SHALL label the header
`**Analysed rows:** n (full scan)` when the file fits the cap, `(sample)` when
capped.

(Previously: `generate_all` accepted no `max_sample`; per-file codebooks always
analysed the full file, so `sofer_codebook_all` (MSP-R17) and
`codebook --all-files` could not cap — parity gap #155.)

#### Scenario: Override caps per-file analysis

- GIVEN a batch config with files whose row count exceeds the cap
- WHEN `generate_all(cfg, output_dir=out, max_sample=1)` runs
- THEN every emitted codebook SHALL show `**Analysed rows:** 1 (sample)`
- AND the cap SHALL apply identically to each per-file codebook, including
  per-sheet `.xlsx` outputs

#### Scenario: Omitted resolves to the config default at call time

- GIVEN `[tool.sofer] codebook_max_sample` set (or the default `100_000`) and
  batch files below the cap
- WHEN `generate_all` runs without `max_sample`
- THEN each codebook SHALL analyse up to the configured rows
- AND codebooks whose files fit SHALL report `(full scan)`, never a sample cap