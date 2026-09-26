# Explore: 2026-09-25-fix-mcp-native-delegation

## Question

#167 and #232 both report that the native `codex`/`gemini` delegation path in
`sofer mcp add/remove` silently produces a registration different from the
file-edit fallback. Can one mechanism fix both without two ad-hoc patches?

## Findings (re-derived on `dev@8d2f5eb`)

- Call sites: `cli._cmd_mcp_add` (`src/sofer/cli.py:697`) calls
  `delegate_add(_agent, cwd_resolved, list(env.keys()))` and `continue`s on
  success; `_cmd_mcp_remove` (`src/sofer/cli.py:775`) calls `delegate_remove(agent)`.
- `mcp_registration.delegate_add` (`src/sofer/mcp_registration.py:461`) ignores
  `env_keys` and emits `<exe> mcp add sofer --command sofer-mcp --cwd <cwd>`;
  `delegate_remove` (`:492`) emits `<exe> mcp remove sofer`. Neither takes a
  scope.
- `probe_native` returns `True` whenever the agent CLI is on `PATH`, so the
  path is taken by default for an installed agent.
- Single-source registry `ADAPTERS` (`:95`) already carries per-agent
  capabilities (`delegates`, `env`, `command`, …) and is the natural home for
  two more.
- Native capabilities (context7): gemini `mcp add/remove` support
  `-s/--scope`; codex has no scope selector (global `$CODEX_HOME/config.toml`).
  Both native env flags take literal `KEY=VALUE` values, which is incompatible
  with sofer's persist-NAMES-only contract (CF-3).
- Existing test that codifies the bug: `tests/test_cli.py` `TestMcpAddCliCoverage`
  mocks `probe_native`/`delegate_add` and asserts the delegated path skips the
  file edit; `tests/test_mcp_registration.py::TestDelegation::test_present_delegates`
  asserts `delegate_add("codex", …, ["HF_TOKEN"]) is True` — i.e. the env-dropping
  call is currently pinned as correct.

## Conclusion

Model "can the native CLI faithfully express the file-edit entry?" as two
registry capability flags (`native_env`, `native_scope`) plus one pure
predicate; have both delegates gate on it. That single criterion resolves #167
(env decline) and #232 (scope forward for gemini / decline for codex) together.
