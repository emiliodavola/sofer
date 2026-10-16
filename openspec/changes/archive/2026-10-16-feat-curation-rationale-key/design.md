# Design — `2026-10-16-feat-curation-rationale-key`

> **Change** `2026-10-16-feat-curation-rationale-key` · issue **#324** · branch
> `feat/324-curation-rationale-key` from `dev@5249be6` · store **hybrid**.


---

## 1. The defect, precisely

`build_dataset_card()` fills six narrative sections from configuration. Five of them read a
`[meta]` key added by #291. The sixth did not:

| Site | Reads before | Fillable without a file |
| --- | --- | --- |
| `### Direct Use` | `cfg.direct_use` | yes |
| `### Out-of-Scope Use` | `cfg.out_of_scope_use` | yes |
| `### Curation Rationale` | the `study_design_content` **parameter** | **no — a path is needed** |
| `## Bias, Risks, and Limitations` | `cfg.bias_risks_limitations` | yes |
| `## Dataset Card Contact` | `cfg.contact` | yes |
| `- **Repository:**` | `cfg.repository` → `cfg.source` | yes |

The asymmetry is the defect, and it is an asymmetry rather than a missing feature: every neighbour
takes inline text, so a user with the same three paragraphs and no other need must create a file.

## 2. Why a key in front of the file, and not in place of it

`study_design` is a **document** path (`resolve_doc_path`, existence-checked by
`DatasetConfig.validate()`, pre-loaded by `prepare.py` and passed as a parameter). Making it accept
inline text as well would give one key two types and two lifecycles. Adding a key keeps every existing
config valid, keeps `validate()`'s "declared `study_design` not found" diagnostic meaningful, and
leaves the file path as the verbose option — which is what a long rationale with structure wants.

## 3. The edits

### 3.1 `src/sofer/model.py`

One field on `DatasetConfig`, appended after `contact` in the HF Dataset Card metadata block, plus its
`from_toml` read:

```python
curation_rationale: str = ""
# ...
curation_rationale=meta.get("curation_rationale", ""),
```

Keyword field with a `""` default, so the existing construction sites are unaffected — the same
argument #291's design §5 R4 made for its five keys.

### 3.2 `src/sofer/repo_compliance.py`

The two-arm branch becomes a three-arm chain, and the branch taken when the key is absent is the
pre-change one byte for byte:

```python
if cfg.curation_rationale.strip():
    rationale = cfg.curation_rationale.strip()
elif study_design_content is not None:
    rationale = study_design_content.strip()
else:
    rationale = _MORE_INFO
lines.append(rationale)
lines.append("")
```

Two properties this shape protects deliberately:

- **`_MORE_INFO` stays one constant at four sites.** The issue's §"Proposed solution" names this
  explicitly ("the sentinel constant (`_MORE_INFO`) and the 'one sentinel site' test … both need
  updating, which is exactly what that test exists to force"). Folding the arms into one `rationale`
  variable keeps the count at four, so `test_the_sentinel_is_the_single_shared_constant` passes
  unchanged rather than being relaxed.
- **The file's own whitespace edge is untouched.** `.strip()` decides *which source wins* — a
  whitespace-only key is not content — but a resolved file's content is appended exactly as before,
  including the pre-existing case of a whitespace-only file yielding an empty section. Changing that
  would be an unrequested behaviour change on code the issue did not mention.

### 3.3 The spec clause could not simply be extended

§2.1.2's #291 paragraph ended with a sentence that asserts the **opposite** of the new behaviour:
"`### Curation Rationale` SHALL continue to be filled by `[meta] study_design` … it has no free-text
key of its own." Extending the paragraph in place would have left a false sentence in the spec of
record, so the paragraph now delegates that one section to a new clause that owns both fill paths. The
first draft of this change **did** leave both sentences and was corrected — recorded here because a
contradiction in a spec is the defect class AGENTS.md rule 15 is written about.

### 3.4 Tests

Seven new tests in `TestCurationRationaleKey`, plus the new key in the two existing
`TestCardSectionKeysFromToml` fixtures, plus the docstrings of the two `TestCardSectionKeys` tests
that claimed the section "has no free-text key of its own".

| Test | What it pins |
| --- | --- |
| `test_the_key_fills_the_section_without_a_file` | SC-1, the issue's whole point |
| `test_the_key_wins_over_the_study_design_file` | SC-2, the precedence S1 defines |
| `test_a_whitespace_only_key_falls_back_to_the_file` | a whitespace-only key is not content (§2.1.2 rule) |
| `test_a_whitespace_only_key_alone_keeps_the_sentinel` | and neither is it a fill |
| `test_neither_source_keeps_the_sentinel` | SC-3's sentinel arm |
| `test_declaring_study_design_alone_is_unchanged` | **the touched existing behaviour**, i.e. that the file path still works |
| `test_an_undeclared_study_design_with_a_key_is_enough` | the key needs no path beside it |

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The new tests observed RED before the production
edits — `7 failed, 11 passed`, every failure an `AttributeError`/`TypeError` on the missing field —
so the red-green half of the contract held. The **artifact ordering** did not: `odd/README.md` asks
for the feature file before the first source edit, and this one was written after (D6).

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | A declared key silently overrides a `study_design` file the user expected to win. | Low | The precedence is the issue's own ("used when set and falling back to"); it is now stated in §2.1.2 and pinned by a test. |
| R2 | A whitespace-only key is treated as content and blanks the section. | Low | `.strip()` in the condition; two tests cover both arms. |
| R3 | A multi-line rationale breaks the card's Markdown. | Low | Values are appended verbatim as body text, never into the YAML frontmatter — the same argument #291 recorded for its five keys. |
| R4 | Adding a `DatasetConfig` field breaks existing construction sites. | Low | Keyword field with a `""` default; the full suite passed with no existing expectation changed. |
| R5 | The four-site sentinel count is relaxed to accommodate the change. | Low | The count is unchanged at 4 and the test is untouched — the issue named it as the guard, so weakening it would have defeated the point. |

## 6. Rollback

Revert-only: remove the field and restore the two-arm branch, and the previous card returns exactly.
No state, no migration, no config rewrite.
