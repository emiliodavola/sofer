# Design: OpenCode Env-Drop Warning for `sofer mcp add` (GitHub #147)

> **Change:** `2026-09-12-fix-mcp-opencode-env` · **Branch:** `fix/147-opencode-env-warning` (base `dev`).
> Closes the silent env-drop: `sofer mcp add --agent opencode` (and the opencode
> member of `--agent all`) now emits an informational stderr warning — names only,
> never values — when `HF_TOKEN` / `SOFER_MCP_APPROVAL_PHRASE` are present but the
> generated opencode entry cannot carry them. Warning + documentation only; the
> opencode entry shape stays `{type:"local",command:["sofer-mcp"],cwd}`.

## Technical Approach

Three additive changes and one pure refactor, all on already-contacted files:

1. **`mcp_registration.py` — single source for "which env names are dropped".**
   Extract the allow-list filter (the only place that knows `_ENV_KEYS`
   membership) into a private `_present_env_keys(env)`; add a public
   `dropped_env_keys(agent, env) -> list[str]` that returns the present known
   keys for opencode and `[]` for codex/gemini. Refactor `build_entry` so the
   codex `env_vars` and gemini `env` computations consume `_present_env_keys`
   instead of re-typing `[k for k in _ENV_KEYS if env.get(k)]` — output is
   byte-identical (existing `TestEnvForwarding` tests are the regression proof).
   `cli.py` then formats the warning from the returned **names** and never
   hardcodes env knowledge (AGENTS.md §1, §4).
2. **`cli.py` — the warning.** Inside the per-agent loop of `_cmd_mcp_add`,
   immediately after the agent is cast and **before** `probe_native` and the
   `dry_run` branch, print one stderr line (existing `!` informational
   prefix) when `dropped_env_keys` returns a non-empty list. Informational:
   `overall` (exit code) is untouched; stdout registration output is untouched.
3. **`cli.py` — help text.** Append one ASCII-only sentence to the
   `mcp add` argparse `description=` covering codex/gemini names-only forwarding
   and the opencode no-env warning (AGENTS.md §7; issue #161: no U+2192 or other
   non-cp1252 characters in new help text).
4. **`README.md` + `README_ES.md` — one additive sentence each** (same commit,
   AGENTS.md §13) describing the warning, appended to the existing **Env** bullet.
   The manual `environment`-literal alternative and the "opencode receives no
   env" fact are **already documented** (verified README.md:619-621/682-685,
   README_ES.md:652-654/717-720) — verify-only, no re-documentation (AGENTS.md §4).
5. **Tests** — five new runtime tests in `tests/test_mcp_registration.py`
   (`TestEnvForwarding`) and one new help test in `tests/test_cli.py`
   (`TestMcpCliHelp`), each mapped to its spec scenario (see Testing Strategy).

## Architecture Decisions

### Decision: Public `dropped_env_keys(agent, env)` + private `_present_env_keys(env)`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| One public `dropped_env_keys` that re-typos `[k for k in _ENV_KEYS if env.get(k)]` | Duplicates the allow-list filter already in `build_entry` → drift risk (AGENTS.md §4) | Reject |
| Extract `_present_env_keys` (single filter expression) + public `dropped_env_keys` composing it; refactor `build_entry` to consume `_present_env_keys` | One place owns `_ENV_KEYS` membership; codex/gemini outputs byte-identical; opencode return value untouched | **Accept** |

**Signature (both in `src/sofer/mcp_registration.py`, near `collect_env`):**

```python
def _present_env_keys(env: Mapping[str, str]) -> list[str]:
    """Known env keys from ``_ENV_KEYS`` present (non-empty) in *env*.

    Single source for which of ``HF_TOKEN`` / ``SOFER_MCP_APPROVAL_PHRASE``
    are set in the environment. NAMES only — values are never returned.
    """

def dropped_env_keys(agent: AgentName, env: Mapping[str, str]) -> list[str]:
    """Known env NAMES that would be dropped for *agent*.

    opencode entries cannot carry env, so every present known key is dropped;
    codex/gemini forward names (``env_vars`` allow-list / ``env`` ``$KEY``
    refs), so nothing is. Reads *env* keys only; returns NAMES never values.
    Returns ``[]`` (not ``None``) when nothing is dropped.
    """
```

- `env` is typed `Mapping[str, str]` (read-only) so the helper's contract is
  "name-presence query, never value sink". The values that `collect_env()` put
  in the dict are never referenced: `_present_env_keys` uses `env.get(k)`
  truthiness only, matching `collect_env`'s present-and-non-empty semantics.
- Return `[]` instead of `None`: falsy, so `if dropped:` works in the CLI and in
  tests without `Optional` gymnastics.
- `build_entry` refactor: codex leg becomes `env_vars = _present_env_keys(env)`;
  gemini leg becomes `env_refs = {k: f"${k}" for k in _present_env_keys(env)}`.
  Docstring updated: state that the opencode selection-time warning is the CLI's
  responsibility and that the opencode entry stays env-less.

### Decision: Warning text — one stderr line, stable substrings, cp1252-safe, values never included

```python
print(
    f"  !  opencode registration receives no env: {', '.join(dropped)} "
    "not forwarded. See README for the launcher environment or an explicit "
    "'environment' literal in opencode.json.",
    file=sys.stderr,
)
```

- Prefix `!` matches the file's existing informational convention
  (`_cmd_mcp_remove` fallback message); fatal stays `X` — the warning is not
  a gate.
- Stable substrings tests assert (exact, in the string above):
  - no-env statement: `"receives no env"` (echoes README's "no env" wording);
  - README pointer: `"See README"`;
  - names, joined in `_ENV_KEYS` order: `"HF_TOKEN, SOFER_MCP_APPROVAL_PHRASE"`.
- ASCII-only: no arrows, no em-dashes, single quotes around `'environment'` for
  console safety (issue #161 applies to console-rendered text, and stderr is
  console-rendered on Windows).
- Values can never appear: the string interpolates only `dropped` names (from
  `_ENV_KEYS`) plus fixed literals; no `env.values()` ever reaches the format.

### Decision: Placement — top of the per-agent loop, before `probe_native` and the dry-run branch

```python
for agent in agents:
    _agent = cast(_AgentName, agent)
    dropped = mcp_registration.dropped_env_keys(_agent, env)   # NEW
    if dropped:
        print(<warning>, file=sys.stderr)                       # NEW
    if mcp_registration.probe_native(_agent, timeout=3.0):      # unchanged
        ...
    if dry_run:                                                 # unchanged
        ...
```

- **`--agent opencode` and `--agent all`:** the loop runs the opencode member
  exactly once; the warning fires exactly once. codex/gemini members return
  `[]` from the helper → silent (spec: "warning fires for the opencode member
  only").
- **Before `probe_native`:** opencode's probe hard-returns `False` (file-edit
  path always runs), but top-of-loop placement is still the single correct
  point — it also covers the (theoretical) fallback branch and costs nothing
  for codex/gemini.
- **Before the `if dry_run:` branch:** the warning precedes the preview print,
  so it appears in real runs AND `--dry-run`, satisfying MCP-REG-03's dry-run
  scenario without touching the `drry_run` guard's no-write/no-`.bak` contract.
- **Idempotent reruns:** the `changed == False → "already registered" → continue`
  path is *after* the warning, so a repeat run with env set still warns. This is
  intentional and truthful: the already-written entry equally carries no env.
- **Exit code:** the print never touches `overall`; the function returns it
  unchanged (0/1 exactly as today). `_cmd_mcp_add` docstring updated to
  document the warning as an orchestration step (AGENTS.md §2).
- **Message-string style:** follow the file's existing convention — inline
  f-strings, no new module-level constants (the only cli.py constant today is
  `_INIT_TEMPLATE`; none of the ~25 stderr messages use constants). Test
  assertions target stable substrings, not full-string equality, bounding drift
  risk.

### Decision: Help text — one appended ASCII sentence to the `add` description

Append to the `mcp_add` parser `description=` (cli.py ~L1471-1480):

```
"Env: codex and gemini receive env forwarding (names only, values never "
"written); opencode entries carry no environment, and a warning is printed "
"on stderr when HF_TOKEN or SOFER_MCP_APPROVAL_PHRASE are set with "
"--agent opencode (or all)."
```

- Text matches the CLI-R09 spec wording so spec ⇄ help ⇄ test stay aligned.
- Stable substrings for `test_mcp_add_help_env_forwarding`:
  `"codex and gemini receive env forwarding (names only)"` and
  `"opencode entries carry no environment"`.
- ASCII-only (no U+2192, no em-dash — issue #161). Backtick style follows the
  existing description (doubled backticks are already used); new sentence uses
  none for flag names since `--agent` reads fine in plain text.
- Existing `test_mcp_add_help_flags` (flags listed) is unaffected — no flag is
  removed or renamed.

### Decision: README delta — verify existing coverage, add one warning sentence per file

Verified already present (do not rewrite):

- README.md:619-621 **Env** bullet: "Opencode receives no env."
- README.md:682-685 manual alternative: launcher environment / explicit
  `environment` literal (plaintext on disk).
- README_ES.md:652-654 / 717-720 — mirrored Spanish.

Additive sentence (same commit, AGENTS.md §13), appended to the **Env** bullet:

- EN: "When `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set and `--agent opencode`
  (or `all`) is chosen, `sofer mcp add` prints a warning on stderr naming the
  dropped variables and leaves the exit code unchanged."
- ES: "Cuando `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` están definidas y se elige
  `--agent opencode` (o `all`), `sofer mcp add` muestra una advertencia en
  stderr con los nombres de las variables descartadas y deja el código de salida
  sin cambios."

Technical content (env var names, flags, `stderr`, exit-code wording) stays
English in both files; only prose is translated.

## Data Flow

```
_cmd_mcp_add(args)
│  env = mcp_registration.collect_env()            # present non-empty known keys
│  overall = 0
│  for agent in [opencode, codex, gemini] (or single):
│  │  dropped = dropped_env_keys(agent, env)
│  │  ├─ agent == opencode and env → [HF_TOKEN, SOFER_MCP_APPROVAL_PHRASE…]
│  │  │   → print "  !  … receives no env: … See README …" → stderr   [NEW]
│  │  └─ codex/gemini → [] → silent
│  │
│  ├─ probe_native? → delegate_add? → OK delegated → continue
│  ├─ read_config → build_entry → merge
│  │   ├─ unchanged → "OK already registered" → continue   (warning already shown)
│  │   └─ changed + dry_run → "DRY RUN Would register …" → continue  (warning already shown)
│  │   └─ changed + real   → backup → atomic_write → "OK registered"
│  └─ overall = 0 if all agents OK else 1               (warning never affects it)
└─ return overall
```

## File Changes

| File | Action | Description |
| ------ | -------- | ------------- |
| `src/sofer/mcp_registration.py` | Modify | Add private `_present_env_keys(env)` and public `dropped_env_keys(agent, env)` near `collect_env` (L441-451); refactor `build_entry` codex/gemini legs (L161-165) to consume `_present_env_keys`; update `build_entry` docstring (env-forwarding contract + opencode warning contract); module docstring unchanged (already documents names-only persistence). |
| `src/sofer/cli.py` | Modify | `_cmd_mcp_add` (L605-719): add `dropped`/warning block at top of per-agent loop (after L661 `_agent = cast(...)`, before `probe_native` at L672); update `_cmd_mcp_add` docstring with the warning step; append env-forwarding sentence to `mcp add` description (L1471-1480). |
| `README.md` | Modify | One additive sentence in the **Env** bullet (after L621). |
| `README_ES.md` | Modify | One additive sentence in the **Env** bullet (after L654), prose mirrored. |
| `tests/test_mcp_registration.py` | Modify | 5 new tests in `TestEnvForwarding` (after L481): `test_opencode_warning_env_present`, `test_opencode_warning_dry_run`, `test_opencode_warning_all_once`, `test_no_warning_without_env` + `test_no_warning_codex_gemini_env`, `test_warning_values_never_leak`. |
| `tests/test_cli.py` | Modify | 1 new test in `TestMcpCliHelp` (after L1196): `test_mcp_add_help_env_forwarding`. |

No files deleted, no new files. `mcp_server.py`, `delegate_add`, `_ENV_KEYS`,
the opencode entry shape, and the `--agent all` 3-agent expansion are untouched.

## Interfaces / Contracts

- `dropped_env_keys(agent: AgentName, env: Mapping[str, str]) -> list[str]` —
  opencode → present non-empty keys from `_ENV_KEYS` (names only); codex/gemini
  → `[]`. Never `None`; never reads or returns values.
- `_present_env_keys(env: Mapping[str, str]) -> list[str]` — private; the single
  `_ENV_KEYS` membership filter (`[k for k in _ENV_KEYS if env.get(k)]`).
- Warning line (stderr, one line, `!` prefix) — exact text in the
  "Warning text" decision above; stable substrings `"receives no env"`,
  `"See README"`, and the joined names.
- `sofer mcp add` help description — appended sentence exact text in the "Help
  text" decision above.
- Exit code / stdout: unchanged in every path (informational only); `--dry-run`
  still creates no file and no `.bak`.
- opencode entry invariant: `mcp.sofer={type:"local",command:["sofer-mcp"],cwd}`
  byte-identical; no env name or value in `opencode.json`.

## Testing Strategy

| Spec scenario | Test | Approach |
| --------------- | ------ | ---------- |
| MCP-REG-03: warning when opencode chosen with env set | `test_opencode_warning_env_present` (TestEnvForwarding) | `capsys` captures stderr; assert `"receives no env"`, `"See README"`, `"HF_TOKEN"`, `"SOFER_MCP_APPROVAL_PHRASE"` present; rc == 0; `opencode.json` entry == `{type:"local",command:["sofer-mcp"],cwd}` with no `env` key |
| MCP-REG-03: warning previewed in dry-run | `test_opencode_warning_dry_run` | `--dry-run` with `HF_TOKEN` set → warning on stderr; no file, no `.bak` |
| MCP-REG-03: one warning for opencode member of `all` | `test_opencode_warning_all_once` | `--agent all` + env set → exactly one warning line on stderr; codex/gemini files contain names only; `all` still expands to 3 agents |
| MCP-REG-03: no warning without env / for forwarding agents | `test_no_warning_without_env` + `test_no_warning_codex_gemini_env` | env absent → stderr has no `"receives no env"`; codex/gemini with env → no warning, `env_vars`/`env` names-only persisted |
| MCP-REG-03: values never leak | `test_warning_values_never_leak` | `HF_TOKEN=hf123`, `SOFER_MCP_APPROVAL_PHRASE=phrase123`; assert `hf123`/`phrase123` absent from captured stdout+stderr and from any written file (real and dry-run) |
| CLI-R09: add help documents env forwarding | `test_mcp_add_help_env_forwarding` (TestMcpCliHelp) | `parse_args(["mcp","add","--help"])` → assert `"codex and gemini receive env forwarding (names only)"` and `"opencode entries carry no environment"` in help output |

Test harness notes: runtime tests use the existing `TestEnvForwarding` pattern
(`monkeypatch.chdir(tmp_path)`, stub `probe_native` → `False`,
`validate_cwd` → `True`, explicit `setenv`/`delenv` for `HF_TOKEN` /
`SOFER_MCP_APPROVAL_PHRASE` so results don't depend on the runner's own
environment), plus `capsys` for stderr. Regression: the full suite must stay
green — `uv run pytest tests/ -q` (baseline 1501/1495/6), `uv run ruff check
src/ tests/`, `uv run mypy src/`. Existing `TestEnvForwarding` gemini/codex
tests are the byte-identical-output proof for the `build_entry` refactor; the 6
existing dry-run/delegation/remove tests must pass unmodified.

## Migration / Rollout

No migration, no data, no config-format change. The change is additive
(warning print + docstring line, help sentence, one README sentence per file,
new tests). Revert of the PR cleanly restores prior behavior; `build_entry`'s
opencode return is unchanged, so removing the helper leaves entry generation
byte-identical with no `.bak`/format coexistence concern. README.md and
README_ES.md must revert together (AGENTS.md §13); runtime warning and help text
revert with `cli.py`. Rollout order within the PR: `mcp_registration.py` helper
→ `cli.py` warning + help → tests → README pair in the same commit.

## Open Questions

- **Warning under `--agent all` (proposal assumption 1, flagged for the review
  gate):** the design warns once for the opencode member of `all` when env is
  set. If the parent prefers suppressing the warning under `all`, that is a
  one-line deviation (`if dropped and raw_agent != "all"`).
- **Warning on idempotent reruns:** decided *yes* (the registered entry equally
  carries no env); alternative is to only warn when `changed` is true. Flagged
  so the reviewer can veto.
- **`delegate_add` env gap (out of scope, follow-up candidate):** native
  `codex mcp add` / `gemini mcp add` still ignore `env_keys` (signature parity,
  `delegate_add` L380-413). Not changed here (#147 scope); tracked as a follow-up
  issue candidate, not silently fixed.
- **cp1252 help-text guard:** the added help sentence is ASCII-only; if future
  non-ASCII characters are ever needed in argparse text, issue #161's constraint
  must be revisited (out of scope here, referenced only).
