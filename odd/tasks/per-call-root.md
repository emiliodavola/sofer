# ODD feature: per-call containment root (#347)

Branch: `feat/347-per-call-root` (stacked on `feat/344-file-entry-tool`). Delivery: one PR assigned to the maintainer. Test runner: `uv run pytest tests/ -q`.

## Specs

Source: issue #347 v3 is the implementation contract (pinned decisions P0–P9 and behaviour matrix B1–B18). This record does not restate it; it records the deltas this branch must honour.

- **S1** — Every path-bearing tool accepts `root: str | None = None` as its last parameter (P1 description verbatim). Omitted/blank is unset and behaves byte-identically to today. The roster is 19 callables; path-bearing are 18 (`sofer_report_failure` is excluded, P0) — the #344 addition (`sofer_file_set`) is path-bearing and carries `root` too.
- **S2** — One context variable plus one decorator applied at each `def`: `_get_root()` prefers the per-call root, then `_SERVER_ROOT`, then the resolved cwd. The decorator never pops `root`; the body never reads it (P2).
- **S3** — `_resolve_call_root` mirrors the contract: `expanduser`, relative anchored on the registration root (never the ambient cwd), `resolve()`, must exist and be a directory, then the allowlist. Failures raise `RootUnavailableError(MCPToolError)`; the 10.3 enum is untouched (P7).
- **S4** — Registrations are explicit or legacy. `why: explicit`; `when: agent`; `skill: none`.
- **S5** — `SOFER_MCP_ROOT_ALLOWLIST` is read once in `build_server`, split on `os.pathsep`, entries resolved; the registration root and omitted-`root` calls are never gated (P4/P5). Out of scope: propagating it through `sofer mcp add`/doctor.
- **S6** — Every dict envelope gains `effective_root` through one central stamp; a bound `next.arguments` gains `root` only when the effective root differs from the registration root (P6). ~47 return sites stay untouched.
- **S7** — `_ERROR_ENVELOPE_SCHEMA_FIELDS` declares `effective_root` (one edit reaches all 19 output schemas; `required` unchanged). Every path-bearing input schema grows `root` purely from the signature.
- **S8** — Containment refusal text keeps the prefix `"<what> resolves outside the server root"` and appends `" (within <effective root>)"` where the raise site knows it (already true from #343; this branch must not reword it).
- **S9** — Not touched: `workflow.py` (except the #344 registry entry already merged), `execution_context.py`, resources, the 10.3 enum, the publish ladder, `sofer_report_failure`, `_contained_path`'s algorithm. Resource access to another dataset is documented as a tool workaround.
- **S10** — Cross-platform correctness by construction (resolve-on-both-sides, `os.pathsep` only); the CI matrix stays `ubuntu-latest` × `windows-latest`. Tests are OS-portable, platform-shape cases behind `skipif` with a reason.

## Tasks

- T1 (inline) — core: `_EFFECTIVE_ROOT`, `_registration_root`, `_resolve_call_root`, `_resolve_root_allowlist`, `RootUnavailableError`, `_with_call_root`, `_stamp_envelope`, `build_server` allowlist read, `_get_root` chain. Evidence: unit tests for resolution + stamp.
- T2 (inline) — apply the decorator and `root` parameter to the 18 path-bearing tools; add `effective_root` to the envelope schema fields.
- T3 (inline) — behaviour matrix tests (B1–B18 subset), isolation, allowlist, continuations, schema coverage.
- T4 (inline) — instructions, README/README_ES, spec MSP-R21 + MSP-R03/MSP-R13 deltas, feature record; full suite + type gates; commit.

## Log

- **L1** (user, verbatim): the batch request — sync/prune, verify issues, roadmap, branch + PR per issue, ODD, no SDD.
- **L2** (issue #347, verbatim excerpt): "A registration-time containment root cannot follow the agent: accept a per-call `root` argument". v3 pins P0–P9 and B1–B18; the operator's cross-platform mandate and the macOS-CI discard are recorded there.
- **L3** (decision): roster amendment — the contract was written against 17 path-bearing tools at `main@13efbe1`; #344 adds `sofer_file_set` before this branch, so it grows `root` and the path-bearing roster is 18 of 19 (P0 + file_set; report_failure still excluded).
- **L4** (decision): implementation order is a linear stack (#343 → #344 → #347) so the PRs are reviewable; the #343 refusal text and `server_root` field are already in the base and are extended, not duplicated.
