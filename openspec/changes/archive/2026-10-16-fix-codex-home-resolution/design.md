# Design — `2026-10-16-fix-codex-home-resolution`

> **Change** `2026-10-16-fix-codex-home-resolution` · issue **#325** · branch
> `fix/325-codex-home-and-321-delegation`.

## D1 — One field, not two

The issue's own proposed solution replaced `user_parts` as well:

```python
"user_parts": ("config.toml",),
"user_env_dir": "CODEX_HOME",
```

That would have moved the **default** to `~/config.toml`. `resolve_config_path` joins only
`user_parts[-1]` onto the override, and falls back to the full `user_parts` when the variable is absent
(`:375-379`) — which the adapter contract states explicitly at `:110-111`: "`user_parts` … also the
fallback when `user_env_dir` is set but its variable is absent".

So `user_parts` stays `(".codex", "config.toml")` and only `user_env_dir` is declared. That is the shape
Pi (`(".pi", "agent", "mcp.json")` + `PI_CODING_AGENT_DIR`) and Hermes (`(".hermes", "config.yaml")` +
`HERMES_HOME`) already use, so the fix adds no new shape to the registry.

The correction is recorded on the issue itself (`#325` comment) because the wrong version was published
first and a reader could have implemented it.

## D2 — User scope only

`resolve_config_path` consults the override on the user branch only, and `--user-config` is a user-scope
concept by decision of `2026-10-09-feat-mcp-user-config-flag` (issue #274). Codex's project-scope file
therefore stays `cwd/.codex/config.toml`, and a test asserts it rather than leaving it implied.

## D3 — The guard test exists because of D1

`test_codex_default_survives_the_override_being_declared` is the test that would have caught the issue's
own proposed fix. It is not ceremony: this change's most likely future edit is "clean up the redundant
leading path component", and that edit silently moves every user's config to `~/config.toml`.

## D4 — Declaring the override is what makes the two writers agree

`native_scope: False` for codex is *because* its native commands act on the global `$CODEX_HOME` config,
so a native delegation and a file edit must resolve to the same file for #321's option 1 to be safe at
all: delegating writes `$CODEX_HOME/config.toml`, and the patch step must find it there. Before this
change, option 1 would have written the entry in one file and the timeouts in another.

## Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Leave `user_env_dir: None` and make the *native* path the only correct one | The file-edit path is the fallback for every host that cannot delegate, and it would keep writing the wrong file. |
| Resolve `CODEX_HOME` inside `resolve_config_path` as a codex special case | The registry is the single source of truth for agent facts; a per-agent branch there is the duplication #235 removed. |
| Change the `Adapter.user_env_dir` contract so the override replaces the whole path | It would break `--user-config`'s precedence and the `user_parts[-1]` file-name rule that Pi and Hermes rely on. |
