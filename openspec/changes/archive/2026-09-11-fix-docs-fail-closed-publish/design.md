# Design: Fix README fail-closed publish documentation

**Change**: `2026-09-11-fix-docs-fail-closed-publish` (Fixes GitHub #148)
**Date**: 2026-09-11
**Status**: designed
**Change type**: docs-only — `README.md` + `README_ES.md`, one commit
**Spec delta**: none (see `specs/no-delta.md`; this design introduces no behavior)

---

## 1. Design summary

This change has **no runtime design**. It is a documentation correction: two prose
regions in `README.md` and their Spanish mirrors in `README_ES.md` are rewritten so the
user-facing text matches the posture `src/sofer/mcp_server.py` already enforces and
`openspec/specs/mcp-server/spec.md` already mandates.

The engineering content of the design is therefore:

1. **A wording contract** — the exact set of claims the new text may and may not make (§4),
   each traced to a source of truth (§5), with the technical tokens that must stay in
   English in both files (§4.4).
2. **A concrete edit specification** — the two edited regions, their boundaries, the exact
   before/after wording in EN and ES (§6).
3. **A mechanical acceptance procedure** — greps with hard-zero expectations that replace a
   test suite for a prose-only change (§7).

Three design decisions carry all the risk, and are recorded in §3: (D1) the phrase is
stated as **unconditionally mandatory** rather than "recommended for sensitive hosts";
(D2) the corrected wording is written so the older defective phrases are **grep-provably
absent** instead of merely contradicted; (D3) per-agent setup **references** the existing
MCP-registration guidance instead of duplicating it.

## 2. Design constraints and invariants

| # | Invariant | Source |
|---|---|---|
| C1 | Only `README.md` and `README_ES.md` change. Nothing under `src/`, `tests/`, `docs/`, `openspec/specs/`, `TRACE.md`, `scratch/`, `.gitignore`. | `specs/no-delta.md` §4; proposal *Out of Scope* |
| C2 | Both files are edited in the **same commit**; heading count/order stay mirrored; prose is translated, technical content stays English. | AGENTS.md §13 |
| C3 | No claim beyond the already-normative statements (MSP-R05, 10.3, 10.8, MCP-REG-01). | `specs/no-delta.md` §2/§4 |
| C4 | The phrase must be scoped to the **MCP server** (`sofer_publish_confirm`), never implied for the CLI (`sofer publish`). | `mcp_server.py:217,1148,2637-2648`; `cli.py:624` forwards env *names* only |
| C5 | The `### Hardening for sensitive hosts` / `### Endurecimiento para hosts sensibles` headings are unchanged (anchor stability + ES parity). | README.md:662, README_ES.md:697 |
| C6 | No new env var names, flags, paths, or error codes are invented; only tokens that exist in code/spec are used. | AGENTS.md §1; `specs/no-delta.md` §4 |
| C7 | The diff stays minimal and well inside the 400-line review budget; delivery is a dedicated branch off `dev`, merged only via PR. | Session preflight (`ask-on-risk`), proposal *Delivery* |
| C8 | No new test. `tests/test_mcp_server.py::…test_no_phrase_configured_refuses_fail_closed` and `tests/test_mcp_process.py` must pass **unchanged** — they are the executable proof the corrected prose is true. | `tests/test_mcp_server.py:751-758`, `tests/test_mcp_process.py:621`; `specs/no-delta.md` §2 |

## 3. Decisions (with rationale)

### D1 — State the phrase as unconditionally mandatory; delete the "SHOULD for sensitive hosts" framing

**Decision.** The section's opening no longer frames the phrase as a recommendation for
sensitive hosts. It states that the phrase is mandatory for every Hugging Face publish
made through `sofer_publish_confirm`, and that without it the publish is refused.

**Rationale.** `mcp_server.py:1148-1155` returns `PUBLISH_APPROVAL_NOT_CONFIGURED` whenever
`_APPROVAL_PHRASE is None` — there is no host profile that re-enables an
acknowledgment-only posture. The old "SHOULD configure … for sensitive hosts" sentence
plus the "weaker posture suited to trusted single-user stdio setups" sentence together
asserted a supported mode that does not exist in code. Keeping the SHOULD framing while
fixing only the last sentence would preserve the same misreading. Proposal question-round
assumption 1 is adopted: **no such mode exists; the refusal is unconditional.**

**Consequence.** The section title stays (C5) even though the body is no longer
conditional — the heading is an anchor contract, not a behavioral claim.

### D2 — Write the corrected prose so the defective phrases are provably absent (hard-zero greps)

**Decision.** The new wording avoids the literal bigrams `acknowledgment booleans` /
`booleanos de reconocimiento` entirely; it refers to *the two `acknowledge_*` flags* /
*los dos flags `acknowledge_*`*. Acceptance is a grep returning **zero** matches for
`weaker posture`, `when configured`, `acknowledgment booleans`, `postura más débil`,
`configurada — una frase`, `booleanos de reconocimiento` (§7.1 — ES patterns are chosen to
be line-local, because the ES defect is wrapped mid-phrase).

**Rationale.** The mandate's self-check is a grep, so it must be machine-decidable. If the
corrected text says "do not rely on the two acknowledgment booleans alone", the raw grep
still matches and acceptance degrades into human judgement about whether each remaining
hit is negated. Renaming the referent costs nothing (the flags are the two
`acknowledge_*` parameters of `sofer_publish_confirm`) and turns the check into a
hard-zero assertion. `acknowledge_risk=True` / `acknowledge_confidential=True` — the
precise forms the code uses — remain, and they do not match either pattern.

### D3 — Reference the existing MCP-registration env guidance; do not duplicate it

**Decision.** The per-agent paragraph links to the existing
`### Register sofer-mcp with AI agents (opencode, codex, gemini)` section (README.md:585;
ES mirror: README_ES.md:618) and restates only the four facts the publish gate depends on:
codex `env_vars` and gemini `env` persist env **names** only; opencode receives no env from
`sofer mcp add`; the opencode literal form written to disk is plaintext.

**Rationale.** README.md:619-621 already documents the per-agent env shape and
`mcp-registration` spec:19 is its normative source. A second copy of the table would
duplicate logic (AGENTS.md §4) and create a future drift point — exactly the failure mode
this change is repairing. The proposal's risk table flags this explicitly.

### D4 — Read-once/restart semantics, Windows launcher note, verification block

**Decision.** The rewrite adds three short blocks, all previously absent from the README:

- **read once at process start** — the phrase is resolved in `build_server` and stored in
  the module-level `_APPROVAL_PHRASE`, so it is immutable for that process
  (`mcp_server.py:217,2637-2648`); changing it requires restarting the host that launched
  `sofer-mcp`. The section states the launcher, not "the shell you typed in".
- **Windows** — one sentence: the variable must be in the *launcher's* environment and the
  host must be **fully restarted**.
- **verification** — `sofer_auth_status(config)` → `approval_configured`, with
  `requires_approval_phrase` always `true`, plus the disambiguation
  `PUBLISH_APPROVAL_NOT_CONFIGURED` (no phrase on the server) vs
  `PUBLISH_APPROVAL_REQUIRED` (missing/mismatched phrase in the call).

**Rationale.** The read-once semantics are the difference between "documented as a knob"
and a support incident: an agent host that edited only its shell never sees the change and
publish stays refused, which is precisely the loop recorded in `TRACE.md`. `approval_configured`
is the spec-blessed preflight field (`spec.md:424`), so verification requires no new
surface. No per-host restart recipe is written (proposal question-round assumption 2).

### D5 — Fix the adjacent `### Security model` bullet in the same change

**Decision.** The clause `and — when configured — an approval phrase compared with
hmac.compare_digest` becomes an always-in-force statement including the
`PUBLISH_APPROVAL_NOT_CONFIGURED` refusal. ES mirror follows.

**Rationale.** It is the same defect (implies the phrase is optional) in an adjacent
location, and the acceptance criterion is explicitly "no leftover text implies
optionality". Leaving it would fail the change's own success criteria and would have to be
a second PR against the same sentence. Proposal question-round assumption 5 is adopted:
**include it.**

### D6 — No spec delta, no test

**Decision.** No requirement file is added or modified; no test is added or changed.

**Rationale.** Already settled and reasoned in `specs/no-delta.md` §2-§3: every claim the
new text makes restates MSP-R05 (`spec.md:137`), 10.3 (`:390`), 10.8 (`:424`), or
MCP-REG-01 (`mcp-registration/spec.md:19`). A requirement of the form "the README SHALL
describe the fail-closed posture" is not a behavior contract and, under AGENTS.md §6, would
oblige a README-grep test — expanding a prose change into `tests/`. The grep procedure in
§7 lives in this design and in the verify report, not in the suite.

### D7 — Keep the diff minimal and prose-shaped

**Decision.** Edits are confined to the two named regions; no reflowing of surrounding
paragraphs, no reordering, no heading renames, no TOC changes (the TOC lists only `##`
headings and is untouched).

**Rationale.** C7 + the issue's own scope. A minimal diff also makes the EN/ES mirror
auditable line-by-line by a reviewer, which is the mitigation for the "mirrored file
under-checked" risk.

## 4. Wording contract

### 4.1 Claims the new text MUST make (EN; ES mirrors each)

| # | Claim | Traced to |
|---|---|---|
| W1 | The approval phrase is mandatory for every HF publish through `sofer_publish_confirm`; the two `acknowledge_*` flags are additional gates, never sufficient. | `mcp_server.py:1063,1148-1155`; `spec.md:137` |
| W2 | With no phrase configured the call is refused with `PUBLISH_APPROVAL_NOT_CONFIGURED` and the upload is disabled entirely. | `mcp_server.py:1148-1155`; `spec.md:137` |
| W3 | An empty or whitespace-only value counts as unconfigured. | `mcp_server.py:2648`; `spec.md:424` |
| W4 | The phrase comes from `build_server(root, approval_phrase=...)` or `SOFER_MCP_APPROVAL_PHRASE`. | `mcp_server.py:1627,2637-2644` |
| W5 | It is read once at process start and is immutable for that process; restart the launching host after a change. | `mcp_server.py:217,2637-2648` |
| W6 | Per-agent: codex `env_vars`, gemini `env` (names only, never the secret), opencode via launcher env or an explicit `environment` literal (plaintext on disk). | `mcp-registration/spec.md:19`; `mcp_server.py:1063`; README.md:619-621 |
| W7 | Windows: the variable must be in the launcher's environment and the host fully restarted. | same as W5 (env read at process start) |
| W8 | Verify with `sofer_auth_status(config)` → `approval_configured`; `requires_approval_phrase` is always `true`. | `mcp_server.py:1627-1670`; `spec.md:424` |
| W9 | `PUBLISH_APPROVAL_NOT_CONFIGURED` = no phrase on the server; `PUBLISH_APPROVAL_REQUIRED` = phrase missing or mismatched in the call. | `mcp_server.py:1148-1155` vs `:1166`; `spec.md:390` |
| W10 | The `openssl rand -hex 16` example and the `export … ; sofer-mcp` shape are retained. | README.md:667-670 (existing, accurate) |

### 4.2 Claims the new text MUST NOT make

| # | Forbidden claim | Why |
|---|---|---|
| N1 | That an unconfigured phrase yields a weaker-but-working posture ("weaker posture", "trusted single-user stdio setups", "only the two acknowledgment booleans gate the publish"). | No such mode exists — the primary defect. |
| N2 | That the phrase is optional, conditional, or enabled "when configured". | Adjacent defect; contradicted by `mcp_server.py:1148`. |
| N3 | That the CLI (`sofer publish`) needs an approval phrase. | `_APPROVAL_PHRASE` exists only in `mcp_server.py`; `cli.py:624` merely forwards env *names* during `mcp add`. |
| N4 | That the secret value is stored on disk by `mcp add`. | `mcp-registration/spec.md:19` — names only. |
| N5 | Anything about `approval_configured` envelope reporting, diagnostics, or approval hardening beyond the fields at `spec.md:424`. | Open issues #144/#145/#151 — explicitly not folded in. |
| N6 | A per-host (codex/gemini/opencode) restart recipe. | Out of scope (proposal question round 2). |
| N7 | A hardcoded "correct" phrase length, algorithm, or rotation policy. | AGENTS.md §1 — no invented values. |

### 4.3 Structural constraints

- Region boundaries: body of `### Hardening for sensitive hosts` only, plus the one
  `### Security model` bullet clause; blank-line separation and list indentation preserved.
- Prose wraps at ≤ 80 columns, matching the surrounding README style (no reflow of
  neighbours).
- The single Bash fence is kept; no new fences, tables, or images.
- No new headings → no TOC edits → no anchor churn beyond the two intra-page links the new
  text adds (which point at existing headings).

### 4.4 Language split (AGENTS.md §13)

| Stays English in both files | Translated in `README_ES.md` |
|---|---|
| `SOFER_MCP_APPROVAL_PHRASE`, `HF_TOKEN`, `env_vars`, `env`, `environment`, `build_server(root, approval_phrase=...)`, `sofer_publish_confirm`, `sofer_auth_status(config)`, `approval_configured`, `requires_approval_phrase`, `acknowledge_risk`, `acknowledge_confidential`, `PUBLISH_APPROVAL_NOT_CONFIGURED`, `PUBLISH_APPROVAL_REQUIRED`, `hmac.compare_digest`, `openssl rand -hex 16`, `sofer-mcp`, `sofer mcp add`, code fences | All surrounding prose, including the W7 Windows sentence and the W1/W2/W3/W5/W10 statements |

## 5. Claim → source traceability (no new facts)

```
W1,W2  → src/sofer/mcp_server.py:1148-1155   if _APPROVAL_PHRASE is None → PUBLISH_APPROVAL_NOT_CONFIGURED
W1     → src/sofer/mcp_server.py:1063        param docstring: "ALWAYS required for publish"
W3     → src/sofer/mcp_server.py:2648        raw_phrase if raw_phrase.strip() else None
W4     → src/sofer/mcp_server.py:2637-2644   build_server(root, approval_phrase) / env fallback
W5     → src/sofer/mcp_server.py:217         module-level _APPROVAL_PHRASE (process lifetime)
W8     → src/sofer/mcp_server.py:1627-1670   sofer_auth_status: approval_configured, requires_approval_phrase=True
W9     → src/sofer/mcp_server.py:1166        approval_phrase is None or not compare_digest → PUBLISH_APPROVAL_REQUIRED
W6     → src/sofer/mcp_registration.py:38,442  _ENV_KEYS = ["HF_TOKEN", "SOFER_MCP_APPROVAL_PHRASE"]
       → openspec/specs/mcp-registration/spec.md:19  names only; secret values never written to disk
C4/N3  → src/sofer/cli.py:624                mcp add collects env names; no phrase gate in the CLI
       → openspec/specs/mcp-server/spec.md:137,390,424  normative baseline for every claim
```

Note (factual correction to the proposal's reference list): `docs/cli-vs-mcp.md` does **not
exist** in the current tree — `docs/` contains only `configuration.md` (verified by
directory-wide grep, including the anchors `cli-vs-mcp` / `read once at process start`,
which match only inside the proposal itself). The prohibition on touching it is therefore
vacuous, and **no claim in the new README text may be justified by it**: the N3 scoping
invariant rests on `mcp_server.py` / `cli.py` / the mcp-server spec, which were re-read for
this design. `TRACE.md` was also not modified and is not cited by the new text.

## 6. Edit specification

### 6.1 `README.md` — primary defect (body of `### Hardening for sensitive hosts`, L663-673)

Replace the body (keep the heading at L662 and the blank line at L663). Draft replacement
text — the invariant set {W1…W10, N1…N7} is binding; the exact wrap is the implementer's
within the ≤80-column rule:

```markdown
Do not rely on the two `acknowledge_*` flags alone — the approval phrase is
**mandatory for every Hugging Face publish** made through
`sofer_publish_confirm`. Without one, the call is refused with
`PUBLISH_APPROVAL_NOT_CONFIGURED` and the upload is disabled entirely; an empty
or whitespace-only value counts as unconfigured. An agent can publish only
after a human reveals the phrase:

```bash
export SOFER_MCP_APPROVAL_PHRASE="$(openssl rand -hex 16)"
sofer-mcp
```

It is read **once at process start** (`build_server(root, approval_phrase=...)`
or `SOFER_MCP_APPROVAL_PHRASE`) and stays immutable for that process — change
the value in the launcher, then fully restart the agent host. Configure it the
way each agent persists MCP env (see
[Register sofer-mcp with AI agents](#register-sofer-mcp-with-ai-agents-opencode-codex-gemini)):
codex `env_vars` and gemini `env` persist the env **name** only, never the
secret; opencode receives no env from `sofer mcp add`, so use the launcher
environment or an explicit `environment` literal (plaintext on disk).

**Windows:** the variable must be in the launcher's environment — the process
that starts `sofer-mcp` — not merely in the shell you typed in, and the host
must be fully restarted for the change to take effect.

**Verify:** `sofer_auth_status(config)` → `approval_configured` (`true` when the
server has a non-blank phrase; `requires_approval_phrase` is always `true`).
`PUBLISH_APPROVAL_NOT_CONFIGURED` = no phrase on the server;
`PUBLISH_APPROVAL_REQUIRED` = the phrase passed to the call is missing or does
not match.
```

Size: ~30 lines including the fence, inside the ~15-25-line body budget the proposal
assumed plus the retained fence. The heading and the `openssl rand -hex 16` example are
preserved (C5, W10); the sentence pair at L664-665 and L672-673 is deleted.

### 6.2 `README.md` — adjacent defect (`### Security model`, L643-647)

Minimal clause replacement inside the existing bullet; the rest of the bullet (token
resolution chain) is untouched:

```diff
       `acknowledge_risk=True`, requires `acknowledge_confidential=True` for
-      configs marked `[meta] confidential`, and — when configured — an approval
-      phrase compared with `hmac.compare_digest`. Token is resolved via
+      configs marked `[meta] confidential`, and always requires a server
+      approval phrase compared with `hmac.compare_digest` — with no phrase
+      configured the call is refused with `PUBLISH_APPROVAL_NOT_CONFIGURED` and
+      the publish is disabled. Token is resolved via
```

This satisfies N2 and reinforces W1/W2 without restating the hardening section.

### 6.3 `README_ES.md` — mirrors, same commit (AGENTS.md §13)

- **Adjacent defect** (L680-681 inside `### Modelo de seguridad`, heading at L665):
  `… y — cuando está configurada — una frase de aprobación comparada con
  hmac.compare_digest.` → `… y siempre requiere una frase de aprobación del servidor
  comparada con hmac.compare_digest — sin frase configurada la llamada se rechaza con
  PUBLISH_APPROVAL_NOT_CONFIGURED y la publicación queda deshabilitada.` Re-wrap the
  paragraph to the existing width.
- **Primary defect** (body of `### Endurecimiento para hosts sensibles`, L699-710; heading
  at L697): mirror 6.1 sentence-by-sentence in neutral Spanish, keeping every technical
  token English (§4.4). Key rendered forms:
  - W1: `No confíes solo en los dos flags \`acknowledge_*\` — la frase de aprobación es
    **obligatoria para toda publicación en Hugging Face** hecha a través de
    \`sofer_publish_confirm\`.`
  - W5: `Se lee **una sola vez al iniciar el proceso** … cambia el valor en el lanzador y
    reinicia por completo el host del agente.`
  - W7: `**Windows:** la variable debe estar en el entorno del lanzador — el proceso que
    inicia \`sofer-mcp\` —, no solo en el shell donde escribiste, y el host debe
    reiniciarse por completo.`
  - W8/W9: `**Verificación:** \`sofer_auth_status(config)\` → \`approval_configured\` …`
  - The intra-page link targets the ES heading:
    `[Registrar sofer-mcp con agentes de IA](#registrar-sofer-mcp-con-agentes-de-ia-opencode-codex-gemini)`
    (README_ES.md:618).
- Keep the ES-specific trailing sentence that already exists in the Configuration section
  ("Los documentos técnicos de referencia … están en inglés.") untouched.

### 6.4 Heading parity check (structural, no edits)

```
README.md      L632 ### Security model                 → L662 ### Hardening for sensitive hosts
README_ES.md   L665 ### Modelo de seguridad            → L697 ### Endurecimiento para hosts sensibles
```

Both files keep the pair in the same order and the same count (`grep -c '^### '` equal — 17
each as of this design). No heading text changes, so no anchors break.

## 7. Verification strategy (no new tests)

Because the change is prose, the executable proof of the *documented* behavior is the
existing suite, which must pass **unchanged**; the executable proof of the *documentation*
is the grep set below. Both belong in the verify report.

### 7.1 Hard-zero greps (the acceptance criterion)

Run from the repo root; each command must print nothing (line-local patterns — see the
soft-wrap caveat below):

```bash
grep -n "weaker posture\|when configured\|acknowledgment booleans" README.md
grep -n "configurada — una frase\|postura más débil\|booleanos de reconocimiento" README_ES.md
```

(D2 makes both lines hard-zero together: the negated phrasing uses `acknowledge_*`, not
"acknowledgment booleans". Baseline before the edit — 6 matches: README.md:646,672,673 and
README_ES.md:681,708,709.)

**Soft-wrap caveat (must be respected when authoring the greps).** The ES adjacent defect
is wrapped mid-phrase, so the natural pattern `cuando está configurada` matches **nothing**
even before the fix — `cuando está` ends L680 and `configurada —` starts L681. Greps are
line-local, so ES patterns must be line-local too: `configurada — una frase` is fully
contained in L681 and is hard-zero after the fix. Do **not** widen the ES pattern to
`cuando está` — that form also occurs benignly at README_ES.md:332, 363 and 400
(`cuando está disponible` / `fuera de la raíz` / `Una palabra clave solo cuenta cuando
está`) and would produce false failures. EN needs no such care: its defective clauses are
line-contained (README.md:646, 672-673).

### 7.2 Positive-presence greps (each must return ≥1 hit in each file)

```bash
grep -c "PUBLISH_APPROVAL_NOT_CONFIGURED" README.md README_ES.md
grep -n "approval_configured"              README.md README_ES.md
grep -n "SOFER_MCP_APPROVAL_PHRASE"        README.md README_ES.md
```

Plus per-language assertions on the W5/W7 claims:
`grep -n "once at process start" README.md` and
`grep -n "una sola vez al iniciar el proceso" README_ES.md` — each ≥1.

### 7.3 Anti-regression greps

- **No CLI over-claim (N3):** every `SOFER_MCP_APPROVAL_PHRASE` occurrence must sit inside
  the MCP region — `grep -n "SOFER_MCP_APPROVAL_PHRASE" README.md` (and ES) must return only
  lines within the `## AI and MCP server` block (README.md:485-674 as of this design;
  pre-existing hits at :170, :320, :619 plus the new one) — never inside
  `## Command reference` / the `sofer publish` examples.
- **Scope guard (C1):** `git status --short` lists exactly `README.md` and `README_ES.md`.
- **Mirror guard (§13):** `grep -c '^#' README.md README_ES.md` counts are equal per level
  (same heading count/order), and the two changed regions are the same two regions.
- **Whitespace:** `git diff --check` clean.

### 7.4 Suite and tooling (must be unchanged)

```bash
uv run pytest tests/ -q          # includes test_mcp_server.py:751-758 and test_mcp_process.py:621
uv run ruff check src/ tests/    # docs-only change: must be a no-op
uv run mypy src/                 # docs-only change: must be a no-op
```

`tests/test_mcp_server.py::TestPublishConfirm…::test_no_phrase_configured_refuses_fail_closed`
and the fail-closed assertions in `tests/test_mcp_process.py` are the RED/GREEN-equivalent
evidence that the corrected prose describes real behavior; they are read-only evidence and
must not be edited to accommodate wording.

## 8. File change map

| File | Region | Change | Lines (est.) |
|---|---|---|---|
| `README.md` | L663-673 body of `### Hardening for sensitive hosts` | replace sentence pair + defect sentence with the W1-W10 block | ~13 → ~30 |
| `README.md` | L643-647 clause in `### Security model` bullet | "when configured" → always in force + refusal code | ±4 |
| `README_ES.md` | L699-710 body of `### Endurecimiento para hosts sensibles` | ES mirror of 6.1 | ~13 → ~30 |
| `README_ES.md` | L680-681 clause in `### Modelo de seguridad` bullet | ES mirror of 6.2 | ±4 |

Estimated diff: ~70 changed lines across 2 files — ~18% of the 400-line review budget, so
no chain strategy is required. Unchanged by design: `src/**`, `tests/**`, `docs/**`,
`openspec/specs/**`, `TRACE.md`, `.gitignore`, `scratch/**`.

## 9. Delivery and rollout

- **Branch:** dedicated branch cut from `dev` (repo flow: all work lands on `dev` first;
  `main` receives only merges). Merged **only via PR**, with the
  `.github/PULL_REQUEST_TEMPLATE.md` section *SDD artifacts* filled in this change's paths.
- **Commits:** one commit (or, if the implementer prefers, EN then ES — the same-commit
  rule in C2/§13 is satisfied by a single squash-merge only if both files appear in the
  final commit; the design recommends one commit containing both files).
- **Rollout:** none needed — documentation-only, no runtime surface, no migration, no
  feature flag, no release step specific to this change.
- **Rollback:** `git revert` of the docs commit. Because no spec or code changed, there is
  nothing else to roll back.
- **Verify-phase evidence to capture:** the two hard-zero grep outputs (§7.1), the
  presence greps (§7.2), `git status --short` (§7.3), and the three tool outputs (§7.4).

## 10. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| The rewrite over-claims (e.g. says the phrase lives only in env, or that the CLI needs it) | Med | W/N tables (§4.1-4.2) + traceability (§5); N3 enforced by the §7.3 grep |
| ES mirror drifts or lands in a later commit | Med | Same commit (C2); §6.3 lists the exact ES anchors; §7.3 mirror guard |
| A reviewer treats a docs diff as trivially safe and under-checks ES | Low | §6.3 is a sentence-by-sentence mapping; the diff shows matching regions in both files |
| Accepted hard-zero grep is defeated by a future re-introduction of the phrase | Low | Out of scope by design (a docs-conformance requirement + test is the recorded follow-up, `specs/no-delta.md` §5) |
| The proposal's `docs/cli-vs-mcp.md` reference is stale and someone "fixes" the missing file as part of this change | Low | §5 note + C1: `docs/**` is read-only for this change |
| Anchor link added to the hardening section breaks on GitHub | Low | Target heading is unchanged and already present in both files (§6.1/6.3); verify identical slug form in EN and ES |
| The section grows beyond the assumed ~15-25 lines | Med | §6.1 sized at ~30 lines incl. fence; if the implementer must trim, the binding part is {W1,W2,W5,W7,W8} — drop prose, never a claim |

## 11. Out of scope (guardrails)

- Any code, behavior, config, test, or spec change (C1, D6).
- `TRACE.md`, `docs/**`, `CONTRIBUTING.md`, `scratch/**`, `.gitignore` — untouched.
- README sections outside the two regions (MCP registration, tools table, workflow diagram,
  TOC, Configuration).
- Issues #144 / #145 / #151 (approval diagnostics, envelope reporting, related hardening) —
  no speculative wording, not referenced as pending work.
- A docs-conformance requirement and its grep test — recorded as a separate follow-up
  candidate in `specs/no-delta.md` §5.

## 12. Traceability to proposal success criteria

| Proposal criterion | Where handled here |
|---|---|
| README describes mandatory phrase + `PUBLISH_APPROVAL_NOT_CONFIGURED` | W1, W2, §6.1 |
| Read once at process start + restart; verify via `sofer_auth_status` → `approval_configured` (+ `requires_approval_phrase` true) | W5, W8, §6.1 |
| Per-agent config + plaintext caveat + Windows launcher/restart note | W6, W7, D3, D4, §6.1 |
| No surviving text implying the flags suffice / the phrase is optional | D1, D2, §4.2, §7.1 (hard-zero) + §6.2 |
| ES mirrors both edits in the same commit, tokens English, parity preserved | C2, §4.4, §6.3, §6.4, §7.3 |
| Zero changes to `src/`, `tests/`, `docs/`, `TRACE.md`, `openspec/specs/` | C1, §8, §7.3 |
| Suite passes unchanged; `git diff --check` clean | C8, §7.4 |
| No leftover "weaker posture" / "postura más débil" | §7.1 (hard-zero, incl. the wrap-aware ES pattern) |
