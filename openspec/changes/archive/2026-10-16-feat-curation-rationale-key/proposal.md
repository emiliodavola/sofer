# Proposal — `2026-10-16-feat-curation-rationale-key`

> **Change** `2026-10-16-feat-curation-rationale-key` · issue **#324** · branch
> `feat/324-curation-rationale-key` from `dev@5249be6` · store **hybrid**.

> **Status:** delivered in one PR and archived in the same branch (AGENTS.md rule 15).

---

## 1. Intent

`### Curation Rationale` was the one Dataset Card section whose sole fill path was `[meta]
study_design` — a *path* to a markdown file whose content the caller resolves — while every
neighbouring narrative section takes a plain multi-line string. A config with three paragraphs of
rationale and nothing else to say had to author a file. Nothing reported an error; the only way to
notice was to read the emitted card.

The issue is the follow-up its own predecessor recorded: `odd/tasks/card-section-keys.md` decision D4
("keeps `study_design` as its only fill path … recorded as a follow-up instead") and
`2026-10-16-feat-card-section-keys/archive-report.md` §6.

## 2. Scope

- `src/sofer/model.py`: one `[meta]` field and its `from_toml` read.
- `src/sofer/repo_compliance.py`: the three-arm resolution chain at the `### Curation Rationale` site.
- `openspec/specs/repo-compliance/spec.md`: §2.1.1's TOML block and §2.1.2's resolution rules, where
  the clause asserted the opposite of the new behaviour.

Not in scope: the `sofer init` template (the five #291 keys are not in it either), the README (it
delegates the full key set to §2.1.1), and any change to the `study_design` path itself.

## 3. Approach — option 1 of the issue

The issue offered three options. **Option 1 is delivered**: a free-text `curation_rationale` key used
when set, falling back to `study_design_content`, then to the sentinel.

- Option 2 (let `study_design` accept inline text as well as a path) is rejected for the reason the
  issue itself gives: it makes one key mean two things.
- Option 3 ("keep it and say so") is delivered as a by-product: the amended §2.1.2 clause and §2.1.1's
  TOML block now say where a TOML author looks, which is what the issue called the honest minimum.

## 4. Success criteria

- SC-1: a config declaring only `curation_rationale` fills the section, with no file.
- SC-2: a declared key wins over a resolved `study_design` file.
- SC-3: a config declaring neither emits the byte-identical card it did before the change.
- SC-4: the new field round-trips from a TOML, and an absent key defaults to empty.
- SC-5: `_MORE_INFO` stays one constant at four sites in `build_dataset_card()` — the issue's own
  acceptance test for a one-site addition.
- SC-6: the full gate set is green.
