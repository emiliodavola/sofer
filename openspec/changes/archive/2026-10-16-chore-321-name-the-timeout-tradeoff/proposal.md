# Proposal — `2026-10-16-chore-321-name-the-timeout-tradeoff`

> **Change** `2026-10-16-chore-321-name-the-timeout-tradeoff` · issue **#321** · branch
> `fix/325-codex-home-and-321-delegation` (from `fix/316-321-bug-chore-followups`) · store **hybrid**.
>
> **Status:** implementation complete; archived inside the delivering PR (AGENTS.md rule 15).

## 1. Intent

#321 filed the trade-off #311 introduced — native codex/gemini delegation now declines because neither
`<agent> mcp add` can write the timeout keys, and `--no-timeout` is the only way back — and asked for it to
be re-considered rather than lost in a 1 800-line diff. The maintainer's decision was to keep the decline
and make the trade-off honest and visible instead of building the issue's option 1.

This change is that decision, and the record of why option 1 was rejected. The rejection is the substance:
it rests on measurements, not on preference, and the measurements contradict the option's own premise.

## 2. Why option 1 was rejected

Option 1 was "let the native CLI write the entry, then add the timeout keys to the `sofer` entry in the same
file". Measured:

- **`atomic_write` is a whole-document rewrite for TOML and JSON.** `tomli_w.dump(doc, fh)` for codex,
  `json.dump(doc, fh, indent=2)` for gemini; only YAML is a byte-level splice
  (`_yaml.splice_entry(pre_write, ...)`). So the patch that followed a native write would reformat the file
  anyway — option 1 could **not** deliver #321's claim 1 ("users who relied on delegation to keep their
  `config.toml` intact").
- **The patch also replaces the `sofer` entry wholesale.** `merge()` builds `desired` from
  `build_entry(agent, cwd, env, timeouts)` and assigns it, so the native writer's entry shape does not
  survive either. The final document is therefore **identical to the one the direct file edit produces**.
- Option 1 would have added a `subprocess` call and an extra `.bak` for **no user-visible difference**.

A surgical TOML splice would have delivered claim 1, and it was offered as an alternative. It was not taken
because it adds a text-level writer over *user config files* — the highest-risk code in this area, since a
bad splice corrupts someone's config — to chase a benefit that cannot be verified here: **`codex` is not
installed on this machine** (checked; only `opencode` and `pi` are), so whether codex's own writer preserves
comments is unknown. If it does not, claim 1 was never real, not even before #311.

Two corrections to the issue's framing are recorded on the issue itself:

- **Claim 1 was already narrower than stated.** `native_env` is `False` for *every* agent, so delegation
  already required `env_keys == []` before #311: any present `HF_TOKEN` sent codex through the file edit
  then too. Only users with no known env key present ever got delegation.
- **The premise is unverified.** "Users who relied on delegation to keep their `config.toml` intact" assumes
  codex's writer preserves the file; that is not established anywhere in the repository.

## 3. Scope

- `src/sofer/cli.py`: the decline message names `--no-timeout` **only when `timeout` is the sole reason**,
  and the flag's `--help` states the trade-off (it is the only path where sofer does not rewrite the file).
- `README.md`, `README_ES.md`: the `--no-timeout` row and the timeout paragraph state the same, including
  why the trade-off cannot be avoided by doing both.
- The `#321` correction comment (§2).

## 4. Why this carries no spec delta

MCP-REG-05's clause is **kept, not reversed**: "a registration carrying timeouts MUST decline native
delegation with the reason `timeout` and fall back to the file edit … and `--no-timeout` MUST restore the
delegation path". This change makes the existing behaviour visible at the point a user meets it; no clause
changes, and the spec does not pin the message wording. Nine archived changes carry no `specs/` delta.

## 5. Non-goals

- **Option 1 of the issue**, for the reasons in §2.
- **A surgical TOML writer.** If comment preservation is worth it, that is its own change, and it should
  start by measuring codex's own behaviour on a host that has codex.
- **`#320` (opencode's missing timeout key)**, which is a different defect on the same capability.
