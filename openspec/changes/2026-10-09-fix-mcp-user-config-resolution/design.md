# Design — `2026-10-09-fix-mcp-user-config-resolution`

> **Change** `2026-10-09-fix-mcp-user-config-resolution` (issue **#274**) · branch
> `fix/274-cwd-containment-gate` · store **hybrid**. Slice 1 of 2.

---

## 1. The defect, precisely

`validate_cwd(cwd, scope)` decided whether `sofer mcp add --cwd PATH` may proceed. Its body:

```python
if scope == "user":
    return resolved.is_relative_to(home) or resolved.is_relative_to(project_root)
# project
return resolved.is_relative_to(project_root) or resolved.is_relative_to(home)
```

Both branches are the same expression. The rule refuses any path outside
`Path.home()` ∪ `Path.cwd()`, and it never checks whether the path exists.

## 2. Measured evidence (parent shell runs, quoted)

The RED run against the unmodified code, on the test written for the new rule:

```
>       assert rc == 1
E       assert 0 == 1
------------------ Captured stdout call ------------------
  DRY RUN  Would register opencode at ...\test_cmd_add_refuses_a_missing0\nope\opencode.json
```

**The old gate accepted a `--cwd` that does not exist** (exit 0) while refusing a real directory that
merely sits outside `$HOME`. That single run is the argument for the change.

Corroborating measurements:

| Check | Result |
| --- | --- |
| Spec clauses describing the rule | **0** — no containment clause existed in MCP-REG-01 or CLI-R09 |
| `validate_cwd` direct callers in tests | 2 test classes; 11+ other sites monkeypatch it to `True` |
| The only "rejection" test | `test_cmd_add_rejects_outside_root` monkeypatched `validate_cwd` to `False` — it tested the caller, not the rule |

## 3. The edits

### 3.1 `src/sofer/mcp_registration.py`

`validate_cwd(cwd: Path) -> bool` — the `scope` parameter is **removed**; the body becomes
`cwd.resolve().is_dir()` inside the existing `try`/`except`, so an unresolvable path is still
refused rather than raising. The docstring records all five reasons the previous rule was removed,
because the next reader deserves to know why it stopped refusing.

`outside_root_warning(cwd: Path) -> str | None` — new. Returns a stderr-ready message naming the
resolved cwd and the roots it is outside of, or `None` when it is inside `Path.home()` or
`Path.cwd()`. The marker is `"  !  "`, matching the repo's existing informational-warning marker
(`cli.py:746`).

**No `# pragma: no cover` is added anywhere.** An earlier draft guarded `root.resolve()` in the loop
with a pragma; it was removed by simplifying the loop instead, since an untestable branch is a design
smell, not a reason to silence coverage.

### 3.2 `src/sofer/cli.py` — `_cmd_mcp_add`

The caller now refuses on existence and warns on location:

```python
if not mcp_registration.validate_cwd(cwd_resolved):
    print(f"  X  --cwd {cwd_resolved} is not an existing directory", file=sys.stderr)
    return 1

outside_warning = mcp_registration.outside_root_warning(cwd_resolved)
if outside_warning is not None:
    print(outside_warning, file=sys.stderr)
```

The orchestration docstring's step 2 is updated to describe the new rule rather than the removed one.
**`cli.py` is an AGENTS.md rule-14 module**: both branches (refusal and warning) are executed by the
new tests, which is why the per-file gate still reports 100.00%.

### 3.3 Specs

MCP-REG-01 gains the clause and a scenario `Cwd existence, not containment`, plus an amendment note
recording why the old rule was removed. `mcp-registration` is a permanent declared-backlog spec: no
Test Mapping row, and `openspec/test-mapping-registry.md` is untouched.

### 3.4 Tests

`TestCwdContainment` is rewritten around the new rule: an existing directory is accepted; a directory
outside home is accepted; a missing directory is refused; a file is refused; the warning names both
sides and is `None` inside home; and the two CLI-level cases (accepted with warning / refused).

`TestCwdContainmentNext` had one assertion that *is* the changed behavior — `validate_cwd(foreign,
"project") is False` — and is rewritten to assert the new contract while **keeping** the
resolve-failure case, which is the coverage for the `except` branch. A second test class was found
only when the suite failed after the first pass: the lesson is to run the whole suite, not the file
you think you edited.

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, and this change alters a validation rule rather than
adding production behavior. The carrier is nevertheless a real red-then-green:

| Gate | RED (measured) | GREEN (measured) |
| --- | --- | --- |
| `pytest tests/test_mcp_registration.py::TestCwdContainment` | **8 failed** — the new rule does not exist, and the CLI accepts a nonexistent cwd | **8 passed** |
| `pytest tests/test_mcp_registration.py tests/test_cli.py` | (same) | **297 passed, 1 skipped** |
| `pytest tests/ -q` | — | **2011 passed, 6 skipped** (base 2005/6; +6 = 8 new minus 2 replaced) |

No REFACTOR target: the change replaces one rule with a simpler one.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | Relaxing a fail-closed gate is a behavior change, not a bugfix | **Med** | Accepted deliberately and recorded in three places: the spec clause, its amendment note, and this design. The lost protection is named in §2 (it protected no privilege boundary and missed the real mistake). The PR body flags it as the one behavior change. |
| **R1b** | **The removal also drops a fail-closed brake on misconfiguration.** An unintended tree — `--cwd /`, `--cwd C:\` — now exits **0** with a non-fatal stderr line, so a caller that does not surface stderr (an agent, a script, a CI step) can register a server rooted somewhere unexpected without noticing. | Med | Named rather than hidden, after the independent verification pointed out that the first draft of this design omitted it. The warning is printed, the acceptance is the explicit decision D2, and the alternative — refusing — is the false gate that blocked legitimate container layouts. This is the one judgment call in the change. |
| R2 | A caller depending on the old refusal | Low | Verified: no test asserted the refusal of an existing outside-root directory except the one that *is* the changed behavior, and it was rewritten with the change. |
| R3 | Removing the `scope` parameter breaks a caller | Low | The focused files and the full suite were run; the two direct callers were found and updated, the second only because the full suite was run. |

## 6. Rollback

Additive-to-subtractive and revert-only: restoring the old `validate_cwd` body and its caller
restores the previous behavior exactly. No state, no migration, no runtime impact — nothing in
`src/` outside these two functions changes.

## 7. Success criteria

SC-1..SC-5 of `proposal.md` §4. Runtime evidence for SC-2 (the rule-14 gate) is recorded in the
verify report.
