# Delta for mcp-server

> **Change:** `2026-09-13-test-mcp-injection-semantics` (GitHub #139) · branch `test/139-mcp-injection-semantics`.
>
> Test-only delta. It pins the acceptance criterion never dedicatedly tested before — caller-controlled
> newlines / instruction text cannot alter prompt workflow semantics — against the executable surfaces of
> the three `prompts/get` templates (`prepare_dataset`, `assess_dataset`, `finalize_and_publish`).
> No `src/sofer/` behavior changes: the two existing MSP-R08 scenarios are preserved byte-identical, the
> canonical-chain text is unchanged, `prompts/list` still returns exactly 3 prompts, and
> `_with_untrusted_note` stays untouched. The raw-interpolation sites in the three intro sentences
> (`mcp_server.py:2987`, `3017-3018`, `3042`) are recorded as a **known limitation tracked by issue #169**
> and are deliberately NOT asserted as prose-pure here; the delta specifies the current repr-protection
> contract only where it holds.
>
> Block format follows the repo's archived change specs: a full-block `## MODIFIED Requirements`
> replacement of MSP-R08 (every pre-existing scenario copied intact) so archive-time replacement loses
> nothing.

## MODIFIED Requirements

### Requirement: Prompts (MSP-R08)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `2026-09-13-test-mcp-injection-semantics` — adds the injection-semantics contract and its probe suite (test-only; no runtime change).

The server SHALL expose 3 user-controlled workflow templates — `prepare_dataset`, `assess_dataset`, `finalize_and_publish` — encoding the validate → prepare → confirm-before-publish idiom. Any publish step SHALL instruct calling `sofer_publish` (dry-run) and stopping for human approval before `sofer_publish_confirm`.

Caller-controlled prompt arguments (`config`, `output`, and `dataset` for `assess_dataset`) SHALL be rendered as DATA inside every template: a hostile argument carrying newlines, instruction-like prose, fake numbered-step lines, fake tool-call lines, quotes, or backslashes SHALL NOT add a workflow step, SHALL NOT remove or reorder an existing step, SHALL NOT split or break out of any executable line (step, numbered step, or copy-paste block), and SHALL NOT displace the human-approval STOP that precedes `sofer_publish_confirm`. Every executable argument position SHALL be `repr`-quoted, so a payload newline SHALL appear as the escaped literal `\n` inside a quoted position — never as a real line break that could start a new instruction line. `prompts/list` SHALL still return exactly 3 prompts and the canonical-chain text SHALL be unchanged by any caller argument. The static `_with_untrusted_note` guard SHALL still be appended to each rendered prompt under hostile arguments.

The three intro sentences currently interpolate caller arguments raw (`mcp_server.py:2987`, `3017-3018`, `3042`). This raw-intro behavior is a KNOWN LIMITATION (tracked separately by issue #169) and is NOT part of this requirement's asserted contract: the injection probes SHALL assert containment over the executable surfaces only and SHALL NOT assert that intro prose is free of verbatim payload text. Any future fix for the raw-intro sites belongs to a separate change and SHALL NOT be specified here.

The dedicated injection probe suite SHALL live in `tests/test_mcp_server.py` (`TestPrompts`) as net-new, additive tests; every scenario below SHALL map to a test (AGENTS.md rule 6 / `openspec/config.yaml` specs rule). A probe that fails because a payload genuinely altered rendered semantics SHALL STOP — the red probe plus rendered output is the finding; `src/sofer/mcp_server.py` SHALL NOT be silently edited in this change.

(Previously: the requirement specified only the 3 templates and the confirm-before-publish idiom; no caller-payload containment contract and no probe suite were specified.)

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

#### Scenario: Intro raw interpolation is a recorded known limitation, not asserted

- GIVEN a hostile payload in `config` (and `dataset` for `assess_dataset`)
- WHEN the rendered prompt is inspected at the executable surfaces and at the intro sentence
- THEN the probe SHALL assert repr-containment over the executable surfaces only (step lines, numbered steps, canonical-chain line, copy-paste block)
- AND the probe SHALL NOT assert prose purity, because the three intro sentences interpolate raw (`mcp_server.py:2987,3017-3018,3042`) and are KNOWN LIMITATION sites tracked by issue #169
- AND no server fix for the intro sites SHALL be specified or required by this change

---

<!-- Informational only: maps each new scenario to its apply-phase test
(AGENTS.md §6 / openspec/config.yaml — every spec scenario MUST have a
corresponding test). Not part of the archived requirement blocks. -->

| Scenario | Test (`tests/test_mcp_server.py`, `TestPrompts`) |
| --- | --- |
| Prompt list shows 3 templates | existing `test_prompt_list_shows_three` (preserved, unchanged) |
| Confirm-before-publish idiom enforced | existing `test_publish_prompt_mandates_approval_stop` (preserved, unchanged) |
| Hostile payload cannot alter the prepare_dataset workflow | new `test_prepare_dataset_payload_no_steps_added` + `test_prepare_dataset_payload_arg_containment` — canonical sequence equal; escaped `\n`; no line-start marker; STOP before confirm; UNTRUSTED note present |
| Hostile payload cannot alter the assess_dataset workflow | new `test_assess_dataset_payload_no_steps_added` + `test_assess_dataset_payload_arg_containment` — assess chain equal; escaped `\n`; no line-start marker; UNTRUSTED note present |
| Hostile payload cannot alter the finalize_and_publish workflow | new `test_finalize_payload_no_steps_added` + `test_finalize_payload_arg_containment` — canonical sequence equal; escaped `\n`; no line-start marker; STOP before confirm; UNTRUSTED note present |
| Canonical chain order is payload-invariant | new `test_prepare_dataset_payload_canonical_order` + `test_assess_dataset_payload_canonical_order` + `test_finalize_payload_canonical_order` — `text.index()` relative order equal to payload-free baseline |
| Intro raw interpolation is a recorded known limitation, not asserted | new `test_prepare_dataset_intro_contract_scope` — asserts executable-block containment only and documents the #169 raw-intro sites; asserts no prose-purity claim |

> Payloads are module-level `_INJECT_*` constants (AGENTS.md rule 1 — no inline literals); the shared
> `_get_prompt_text(server, name, args)` helper is docstring'd (AGENTS.md rule 2).
