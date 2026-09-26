# Proposal: 2026-09-25-csv-dialect-override

**Change:** `2026-09-25-csv-dialect-override` · **Issue:** #204 `type:feature`
· **Branch:** `feat/204-csv-dialect-override` (base `dev@e9d5101`, PR-only)

## Intent

Add an **optional explicit CSV dialect override** so a human or an agent can state
the delimiter/encoding for a single invocation instead of relying on the resolved
config. The explicit value **wins over config**; when omitted, nothing changes —
`[tool.sofer]`, dataset `[meta]`, and the existing reader fallback behave exactly as
they do today.

The issue's own evidence table (244 `DatasetConfig(` constructions, MSP-R10, CB-R11)
rules out making the dialect mandatory, so this is the purely additive form.

## Scope

### In Scope

- `src/sofer/cli.py`: optional `--delimiter` / `--encoding` on `codebook` and
  `profile` (single-file and `--all-files`); explicit-wins resolution; a stderr
  echo of the explicit dialect; updated `help=` text.
- `src/sofer/mcp_server.py`: optional `delimiter` / `encoding` on
  `sofer_codebook`, `sofer_codebook_all`, `sofer_profile`, `sofer_profile_all`;
  explicit-wins resolution; a `dialect` envelope field when supplied; parameter
  descriptions stating the fallback.
- `src/sofer/profile.py`: optional `delimiter` / `encoding` parameters on
  `profile` / `generate_all_profiles` / `_read_dataset_for_profile`; `None`
  keeps today's `config.CSV_*` resolution.
- `codebook.py` needs **no** change: `generate` already takes the reader dialect
  and `generate_all` already resolves `None` → `cfg.csv_*`.
- Tests: `tests/test_cli.py`, `tests/test_mcp_server.py`,
  `tests/test_mcp_schema.py` (schema/description), `tests/test_profile.py`.
- Docs: `README.md` + `README_ES.md` (rule 13).
- Specs: `codebook` (CB-R12), `profile` (PRF-07), `cli` (CLI-R12),
  `mcp-server` (MSP-R18) deltas.

### Out of Scope

- **Making the dialect mandatory anywhere** — rejected in the issue.
- The `prepare` conversion tier (issue **#181**) and the latent defaults in
  `repo_compliance.py` (issue **#202**).
- `scan` (CLI and MCP): it never parses CSV bytes, so a dialect parameter would
  be inert. The design substitutes `profile` — the actual second content-reading
  surface — for the issue's "scan tools" mention.
- `validate` / quality-check reads, changes to config tiers (TC-02/TC-04),
  and serialization of any dataset/agent call shape.

### New Capabilities

None. Four existing capabilities gain one requirement each.

## Approach

Resolution order, identical on both surfaces:

```
explicit flag/parameter  →  configured value  →  existing reader fallback
```

The configured tier is the one each command already uses: single-file
`codebook`/`profile` read the tool-wide post-reload `config.CSV_DELIMITER` /
`config.CSV_ENCODING`; the batch (`--all-files` / `_all`) tier reads the dataset
`[meta]` `cfg.csv_delimiter` / `cfg.csv_encoding` (which itself falls back to the
tool-wide values). An explicit value is placed **above** whichever tier applies.

`None` (argparse default / MCP default) is the only "not supplied" sentinel, so the
omitted path reuses the exact code it uses today — byte-identical output by
construction, pinned by at least one omitted-case test per surface.

`.tsv` stays tab-delimited by format; the explicit delimiter applies to `.csv`, and
the explicit encoding applies to `.csv` and `.tsv`. This mirrors the existing
`_read_tsv` behaviour and is documented in the flag help.

Traceability: the CLI prints the supplied override to **stderr**
(`  i  Explicit dialect: delimiter=',' encoding='utf-8'`) so `codebook` stdout stays
pure markdown; the MCP tools add an optional `"dialect"` key to their envelope.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/cli.py` | Modified | Two flags on two subparsers; explicit-wins resolution; stderr echo; help |
| `src/sofer/profile.py` | Modified | Optional dialect params threaded to the streamed read |
| `src/sofer/mcp_server.py` | Modified | Four tools gain two optional params, `dialect` envelope, descriptions |
| `README.md`, `README_ES.md` | Modified | New flags and precedence |
| `openspec/specs/{codebook,profile,cli,mcp-server}/spec.md` | Modified | CB-R12, PRF-07, CLI-R12, MSP-R18 |
| `tests/*` | Modified | Precedence, explicit-disagrees-with-config, omitted-unchanged |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Omitted path drifts (not byte-identical) | Low | `None` sentinel; omitted-case test per surface; existing suite unchanged |
| `cli.py` 100% per-file coverage (rule 14) regresses | Med | Every new branch (flag present/absent, echo variant) gets a test |
| MCP schema tests pinned exact properties | Low | New params optional + described; no `required` change |
| A batch override silently mis-splits mixed-dialect files | Low | Batch override is explicit opt-in; dataset `[meta]` stays the default |
| Reader gets an unknown codec | Low | Existing `LookupError`/`ValueError` diagnostics unchanged |

## Rollback Plan

Revert the change. No persisted state or migration is involved; omitting the new
flags/params is today's behaviour, so a revert touches nothing downstream.

## Dependencies

None new. Reuses the existing `codebook.generate` / `generate_all` dialect
parameters and the `stream_csv` encoding fallback chain.

## Success Criteria

- [ ] `--delimiter` / `--encoding` exist on `codebook` and `profile` (both tiers);
  when supplied they win over config; when omitted the output is byte-identical.
- [ ] `delimiter` / `encoding` exist on the four MCP tools with the same
  precedence; descriptions state the fallback; envelope echoes the override.
- [ ] Tests cover precedence, explicit-disagrees-with-config, and the omitted case.
- [ ] `cli.py` 100% line coverage, no `# pragma: no cover`.
- [ ] README + README_ES + help updated; specs synced; quality gates green.
