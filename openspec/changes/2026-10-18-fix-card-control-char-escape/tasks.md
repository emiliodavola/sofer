# Tasks: fix-card-control-char-escape

**Change** `2026-10-18-fix-card-control-char-escape` (GitHub **#348**) · branch
`fix/348-card-control-char-escape` from `dev@c68e090` · store **hybrid**.

**One-line outcome:** the Data Fields tables render every data-derived cell as
printable text, so a corpus whose sample value is a control character produces a
card that is a text file, and a value containing `|` or a backtick cannot break the
table.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real
red-then-green:

- **RED:** with the pre-fix `src/`, a `ColumnSchema` whose `example` is `"\x00"`
  produces a card containing the raw byte — the new assertions fail on
  `b"\x00" in result.encode("utf-8")` — and a card whose `example` is `"a|b"`
  renders a row with an extra cell.
- **GREEN:** the same tests pass with the helper in place, and the ordinary-value
  card is unchanged.

The measured RED output is recorded in the archive report.

---

## Tasks

| # | Task | Spec | State |
| --- | --- | --- | --- |
| T1 | `_md_visible` + `_md_cell` in `repo_compliance.py` | S1, S4 | pending |
| T2 | Both Data Fields branches render `s.name`, `origin` and `s.example` through the helper | S1, S2 | pending |
| T3 | Tests: no raw control byte in the card, a pipe cannot split the row, a backtick keeps the value, ordinary values unchanged | S1-S3 | pending |
| T4 | RC-R21 clause + RC-R21.10/.11 in the canonical spec, the delta and the archive report | S1-S4 | pending |
| T5 | Gates: `pytest`, `ruff check`, `ruff format --check`, `mypy`, `pyright`, `scripts/check_test_mapping.py` | — | pending |

## Work units

1. `fix(card): escape data-derived cells so the card stays text (#348)` — T1, T2, T4.
2. `test(card): pin the printable-cell contract (#348)` — T3.
3. `chore(odd): record the #348 work units and archive the change` — T4, T5.
