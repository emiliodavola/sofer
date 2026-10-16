# Design — `2026-10-16-chore-321-name-the-timeout-tradeoff`

> **Change** `2026-10-16-chore-321-name-the-timeout-tradeoff` · issue **#321** · branch
> `fix/325-codex-home-and-321-delegation`.

## D1 — Keep the decline; reject option 1 on measurement

MCP-REG-05's clause stays exactly as it is: a registration carrying timeouts declines with the reason
`timeout` and falls back to the file edit, and `--no-timeout` restores delegation. What this change adds is
that the decline *says so*.

Option 1 was rejected because it cannot deliver its own premise, measured rather than argued:

| Fact | Source |
| --- | --- |
| TOML and JSON writes are whole-document rewrites; only YAML is spliced | `atomic_write`: `tomli_w.dump` / `json.dump` / `_yaml.splice_entry` |
| The patch replaces the `sofer` entry wholesale | `merge()` assigns `servers["sofer"] = desired` from `build_entry(...)` |

Together those mean the document after "delegate then patch" is byte-equivalent to the document the direct
file edit produces — so option 1 bought a `subprocess` and an extra `.bak` for nothing, and claim 1 stayed
broken.

## D2 — The hint must be *true*, and the predicate is exact

`--no-timeout` restores delegation only when `timeout` is the **sole** decline reason. Measured:

```text
native_delegation_decline_reasons("codex", [], "user", timeouts)          -> ['timeout']
native_delegation_decline_reasons("codex", ["HF_TOKEN"], "user", timeouts) -> ['env forwarding', 'timeout']
native_delegation_decline_reasons("codex", ["HF_TOKEN"], "user", None)     -> ['env forwarding']
```

So the message names the flag under `reasons == ["timeout"]` and stays silent otherwise. With an env key
present, `--no-timeout` clears only the second reason and delegation still declines; naming the flag there
would send the user to a flag that changes nothing. That is the same class of defect this batch has already
corrected three times — a body, a diagnosis and a proposal that were plausible and wrong — so it gets a
guard test of its own rather than a comment.

The `reasons == ["timeout"]` form is a fixed-order list from a single gate, so it is an exact predicate and
not a heuristic.

## D3 — The docs state the trade-off, not just the flag

`--no-timeout` is not merely "the pre-#287/#296 shape": it is **the only path where sofer does not rewrite
the config file**. That is the honest description of what a codex or gemini user is choosing between, and it
belongs in the flag's help and in both READMEs next to the flag, not only in the issue.

## D4 — No spec delta

The clause this change serves is kept, not reversed (proposal §4). The spec pins the decline and the reason
name; it does not pin the message wording. Nine archived changes carry no `specs/` delta.

## Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Option 1 as specified | D1: whole-document patch, so the result equals the direct edit. |
| Option 1 plus a surgical TOML splice | Would deliver claim 1, but adds a text-level writer over user config files (the highest-risk code here — a bad splice corrupts a config) for a benefit that cannot be verified without codex installed. It is its own change, and it should start by measuring codex's own behaviour. |
| Make `--no-timeout` louder in the docs only | Leaves the user to discover the trade-off by reading; the decline is where they actually meet it. |
| Name the flag unconditionally on any timeout decline | D2: false whenever an env key is present. |
| Silently decline, as before | The status quo #321 exists to remove. |
