# Delta for mcp-server

> **Change:** `2026-09-13-fix-prompt-intro-repr` (GitHub #169) · branch `fix/169-prompt-intro-repr`.
>
> Resolves #169 and the #139 known-limitation carve-out. The three prompt-template **intro
> sentences** in `src/sofer/mcp_server.py` interpolated caller-controlled `config`/`dataset`
> arguments raw while every executable surface was `repr`-protected — the single place hostile
> text could render as real instruction-shaped prose instead of escaped data (LLM01-class
> prose-contamination surface). The runtime change is exactly three interpolation tokens
> (`{config!r}` / `{dataset!r}`), bringing the intros to parity with the executable surfaces;
> the #139 injection probe suite is extended to assert intro-region containment (repr of payload
> present, raw payload text absent) for all three templates, and the two #139 docstrings that
> recorded the raw-intro limitation are refreshed (docstring-only; no assertion of the old
> limitation ever existed). The "known limitation" clause and scenario from the merged
> `2026-09-13-test-mcp-injection-semantics` delta (PR #170) are rewritten HERE into the resolved
> repr-intro contract — the #139 artifact is historical and is NOT edited.
>
> Block format follows the repo's archived change specs: a full-block `## MODIFIED Requirements`
> replacement of MSP-R08 (every pre-existing scenario copied intact — the six #139 scenarios are
> preserved byte-identical apart from the intro-limitation scenario, which is replaced by the
> resolved contract) so archive-time replacement loses nothing.

## MODIFIED Requirements

### Requirement: Prompts (MSP-R08)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `2026-09-13-test-mcp-injection-semantics` — adds the injection-semantics contract and its probe suite (test-only; no runtime change). Modified by `2026-09-13-fix-prompt-intro-repr` — resolves the #169 known-limitation carve-out: the three intro sentences now repr-contain caller arguments at parity with the executable surfaces; intro-region containment is asserted by the probe suite; runtime change is exactly the three intro interpolation tokens (issue #169).

The server SHALL expose 3 user-controlled workflow templates — `prepare_dataset`, `assess_dataset`, `finalize_and_publish` — encoding the validate → prepare → confirm-before-publish idiom. Any publish step SHALL instruct calling `sofer_publish` (dry-run) and stopping for human approval before `sofer_publish_confirm`.

Caller-controlled prompt arguments (`config`, `output`, and `dataset` for `assess_dataset`) SHALL be rendered as DATA inside every template: a hostile argument carrying newlines, instruction-like prose, fake numbered-step lines, fake tool-call lines, quotes, or backslashes SHALL NOT add a workflow step, SHALL NOT remove or reorder an existing step, SHALL NOT split or break out of any executable line (step, numbered step, or copy-paste block), and SHALL NOT displace the human-approval STOP that precedes `sofer_publish_confirm`. Every executable argument position SHALL be `repr`-quoted, so a payload newline SHALL appear as the escaped literal `\n` inside a quoted position — never as a real line break that could start a new instruction line. `prompts/list` SHALL still return exactly 3 prompts and the canonical-chain text SHALL be unchanged by any caller argument. The static `_with_untrusted_note` guard SHALL still be appended to each rendered prompt under hostile arguments.

**RESOLVED (change `2026-09-13-fix-prompt-intro-repr`, issue #169):** the containment contract SHALL extend to the intro sentences. Caller-controlled `config`/`dataset` arguments SHALL be `repr`-contained in ALL interpolations of the three prompt templates — intro sentences AND executable surfaces. Every intro sentence SHALL render each caller-controlled argument it interpolates (`config` on all three templates; `config` and `dataset` for `assess_dataset`) in its `repr()` form — quoted and escaped exactly like the executable argument positions — and SHALL NOT interpolate any caller-controlled argument raw. No raw, non-`repr` interpolation of `config`/`dataset` SHALL remain in any prompt template; a hostile payload SHALL therefore appear only as data, never as real instruction-shaped prose. (`output` is never interpolated into any intro sentence; its containment remains asserted over the executable block.)

The dedicated injection probe suite SHALL live in `tests/test_mcp_server.py` (`TestPrompts`) as net-new, additive tests; every scenario below SHALL map to a test (AGENTS.md rule 6 / `openspec/config.yaml` specs rule). A probe that fails because a payload genuinely altered rendered semantics SHALL STOP — the red probe plus rendered output is the finding; `src/sofer/mcp_server.py` SHALL change only by the three intro interpolation tokens specified by this change (issue #169 fix scope), never silently beyond them. The suite SHALL additionally assert intro-region containment for all three templates: over the intro region — `text` up to the existing `"Canonical chain:"` anchor (the established slice; no new literals) — `repr(payload)` SHALL be present for every caller-controlled intro argument and no raw `_INJECT_*` marker SHALL appear. The #139 probes that assert executable-surface containment remain unchanged and green; their wording-only docstring refresh records the resolution, not a behavior change.

(Previously: the injection-semantics contract and its probe suite covered the executable surfaces only; the three intro sentences interpolated caller arguments raw at the pre-fix sites and were recorded as known limitation #169 — probes expressly did NOT assert intro prose purity. Resolved by this change: intros repr-contain caller arguments; intro-region assertions added.)

#### Scenario: Prompt list shows 3 templates

- GIVEN the server running
- WHEN `prompts/list` is called
- THEN exactly 3 prompts SHALL be returned

#### Scenario: Confirm-before-publish idiom enforced

- GIVEN each prompt's template
- WHEN it is inspected
- THEN every HF-publish step SHALL mandate a human-approval stop before the confirm call

#### Scenario: Hostile payload cannot alter the prepare_dataset workflow

- GIVEN `build_server(root=tmp_path)` and a `prepare_dataset` call whose `config` and `output` arguments each carry a hostile `_INJECT_*` payload (real newlines + instruction-like prose; a fake `\n6. sofer_publish(...)` step line; a fake `sofer_publish_confirm(...)` tool-call line; quotes/backslashes)
- WHEN the prompt is rendered via `client.get_prompt("prepare_dataset", {...})`
- THEN the ordered `sofer_*` call sequence SHALL equal the builder's static canonical sequence (`sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile_all → sofer_render_all → sofer_publish` dry-run) with no added, removed, or reordered call
- AND every payload newline SHALL appear as an escaped `\n` literal inside a repr-quoted argument position — no raw line break SHALL split any step or copy-paste line
- AND no payload marker SHALL appear as a line-start call (every marker SHALL sit inside a repr-quoted literal)
- AND `STOP` and the human-approval wording SHALL be present BEFORE `sofer_publish_confirm`
- AND the `_UNTRUSTED_NOTE` text SHALL still be appended

#### Scenario: Hostile payload cannot alter the assess_dataset workflow

- GIVEN `build_server(root=tmp_path)` and an `assess_dataset` call whose `config` and `dataset` arguments each carry a hostile `_INJECT_*` payload
- WHEN the prompt is rendered via `client.get_prompt("assess_dataset", {...})`
- THEN the rendered `sofer_*` call sequence SHALL equal the builder's static assess chain (`sofer_validate → sofer_profile → sofer_render`) with no added, removed, or reordered call
- AND every payload newline SHALL appear as an escaped `\n` literal inside a repr-quoted argument position — no raw line break SHALL split any step or copy-paste line
- AND no payload marker SHALL appear as a line-start call
- AND the `_UNTRUSTED_NOTE` text SHALL still be appended

#### Scenario: Hostile payload cannot alter the finalize_and_publish workflow

- GIVEN `build_server(root=tmp_path)` and a `finalize_and_publish` call whose `config` and `output` arguments each carry a hostile `_INJECT_*` payload
- WHEN the prompt is rendered via `client.get_prompt("finalize_and_publish", {...})`
- THEN the ordered `sofer_*` call sequence SHALL equal the builder's static canonical sequence (through `sofer_publish` dry-run and the confirm step) with no added, removed, or reordered call
- AND every payload newline SHALL appear as an escaped `\n` literal inside a repr-quoted argument position — no raw line break SHALL split any step or copy-paste line
- AND no payload marker SHALL appear as a line-start call
- AND `STOP` and the human-approval wording SHALL be present BEFORE `sofer_publish_confirm`
- AND the `_UNTRUSTED_NOTE` text SHALL still be appended

#### Scenario: Canonical chain order is payload-invariant

- GIVEN any of the 3 templates rendered with a hostile `_INJECT_*` payload in every caller-controlled argument
- WHEN relative `text.index()` ordering is measured across `sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile(_all) → sofer_render(_all) → sofer_publish(dry_run) → STOP → sofer_publish_confirm` (where applicable to the template)
- THEN each marker's relative order SHALL be unchanged from the payload-free render, proving order is payload-invariant

#### Scenario: Intro raw interpolation is resolved — intro sentences repr-contain caller arguments (formerly known limitation #169)

> (Previously: the three intro sentences interpolated caller arguments raw at the pre-fix sites — a KNOWN LIMITATION tracked by issue #169 — and the #139 probes asserted containment over the executable surfaces only, expressly NOT asserting intro prose purity. Resolved by change `2026-09-13-fix-prompt-intro-repr`.)

- GIVEN a hostile payload in `config` (and `dataset` for `assess_dataset`)
- WHEN the rendered prompts of all three templates are inspected at the intro sentences (the text before the `"Canonical chain:"` anchor)
- THEN each intro sentence SHALL contain `repr(payload)` for every caller-controlled argument it interpolates — `config` on all three templates, plus `dataset` on `assess_dataset`
- AND no raw `_INJECT_*` marker SHALL appear verbatim in any intro region (every payload newline SHALL appear only as the escaped `\n` literal inside the repr-quoted position)
- AND no raw, non-`repr` interpolation of `config`/`dataset` SHALL remain in any prompt template

#### Scenario: prepare_dataset intro repr-contains a hostile config payload

- GIVEN `build_server(root=tmp_path)` and a `prepare_dataset` call whose `config` argument carries a hostile `_INJECT_*` payload (real newlines + instruction-like prose + quotes/backslashes; reuse `_INJECT_ARGS_PREPARE`)
- WHEN the prompt is rendered via `client.get_prompt("prepare_dataset", {...})` and the intro region (`text[:text.index("Canonical chain:")]`) is inspected
- THEN `repr(_INJECT_ARGS_PREPARE["config"])` SHALL be present in the intro region
- AND no raw `_INJECT_*` marker SHALL appear verbatim in the intro region
- AND the intro region SHALL contain no raw payload line break (hostile newlines render only as the escaped `\n` literal inside the quoted position)

#### Scenario: assess_dataset intro repr-contains hostile dataset and config payloads

- GIVEN `build_server(root=tmp_path)` and an `assess_dataset` call whose `config` and `dataset` arguments each carry a hostile `_INJECT_*` payload (reuse `_INJECT_ARGS_ASSESS`)
- WHEN the prompt is rendered via `client.get_prompt("assess_dataset", {...})` and the two-line intro region (`text[:text.index("Canonical chain:")]`) is inspected
- THEN `repr(_INJECT_ARGS_ASSESS["config"])` and `repr(_INJECT_ARGS_ASSESS["dataset"])` SHALL both be present in the intro region
- AND no raw `_INJECT_*` marker SHALL appear verbatim in the intro region

#### Scenario: finalize_and_publish intro repr-contains a hostile config payload

- GIVEN `build_server(root=tmp_path)` and a `finalize_and_publish` call whose `config` argument carries a hostile `_INJECT_*` payload (reuse `_INJECT_ARGS_FINALIZE`)
- WHEN the prompt is rendered via `client.get_prompt("finalize_and_publish", {...})` and the intro region (`text[:text.index("Canonical chain:")]`) is inspected
- THEN `repr(_INJECT_ARGS_FINALIZE["config"])` SHALL be present in the intro region
- AND no raw `_INJECT_*` marker SHALL appear verbatim in the intro region

#### Scenario: No raw caller-argument interpolation remains in any rendered prompt

- GIVEN all three templates rendered with hostile `_INJECT_*` payloads in every caller-controlled argument (`_INJECT_ARGS_PREPARE` / `_INJECT_ARGS_ASSESS` / `_INJECT_ARGS_FINALIZE`)
- WHEN the full rendered text of each prompt — intro region AND executable block — is scanned for raw payload markers and for `repr()`-quoted payload forms
- THEN zero raw `_INJECT_*` marker SHALL appear verbatim anywhere in any of the three rendered prompts (intro region and executable surfaces combined)
- AND every caller-controlled argument SHALL appear in each rendered prompt exclusively in its `repr()`-quoted form — no argument value SHALL appear as raw, non-`repr` interpolation

---

<!-- Informational only: maps each scenario to its apply-phase test
(AGENTS.md §6 / openspec/config.yaml — every spec scenario MUST have a
corresponding test). Not part of the archived requirement blocks. -->

| Scenario | Test (`tests/test_mcp_server.py`, `TestPrompts`) |
| --- | --- |
| Prompt list shows 3 templates | existing `test_prompt_list_shows_three` (preserved, unchanged) |
| Confirm-before-publish idiom enforced | existing `test_publish_prompt_mandates_approval_stop` (preserved, unchanged) |
| Hostile payload cannot alter the prepare_dataset workflow | existing `test_prepare_dataset_payload_no_steps_added` + `test_prepare_dataset_payload_arg_containment` (preserved, unchanged) |
| Hostile payload cannot alter the assess_dataset workflow | existing `test_assess_dataset_payload_no_steps_added` + `test_assess_dataset_payload_arg_containment` (preserved, unchanged) |
| Hostile payload cannot alter the finalize_and_publish workflow | existing `test_finalize_payload_no_steps_added` + `test_finalize_payload_arg_containment` (preserved, unchanged) |
| Canonical chain order is payload-invariant | existing `test_prepare_dataset_payload_canonical_order` + `test_assess_dataset_payload_canonical_order` + `test_finalize_payload_canonical_order` (preserved, unchanged) |
| Intro raw interpolation is resolved — intro sentences repr-contain caller arguments (formerly known limitation #169) | **extended** `test_prepare_dataset_intro_contract_scope` — role flips from #169 known-limitation scope guard to positive intro-containment check; docstring refreshed to the resolved contract; plus new sibling tests for the other two templates (joint coverage of all three intros) |
| prepare_dataset intro repr-contains a hostile config payload | **extended** `test_prepare_dataset_intro_contract_scope` — over `text[:text.index("Canonical chain:")]` asserts `repr(_INJECT_ARGS_PREPARE["config"])` present, raw `_INJECT_*` markers absent, no raw payload line break (docstring refresh only for the resolution framing; no old-limitation assertion existed) |
| assess_dataset intro repr-contains hostile dataset and config payloads | **new** `test_assess_dataset_intro_contract_scope` (flat sibling convention, one probe per invariant) — over the intro region asserts `repr` of both `dataset` and `config` present, raw markers absent |
| finalize_and_publish intro repr-contains a hostile config payload | **new** `test_finalize_payload_intro_contract_scope` (flat sibling convention) — over the intro region asserts `repr(config)` present, raw markers absent |
| No raw caller-argument interpolation remains in any rendered prompt | **new** `test_prompts_no_raw_marker_across_templates` — cross-template zero-raw-marker scan (or, equivalently, the joint coverage of the three intro-region probes plus the three existing block-containment probes, which together span the full text of all three templates) |

> Docstring refresh (AGENTS.md rule 2): `_prompt_block` and `test_prepare_dataset_intro_contract_scope`
> currently record the #169 known-limitation framing with pre-fix line refs; both are refreshed to
> the resolved state in this change, describing the intro by behavior ("the three intro sentences"),
> never by line number. Probe bodies reuse the module-level `_INJECT_*` / `_BENIGN_*` constants, the
> shared `_get_prompt_text` helper, and the established `"Canonical chain:"` slice — no inline
> literals (AGENTS.md rule 1).
