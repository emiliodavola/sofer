# Exploration: codebook dialect defaults moved out of the signatures (GitHub #260)

## Current State

`src/sofer/codebook.py` still hardcodes the CSV delimiter/encoding as default
parameter values, violating AGENTS.md rule 3 ("Any function that accepts a file
path should get its encoding/delimiter from config, not from a default
parameter"):

| Site | Signature |
|---|---|
| `_read_csv` (`codebook.py:65-68`) | `encoding: str = "utf-8-sig"`, `delimiter: str = ";"` |
| `_read_tsv` (`codebook.py:112-114`) | `encoding: str = "utf-8-sig"` |
| `_read_file` (`codebook.py:274-277`) | `delimiter: str = ";"`, `encoding: str = "utf-8-sig"` |
| `generate` (`codebook.py:399-404`) | `delimiter: str = ";"`, `encoding: str = "utf-8-sig"` |

Callers already work around the defaults by passing config explicitly:

- `cli.py:241-253` passes the post-reload `config.CSV_DELIMITER`/`config.CSV_ENCODING`.
- `mcp_server.py:1552-1558` passes the same per call.
- `generate_all` resolves `None` → `cfg.csv_delimiter`/`cfg.csv_encoding`
  (`codebook.py:522-523`).
- `profile.py:180,521` calls `_read_file` with **no** dialect for the
  non-CSV/TSV formats (parquet/xlsx/jsonl), relying on the literal defaults —
  the only production call sites that actually lean on them.

The `codebook` capability spec pins the debt in place: CB-R11 says
"`codebook.generate`'s parameter defaults ... SHALL remain unchanged" and
CB-R12 ends with "`codebook.generate`'s and `generate_all`'s parameter defaults
SHALL remain unchanged." `mcp-server` MSP-R10 already calls the literals the
"rule-3 debt in `codebook.generate`". So removing the literals is a spec change,
not a pure refactor — it is SDD.

## Affected Areas

- `src/sofer/codebook.py` — the four entry points; `generate_all` stays as-is
  (its `None` sentinel already resolves from the dataset `[meta]`).
- `src/sofer/profile.py` — the two non-streamed `_read_file` calls now pass the
  configured dialect (ignored by the parquet/xlsx/jsonl readers).
- `src/sofer/cli.py` — docstring/comment truth only; it already passes config.
- `tests/test_codebook.py`, `tests/test_config.py` — pass the dialect explicitly
  and pin the required-argument contract.
- `openspec/specs/codebook/spec.md` — CB-R11/CB-R12 amended.

## Approaches

1. **Required keyword arguments (recommended).** Remove the literal defaults;
   make `delimiter`/`encoding` required. A caller that omits them fails closed
   with `TypeError` instead of silently assuming `;`/`utf-8-sig`. This is what
   GitHub #260 asks for and is the strongest reading of rule 3.
2. **`None` sentinel → `config` resolution.** Keep the parameters optional but
   resolve `None` from `config` at call time (the `max_sample` pattern). Smaller
   diff, no test churn, but a caller that omits the dialect still silently
   inherits the config default — the trap #260 identifies is only narrowed, not
   closed.

## Recommendation

Approach 1. The maintainer's issue explicitly says "make them required ... and
fail-closed for any call site that relied on the default", and rule 3 names the
literal default as the defect. `generate_all` keeps its `None` sentinel because
its tier is the dataset `[meta]`, not a literal.

## Risks

- `codebook` has no per-file coverage floor (COV-01/COV-06 exclude it), and the
  four core modules are untouched, so the 100% gates are unaffected.
- `profile.py` gains two covered lines; its ≥90% floor row is exercised by the
  existing non-streamed profile tests.
- Direct library callers of `codebook.generate` break loudly (`TypeError`) — the
  intended fail-closed behaviour, documented in the docstring.

## Ready for Proposal

Yes.
