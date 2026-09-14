```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:3cc13e52ba0d2e79049eadbb0a4e0fee198193064109cc9a2cd60a4167d116e9
verdict: pass
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 5/5
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:809189a0aa8b97f8d8cb20120ec83127e197efde66608a0dc237a27782d00e59
build_command: uv run mypy src/ && uv run ruff check src/ tests/
build_exit_code: 0
build_output_hash: sha256:ac515e8bd9573c047b5c2feb8e57ff31c7690dab3a6edf92a68275a60ea8b7b4
```

# Verify Report — chore-agents-count-infer-type (issue #162)

**Change**: `2026-09-14-chore-agents-count-infer-type` · **Branch**: `chore/162-agents-count-infer-type`
**Verdict**: **PASS** — 0 blockers, 0 critical findings · **Store**: openspec (mirrored to Engram)
**Artifacts**: full set present (proposal + spec delta + design + tasks + apply-progress) → full verification
(tasks, specs, design, implementation, tests, review workload). Nothing skipped.

**Hash provenance** (all three `sha256:` fields are literal hashes of files captured during this run, via
`sha256sum`): `evidence_revision` = `sha256sum` of `git diff` captured to `/tmp/v162/candidate.diff` (the
verified candidate = the three-file tracked diff, 22 insertions / 40 deletions); `test_output_hash` =
`sha256sum /tmp/v162/pytest_full.txt` (stdout+stderr of `uv run pytest tests/ -q > /tmp/v162/pytest_full.txt 2>&1`);
`build_output_hash` = `sha256sum /tmp/v162/build.txt` (stdout+stderr of `uv run mypy src/ && uv run ruff check src/ tests/`,
both streams appended in command order to `/tmp/v162/build.txt`). The test-output hash covers
the captured artifact including pytest's timing line, so it identifies a fixed captured file rather than being
byte-reproducible across reruns.

## 1. Candidate identity and scope

`git diff --stat` on the working tree shows **exactly three tracked files** and no others:

```
 AGENTS.md              |  3 ++-
 src/sofer/codebook.py  | 15 ---------------
 tests/test_codebook.py | 44 ++++++++++++++++++++------------------------
 3 files changed, 22 insertions(+), 40 deletions(-)
```

`git diff --stat` over `README.md`, `README_ES.md`, `pyproject.toml`, `.github`, `openspec/specs`,
`openspec/changes/2026-09-14-chore-python-version-313` and `openspec/changes/archive` is **empty** (exit 0,
no output) — the binding three-file boundary held. The change directory itself is untracked SDD state
(`proposal.md`, `design.md`, `specs/`, `tasks.md`, `apply-progress.md`, this report) and is not review load.

## 2. Gates reproduced independently

| # | Exact command | Observed | Exit |
| --- | --- | --- | --- |
| G1 | `uv run pytest tests/ -q` | `1766 passed, 6 skipped, 1 warning in 54.36s` | 0 |
| G1b | `grep -c "DeprecationWarning" /tmp/v162/pytest_full.txt` | `0` (grep exits 1 → no matches) | 1 (no match) |
| G2 | `uv run pytest tests/test_codebook.py -q` | `82 passed in 1.77s` | 0 |
| G3 | `uv run pytest tests/test_codebook.py -q -W error::DeprecationWarning` | `82 passed in 1.07s` | 0 |
| G4 | `uv run mypy src/` | `Success: no issues found in 32 source files` | 0 |
| G5 | `uv run ruff check src/ tests/` | `All checks passed!` | 0 |
| G6 | `bash scripts/check_core_coverage.sh` | four rows (`cli.py` 574, `scanner.py` 159, `prepare.py` 432, `publish.py` 326) all `100%`, `Missing` column empty | 0 |
| G7 | `uv run coverage report -m` | `TOTAL 6002 365 2322 166 93%` vs `pyproject.toml:98 fail_under = 90` | 0 |

**Zero-warning claim made checkable**: G1's warnings summary contains exactly one line, and it is not related
to codebook — `tests/test_cli.py::test_cli_main_guard_executed_via_runpy` →
`RuntimeWarning: 'sofer.cli' found in sys.modules … (runpy)`. `grep -c "DeprecationWarning"` over the captured
file returns **0**, and `grep -n "codebook"` over the same file returns nothing. G3 is the gate that turns that
from an eyeball into an assertion: the migrated module passes with `DeprecationWarning` promoted to an error.

G7's TOTAL (93%) is comfortably above the config-owned floor. The deleted alias lived in `codebook.py`, which
backs **no** per-file floor (COV-01 = `profile.py`/`mcp_registration.py`/`verification.py`; COV-06 =
`cli.py`/`scanner.py`/`prepare.py`/`publish.py`, the four rows G6 loops over), so removing fully covered lines
could not drop a scoped gate — confirmed by G6 exiting 0 with an empty `Missing` column.

## 3. Scenario-by-scenario evidence (PB-11 = 2, PB-12 = 3)

| Req | Scenario | Command(s) that evidence it | Strength (honest) |
| --- | --- | --- | --- |
| PB-11 | Anchor carries its own command | G1 (fresh `uv run pytest tests/ -q` tally) + direct inspection of `AGENTS.md:44-45`, which now names `uv run pytest tests/ -q` and labels the figure an observation | **Weaker** — prose/command fact, not pytest-asserted (delta marks it so) |
| PB-11 | The stale literal is gone | `git diff -- AGENTS.md` shows `@@ -44 +44,2 @@` replacing the literal; `grep -n "1149\|1151" AGENTS.md` → no match (exit 1); post-change text sits at `AGENTS.md:44-45` | **Weaker** — same class (delta marks it so) |
| PB-12 | Suite run is deprecation-free | G1 + G1b + G3 | **Medium** — runtime fact; no `filterwarnings` config exists and adding one is out of scope, so G3 is the strongest available form |
| PB-12 | Behavioural parity preserved on the live API | G2 + the independent 13-case diff against `git show HEAD:tests/test_codebook.py` (§4) | **Strong** — pytest-asserted |
| PB-12 | No residual alias reference | `grep -rn "_infer_type" src/ tests/ AGENTS.md README.md README_ES.md` → **0 matches** (exit 1); `src/sofer/codebook.py` diff is a pure deletion (`0 15` numstat) | **Medium** — static scan |

`grep -rn "_infer_type"` over the **whole worktree** (excluding `.git`) returns hits only in places the
scenario does not constrain: `openspec/changes/2026-09-14-chore-agents-count-infer-type/**` prose,
`openspec/specs/repo-compliance/spec.md:1494` (historical rename record), `tmp/**` scratch notes,
`.venv/**` third-party, `htmlcov/**` and `.mypy_cache/**`/`.codegraph/**` generated artifacts. **Zero** hits in
`src/`, `tests/`, `AGENTS.md` or the READMEs.

## 4. Behavioural parity — verified against the git baseline, not accepted

Checked against `git show HEAD:tests/test_codebook.py` (pre-change tree), not against the apply-progress claims:

- Pre-change `_infer_type` assertion call sites: **9** sample assertions (baseline L28/31/34/38/41/46/49/52/53)
  replayed through the alias, plus the parity loop at L73 (`2 assertions × 4 cases = 8` executions, of which
  4 are the `infer_column_type(v) == _infer_type(v)` statements). Counting type-inference assertions only:
  **17 → 13**.
- The 9 sample cases are byte-identical in input and expected output post-change, with `infer_column_type`
  substituted for `_infer_type` (diff inspection, one-for-one).
- The 4 parity cases (`["1","2","3"]`→numeric, `["red","blue"]`→categorical/text, `["1","two","3"]`→
  `"mixed (mostly numeric)"`, `["NA","","MISSING"]`→categorical/text) survive as 4 direct assertions on the
  live API.
- **The duplicate claim is true and provable.** `_infer_type` was defined as `return infer_column_type(values)`
  after the `warnings.warn` (HEAD `src/sofer/codebook.py:60-71`), so each discarded
  `infer_column_type(v) == _infer_type(v)` reduces to `infer_column_type(v) == infer_column_type(v)` over the
  identical input already covered by the kept `== expected` assertion one line above it. Nothing distinct was
  discarded — this is equivalence, not a lost case.
- **No assertion was dropped, weakened, skipped or xfailed.** `grep -n "skip\|xfail" tests/test_codebook.py`
  finds only three unrelated pre-existing tests whose *names* contain "skips"
  (`test_skips_unsupported_format`, `test_skips_missing_file`, `test_skips_directory_entry`); no `@pytest.mark.skip`,
  `pytest.skip`, `xfail` or parametrisation was introduced by the diff. Test-function count is **82**, matching
  G2's `82 passed`.

Result: **13 cases / 13 primary assertions, case-for-case equal to the design §D2 baseline.**

## 5. Task completion, status and action context

- `tasks.md`: **13/13** implementation tasks complete. `grep -n "^\s*- \[ \]" tasks.md` → **no matches**
  (exit 1). There are **no unchecked implementation task lines** — no CRITICAL completeness issue, no archive
  blocker from task state.
- Structured status consumed: `apply: all_done`, `verify: ready`, `actionContext.mode: repo-local`,
  `allowedEditRoots: ["C:\Users\elaze\Desktop\sofer"]` with every edited path inside it. `blockedReasons: []`.
- **Strict TDD is not active** (`openspec/config.yaml` `strict_tdd: false`), so no `TDD Cycle Evidence` table is
  required and no assertion-quality audit under that clause is due. A behaviour-preserving migration has no RED
  state; the sequence was migrate → measure parity → measure gates, as `apply-progress.md` records.
- Delta numbering hazard reproduced: `openspec/specs/process-boundary/spec.md` ends at **PB-09** on this
  branch; **PB-10 is absent** because it belongs to the unmerged sibling `2026-09-14-chore-ruff-format-drift`
  (PR #196). After that PR merges, the archive step must insert PB-11/PB-12 *after* PB-10 and **must not**
  renumber anything. If the order slips, the breakage is the cosmetic PB-09 → PB-11 gap — report it, do not
  "fix" it.

## 6. Review workload / PR boundary

`apply-progress.md` and `tasks.md` declare a single work unit, single PR, `ask-on-risk` with no trigger:
measured **62 changed lines** against the 400-line canonical threshold and the 2000-line session budget. The
verified diff implements **only** that slice — three files, no fourth, no `size:exception` claimed or needed, no
chaining recommended and none performed. **No scope creep.** Rollback remains a single `git revert` of the
three-file diff (no data, migration, flag, config or CI change).

## 7. Pre-existing reds and static-analysis findings (not caused by this change)

1. **`uv run ruff format --check src/ tests/` is red (exit 1) on six files** —
   `tests/test_ci_workflows.py`, `tests/test_coverage_contract.py`, `tests/test_mcp_registration.py`,
   `tests/test_profile.py`, `tests/test_publish.py`, `tests/test_splits.py` (`6 files would be reformatted,
   61 files already formatted`). None of the six is in this diff, and the two files this change touches pass
   standalone. This drift is owned by the **unmerged sibling `2026-09-14-chore-ruff-format-drift` (PR #196)**,
   whose design mandates it merges first. **Recorded as pre-existing, owned by PR #196 — not a finding against
   this change, and deliberately not fixed here** (fixing it would break the binding three-file scope).
2. **Static-analysis findings inside `tests/test_codebook.py` and `src/sofer/codebook.py` are pre-existing**:
   the apply-progress reports `tests/test_codebook.py` L299/300/301/319/403/404/877/878/879/1133 == HEAD
   L303/304/305/323/407/408/881/882/883/1137 (net offset **−4**) and `src/sofer/codebook.py` L75/230/235 ==
   HEAD L90/245/250 (net offset **−15**). Both offset sets are consistent with this diff's pure deletions and
   one-for-one substitutions, i.e. byte-identical to `HEAD` apart from the intended alias removal. The
   project's type gate is **`uv run mypy src/` (source only)** — G4 is clean — so these are **pre-existing, out
   of scope, not regressions**. (`tests/` is outside that gate by AGENTS rules 5/12.)

## 8. Compatibility note for the PR description and release notes (verbatim, design §D3)

> Removes the private, deprecated alias `sofer.codebook._infer_type`. It was uncalled anywhere in the repository
> (tests included); use the public `sofer.codebook.infer_column_type` instead. No public API changes.

A **private, deprecated, now-uncalled** symbol was removed — a private-name breaking change only for
hypothetical out-of-repo importers. The documented fallback if a reviewer objects is **design §D3 option (A)**:
keep the alias behind a `pytest.warns(DeprecationWarning)` test as a migration window, replacing the parity test
while keeping the same acceptance criterion (zero `DeprecationWarning`s).

## 9. Blockers and exact risks

**Blockers: none.**

- **Merge order (delivery risk, not a code blocker)** — PR #196 (PB-10) must merge before this change's PR,
  otherwise archive shows the cosmetic PB-09 → PB-11 gap. Never renumber a merged requirement.
- **Option B private-name removal** — mitigated by the §8 compatibility note; option (A) remains the fallback.
- **Repo-wide `ruff format --check` stays red until #196 merges** — pre-existing, unrelated, out of scope.

## 10. Validation

`gentle-ai sdd-verify-validate` is run against this file with `--requirements 2 --scenarios 5`; its verbatim
output is recorded below in §11.

## 11. Validator output (verbatim)

```text
$ B="/c/Users/elaze/.pi/agent/npm/node_modules/gentle-pi/.gentle-ai/v2.9.0/gentle-ai.exe"
$ "$B" sdd-verify-validate --input openspec/changes/2026-09-14-chore-agents-count-infer-type/verify-report.md --requirements 2 --scenarios 5
{
  "valid": true,
  "verdict": "pass",
  "evidence_revision": "sha256:3cc13e52ba0d2e79049eadbb0a4e0fee198193064109cc9a2cd60a4167d116e9"
}
validate_exit=0
```

Admission note: the first validation attempt was denied (`Error: verify report admission denied: test_command and
build_command require concrete current execution evidence`) because the envelope's `build_command` used a shell
command group (`{ …; }`), whose braces the validator reads as an unfilled template placeholder. Replacing it with
the brace-free equivalent `uv run mypy src/ && uv run ruff check src/ tests/` — the same commands, same captured
bytes, same `build_output_hash` (`ac515e8b…`, re-derived and byte-identical) — was admitted. No gate result or
evidence changed; only the command spelling was made explicit.
