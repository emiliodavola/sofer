# Design — `2026-10-16-feat-card-section-keys`

> **Change** `2026-10-16-feat-card-section-keys` (issue **#291**) · branch
> `feat/291-card-section-keys` from `dev@6786ba1` · store **hybrid**.

---

## 1. The defect, precisely

`build_dataset_card()` emitted seven sites from a sentinel and read no configuration for any of them:

| Site | Emitted | Fillable before |
| --- | --- | --- |
| `### Dataset Sources` → `- **Repository:**` | `_ns` | no |
| `### Direct Use` | `[More Information Needed]` | no |
| `### Out-of-Scope Use` | `[More Information Needed]` | no |
| `### Curation Rationale` | `[More Information Needed]` | only via `[meta] study_design` |
| `## Bias, Risks, and Limitations` | `[More Information Needed]` | no |
| `## Dataset Card Contact` | `_ns` | no |

The issue's reproduction is exact: a config with every ROTW field filled, `grep -c 'TODO'` on the card
→ 0 and `grep -c '\[More Information Needed\]'` → 4, plus 2 × `[Not specified]`. Nothing reported an
error; the only way to notice was to read the output files.

## 2. Why "add the keys" rather than "omit the section"

The issue prefers omission, and that is the cleaner-looking rule. It is not the cheaper one here:
`openspec/specs/repo-compliance/spec.md` §2.1.2 **requires** the placeholder ("the Dataset Card body
SHALL use a placeholder string such as `"[Not specified]"` for that section"), and the *Minimal config*
scenario requires it again. Omitting a section would therefore carry a spec delta and rewrite the tests
that assert the sentinel, for a card that is shorter but no more informative.

Adding the keys fixes the reported defect — a **fully-filled** config shipping placeholders — without
touching the rule that an unfilled config states it is unfilled. That is the maintainer's decision D1,
and the issue's own option 3 is delivered alongside it for `repository`.

## 3. The edits

### 3.1 `src/sofer/model.py`

Five fields on `DatasetConfig`, all `str`, all defaulting to `""`, read in `from_toml` with
`meta.get(key, "")` so an absent key is unchanged behaviour:

```python
repository: str = ""
direct_use: str = ""
out_of_scope_use: str = ""
bias_risks_limitations: str = ""
contact: str = ""
```

### 3.2 `src/sofer/repo_compliance.py`

- `_MORE_INFO` is promoted to a module constant. It was four identical inline literals; one constant
  means the sentinel the card emits and the value a test asserts cannot drift, and the "omit instead"
  variant the issue also offered becomes one edit rather than four (AGENTS.md rule 4).
- Each site reads its key with `.strip()` and falls back to the sentinel, so a whitespace-only value
  behaves exactly like an unset one — a value that is only whitespace is not content.
- `- **Repository:**` falls back to `cfg.source.strip()` **before** `_ns`: `source` is conventionally
  the organisation and is the best available value for a repo link, which is the issue's option 3.
- `### Curation Rationale` keeps `study_design_content` as its only fill path, which is the issue's
  "promoted from the documented-but-obscure path to the obvious one".

### 3.3 Tests

`TestCardSectionKeys` (8 tests) and `TestCardSectionKeysFromToml` (2 tests).

Three of them had to be corrected while writing them, and the corrections are the interesting part
because each was a wrong premise of mine rather than a code defect:

| First form | What it showed | Final form |
| --- | --- | --- |
| `test_a_fully_filled_config_emits_no_sentinel` with `_filled()` lacking `language` and `collection_method` | Two `[Not specified]` remained — from keys that **already existed**. My fixture did not match the issue's premise ("every ROTW field filled"). | `_filled()` sets `language` and `collection_method`, with the reason in its docstring. |
| Same, with `citation` still unset | One `[Not specified]` remained, in `## Citation`. Same class of error. | `citation` is set too. |
| Passing `cfg.study_design` to the builder | `build_dataset_card()` takes `study_design_content` as a **parameter**; it never reads `cfg.study_design`. | The test passes `study_design_content=`, and a separate test asserts that without it exactly **one** sentinel remains — in Curation Rationale, and only there. |

The third is the one worth keeping: it documents the actual contract of `study_design` rather than an
assumption about it, and the new `test_curation_rationale_needs_study_design` is what makes the
acceptance claim precise ("no sentinel, given study_design") instead of overbroad.

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The production edits landed before the new tests, so
the new tests did not themselves observe RED. What was observed: `370 passed` on the four affected test
files **before** the new tests existed (no existing expectation changed — the new fields default to
empty, so every pre-existing sentinel assertion still holds), then the three fixture corrections above,
then `217 passed` on `tests/test_repo_compliance.py`.

That "no existing test changed" is itself evidence worth stating: the change is additive for every
config that does not declare the new keys.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | A whitespace-only value silently replaces a placeholder with blank text. | Low | `.strip()` + fallback; `test_whitespace_only_values_keep_their_sentinel` pins it. |
| R2 | The `repository` → `source` fallback surprises a config whose `source` is not a repository. | Low | It is the issue's own option 3, and a declared `repository` wins. `test_a_declared_repository_beats_the_source` pins the precedence. |
| R3 | A multi-line value breaks the card's Markdown structure. | Low | Values are appended verbatim as body text, never into the YAML frontmatter; `test_multiline_values_render_verbatim` covers the newline/`#`/`-` cases. |
| R4 | Adding `DatasetConfig` fields breaks the 244 existing construction sites. | Low | All five are keyword fields with `""` defaults appended at the end of the metadata block; no positional site exists in the suite (it passed unchanged). |

## 6. Rollback

Revert-only: removing the five fields and restoring the four literals returns the previous card exactly.
No state, no migration.
