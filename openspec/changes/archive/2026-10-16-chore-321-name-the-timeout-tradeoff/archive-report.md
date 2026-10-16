# Archive report — `2026-10-16-chore-321-name-the-timeout-tradeoff`

> **Change** `2026-10-16-chore-321-name-the-timeout-tradeoff` · issue **#321** · branch
> `fix/325-codex-home-and-321-delegation` (from `fix/316-321-bug-chore-followups`) · store **hybrid**.
>
> **Status:** implementation complete; archived inside the delivering PR (AGENTS.md rule 15).

---

## 1. What landed

| File | Change |
| --- | --- |
| `src/sofer/cli.py` | the native-delegation decline names `--no-timeout`, **only when `timeout` is the sole reason**; the flag's `--help` states the trade-off instead of just the entry shape. |
| `tests/test_cli.py` | two tests: the hint appears when it is true, and is **absent** when it would be false. The second is a guard, passing before and after by construction. |
| `README.md`, `README_ES.md` | the `--no-timeout` row and the timeout paragraph state what the user is actually choosing between, and why doing both is not an option. |
| `openspec/changes/archive/2026-10-16-chore-321-name-the-timeout-tradeoff/` | proposal, design, tasks, this report. **No `specs/` delta** — §4. Archived late; see §7. |
| `#321` | the framing correction comment (`6221654849`). |

## 2. The decision this records

#321 asked for the trade-off #311 introduced to be re-considered. The maintainer's decision was to keep the
decline and make the trade-off honest, **not** to build the issue's option 1. This folder is the durable
record of why, because the reasoning is worth more than the change: option 1 was rejected on measurement,
and the measurements also correct the issue's own premises.

| Measurement | Consequence |
| --- | --- |
| `atomic_write` rewrites the whole document for TOML (`tomli_w.dump`) and JSON (`json.dump`); only YAML is a byte-level splice | Option 1's patch reformats the file anyway, so its claim 1 (comment preservation) is not delivered |
| `merge()` assigns `servers["sofer"] = desired` from `build_entry(...)` | The native writer's entry shape does not survive either; the final document equals the direct file edit's |
| `native_env` is `False` for every agent | Delegation already required `env_keys == []` before #311, so claim 1's population was already small |
| `codex` is not installed on this machine (only `opencode` and `pi`) | Claim 1's premise — that codex's own writer preserves comments — cannot be verified here, and neither can the benefit of a surgical splice |

## 3. What the decline now says, and when

The hint is conditioned on the gate's own output rather than on the shape of the request:

```text
native_delegation_decline_reasons("codex", [], "user", timeouts)           -> ['timeout']            -> hint shown
native_delegation_decline_reasons("codex", ["HF_TOKEN"], "user", timeouts) -> ['env forwarding', 'timeout'] -> hint withheld
native_delegation_decline_reasons("codex", ["HF_TOKEN"], "user", None)     -> ['env forwarding']     -> (no timeout decline)
```

With an env key present, `--no-timeout` clears only the second reason and delegation still declines, so
naming the flag there would send the user to a flag that changes nothing. Given that this batch has already
corrected three plausible-and-wrong statements — an issue body's diagnosis, an issue body's probe, and this
issue's own proposed fix — the false case gets a test rather than a comment.

## 4. Why there is no spec delta

MCP-REG-05's clause is **kept**: "a registration carrying timeouts MUST decline native delegation with the
reason `timeout` and fall back to the file edit … and `--no-timeout` MUST restore the delegation path". This
change makes the behaviour visible where a user meets it; it does not alter it. The spec pins the decline and
the reason name, not the message wording, and nine archived changes carry no `specs/` delta.

## 5. What this does not claim

- **Not** that the trade-off is gone. It remains: the entry carries a deadline, **or** codex/gemini write the
  entry themselves and sofer never touches the file. What changed is that the user is told, in the right
  place, and the docs stop implying that both are available.
- **Not** that claim 1 is fixed. Delivering it needs a surgical TOML splice: a text-level writer over user
  config files, which is the highest-risk code in this area and belongs in its own change — one that should
  begin by measuring codex's own writer on a host that has codex.
- **Not** a fix for `#320` (opencode's missing timeout key), a different defect on the same capability.

## 6. Verification gates

| Gate | Result |
| --- | --- |
| `uv run pytest tests/ -q` | **2238 passed, 9 skipped** — the #325 revision's 2236 plus the two tests this change adds |
| The hint test | RED before the implementation: stderr was `"  !  codex native mcp add cannot express timeout; falling back to file edit\n"`, with no `--no-timeout` |
| The guard test | Passing before and after by construction — it exists to fail if the hint is ever named when `env forwarding` is also a reason |
| `uv run ruff check` / `ruff format` | clean (pre-commit hooks on the commit) |
| `uv run mypy src/ scripts/` | clean (pre-commit hook) |
| `uv run pyright` | 0 errors (the 1 warning is the pre-existing `_tomli.py` one) |

## 7. Late archive, and what it corrects

#328 delivered this change and merged **without** the archive move AGENTS.md rule 15 requires, so the
folder sat at `openspec/changes/2026-10-16-chore-321-name-the-timeout-tradeoff/` on `dev`. That is the
rule's first bullet broken, and two more defects travelled with it: this folder's `tasks.md` still carried
`TT-8`, `TT-9` and `TT-10` as `pending` after all three were done, and the delivering PR body called a
non-archive path "Archived at…".

This commit closes all three: the folder moved to `openspec/changes/archive/`, the three rows now record
the work that had in fact been done, and this note exists so the correction is legible instead of silent.

The rule names this exact case, which is why it is worth the paragraph:

> Never open a second PR whose only purpose is to archive a change that already merged. By then the change
> is delivered, the archive is orphaned from its own diff, and the reviewer can no longer read the change
> and its record together — which is exactly what happened to the changes delivered by #276 and #279 and
> only archived later in #281.

The remedy taken here is the narrower reading of that prohibition: the archive travels with a commit whose
**declared purpose is closing the v0.7.0 durable record** — the archive move, the corrected task rows and
`odd/` — and the PR body says so rather than presenting it as an ordinary archive.

The cause is worth naming because it is the kind of mistake that repeats: I conflated *the change folder is
in the PR's diff* with *the change folder is in `archive/`*. A future reader of this folder is exactly who
would otherwise repeat it.
