# Design — `2026-10-09-feat-mcp-explicit-root`

> **Change** `2026-10-09-feat-mcp-explicit-root` (GitHub **#273**) · branch
> `feat/273-mcp-explicit-root` from `dev@b05d977` · store **hybrid**.
>
> **Inputs:** `proposal.md` (this change) and the measured tree evidence recorded below. No other
> document is consulted; every fact below is a citation of the parent's shell-run evidence.

---

## 1. The defect, restated precisely

| Surface | Measured today | Consequence |
| --- | --- | --- |
| `mcp_server.main()` | no argv parsing, calls `build_server()` bare | no launch knob exists |
| `SOFER_MCP_ROOT` | absent from the whole package | no env knob exists |
| `build_server(root=None)` | `Path.cwd().resolve()` | the root is always the host process cwd |

`README.md` documents the opposite (*"pass an explicit root"*), so the documentation is false and
every path-bearing tool is refused for any host whose cwd is not the dataset tree.

## 2. The precedence contract

**explicit `--root PATH` > `SOFER_MCP_ROOT` > resolved process cwd** (the documented default).

`_resolve_root(argv)` builds a one-argument `argparse.ArgumentParser` (`prog="sofer-mcp"`), reads
`args.root`, and falls back to `os.environ.get(_MCP_ROOT_ENV_VAR)` only when the flag is absent. A
`None` or blank/whitespace-only value resolves to `Path.cwd().resolve()`; otherwise the value is
`Path(raw).expanduser().resolve()`. The single resolution point means the path validated at startup
is the same absolute path the containment checks use.

The flag and env names are module constants (`_MCP_ROOT_ENV_VAR`, `_MCP_ROOT_FLAG`), never inline
literals (AGENTS.md rule 1). The two refusal reasons are constants too
(`_MCP_ROOT_MISSING_REASON`, `_MCP_ROOT_NOT_DIR_REASON`).

## 3. The edits

### 3.1 `src/sofer/mcp_server.py`

`main` gains an optional argv and a startup validation; `build_server` is untouched:

```python
def main(argv: Sequence[str] | None = None) -> None:
    root = _resolve_root(argv)
    if not root.is_dir():
        reason = _MCP_ROOT_NOT_DIR_REASON if root.exists() else _MCP_ROOT_MISSING_REASON
        print(
            f"sofer-mcp: refusing to start: containment root {root} {reason} "
            f"(from {_MCP_ROOT_FLAG} or {_MCP_ROOT_ENV_VAR})",
            file=sys.stderr,
        )
        raise SystemExit(1)
    server = build_server(root=root)
    server.run("stdio")
```

**Why refuse before building (D3).** `build_server` mutates process-global posture; refusing first
guarantees no partially-configured server can ever serve a request from an unrelated cwd, and the
non-zero exit is the fail-closed signal a stdio host observes. The message names the **resolved**
path so `~`, relative segments, and drive-relative forms are all echoed in canonical form.

**Why `argv=None` (D2).** `None` makes `argparse` read `sys.argv[1:]`, so the console script keeps
working with no arguments, while a test can pass `[]` or `["--root", ...]` to drive the real entry
point in-process.

**Why `argparse`.** It gives `--help` a clean exit 0, which MSP-R02 already requires of
`sofer-mcp --help`, and rejects unknown flags with a non-zero exit.

### 3.2 `tests/test_mcp_process.py`

A new `TestExplicitRoot` class drives `main()` in-process. A `build_server` spy calls the real
builder (so the captured server is the real `FastMCP`) but returns a `_RunlessServer` stub whose
`run` is a no-op, so `main` never blocks on stdio. Seven tests: flag sets root (and a tool resolves
inside it), env sets root, flag beats env, default is the resolved cwd, blank env is unset, missing
root refuses, file root refuses. The two refusal tests assert a non-zero exit and that stderr names
the resolved path.

### 3.3 `openspec/specs/mcp-server/spec.md`

MSP-R01 is **amended, not replaced** (D5): the header note is extended with the change's
attribution, one clause is added to the requirement body, and one scenario
(`Explicit root with fail-closed startup refusal`) is added. No Test Mapping row — `mcp-server` is a
permanent declared backlog spec. The same block is mirrored as the delta under
`openspec/changes/2026-10-09-feat-mcp-explicit-root/specs/mcp-server/spec.md`.

### 3.4 `README.md` + `README_ES.md` (rule 13)

The false sentence is replaced with the truth (cwd default, `--root` / `SOFER_MCP_ROOT` override,
argument wins, outside paths refused), the Windows `MCP cwd param` rows are extended with the launch
flag and precedence, and the security-model parenthetical names the override. Both files change in
the same edit and keep identical heading structure and section order; technical tokens stay in
English.

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, but this change has a real runtime capability, so
the carrier is genuine red-then-green:

| Gate | RED (measured) | GREEN (measured) |
| --- | --- | --- |
| `pytest tests/test_mcp_process.py -q -k TestExplicitRoot` | `7 failed` — `TypeError: main() takes 0 positional arguments but 1 was given` at the two refusal tests and `AttributeError` on `mcp_server._MCP_ROOT_ENV_VAR` on the rest | `7 passed` |

REFACTOR has no target: the change adds one resolution helper, one validation branch, and their
assertions.

## 5. Affected areas and review load

| File | Change | Est. lines |
| --- | --- | --- |
| `src/sofer/mcp_server.py` | imports + 2 constants + `_resolve_root` + `main` body | ~+60 |
| `tests/test_mcp_process.py` | import + `_RunlessServer` + `TestExplicitRoot` (7 tests) | ~+150 |
| `openspec/specs/mcp-server/spec.md` | 1 clause + 1 scenario + note | ~+12 |
| `README.md`, `README_ES.md` | 3 spots each | ~+12 / −6 |
| SDD artifacts | not source | — |

## 6. Rollback

Additive and revert-only. Reverting `mcp_server.py` restores the cwd-only behavior; reverting the
tests, the MSP-R01 amendment, the delta, and the README edits together leaves no requirement or doc
asserting a capability that does not exist. No state, no migration, no dependency change.

## 7. Success criteria

SC-1..SC-6 of `proposal.md` §7. Runtime evidence is recorded in the verify report.
