# Delta for mcp-registration

> **Change** `2026-10-09-fix-mcp-user-config-resolution` (issue **#274**) · branch
> `fix/274-cwd-containment-gate` · store **hybrid**.
>
> **One modification, no new requirement.** MCP-REG-01 gains the `--cwd` clause it never had. The rule
> was enforced in code and described nowhere — and it refused legitimate trees (a dataset tree outside
> `$HOME`) while *accepting* a path that does not exist.
>
> **Rule-6 resolution.** `mcp-registration` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the new scenario maps to its tests in
> `tests/test_mcp_registration.py` without a Test Mapping row, and the registry is not edited.

## MODIFIED Requirements

### Requirement: MCP add idempotent and safe (MCP-REG-01)

> Added by change `sofer-mcp-agents` (archived 2026-08-30).
>
> Modified by `2026-10-09-fix-mcp-user-config-resolution` (issue #274) — the `--cwd` rule becomes
> **existence instead of containment**, and the rule is declared here for the first time.

**Modification scope.** Exactly three spans move, and nothing else in the requirement does:

| Span | Operation |
| --- | --- |
| the requirement body | one paragraph appended after the env-NAMES paragraph: the `--cwd` existence clause, the outside-root acceptance, and the pointer that server-root containment is a separate contract |
| the requirement body | one amendment blockquote appended after that paragraph, recording the measured reasons the previous rule was removed |
| the scenarios | one scenario appended after `Cwd custom` |

**Added clause (verbatim, as it reads in the canonical spec after this change):**

The `--cwd` value SHALL be an **existing directory**, and that SHALL be the whole rule: `add` SHALL
exit 1 with a message naming the resolved path when it is not, and SHALL NOT write. A resolved `--cwd`
that is an existing directory but lies **outside** both `Path.home()` and the process cwd SHALL be
**accepted**, with a warning naming the resolved cwd and the roots it is outside of printed to stderr
— an explicit `--cwd` is the caller's own declaration, so an unusual tree is named rather than
refused. Containment of the *server root* is a separate contract (MSP-R01/MSP-R07) and is unaffected
by this clause.

> Amended by `2026-10-09-fix-mcp-user-config-resolution` (issue #274). The previous rule refused any
> cwd outside `Path.home()` or the process cwd. It was removed because, measured: it was undeclared in
> any spec (this clause did not exist); it was scope-blind (its `user` and `project` branches were the
> *same expression*); it was effectively untested (the only "rejection" test monkeypatched the
> function away); it protected no privilege boundary; it rejected legitimate trees (a dataset tree
> outside `$HOME`, which is the reported container case); and it still *accepted* a nonexistent path
> under either root, so it failed to catch the mistake that matters.

**Added scenario (verbatim):**

#### Scenario: Cwd existence, not containment

- GIVEN `--cwd` resolving to a path that is not an existing directory
- WHEN add runs
- THEN exit 1 SHALL be returned with a message naming the resolved path, and no write SHALL occur
- AND GIVEN `--cwd` resolving to an existing directory outside both the home and the process cwd
- THEN the add SHALL proceed and a warning naming the resolved cwd and the roots it is outside of SHALL
  be printed to stderr

## Non-goals recorded by this change

No change to the server-root containment (`_contained_path`, `_get_root`, `PathOutsideRootError`,
`build_server`); no `--user-config` flag in this slice — that is the follow-up slice 2 recorded in the
proposal; no version bump; no new requirement; no Test Mapping row; no registry edit; no README
change; no commit/push/PR from SDD phases.
