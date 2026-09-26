# Apply progress: chore-ruff-single-authority

**Change** `2026-09-15-chore-ruff-single-authority` (GitHub #195) · branch
`chore/195-ruff-single-authority` (from `dev@5a2ae38`) · store **hybrid** — this file plus the Engram
mirror under topic key `sdd/2026-09-15-chore-ruff-single-authority/apply-progress`.
**Phase**: `sdd-apply` · **Status**: `complete` for apply's own scope · **Next**: `sdd-sync`, then
`sdd-verify`.
**Strict TDD**: not active (`openspec/config.yaml:12` → `strict_tdd: false`). The plan's test-before-
declaration ordering was followed anyway (RED observed at task 1.3 before any declaration edit).

**One-line outcome**: one ruff version (`0.16.7`) is now declared in three places that CI-08's three new
static guards force equal, `[tool.ruff] required-version` enforces it at config load, `uv.lock` was
refreshed confined to the ruff block, `CONTRIBUTING.md:77` names the version, and **no CI format gate was
armed**.

---

## 1. Structured status consumed

Native `gentle-ai.sdd-status` v2, supplied by the parent for change
`2026-09-15-chore-ruff-single-authority`, canonical workspace `C:\Users\elaze\Desktop\sofer`:

| Field | Value |
| --- | --- |
| `applyState` | `ready` (launch granted: `state: proceed`, attempt token bound to this launch, `max-changed-lines: 400`, `max-attempts: 2`) |
| `actionContext.mode` | `repo-local` |
| `actionContext.workspaceRoot` | `C:\Users\elaze\Desktop\sofer` |
| `actionContext.allowedEditRoots` | `["C:\Users\elaze\Desktop\sofer"]` |
| `taskProgress` | total **49**, completed 0, pending 49 (pre-apply) |
| Dependency state | proposal/specs/design/tasks `all_done`; apply `ready`; verify `blocked`; archive `blocked` |
| `blockedReasons` | `[]` |

**`actionContext` warnings**: none — mode is `repo-local` (not `workspace-planning`), so no
`allowedEditRoots` gate applied; every written path is inside the authoritative workspace. No path outside
`C:\Users\elaze\Desktop\sofer` was written. **Note**: the phase prompt said "40 tasks"; the artifact and
the status engine both say **49** (4+5+8+3+8+7+4+10). The artifact was used, not the prose.

---

## 2. Task status — 45 of 49 complete

| Phase | Tasks | Status |
| --- | --- | --- |
| 0 — Baseline and scope anchor | 0.1–0.4 | ✅ complete |
| 1 — RED: the three guards | 1.1–1.5 | ✅ complete |
| 2 — GREEN: declarations, lock, hook | 2.1–2.8 | ✅ complete |
| 3 — TRIANGULATE: mutation probes | 3.1–3.3 | ✅ complete |
| 4 — Runtime evidence | 4.1–4.8 | ✅ complete, with a **deviation at 4.5** (see §4) |
| 5 — Documentation, docstring, delta text | 5.1–5.7 | ✅ complete |
| 6 — Sync | 6.1–6.4 | ⛔ **not executed** — belongs to `sdd-sync` (see §4, deviation 5) |
| 7 — Final gates | 7.1–7.10 | ✅ complete |

Persisted checkbox updates: `openspec/changes/2026-09-15-chore-ruff-single-authority/tasks.md` — **45
`- [x]`, 4 `- [ ]`**, and the only unchecked rows are exactly 6.1, 6.2, 6.3, 6.4. Re-read after editing
and confirmed.

---

## 3. Files changed

| Path | numstat (add/del) | What changed |
| --- | --- | --- |
| `pyproject.toml` | 5 / 1 | dev pin `ruff>=0.9.0` → `ruff==0.16.7` (`:47`); 3-line comment + `required-version = "==0.16.7"` (`:59-62`) |
| `uv.lock` | 22 / 22 | `ruff` package block `0.16.0` → `0.16.7` (version, sdist, 17 wheels); the single dev specifier line `>=0.9.0` → `==0.16.7` |
| `tests/test_ci_workflows.py` | 75 / 5 | 3 module constants + `_declared_ruff_version()` helper; 3 guard tests appended; module docstring reconciled |
| `CONTRIBUTING.md` | 1 / 1 | `:77` first sentence gains `0.16.7` |
| `openspec/changes/.../specs/ci/spec.md` | (untracked) | the two §1.5 wording fixes (CI-08 body + PKG-06 row) |
| `.pre-commit-config.yaml` | **0** | unchanged, asserted by task 2.4 |

**Measured changed-line count: 132 (103 added / 29 deleted)** — under the 400-line budget and under the
session's 1500-line budget.

---

## 4. Evidence, command by command

### Phase 0 — baseline and scope anchor

**0.1** branch + clean status:

```console
$ git rev-parse --abbrev-ref HEAD
chore/195-ruff-single-authority
$ git status --porcelain
?? openspec/changes/2026-09-15-chore-ruff-single-authority/
```

**0.2** pre-change tally, re-derived (never copied from `AGENTS.md` rule 6, whose figure is stale):

```console
$ uv run pytest tests/ -q
1781 passed, 6 skipped, 1 warning in 58.24s
```

**0.3** pre-change structural figures — all four match the tasks file:

```console
$ grep -c '^def test_' tests/test_ci_workflows.py                 # 19
$ grep '^| CI-0' openspec/specs/ci/spec.md | wc -l                # 22
$ grep '^| CI-0' openspec/specs/ci/spec.md | grep -c 'test_ci_workflows.py'   # 15
$ git diff --numstat uv.lock                                      # (empty)
```

**0.4** append anchor, measured before any edit:

```console
$ grep -n '^def test_pr_template_has_coverage_checklist_item' tests/test_ci_workflows.py
421:def test_pr_template_has_coverage_checklist_item() -> None:
$ wc -l < tests/test_ci_workflows.py
426
$ tail -n 1 tests/test_ci_workflows.py
    assert "README_ES.md updated" in checklist
```

⇒ the guards are appended **after line 426** (end of file), never at `:421`.

### Phase 1 — RED

**1.1** guard block appended. `git diff --numstat tests/test_ci_workflows.py` → `66  0` at that point
(66 added lines; it becomes `75 / 5` after the task-5.4 docstring reconciliation). Constants and the
helper sit with the module's other helpers; the three tests are appended after
`test_pr_template_has_coverage_checklist_item`. No new file, no new import (`re` was already imported).

**1.2** `python-code-style` trio on the single touched Python file (ambient ruff at this point was
still `0.16.0`, which is the defect this change removes):

```console
$ uv run ruff --version
ruff 0.16.0
$ uv run ruff format tests/test_ci_workflows.py
1 file left unchanged                                  # exit 0
$ uv run ruff check --fix tests/test_ci_workflows.py
All checks passed!                                     # exit 0
$ uv run ruff check tests/test_ci_workflows.py
All checks passed!                                     # exit 0
```

Recorded for the record: that skill's "drop a root `ruff.toml`" step **does not apply here** — this
repository keeps ruff config in `pyproject.toml:56-69` (a deliberate divergence recorded in
`explore.md`). No third fix cycle was needed.

**1.3** RED **before any declaration edit** (`pyproject.toml:47` still `"ruff>=0.9.0"`):

```console
$ uv run pytest tests/test_ci_workflows.py -q
E       AssertionError: the ruff dev pin must be an exact ==X.Y.Z specifier, got '>=0.9.0' —
        a floor lets `uv lock` drift the formatter (this is how 0.16.0 got in)
E       assert None is not None
FAILED tests/test_ci_workflows.py::test_ruff_pin_hook_rev_and_required_version_agree
FAILED tests/test_ci_workflows.py::test_workflows_do_not_declare_a_ruff_version
FAILED tests/test_ci_workflows.py::test_contributing_names_the_declared_ruff_version
3 failed, 19 passed in 0.27s
```

All three fail on the **exactness assertion** inside `_declared_ruff_version()` — the drift-explaining
message — not on a missing file or a `KeyError`. That is the guard's teeth on today's defect.

**1.4** the three test names are byte-identical to the delta's CI-08 scenarios and its four Test Mapping
rows. Module: `:459`, `:471`, `:484`. Delta: `specs/ci/spec.md:82`, `:91`, `:99` (scenarios) and
`:132-134` (rows); the fourth row is verify-phase and maps to runtime command evidence by design. One
test per scenario, no vacuous fourth test.

**1.5** **REFACTOR does not apply**: this change adds no production code. The only structural concern —
shared extraction versus duplication — is settled by construction in 1.1 (AGENTS.md rule 4): the helper
is defined once and reused by all three guards, and the existing `_read_text` / `_load_toml` /
`_load_yaml` / `_workflow_names` / `_WORKFLOW_DIR` are reused rather than re-implemented. No duplication
was discovered while writing 1.1, so no extraction beyond the planned one was performed. The touched
module's own docstring is reconciled in task 5.4 rather than by a refactor pass.

### Phase 2 — GREEN: declarations, lock refresh, hook verification

**2.1 / 2.2** declarations:

```console
$ grep -n '"ruff==' pyproject.toml
47:    "ruff==0.16.7",
$ grep -c 'ruff>=' pyproject.toml
0
$ grep -n 'required-version' pyproject.toml
62:required-version = "==0.16.7"
$ grep -c '0.16.7' pyproject.toml
2
$ grep -rn 'ruff' src/
src/sofer/mcp_server.py:1:# ruff: noqa: E501
```

**Rule 1 rationale (recorded, per task 2.2)**: `required-version` is a **build/toolchain declaration**,
not a runtime default — the same class as `.python-version` and `[tool.mypy] python_version`
(`pyproject.toml:74`), both already literals in this file. `[tool.sofer]` holds tool-wide *runtime*
defaults consumed by `src/sofer/config.py`, and **no `src/sofer/` code path reads a ruff version** (the
only `ruff` occurrence under `src/` is a `# noqa` directive). The explanatory comment deliberately does
**not** repeat the version, so each declaration site holds exactly one occurrence.

**2.3** intermediate state, recorded honestly — **not** three greens:

```console
$ uv run pytest tests/test_ci_workflows.py -q
E       AssertionError: the Code style section must name ruff 0.16.7
FAILED tests/test_ci_workflows.py::test_contributing_names_the_declared_ruff_version
1 failed, 21 passed in 0.27s
```

Tests 1 and 2 green; test 3 still RED because `CONTRIBUTING.md:77` is task 5.1 by design ordering.

**2.4** `.pre-commit-config.yaml` needs no edit — "unchanged" is an asserted property:

```console
$ grep -n 'astral-sh/ruff-pre-commit' .pre-commit-config.yaml
2:  - repo: https://github.com/astral-sh/ruff-pre-commit
$ sed -n '3p' .pre-commit-config.yaml
    rev: v0.16.7
$ git diff --stat .pre-commit-config.yaml
(empty)
```

The rev **is** `v0.16.7`, so the escalation branch did not fire and the rev was not touched.

**2.5** `uv.lock` confinement probe. **Flag discovery** (no flag was asserted in advance):

```console
$ uv lock --help | grep -n 'upgrade-package\|check\|locked\|offline'
6:      --check            Check if the lockfile is up-to-date
41:  -P, --upgrade-package <UPGRADE_PACKAGE>
125:      --offline
```

**Step-0 deviation (recorded).** `git status --porcelain uv.lock` was **not** empty at probe time: it
returned ` M uv.lock`. The cause is uv's own default behaviour — `uv run` re-locks when the declarations
change — so the refresh had already happened implicitly during the `uv run pytest` calls of tasks 1.2,
1.3 and 2.3, before the explicit probe. Captured diff:

```console
$ git diff --numstat uv.lock
22	22	uv.lock
```

Full diff, every hunk attributed: `@@ -2031,27 +2031,27 @@` is the `[[package]] name = "ruff"` block
(`version` `0.16.0`→`0.16.7`, the `sdist` line, and the 17 wheel entries); `@@ -2117,7 +2117,7 @@` is
the single dev-specifier line inside the `[[package]] name = "sofer"` metadata block
(`{ name = "ruff", specifier = ">=0.9.0" }` → `"==0.16.7"`). The lock header (`uv.lock:1-11`) is
untouched, no `[[package]]` was added or removed, no non-ruff `requires-dev`/`requires-dist` entry moved,
and there is no whitespace or ordering churn.

The explicit `uv lock` was then run as the task specifies, and proved to be a **no-op**:

```console
$ git diff uv.lock | sha256sum
341eda3d5aab2ed80ae946690de73aac73541c49066682bb4131d03ae8018b94 *-
$ uv lock
Resolved 106 packages in 1ms                     # exit 0
$ git diff uv.lock | sha256sum
341eda3d5aab2ed80ae946690de73aac73541c49066682bb4131d03ae8018b94 *-
```

The `--upgrade-package` fallback was **not** needed (no unrelated churn appeared), and hand-editing was
never performed.

**VERDICT: ACCEPT** — confined to the ruff package block and the dev specifier; the reject rules did not
fire.

**2.6** consistency check — `--check` exists, so it was the flag used:

```console
$ uv lock --check
Resolved 106 packages in 1ms                     # exit=0
```

**2.7** the pinned binary is now in the venv — the precondition for tasks 4.1–4.6:

```console
$ uv sync
Resolved 106 packages in 1ms
Checked 96 packages in 5ms                       # exit=0
$ uv run ruff --version
ruff 0.16.7
```

**2.8** lock-refresh verdict, recorded in one place for the verify report:

- accepted hunks by line range: `uv.lock` `@@ -2031,27` (ruff package block) and `@@ -2117,7` (sofer
  metadata block, ruff specifier line only);
- reject-rule outcome: **no rejection** — no other `[[package]]` touched, no package added/removed, no
  header change, no ordering or whitespace churn;
- **AC5 ownership correction**: AC5's obligation is homed in **`ci` CI-08** (delta wording fixed in task
  5.5), with `packaging` PKG-06's regeneration clause cited as the **same class** scoped to its own
  `fastmcp` declaration, **not** as this obligation's owner. The proposal's AC5 row citing PKG-06 as
  owner is **superseded** by this correction.

### Phase 3 — TRIANGULATE: the guard's teeth

Each leg was observed RED on the specific assertion, then restored and proven restored.

**3.1** mutation leg 1 — the hook rev:

```console
$ git diff --stat .pre-commit-config.yaml          # (empty — the safe baseline)
$ sed -i 's/rev: v0.16.7/rev: v0.16.6/' .pre-commit-config.yaml
$ uv run pytest tests/test_ci_workflows.py -q -k test_ruff_pin_hook_rev_and_required_version_agree
E       AssertionError: ruff-pre-commit rev must be 'v0.16.7', got ['v0.16.6']
E       assert ['v0.16.6'] == ['v0.16.7']
FAILED tests/test_ci_workflows.py::test_ruff_pin_hook_rev_and_required_version_agree
$ git checkout -- .pre-commit-config.yaml          # safe: baseline diff was zero
$ sed -n '3p' .pre-commit-config.yaml
    rev: v0.16.7
$ git diff --stat .pre-commit-config.yaml
(empty — restored byte-identical)
```

**3.2** mutation leg 2 — `required-version`, restored by **re-editing** (never `git checkout --`, which
would have deleted this change's own pin and `required-version` edits — tasks-file correction 5):

```console
$ git diff pyproject.toml | sha256sum
9d40b8f453cdca259b82e70e91973a6921c6a9b5fab6d8c172636fa4397589c2 *-
$ sed -i 's/required-version = "==0.16.7"/required-version = "==0.16.6"/' pyproject.toml
$ uv run pytest tests/test_ci_workflows.py -q -k test_ruff_pin_hook_rev_and_required_version_agree
E       AssertionError: required-version must be '==0.16.7', got '==0.16.6'
FAILED tests/test_ci_workflows.py::test_ruff_pin_hook_rev_and_required_version_agree
$ sed -i 's/required-version = "==0.16.6"/required-version = "==0.16.7"/' pyproject.toml
$ git diff pyproject.toml | sha256sum
9d40b8f453cdca259b82e70e91973a6921c6a9b5fab6d8c172636fa4397589c2 *-   # byte-for-byte match
$ uv run pytest tests/test_ci_workflows.py -q
1 failed, 21 passed in 0.26s        # test 1 green again; the 1 failure is test 3 (task 5.1 not yet done)
```

**3.3** no-residue assertion:

```console
$ git status --porcelain
 M pyproject.toml
 M tests/test_ci_workflows.py
 M uv.lock
?? openspec/changes/2026-09-15-chore-ruff-single-authority/
```

Only the intended change paths plus this change's SDD artifacts. `CONTRIBUTING.md` correctly untouched at
this point; no `.pre-commit-config.yaml` residue; no lint output was needed at this stage.

### Phase 4 — Runtime evidence

**4.1** CI-08 S4 **leg A** — the declared value passes (enforced scope from `ci.yml:19`, not the narrower
documented commands — #212 stays untouched):

```console
$ uv run ruff check src/ tests/ scripts/
All checks passed!                                # exit=0
$ uv run ruff format --check src/ tests/ scripts/
68 files already formatted                        # exit=0
```

**4.2** CI-08 S4 **leg B** — mismatch probe, config created **outside** the repository
(`/tmp/tmp.fG7gYcX01t/ruff-probe/ruff.toml`, resolved by uv to
`C:/Users/elaze/AppData/Local/Temp/tmp.fG7gYcX01t/ruff-probe/ruff.toml`, holding only
`required-version = "==99.0.0"`). `--config` accepted the out-of-tree path, so no fallback substitution
was needed:

```console
$ uv run ruff check --config "$probe/ruff.toml" src/ tests/ scripts/
ruff failed
  Cause: Failed to load configuration `.../ruff-probe/ruff.toml`
  Cause: Required version `==99.0.0` does not match the running version `0.16.7`
# exit=2
$ uv run ruff format --check --config "$probe/ruff.toml" src/ tests/ scripts/
ruff failed
  Cause: Required version `==99.0.0` does not match the running version `0.16.7`
# exit=2
```

Both non-zero, each message naming **both** the required and the running version — so the failure is the
`required-version` gate, not a TOML/parse error. Exit codes recorded as observed (2), not asserted. The
tracked `pyproject.toml` was never edited by this probe (`grep -n required-version pyproject.toml` →
`62:required-version = "==0.16.7"` before and after).

*Incidental confirmation of D2:* the cached `ruff 0.16.0` binary, run against the repo, refuses to load
config at all — `Cause: Required version '==0.16.7' does not match the running version '0.16.0'`, exit 2.
A drifted binary now fails loudly at config load, exactly as D2 intends.

**4.3** AC3 parity probe. Pre-state `git status --porcelain` was the 3 modified paths + the untracked SDD
dir. Then:

```console
$ uv run pre-commit install
pre-commit installed at .git\hooks\pre-commit
$ ls -l .git/hooks/pre-commit
-rwxr-xr-x 1 elaze 197609 668 Sep 15 10:11 .git/hooks/pre-commit
```

Probe file written **once** at the repo root, untracked, deliberately misformatted but valid Python
(`def probe( x,y ):` / `    return    x+y`, sha256 `13e1a389…`).

**Surface A first** (the environment's binary, check-only, does not mutate):

```console
$ uv run ruff format --check _ruff_parity_probe.py
unformatted: File would be reformatted
 --> _ruff_parity_probe.py:1:11
1 + def probe(x, y):
2 +     return x + y
1 file would be reformatted                          # exit=1
$ sha256sum _ruff_parity_probe.py
13e1a3895db60000b1dc7c0d8e32385a70fc45e91a403be2edc1c67632c84cf9    # unchanged by A
```

**Then surface B** (the hook's binary, which rewrites the file):

```console
$ uv run pre-commit run ruff-format --files _ruff_parity_probe.py
[INFO] Initializing environment for https://github.com/astral-sh/ruff-pre-commit.
[INFO] Installing environment for https://github.com/astral-sh/ruff-pre-commit.
ruff format..............................................................Passed
# exit=0
$ sha256sum _ruff_parity_probe.py
09f1e0981af9cfe5db31bb1c34fd89c04139ba82b9e92ad398ee35ac4f010a85    # the hook rewrote it
$ cat _ruff_parity_probe.py
def probe(x, y):
    return x + y
```

**AC3 verdict — see deviation 3 in §5.** The hook's binary judged the same bytes unformatted and rewrote
them to *exactly* the output surface A predicted; the exit code, however, was **0**, not the 1 the tasks
file expected. The two causes are mechanical: (a) the hook's entry is `ruff format --force-exclude`, a
**fixing** surface, and `ruff format` exits 0 after writing changes (only `--check` exits 1); (b)
pre-commit's "files were modified by this hook" detection uses `git diff`, which cannot see an
**untracked** file. Both were confirmed by direct measurement:

```console
$ printf 'def probe( x,y ):\n    return    x+y\n' > _ruff_parity_probe_b.py
$ uv run ruff format _ruff_parity_probe_b.py
1 file reformatted                                  # exit=0  <- the fixing surface exits 0
$ printf 'def probe( x,y ):\n    return    x+y\n' > _ruff_parity_probe_b.py
$ uv run pre-commit run ruff-format --files _ruff_parity_probe_b.py
ruff format..............................................................Passed   # exit=0
```

AC3's substance was therefore established by an additional probe that isolates the hook's **binary** from
the pre-commit wrapper (see 4.4b) — the check-mode verdict of the hook's own bundled 0.16.7 is byte-for-byte
identical to surface A's, exit code included.

**4.4** the hook's bundled binary, and the tag probe in the same measurement:

```console
$ grep -n 'ruff==' ~/.cache/pre-commit/*/pyproject.toml
/c/Users/elaze/.cache/pre-commit/repo27dpqiot/pyproject.toml:5:    "ruff==0.16.6",
/c/Users/elaze/.cache/pre-commit/repo3ptoyxgr/pyproject.toml:5:    "ruff==0.15.21",
/c/Users/elaze/.cache/pre-commit/repon1p3j7_t/pyproject.toml:5:    "ruff==0.16.7",
/c/Users/elaze/.cache/pre-commit/repoqghug3i1/pyproject.toml:5:    "ruff==0.16.0",
/c/Users/elaze/.cache/pre-commit/repoym_k5mue/pyproject.toml:5:    "ruff==0.8.0",
$ ls -ldt ~/.cache/pre-commit/*/ | head -n 3
drwxr-xr-x 1 elaze 197609 0 Sep 15 10:11 /c/Users/elaze/.cache/pre-commit/repon1p3j7_t/
drwxr-xr-x 1 elaze 197609 0 Sep  4 19:05 /c/Users/elaze/.cache/pre-commit/repo27dpqiot/
drwxr-xr-x 1 elaze 197609 0 Jul 30 13:42 /c/Users/elaze/.cache/pre-commit/repoqghug3i1/
```

**A NEW clone appeared** — `repon1p3j7_t`, created `Sep 15 10:11` (this session), pinning
`ruff==0.16.7`. The previously newest clone (`repo27dpqiot`, `Sep 4`) pinned only `0.16.6`.
⇒ **`v0.16.7` resolved: YES**, the upstream tag exists and was fetched. Task 4.8's escalation therefore
does not fire for the tag, and no `language: system` substitution, rev downgrade, or AC3-from-A-alone
claim was made.

**4.4b** exit-code parity from the hook's own bundled binary (supplementary AC3 evidence):

```console
$ ~/.cache/pre-commit/repon1p3j7_t/py_env-python3/Scripts/ruff.exe --version
ruff 0.16.7
$ printf 'def probe( x,y ):\n    return    x+y\n' > _ruff_parity_probe_c.py
$ ~/.cache/pre-commit/repon1p3j7_t/py_env-python3/Scripts/ruff.exe format --check _ruff_parity_probe_c.py
unformatted: File would be reformatted
 --> _ruff_parity_probe_c.py:1:11
1 + def probe(x, y):
2 +     return x + y
1 file would be reformatted                          # exit=1
```

Same verdict, same message, same predicted output, same exit code as surface A.

**4.5** whole-tree leg — **NOT clean; finding surfaced, not absorbed** (see deviation 4 in §5):

```console
$ git diff --stat          # before
 pyproject.toml | 6 ++++-
 tests/test_ci_workflows.py | 66 +++++
 uv.lock | 44 ++++----
$ uv run pre-commit run ruff-format --all-files
ruff format..............................................................Failed
- hook id: ruff-format
- files were modified by this hook
2 files reformatted, 9 files left unchanged
68 files left unchanged
# exit=1
$ git diff --stat          # after
 README.md | 10 +++----
 README_ES.md | 10 +++----
 (+ the three intended paths)
```

The hook rewrote **`README.md` and `README_ES.md`** — it normalised the alignment of inline comments
inside their ```` ```python ```` code blocks (`sofer_scan_dry_run(config="test.toml")   # preview` →
two spaces before `#`). Per the task's own rule the probe stopped, the affected paths were restored with
`git checkout -- README.md README_ES.md`, and the finding is surfaced here rather than absorbed.

**Characterisation (added evidence, and the reason this is not a scope change for this diff):** the
behaviour is **version-independent and pre-existing**. The `ruff-format` hook in ruff-pre-commit
`v0.16.7` declares `types_or: [python, pyi, jupyter, markdown]` — Markdown is in the hook's file set, and
the rev was already `v0.16.7` before this change. Both binaries agree on the original READMEs:

```console
$ ~/.cache/pre-commit/repoqghug3i1/py_env-python3.12/Scripts/ruff.exe format --check --isolated README.md README_ES.md
ruff 0.16.0 → 2 files would be reformatted          # exit=1
$ ~/.cache/pre-commit/repon1p3j7_t/py_env-python3/Scripts/ruff.exe  format --check --isolated README.md README_ES.md
ruff 0.16.7 → 2 files would be reformatted          # exit=1
```

So: **D1's `68 files already formatted` measurement is not falsified** — that measurement covers the
enforced `src/ tests/ scripts/` scope, in which 0.16.7 and 0.16.0 agree exactly. The README condition
predates this change, is outside the enforced scope, and is now visible only because this change is the
first to install the hook and run it over the whole tree. **No `.github/workflows/`, no `src/sofer/`, and
no rule-14 module was affected**, so the four 100.00% per-file gates were never at risk.

**4.6** cleanup and no-residue proof:

```console
$ rm -f _ruff_parity_probe.py _ruff_parity_probe_b.py _ruff_parity_probe_c.py
$ git status --porcelain
 M pyproject.toml
 M tests/test_ci_workflows.py
 M uv.lock
?? openspec/changes/2026-09-15-chore-ruff-single-authority/
```

Identical to the pre-state of task 4.3 — no tracked change, no probe residue. The hook **stays
installed** (`.git/hooks/pre-commit`, the intended contributor state); its rollback is
`pre-commit uninstall`.

**4.7** no-CI-gate static evidence (PB-10's live clause; CI-08's inverse assertion):

```console
$ grep -rn 'format' .github/workflows/               # count=0
$ grep -rn 'format --check' .github/workflows/       # count=0
$ git diff --name-only
CONTRIBUTING.md
pyproject.toml
tests/test_ci_workflows.py
uv.lock
# zero .github/workflows/ paths
```

This change arms no step and adds no workflow file.

**4.8** escalation rule — not triggered: the `v0.16.7` tag **did** resolve (4.4) and the hook **did**
materialise (4.3). No `language: system`, no rev downgrade, no third-party substitution.

### Phase 5 — Documentation, module docstring, delta text

**5.1** `CONTRIBUTING.md:77`, first sentence only. Line 77 was **re-read immediately before applying**
(required because #187 may land on the same line); #187 had not landed, so the anchor was current.
`### Code style` at `:75`, `### Type checking` at `:79` — the edit is inside the section:

```console
$ sed -n '77p' CONTRIBUTING.md
This project uses **ruff** 0.16.7 for linting and formatting. Configuration is in `ruff.toml` at the
repo root. Run `ruff check` and `ruff format` before committing — the pre-commit hook does this
automatically.
```

**5.2** boundary proof:

```console
$ git diff --word-diff CONTRIBUTING.md
@@ -74,7 +74,7 @@
 ### Code style
 This project uses **ruff** {+0.16.7+} for linting and formatting. Configuration is in `ruff.toml` at ...
$ git diff --numstat CONTRIBUTING.md
1	1	CONTRIBUTING.md
```

Exactly one changed line, exactly one inserted token (`0.16.7`) plus its space. **Precision note**: a
plain `grep -c 'ruff.toml'` over the raw `git diff` returns **2** — the unchanged `ruff.toml` sentence
appears as context on both the `-` and the `+` side of the single modified line. `--word-diff` is the
proof that no token of that sentence changed: it appears as plain text, with `{+0.16.7+}` the only
insertion. #187's defect is not absorbed.

**5.3** mutation leg 3 — the documentation half, restored by **re-editing** (never `git checkout --`,
which would have deleted this change's own edit — correction 5):

```console
$ git diff CONTRIBUTING.md | sha256sum
e049c9d7985a10325ae6b600164b8aaf7c38160f619ee367bae94574e570814f *-
$ sed -i 's/\*\*ruff\*\* 0.16.7 for linting/**ruff** for linting/' CONTRIBUTING.md
$ uv run pytest tests/test_ci_workflows.py -q -k test_contributing_names_the_declared_ruff_version
E       AssertionError: the Code style section must name ruff 0.16.7
FAILED tests/test_ci_workflows.py::test_contributing_names_the_declared_ruff_version
$ sed -i 's/This project uses \*\*ruff\*\* for linting/This project uses **ruff** 0.16.7 for linting/' CONTRIBUTING.md
$ git diff CONTRIBUTING.md | sha256sum
e049c9d7985a10325ae6b600164b8aaf7c38160f619ee367bae94574e570814f *-   # byte-for-byte match
$ uv run pytest tests/test_ci_workflows.py -q
22 passed in 0.12s
```

**5.4** module docstring reconciled (`tests/test_ci_workflows.py:1-21`), all four edits:

```diff
-`ci` specification (requirements CI-01..CI-06) by parsing the repository's
+`ci` specification (requirements CI-01..CI-08) by parsing the repository's
-scenario-verifying tests are the 15 mapped rows of the spec Test Mapping table,
-plus one supporting guard (`test_ci_workflow_files_present`) that fails loudly
-before any parse. Runtime gate exit-code evidence (CI-01 S2's local gate run)
-is recorded in the SDD verify report, not asserted here.
+scenario-verifying tests are the 18 `ci` Test Mapping rows whose verification
+names a test in this module, plus four tests owned by other capabilities or
+supporting this one — the two `coverage` COV-06 guards, the CodeQL
+private-window guard, and `test_ci_workflow_files_present`, which fails loudly
+before any parse. Runtime gate exit-code evidence (CI-01 S2's local gate run and
+CI-08 S4's required-version mismatch probe) is recorded in the SDD verify
+report, not asserted here.
```

Figures **re-derived, not copied** (task 7.6 repeats them): 22 `def test_` functions; 18 `ci`-mapped rows
over the canonical+delta union; 18 + 4 = 22 closes. **Zero version literals in the module** (see
deviation 1). `uv run ruff format tests/test_ci_workflows.py` → `1 file left unchanged`;
`uv run ruff check tests/test_ci_workflows.py` → `All checks passed!`.

**5.5** the two-part wording fix in the `ci` delta. The change root is untracked, so `git diff` cannot
show it; before/after text is recorded instead. **(1)** CI-08 body:

> before: `… A change that moves the pin SHALL refresh \`uv.lock\` in the same change; \`packaging\`
> PKG-06 owns that rule and this requirement SHALL NOT re-declare it.`
>
> after (`specs/ci/spec.md:73-77`): `… A change that moves the pin SHALL refresh \`uv.lock\` in the same
> change, confined to the ruff package block and the dev specifier. \`packaging\` PKG-06 states the same
> regeneration class for its own \`fastmcp\` declaration and SHALL NOT be read as owning this one: its
> \`uv.lock\` clause is scoped to that declaration, so the obligation for a ruff pin move is stated here,
> in CI-08.`

**(2)** the *Cross-referenced and deliberately untouched* table's PKG-06 row (`specs/ci/spec.md:185`):

> before: `CI-08 states the same obligation without re-declaring it, so the lock rule keeps exactly one owner`
>
> after: `CI-08 owns its own lock-refresh obligation for a ruff pin move; PKG-06's clause is scoped to the
> \`fastmcp\` declaration and is cited as the same class of rule, not as this one's owner.`

Exactly those two spots changed and **no fifth scenario** was added — the delta still holds four rows.

**5.6** the `process-boundary` delta is **unchanged this phase** (ratified as written): it received no
edit; its `## MODIFIED` PB-10 block replaces exactly one sentence and inserts the `(Previously: …)` note
while its **five** scenarios stay byte-identical (`grep -c '^#### Scenario:'` → `5`). Version literals in
that file occur only in the delta's own framing blockquote (`:9`, `:17` — non-normative, dropped at sync)
and in the `(Previously: …)` line (`:51`, the only one that lands in canonical, exempt by the
canonical-spec convention used at `process-boundary/spec.md:12,63,95,115,232`). The **normative** PB-10
paragraph carries **0** literals; the canonical file's normative paragraph currently carries **1** —
i.e. the invariant is 1 → 0, discharged at sync and checked in task 7.9.

**5.7** local green check:

```console
$ uv run pytest tests/test_ci_workflows.py -q
22 passed in 0.12s                                  # 19 pre-existing + 3 guards, 0 failures
$ grep -c 'pytest.skip' tests/test_ci_workflows.py
1                                                   # unchanged: only _openspec_config's
```

No new skip was introduced.

### Phase 7 — Final gates

**7.1** re-derived totals, side by side:

```console
$ uv run pytest tests/ -q      # before any edit (task 0.2)
1781 passed, 6 skipped, 1 warning in 58.24s
$ uv run pytest tests/ -q      # after
1784 passed, 6 skipped, 1 warning in 57.00s
```

Baseline **+3 passed, 0 failed, unchanged skipped count**.

**7.2 / 7.3 / 7.4** enforced-scope gates (`ci.yml:19,21`; interpreter `Python 3.13.12`, so no `--python`
flag — AGENTS.md rule 12):

```console
$ uv run ruff check src/ tests/ scripts/
All checks passed!                                  # exit=0
$ uv run ruff format --check src/ tests/ scripts/
68 files already formatted                          # exit=0
$ uv run mypy src/ scripts/
Success: no issues found in 33 source files         # exit=0
```

**7.5** rule-14 coverage gate:

```console
$ uv run coverage run -m pytest -q
1784 passed, 6 skipped, 1 warning in 68.49s
$ uv run coverage report -m
Name                    Stmts   Miss Branch BrPart  Cover   Missing
src\sofer\cli.py          580      0    166      0   100%
src\sofer\prepare.py      325      0    180      0   100%
src\sofer\publish.py      326      0    138      0   100%
src\sofer\scanner.py      159      0     76      0   100%
TOTAL                    5939    351   2298    157    93%
$ bash scripts/check_core_coverage.sh
# four scoped 100% tables, each with an empty Missing column
script exit=0
```

All four scoped rows at **100.00%** with empty `Missing`; the TOTAL floor remains the config-owned
`fail_under = 90` (`ci` CI-01), unweakened and not re-declared.

**7.6** docstring figures re-derived (never copied):

```console
$ grep -c '^def test_' tests/test_ci_workflows.py
22
$ grep '^| CI-0' openspec/specs/ci/spec.md \
    openspec/changes/2026-09-15-chore-ruff-single-authority/specs/ci/spec.md | grep -c 'test_ci_workflows.py'
18
```

Both match the docstring's quoted figures (18 + 4 = 22). The union is used deliberately, because `18` is
true of canonical + delta in both the pre- and post-sync states.

**7.7** scope proof:

```console
$ git diff --name-only
CONTRIBUTING.md
pyproject.toml
tests/test_ci_workflows.py
uv.lock
$ git status --porcelain
 M CONTRIBUTING.md
 M pyproject.toml
 M tests/test_ci_workflows.py
 M uv.lock
?? openspec/changes/2026-09-15-chore-ruff-single-authority/
```

Exactly the four intended functional paths (plus, after sync, the two canonical spec paths — Phase 6 is
not executed here, see §5 deviation 5). **Zero** `src/sofer/**`, zero `.github/workflows/**`, zero
`README*`, zero `.pre-commit-config.yaml`; no mutation residue and no probe file.

**7.8** rules 7 and 13, with commands rather than intent:

```console
$ git diff --name-only | grep -c 'README'                            # 0
$ git diff --name-only -- src/sofer/ | wc -l                         # 0
$ git diff -U0 -- src/sofer/cli.py                                   # (empty)
```

No CLI module changed, so no `help=` / `description=` string and no `_cmd_*` handler moved: since no CLI
surface, subcommand or flag changes, **no `README.md` / `README_ES.md` update and no mirroring is due**.
The only documented claim that changes is the `CONTRIBUTING.md:77` sentence (task 5.1). Recorded so the
verify phase does not flag a missing doc update.

**7.9** verify-report inputs, assembled — one section per item, each with its command:

1. **RED before any declaration edit** — `uv run pytest tests/test_ci_workflows.py -q` with the pin still
   `ruff>=0.9.0`; 3 failed / 19 passed, all three on the exact-pin assertion (§Phase 1, task 1.3).
2. **Mutation leg 1 (hook rev)** — `sed rev: v0.16.6` → `ruff-pre-commit rev must be 'v0.16.7', got
   ['v0.16.6']`; restored via `git checkout -- .pre-commit-config.yaml`; `git diff --stat` empty.
3. **Mutation leg 2 (`required-version`)** — `required-version must be '==0.16.7', got '==0.16.6'`;
   restored by re-edit; `git diff pyproject.toml | sha256sum` matches `9d40b8f4…` byte-for-byte; guards
   green again.
4. **Mutation leg 3 (`CONTRIBUTING.md`)** — `the Code style section must name ruff 0.16.7`; restored by
   re-edit; `git diff CONTRIBUTING.md | sha256sum` matches `e049c9d7…` byte-for-byte; `22 passed`.
5. **Lock diff + consistency** — `git diff --numstat uv.lock` → `22  22`; `git diff uv.lock` hunk
   `@@ -2031,27` (ruff block) + `@@ -2117,7` (dev specifier); `uv lock` a no-op at hash `341eda3d…`;
   `uv lock --check` exit **0**.
6. **S4 leg A** — `uv run ruff check src/ tests/ scripts/` exit 0; `uv run ruff format --check src/
   tests/ scripts/` exit 0, `68 files already formatted`.
7. **S4 leg B** — `--config /tmp/.../ruff-probe/ruff.toml` (`required-version = "==99.0.0"`): both
   `ruff check` and `ruff format --check` exit **2**, each naming `==99.0.0` required and `0.16.7`
   running.
8. **AC3 verdicts** — surface A `uv run ruff format --check _ruff_parity_probe.py` exit **1**, `1 file
   would be reformatted`; surface B `uv run pre-commit run ruff-format --files …` exit **0** but rewrote
   the file to exactly A's predicted output; hook-binary check-mode parity exit **1** with identical
   output.
9. **Hook's bundled pin** — `grep -n 'ruff==' ~/.cache/pre-commit/*/pyproject.toml` →
   `repon1p3j7_t/pyproject.toml:5: "ruff==0.16.7"`, clone created `Sep 15 10:11`.
10. **Whole-tree leg** — `pre-commit run ruff-format --all-files` exit 1, `2 files reformatted`
    (`README.md`, `README_ES.md`), reverted, characterised as version-independent; `grep -rn 'format'
    .github/workflows/` → 0; `grep -rn 'format --check' .github/workflows/` → 0.
11. **PB-10 normative-literal check** — `awk '/^### Requirement: Formatter integrity/{f=1}
    /^\(Previously:/{f=0} f' specs/process-boundary/spec.md | grep -cE '0\.16\.[0-9]'` → **0** (delta);
    the same extraction over the canonical file's normative paragraph → **1** pre-sync. Invariant 1 → 0.
12. **AC5 ownership correction** — CI-08 owns the lock-refresh obligation; PKG-06's clause is scoped to
    its `fastmcp` declaration and is the same class, not the owner (§Phase 2, task 2.8).

**7.10** verify-phase scoping rules, recorded so verify cannot manufacture false failures:

1. PB-10's *"Exactly the six test files changed"* and *"Formatting-only"* scenarios describe the
   historical #177 edit and **SHALL NOT** be measured against this diff (this change touches
   `pyproject.toml`, `uv.lock`, `CONTRIBUTING.md` and `tests/test_ci_workflows.py`, plus the two
   change-root spec deltas).
2. The version-literal invariant is **normative clauses 1 → 0**, with the `(Previously: …)` note exempt
   by canonical-spec convention — so `grep "0.16"` over a whole spec file is **not** a check. The delta's
   framing blockquote also carries literals and is dropped at sync.
3. Canonical specs under `openspec/specs/**` are **`sdd-sync`'s write**, never verify's.
4. `ci/spec.md`'s `## Purpose` paragraph deliberately stays enumerating `CI-01..CI-06`: the staleness is
   pre-existing (CI-07 already stale), fixing it would edit canonical prose for another requirement's
   defect, and it must be named in the PR body so a reviewer does not read it as an oversight.

---

## 5. Deviations from the design / plan, with reasons

1. **Version literals removed from the guard module.** `design.md` §3.2 gives the helper "verbatim" with
   the literals `0.16.7` (docstring example) and `0.16.0` (assertion message). Task 1.1 ("**No test may
   carry a version literal**"), task 5.4 ("introduce no version literal anywhere in the module") and
   CI-08 S3 ("the guard SHALL hold no version literal of its own") forbid exactly that. The pre-change
   module held `0` version literals; adopting §3.2 verbatim would have introduced 2 and re-created the
   class of defect this change exists to remove. Both were rewritten digit-free while preserving the
   drift-explaining intent of the assertion message
   (`"… lets \`uv lock\` drift the formatter away from the version the hook runs, which is exactly how
   the ambient binary drifted from the pre-commit rev"`). Verified: `grep -c '0\.16'
   tests/test_ci_workflows.py` → **0**. **The tasks file supersedes the design's sample code here.**
2. **`uv.lock` had already been refreshed before the explicit probe.** `uv run` re-locks by default when
   declarations change, so the task 2.5 step-0 assertion (`git status --porcelain uv.lock` → empty) was
   already false by the time the probe ran, and no `--upgrade-package` fallback was needed. The explicit
   `uv lock` was still run and proved a byte-for-byte no-op (identical diff hash `341eda3d…`). Recorded
   because the tasks file asserted a clean baseline.
3. **AC3 surface B exits 0, not 1.** The tasks file expected `pre-commit run ruff-format --files …` to
   exit 1 with `1 file would be reformatted`. It exits **0** and reports `Passed`, while *rewriting* the
   file. Causes, both measured: (a) the hook's entry is `ruff format --force-exclude` — a **fixing**
   surface; only `--check` returns 1; (b) pre-commit detects "files were modified by this hook" through
   `git diff`, which is blind to an **untracked** file. AC3's substance is still discharged: the hook's
   bundled `ruff 0.16.7` judged the same bytes unformatted, produced the byte-identical formatted result,
   and — run in check mode — returned the same exit 1 and the same message as the environment binary.
   No working around (`language: system`, a rev downgrade, or claiming AC3 from surface A alone) was
   used.
4. **Task 4.5's whole-tree leg is NOT clean.** `pre-commit run ruff-format --all-files` reformatted 2
   tracked files (`README.md`, `README_ES.md`). Per the task's own tripwire the affected paths were
   reverted and the finding is surfaced, never absorbed. Added evidence characterises it as
   **pre-existing and version-independent** (`types_or: [… markdown]` on a hook whose rev was already
   `v0.16.7`; both 0.16.0 and 0.16.7 report the same `2 files would be reformatted`), so D1's
   `68 files already formatted` on the enforced scope is **not** falsified and no rule-14 module was at
   risk. **Escalated to the parent as a standalone finding — see §7.**
5. **Phase 6 (tasks 6.1–6.4) not executed.** The parent prompt for this launch states: *"Do not edit
   canonical specs under `openspec/specs/**`. Those are the `sdd-sync` phase's job."* The tasks file's own
   Phase 6 heading agrees: *"Owning phase: `sdd-sync`."* Although the four rows carry
   `<!-- sdd-owner: implementation -->` markers, the parent's explicit scope boundary and the phase's own
   declaration are authoritative, and Phase 6's central property — landing **both** deltas in **one**
   operation, because PB-10 forward-references `ci` CI-08 — is inherently a sync-phase property. The four
   rows are left unchecked and are the change's only remaining work.
6. **Task count is 49, not the 40 stated in this launch's prompt.** The tasks artifact holds 49 checkbox
   rows (4+5+8+3+8+7+4+10) and the native status engine reports `total: 49`; the artifact and the engine
   agree, so the artifact was used.
7. **Task 5.2's `ruff.toml` check read literally returns 2, not 0.** The unchanged `ruff.toml` sentence
   appears as context on both sides of the single modified line in a raw `git diff`. `--word-diff` —
   which is what the task specifies — proves the intent: exactly one changed line, one inserted token,
   and no token of the #187 sentence altered.
8. **`pre-commit install` left a per-clone, untracked `.git/hooks/pre-commit`** (the intended contributor
   state, per design §5.2(d)). It was absent in this clone before task 4.3. Rollback:
   `pre-commit uninstall`. It is not a tracked change and cannot appear in the diff.

**Nothing was silently truncated for budget.** No comment, blank line, doc, or test was removed or
compressed to fit the review budget.

---

## 6. Remaining work — the exact unchecked task lines

```text
- [ ] 6.1 Land **both** deltas in a **single sync operation**: append the four CI-08 Test Mapping rows to
- [ ] 6.2 Post-sync reference invariant: `grep -c "CI-08" openspec/specs/ci/spec.md` → non-zero (the
- [ ] 6.3 Post-sync table arithmetic: `grep "^| CI-0" openspec/specs/ci/spec.md | wc -l` → **26**
- [ ] 6.4 Canonical-scope guard: `git diff --name-only` shows only those two canonical spec paths among
```

All four are Phase 6 (`sdd-sync`). Everything else — every apply-owned task — is complete and marked
`- [x]` in the persisted artifact.

---

## 7. Workload, PR boundary, and risks

**Workload.** Measured **132 changed lines** (103 added / 29 deleted) across the four functional paths
(`CONTRIBUTING.md` 1/1, `pyproject.toml` 5/1, `tests/test_ci_workflows.py` 75/5, `uv.lock` 22/22). The
tasks file forecast ≈184 including spec-delta prose; the functional subtotal lands comfortably under
both the canonical 400-line budget and the session's 1500-line budget. SDD artifacts under the change
root are not review load by this repository's own precedent.

**PR boundary.** **Single PR** against `dev` (~132 functional lines). `400-line budget risk: Low`,
`Chained PRs recommended: No`, `Decision needed before apply: No`. The delivery strategy is `auto-chain`,
but risk is Low so **no chain was selected and `ask-on-risk` was not exercised**; no `size:exception` is
requested or needed. The guard tests stay in the same PR as the CI-08 scenario rows they satisfy
(AGENTS.md rule 6). Work-unit ordering for commits: unit 1 guards (RED) → unit 2 declarations + lock →
unit 3 mutation/runtime evidence → unit 4 docs + docstring + delta text → unit 5 Phase 6 sync + final
gates. **Nothing was committed or pushed** — the tree is left as an uncommitted working-tree change, as
instructed.

**Risks / escalated findings.**

| # | Finding | Severity | Status |
| --- | --- | --- | --- |
| R1 | `pre-commit run ruff-format --all-files` rewrites `README.md` and `README_ES.md` (inline-comment alignment inside their Python code blocks). Pre-existing, **version-independent** (both 0.16.0 and 0.16.7 agree), outside the enforced `src/ tests/ scripts/` scope, caused by the hook's `types_or: [… markdown]` on a rev that was already `v0.16.7`. Consequence: any contributor with the hook installed and a README change in the diff will get those two files rewritten. | Medium (contributor-facing) | **Escalated, not absorbed.** Reverted here. Wants its own issue; related to #194's ownership of the hook/gate decision. |
| R2 | AC3's exit-code parity is 1 vs 0 between the check surface and the hook surface (deviation 3). | Low | Substance discharged (same verdict on same bytes, plus hook-binary check-mode parity); recorded, not worked around. |
| R3 | `[tool.ruff] required-version` fails **every** ruff invocation at another version, including editor integrations and `uvx ruff` (D2's accepted cost). Incidental evidence: the cached 0.16.0 binary now refuses to load this repo at all. | By design, accepted | Documented in the `pyproject.toml` comment and now in `CONTRIBUTING.md:77`. |
| R4 | `ci/spec.md`'s `## Purpose` still enumerates `CI-01..CI-06` (stale for CI-07 and CI-08). | Low (cosmetic) | Deliberately untouched (pre-existing, another requirement's defect); must be named in the PR body. |
| R5 | `AGENTS.md` rule 6's tally literal (`1766 passed, 6 skipped`) is stale — the re-derived baseline is **1781 passed, 6 skipped**. | Low | Out of scope (owned by the documentation wave); re-derived rather than copied, per instruction. |

---

## 8. Session preflight consumed

Execution mode `auto` · artifact store `hybrid` (this file + the Engram record) · delivery strategy
`auto-chain` · review budget 1500 changed lines (400 canonical) · chain strategy deferred until
chaining is selected (not needed). `exception-ok` was **not** inferred or requested, and no
`size:exception` gate was exercised, because the change is inside budget under both readings.
