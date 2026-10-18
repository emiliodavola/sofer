# Feature: card-control-char-escape — issue #348

**Branch:** `fix/348-card-control-char-escape` from `dev@c68e090`
**Issue:** `emiliodavola/sofer#348` — *bug(prepare): the generated Dataset Card embeds a raw NUL byte from a sample value, making the Markdown artifact non-text*
**Delivery PR:** pending — push and PR creation are the maintainer's decision
**SDD change:** `openspec/changes/archive/2026-10-18-fix-card-control-char-escape/` (archived inside this branch, AGENTS.md rule 15)
**Phase:** 2 of the 2026-10-18 batch (independent of WU-1; no shared file). Rebased onto `dev@d07557e` after PR #350 merged, and the gate evidence re-taken there.

## Goal

`build/README.md` — the Dataset Card, published as the repository's landing page —
interpolates each column's sampled value into a Markdown table cell verbatim:
`` `{s.example}` `` at `repo_compliance.py:1767` (flat table) and `:1787`
(per-sheet collapsible table). A source value that is a control character lands in
the artifact as a raw byte, and `grep README.md` then answers `Binary file
README.md matches`, `diff` and patch tooling treat it as binary, and the card is
no longer a text document.

## Specs

S1 — #348 `## Expected behaviour` (verbatim): "Control characters escaped when a
sampled value is rendered into Markdown — `\0`, `U+0000`, or a visible
placeholder — or the sample column normalising non-printable values before
interpolation. The card is a document; it should not carry bytes that make it
binary."

S2 — #348 `## Impact` (verbatim): "The card is not valid text for ordinary
tooling: `grep README.md` reports `Binary file README.md matches` and stops
printing matches, so the card cannot be searched without `-a`. Editors, `diff`,
and patch tooling classify it as binary and may refuse to show it."

S3 — #348 `## Not the defect` (verbatim): "The data is correct: `build/cpv2022.parquet`
holds the NUL faithfully, which is what a faithful conversion should do." — so the
fix is in the rendering, never in the sampled data or the Parquet.

S4 — maintainer decision, 2026-10-18 (verbatim): "2. ambos" — the escaping covers
control characters **and** the other characters that break the same table cell
(`|`, and a backtick inside the code span).

## Tasks

| # | Task | Spec | Commit |
| --- | --- | --- | --- |
| T1 | One shared cell renderer: control character → `\xNN`, `\|` for a pipe, fence grows when the value holds a backtick | S1, S4 | `d69aa86` |
| T2 | Both Data Fields tables (flat and per-sheet) render data-derived cells through it, in one shared row builder | S1, S2 | `d69aa86` |
| T3 | Tests: the card holds no raw control byte, a pipe cannot split a row, a backtick keeps its value | S1-S3 | `d69aa86` |
| T4 | `repo-compliance` spec clause (RC-R21) + the change's delta and archive report | S1-S4 | `bc2dead` |
| T5 | Gates: pytest 2488/9 on `dev@d07557e`, scanner/cli at 100.00%, ruff, mypy, pyright, mapping checker | — | `d69aa86` |

## Log

**L1** — maintainer request (verbatim): "revisá los issues de tipo bug y armate un
roadmap de implementación"

**L2** — maintainer decisions (verbatim): "1. sí incluir cli.py / 2. ambos / 3.
explicito / abrí los issues también"

**L3** — evidence: two render sites (`repo_compliance.py:1767`, `:1787`); the sample
is taken raw from `non_missing[0]` at `:718`, `:773`, `:885`; the column name and
`origin` are interpolated into the same rows, so the renderer is applied to every
data-derived string cell (`s.name`, `origin`, `s.example`) and not only to the
reported one.

**L4** — scope boundary (recorded, not a silent omission): the guard is on the
card's Data Fields tables. The Parquet keeps the NUL (S3), and the codebook /
profile / render artifacts are separate generators with their own inputs.

**L5** — RED observed first (`4 failed, 1 passed` on `TestCardDataCellsArePrintable`),
then a regression caught by a pre-existing test: my first version fenced the `File`
cell with backticks where the card has always printed the origin bare, and
`TestDataFieldsFileColumn::test_card_renders_file_column` failed. The File cell now
uses `_md_visible` (escaped, unfenced) and only the name/Example cells use `_md_cell`.

**L6** — end-to-end differential on the real artifact (one-row CSV whose only value
is a NUL, through `init` → `scan` → `prepare`): previous code 1725 card bytes with
1 NUL byte and no escape; this change 1728 bytes with 0 NUL bytes and the cell
showing `\x00`. The Parquet still holds the value (53 NUL bytes), so S3 holds.
Correction recorded: my first NUL check used `grep $'\x00'`, which bash expands to an
empty pattern and which counted all 98 lines as "NULs"; every figure here comes from
`tr -cd '\000' | wc -c`.

**L7** — rebase and final evidence: PR #350 merged into `dev` as `d07557e`; the WU-2
commits were rebased onto it (clean) and the battery re-taken there — suite
`2488 passed, 9 skipped` (2476 baseline + 7 from #345 + 5 from this change),
`scanner.py`/`cli.py` at 100.00%, TOTAL 94%, ruff/mypy/pyright clean,
`check_test_mapping.py` OK. The first suite run (2481) was on the pre-merge base and
was deliberately discarded as evidence. Commits: `d69aa86`, `bc2dead`, and the
closeout commit that archives the change.
