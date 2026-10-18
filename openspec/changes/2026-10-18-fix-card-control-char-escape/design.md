# Design — `2026-10-18-fix-card-control-char-escape`

> **Change** `2026-10-18-fix-card-control-char-escape` (issue **#348**) · branch
> `fix/348-card-control-char-escape` from `dev@c68e090` · store **hybrid**.

---

## 1. The defect, precisely

The card builds its Data Fields rows by interpolating the sampled value inside
backticks, in both table branches:

```python
# repo_compliance.py:1767 (flat table) and :1787 (per-sheet <details> table)
lines.append(
    f"| `{s.name}` | {s.dtype} | {file_cell} | {'Yes' if s.nullable else 'No'} | "
    f"`{s.example}` | {s.unique} | {s.missing}% |"
)
```

and the sample is taken raw from the row (`:718`, `:773`, `:885`):

```python
example = non_missing[0] if non_missing else ""
```

Measured on the corpus of #348: 90 805 bytes with exactly one NUL at offset
37 207, inside that cell. Nothing else in the card is affected — the artifact is
valid UTF-8, but it is not valid text, and `grep`/`diff` classify it as binary.

## 2. Why the fix belongs in the renderer

`#348` states the boundary itself: the Parquet holds the NUL faithfully and that is
correct. Normalising at sampling time would change what the card claims the data
contains while leaving the class of defect open (any other generator that renders
the same value would repeat it). The card is a **document**, so the document
generator is where a value becomes printable text.

The same reasoning covers the neighbours that break the same cell and were not in
the original report:

| character in a value | today | with the helper |
| --- | --- | --- |
| `\x00` (NUL) | raw byte in the file | `\x00` in the cell |
| `\n` | breaks the row | `\x0a` in the cell |
| `a\|b` | splits the row into two cells | `a\\\|b`, one cell |
| ``a`b`` | closes the code span early | ``` ``a`b`` ``` |

## 3. The helper

```python
def _md_visible(value: str) -> str:
    """Render *value* as printable text for a Markdown table cell."""
    return "".join(
        f"\\x{ord(ch):02x}" if unicodedata.category(ch) == "Cc" else ch for ch in value
    ).replace("|", "\\|")


def _md_cell(value: str) -> str:
    """Render *value* as one code-spanned Markdown table cell."""
    text = _md_visible(value)
    fence = "``" if "`" in text else "`"
    return f"{fence}{text}{fence}"
```

`unicodedata` is already imported in the module. `Cc` is the control category, so
this covers C0, DEL and C1 — including the newline and carriage return that would
otherwise break a row. The fence grows only when it must, so the common case keeps
the current single-backtick output and RC-R21.06's "unchanged card" scenario still
holds for ordinary data.

Applied at four sites: `s.name`, the `origin` cell and `s.example`, in both the flat
and the per-sheet branches. `s.dtype`, `s.unique` and `s.missing` are generated
values and are left as they are.

## 4. Files touched

| file | why |
| --- | --- |
| `src/sofer/repo_compliance.py` | the two helpers and the four rendering sites |
| `tests/test_repo_compliance.py` | the printable-card contract |
| `openspec/specs/repo-compliance/spec.md` | RC-R21 clause + RC-R21.10/.11 |
| `openspec/changes/.../specs/repo-compliance/spec.md` | the delta |

## 5. Risk

Low and local: the helper changes rendered output only for values that already
produce a broken or binary artifact, so an existing card with ordinary sample
values renders byte-identically. `repo_compliance.py` has no per-file coverage
floor (the 100% mandate covers `cli`, `scanner`, `prepare`, `publish`), but the new
helper is fully exercised by the new tests regardless.
