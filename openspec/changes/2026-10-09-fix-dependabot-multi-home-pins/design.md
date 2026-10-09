# Design — `2026-10-09-fix-dependabot-multi-home-pins`

> **Change** `2026-10-09-fix-dependabot-multi-home-pins` (GitHub **#275**) · branch
> `ci/275-dependabot-multi-home-pins` · store **hybrid**.
>
> **Inputs:** `proposal.md` (this change) and the measured evidence recorded below. No other
> document is consulted; every fact below is a citation of the parent's shell-run evidence.

---

## 1. The defect, restated precisely

Three declarations must agree, and only one is reachable by the bot:

| Home | `mypy` | `pyright` | Movable by the `uv` ecosystem |
| --- | --- | --- | --- |
| `pyproject.toml` `[dependency-groups] dev` | `mypy==2.3.1` | `pyright==1.1.414` | **yes** (+ `uv.lock`) |
| `openspec/project.md` | `mypy 2.3.1` | `pyright 1.1.414` | no |
| `openspec/config.yaml` | `mypy 2.3.1` | `pyright 1.1.414` | no |

The enforcing guard derives the version from the `pyproject.toml` pin and requires both `openspec`
files to name it. Therefore a bot bump of either analyzer is **red by construction**, and because
Dependabot groups all minor/patch `uv` updates together, one poisoned member withholds every
co-mingled safe bump as well (fail-fast cancels the matrix).

## 2. Measured evidence (parent shell runs, quoted)

**PR #271** — `OPEN`, base `dev`, head `dependabot/uv/python-minor-and-patch-3b8b099728`,
`maintainerCanModify=false`, created 2026-10-05. Four bumps:

```
fastmcp        4.0.8  → 4.0.10   single-home, safe
python-dotenv  1.2.3  → 1.2.4    single-home, safe
mypy           2.3.1  → 2.4.0    multi-home  ← poisons the group
coverage       7.16.1 → 7.16.2   single-home, safe
```

**CI run 37273543267** — `lint` green, `Analyze Python` green, two jobs red:

```
FAILED tests/test_ci_workflows.py::test_openspec_context_declares_the_enforced_tool_versions
AssertionError: openspec/project.md must name the enforced mypy 2.4.0 (issue #258)
1 failed, 2000 passed, 2 skipped
```

Failing jobs: `test (ubuntu-latest, 3.14)` and `coverage`. The remaining ten matrix jobs report
`CANCELLED` (fail-fast), so the three safe bumps are withheld by an unrelated analyzer bump.

## 3. The edits

### 3.1 `.github/dependabot.yml`

`updates[uv].ignore` gains two bare entries, placed with the existing blanket `ruff` entry so the
blanket ignores read as one group and the narrowed one follows:

```yaml
    ignore:
      - dependency-name: "ruff"
      - dependency-name: "mypy"
      - dependency-name: "pyright"
      - dependency-name: "fastmcp"
        update-types: ["version-update:semver-major"]
```

The bump-policy comment gains one bullet, in the voice of the existing `ruff` bullet, stating the
three text homes, that the `uv` ecosystem can move only the first, that every PR it would open is
red (#275), and pointing at `CONTRIBUTING.md`.

### 3.2 `tests/test_ci_workflows.py`

One guard, placed immediately after `test_dependabot_ignores_the_coordinated_ruff_pin`:

```python
def test_dependabot_ignores_the_coordinated_analyzer_pins() -> None:
    """CI-14 S4: the `uv` update ignores `mypy` and `pyright` at every update type.
    ...
    """
    uv = _dependabot_update("uv")
    ignores = uv.get("ignore", [])
    assert isinstance(ignores, list), "the `uv` update's `ignore` must be a list"
    for name in ("mypy", "pyright"):
        entries = [entry for entry in ignores if entry.get("dependency-name") == name]
        assert len(entries) == 1, f"expected exactly one `{name}` ignore entry, found {entries!r}"
        assert "update-types" not in entries[0], (
            f"the `{name}` ignore must not narrow its scope: its version is declared in the "
            "pyproject dev pin and named in openspec/project.md and openspec/config.yaml, and "
            "Dependabot can move only the first (GitHub #275)"
        )
```

**Guard properties (D3).** It reuses the existing `_dependabot_update` helper, carries **no version
literal** (CI-08 S1/S3 discipline), and cannot pass vacuously: it asserts the `ignore` value is a
list and asserts exactly one entry per package. It mirrors the S1 guard's shape so the two
coordinated-pin classes are asserted identically.

### 3.3 `openspec/specs/ci/spec.md`

CI-14 is **amended, not replaced** (D4): one bullet added to the requirement body (between the
`ruff` bullet and the `fastmcp` bullet, matching the `ignore` list's order), one scenario added
after `uv updates ignore the coordinated ruff pin`, the header note extended with the change's
attribution, and **one Test Mapping row** inserted after the `ruff` row.

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, and this change declares policy rather than
production behaviour. The honest red-then-green carrier is the **guard plus the mapping gate**, and
both were observed red for the exact reasons the change exists, before any config or spec row was
written:

| Gate | RED (measured) | GREEN (measured) |
| --- | --- | --- |
| `pytest tests/test_ci_workflows.py::test_dependabot_ignores_the_coordinated_analyzer_pins` | `AssertionError: expected exactly one 'mypy' ignore entry, found []` — `tests/test_ci_workflows.py:1318` | `1 passed` |
| `uv run python scripts/check_test_mapping.py` | `FAIL: ci: scenario has no mapping row: 'uv updates ignore the coordinated analyzer pins'` — 1 violation | `exit=0`, `INFO: ci: 51 scenario(s), mapped` |

The focused guard file went **51 → 52 passed**. There is no REFACTOR target: the change adds a
declaration and its assertion.

## 5. Affected areas and review load

| File | Change | Est. lines |
| --- | --- | --- |
| `.github/dependabot.yml` | 2 ignore entries + 1 comment bullet | +8 |
| `tests/test_ci_workflows.py` | 1 guard + docstring | +25 |
| `openspec/specs/ci/spec.md` | 1 bullet + 1 scenario + 1 mapping row + note extension | +18 |
| `CONTRIBUTING.md` | 1 bullet + count word | +7 / −1 |
| `AGENTS.md` | 1 bullet re-wrapped | +1 / −1 |
| SDD artifacts | not source | — |

## 6. Rollback

Additive and revert-only. Reverting the `ignore` entries restores the exact prior behaviour (the
bot opens the red PR again); reverting the guard, the CI-14 amendment and the mapping row together
leaves no requirement asserting a policy that does not exist. The three doc bullets revert with
them. No state, no migration, no runtime impact — nothing in `src/` is touched.

## 7. Success criteria

SC-1..SC-6 of `proposal.md` §7. Runtime evidence for SC-3/SC-4 is recorded in the verify report.
