# Design — `2026-10-15-fix-coverage-guard-freshness`

> **Change** `2026-10-15-fix-coverage-guard-freshness` (issue **#305**) · branch
> `fix/305-coverage-guard-freshness` from `dev@fad1b00` · store **hybrid**.

---

## 1. The defect, precisely

The guard reads `<repo>/.coverage` and asserts the three ≥90 floors
(`profile.py`, `mcp_registration.py`, `verification.py`) plus TOTAL from it. Its
only vouch condition was existence, so any database a previous run left behind —
a different commit, a different branch, an unrelated investigation — was asserted
as if it described the current tree. The database knows what it measured; it
records nothing about whether that is still true.

The guard's own docstring already promised the missing half for the *partial*
case ("an empty or partial mid-run database is treated as absent"). A complete but
stale database is invisible to the existence check.

## 2. Measured evidence

Live, on the untouched tree at the start of the session:

```text
2026-10-09 11:21 .coverage
2026-10-14 02:39 src/sofer/verification.py

$ uv run pytest tests/test_coverage_contract.py -q
E   AssertionError: src/sofer/verification.py measured 78.2% locally (< 90)
1 failed, 2 passed in 0.93s
```

RED of this change, after adding the policy tests and rewiring the guard:

```
$ uv run pytest tests/test_coverage_contract.py -q
7 failed, 2 passed            # NameError: name '_vouch_for_coverage_data' is not defined
```

GREEN: `8 passed, 1 skipped` — the single skip is the guard declining a database
that the `dev` checkout had made stale.

Live demonstration of the new skip (mtime pinned into the past, then restored):

```
SKIPPED [1] tests/test_coverage_contract.py:127: stale coverage database: it is older
than a file it measured (_converters.py) — run `uv run coverage run -m pytest` for
current numbers
```

## 3. The edits

### 3.1 `tests/test_coverage_contract.py` (test-only)

| Site | Change |
| --- | --- |
| module docstring | States the vouch condition and names the residual limitation (a subset `coverage run`). |
| `_vouch_for_coverage_data(data_file, measured, env)` (new) | The policy, pure and documented: existence, `COVERAGE_RUN`, and `db_mtime >= max(measured mtime)` with a vanished measured path rejected. Returns the skip reason or `None`. |
| the guard test | `skipif`-on-absence removed (the helper's reason replaces it); the helper is called before loading (existence, in-flight) and again with the loaded `measured` list (freshness); the assertions are unchanged. |
| `_pinned_file` + six policy tests (new) | Missing file, in-flight run, stale database, vanished measured path, equal mtime accepted, newer database accepted. Module-level functions, matching the file's style and the mapping checker's single-`::` grammar. |

The assertion itself — the three floor rows and TOTAL — is untouched: the local
regression pin survives (D4).

### 3.2 `openspec/specs/coverage/spec.md`

COV-01's optional-guard clause gains the vouch condition (skip reasons listed);
a new scenario ("Contract guard skips an unvouchable database — issue #305") is
added and mapped in the spec's `## Test Mapping` table; COV-07's rationale (b)
accounts for the second skip. No gate, workflow, script or config key is touched,
so COV-07's "No gate is armed" scenario stays true unmodified and
`tests/test_ci_workflows.py` is untouched.

## 4. Rejected alternative

The issue's option 2 (require an environment marker that the coverage job sets)
cannot work as written: `coverage run` erases the data file at start
(`Coverage.start()`) and flushes it at process exit, and it sets `COVERAGE_RUN`
before running the command — the guard executes inside that same process, so the
file on disk at that moment belongs to a previous run. Requiring the marker would
make the guard read stale data or never assert. The marker is still useful,
inverted: its presence is a *reason to skip*. That is what D2 implements.

Option 3 (delete the assertion; move the floors to CI) would arm a gate for the
three floors, which COV-07 forbids outside its own SDD change — a larger change
than #305 asks for. The maintainer chose option 1 (D4).

## 5. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real
red-then-green (§2): RED measured before the helper existed, GREEN after.

## 6. Risks

See `proposal.md` §5: a genuine regression coexisting with a stale database
(R1), the subset-run residual (R2, named in the docstring), and mtime granularity
(R3, mitigated by `>=`), all low, all with CI's own gates as the arbiter.

## 7. Rollback

Revert-only, test-only (§6 of the proposal).

## 8. Success criteria

SC-1..SC-6 of `proposal.md` §7.
