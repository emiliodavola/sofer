# Verify Report: Align the fastmcp cap to `>=4,<5` (#257)

**Change**: `docs-fastmcp-cap-drift`
**Mode**: SDD
**Branch**: `docs/257-fastmcp-cap-drift` (base `dev` @ `5f6c2de`)

## Verification evidence

| Check | Command | Result |
| --- | --- | --- |
| Focused guard | `uv run pytest tests/test_packaging.py -q -k fastmcp_cap` | `1 passed` |
| Wheel cap test | `uv run pytest tests/test_mcp_server.py -q -k wheel_declares_script_and_extra` | skipped locally (hatchling absent); CI builds the wheel |
| Full suite | `uv run pytest tests/ -q` | `1989 passed, 1 skipped` |
| Lint | `uv run ruff check src/ tests/ scripts/` | passed |
| Format | `uv run ruff format --check src/ tests/` | 73 files already formatted |
| Test-mapping contract | `uv run python scripts/check_test_mapping.py` | `OK: test-mapping contract holds` |

## Negative controls

| Probe | Result |
| --- | --- |
| packaging spec cap reverted to `fastmcp>=3.4,<4` | FAILS, restored |
| CONTRIBUTING upper bound `<5` → `<6` | FAILS, restored |
| contradictory `fastmcp>=3,<4` added to a spec | FAILS, restored |

Working tree restored byte-for-byte after each probe.

## Independent verification (subagent)

A read-only adversarial subagent verified the change against `pyproject.toml`, `uv.lock`,
`tests/test_mcp_server.py`, both canonical specs, `CONTRIBUTING.md`, and `.github/dependabot.yml`.
**Verdict: PASS** on all six items (shipped truth, canonical specs, prose homes, guard quality,
delta↔canonical equality, scope discipline).

### Findings and resolution

- **W3 (prose homes had no positive upper-bound check)** — the guard now asserts `` `<5` `` is
  named in `CONTRIBUTING.md` and `.github/dependabot.yml`, so a drift to `` `<6` `` fails. Fixed.
- **W4 (a contradictory spec cap escaped)** — the guard now rejects any fastmcp cap in either
  spec other than the derived one. Fixed.
- **W1/W2 (removing a pyproject home entirely still passes)** — latent; the change does not
  alter the three pyproject homes and the issue's guard asks for cap *agreement*. Reported, not fixed.
- The remaining `<4` in `openspec/specs/ci/spec.md:711` is CI-14's historical narrative (it
  records that Dependabot rewrote the then-declared cap). It is not a requirement; left intact.

Unresolved findings: none material.
