# Spec delta: fix-residual-parity

> Delta for requirement `mcp-server`. Block format follows the repo's archived
> change specs (full requirement blocks, scenarios preserved/added). Requirement
> IDs continue from the active `fix-scan-parity-mcp` change (MSP-R14/R15); the
> canonical `openspec/specs/mcp-server/spec.md` still carries MSP-R01..R13.

## NEW Requirements

### Requirement: Publish cleanup (MSP-R16)

> Added by change `fix-residual-parity` (closes #153).

`sofer_publish` and `sofer_publish_confirm` SHALL accept `clean: bool = False`
and `clean_cache: bool = False`, forwarded verbatim to `publish.publish(...)`.
Cleanup SHALL follow PUB-11 and live in the domain: the build directory (hf
target) or the local destination is deleted ONLY after a successful delivery —
never on dry-run, quality-gate block, or failure. `clean_cache=True` without
`clean=True` SHALL be refused — never silently ignored — with `error_code`
`CLEAN_CACHE_WITHOUT_CLEAN` and a `next` hint to set `clean=True` (explicit
opt-in: a caller cannot enable cache deletion as a side effect).

#### Scenario: clean deletes the build after success and keeps cache/

- GIVEN a successful HF delivery with `clean=True, clean_cache=False`
- WHEN `sofer_publish_confirm` completes
- THEN the build directory SHALL be deleted
- AND `cache/` SHALL remain (tool-wide sibling-shared state untouched)

#### Scenario: clean_cache without clean is refused

- GIVEN `clean_cache=True` and `clean` omitted or `False`
- WHEN either publish tool runs
- THEN an `ok:false` refusal SHALL be returned with `error_code`
  `CLEAN_CACHE_WITHOUT_CLEAN`
- AND no directory SHALL be deleted
- AND the hint SHALL name `clean=True` as the fix

#### Scenario: Dry-run never deletes

- GIVEN `clean=True` on a dry-run call (default for `sofer_publish`)
- WHEN the tool runs
- THEN the result SHALL be a plan only
- AND no build or cache directory SHALL be deleted

### Requirement: Batch codebook max_sample (MSP-R17)

> Added by change `fix-residual-parity` (closes #155).

`sofer_codebook_all` SHALL accept `max_sample: int | None = None`, forwarded to
`codebook.generate_all(...)`. `None` SHALL resolve to
`[tool.sofer] codebook_max_sample` (default `100_000`) at call time — the same
resolution the single-file path uses (CB-R08); never a frozen literal. Each
per-file codebook SHALL cap analysis at `min(total_rows, max_sample)` and SHALL
label the header `**Analysed rows:** N (sample)` when capped, `(full scan)`
when the file fits.

#### Scenario: Override applies

- GIVEN a batch TOML config whose files exceed the cap
- WHEN `sofer_codebook_all(config, max_sample=1)` runs
- THEN every emitted codebook SHALL report `**Analysed rows:** 1 (sample)`
- AND the sampling cap SHALL apply to each per-file codebook

#### Scenario: Omitted uses the config default

- GIVEN `[tool.sofer] codebook_max_sample` configured (or its default) and
  files below the cap
- WHEN `sofer_codebook_all` runs without `max_sample`
- THEN the batch SHALL analyse up to the configured rows per file
- AND codebooks whose files fit SHALL report `(full scan)`