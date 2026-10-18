# Proposal — `2026-10-18-fix-card-control-char-escape`

> **Change** `2026-10-18-fix-card-control-char-escape` · issue **#348** · branch
> `fix/348-card-control-char-escape` from `dev@c68e090` · store **hybrid**
> (this folder + Engram mirror).
>
> **Status:** implementation in progress; to be archived inside the delivering PR
> (AGENTS.md rule 15).

---

## 1. Intent

The Dataset Card is the repository's landing page and a Markdown document, and one
of its table cells is filled with a sampled data value verbatim. A corpus whose
sample value is a control character therefore produces an artifact that ordinary
tools classify as binary: `grep README.md` prints `Binary file README.md matches`
and stops, and `diff`/patch tooling may refuse to show it. The measurement in #348:
90 805 bytes, exactly one NUL at offset 37 207, in the `Example` cell of the
`### Data Fields` table.

The data is not the defect — the Parquet must keep the value faithfully. The defect
is that a document generator writes an unescaped control byte into a document.

## 2. Scope

**In:** one shared renderer for the data-derived cells of the Data Fields tables
(the flat table and the per-sheet collapsible tables); control characters rendered
visibly, `|` escaped so it cannot split a row, code-span fence growing when the
value itself contains a backtick; the `repo-compliance` spec clause and the tests.

**Out:** the sampled values, the Parquet, the card's `bias_risks_limitations`
prose (already documents the anomaly), the codebook / profile / render generators,
and any change to `config.CARD_COLLAPSE_THRESHOLD`.

## 3. Approach

One helper, used by every data-derived cell:

- a character in the Unicode `Cc` category is rendered as its `\xNN` escape
  (so a value that is a NUL renders as `\x00`, a value with a newline as `\x0a`);
- `|` is escaped as `\|` — GFM honours the backslash inside a code span, which is
  what keeps the row from splitting;
- the code span is closed with one backtick, or two when the value contains a
  backtick, so the rendered cell is the value and never a broken span.

Applied to `s.name`, the `origin` cell and `s.example` in both table branches. The
`dtype` cell and the numeric cells are generated vocabularies and stay as they are.

## 4. Affected specs

- `repo-compliance` — RC-R21 gains the rendering clause and two scenarios
  (RC-R21.10, RC-R21.11). `repo-compliance` is a permanent declared-backlog spec
  (`openspec/test-mapping-registry.md:40`), so no `## Test Mapping` row is owed and
  the registry is not edited.

## 5. Delivery

One branch, one delivery PR against `dev`, archived inside that PR. Work-unit
commits:

1. `fix(card): escape data-derived cells so the card stays text (#348)` — T1, T2.
2. `test(card): pin the printable-cell contract (#348)` — T3, T4.
3. `chore(odd): record the #348 work units and archive the change` — T4, T5.
