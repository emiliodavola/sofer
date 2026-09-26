# Explore — `sofer` CLI on consoles that cannot encode its output

Change: `2026-09-13-fix-cli-console-encoding`
Origin: GitHub issue `emiliodavola/sofer#161` — "cli: `sofer scan --help` / `prepare --help` crash on Windows cp1252 consoles (U+2192 in help text)".
Phase: `sdd-explore` · Artifact store: `openspec` · Status: exploration only (no proposal/spec/design/tasks).

---

## 0. Method and provenance (read this first)

This phase had **no shell tool available**. Every claim below is therefore one of three, explicitly labelled kinds:

| Label | Meaning |
| --- | --- |
| **[S]** | **Static** — verified by reading repository source/artifacts in this session. `file:line` given. |
| **[R]** | **Reported** — supplied by the orchestrator as an observed command output; cross-checked against source and found consistent, but *not* re-executed in this phase. |
| **[A]** | **Analysed** — a conclusion derived from documented language/library behaviour or from [S] facts, not observed here. Carries a "confirm in `design`" note where it matters. |

No file outside this change directory was modified. `src/`, `tests/`, `README*`, `AGENTS.md` untouched.

---

## 1. Reproduction status

**[R]** `PYTHONIOENCODING=cp1252 uv run sofer scan --help` → `rc=1`,
`UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 830`.
**[R]** `PYTHONIOENCODING=cp1252 uv run sofer prepare --help` → `rc=1`, same error, position 255.

**[S]** The failure mode is fully explained by source:

- `src/sofer/cli.py:1069-1076` — the `prepare` subparser's `description=` literal contains U+2192 twice (`cli.py:1072`, `cli.py:1073`).
- `src/sofer/cli.py:1425-1436` — the `scan` subparser's `description=` literal contains U+2192 once (`cli.py:1429`).
- `src/sofer/cli.py:1570-1576` — `main()` is:
  ```python
  config.reload(None)
  parser = _build_parser()
  args = parser.parse_args()
  sys.exit(args.func(args))
  ```
  There is **no** `try/except` around parsing, so the `UnicodeEncodeError` raised inside argparse's `_print_message` propagates: a raw traceback on stderr and a non-zero exit. argparse's `--help` would normally call `parser.exit()` (SystemExit 0) *after* writing; the encode error fires during the write, so `exit 0` is never reached. This matches the reported `rc=1`.

**[A]** Why `--help` at all and not only runtime output: argparse resolves `_sys.stdout` at call time and writes the rendered help through it (`argparse.ArgumentParser._print_message`). Reconfiguring `sys.stdout`/`sys.stderr` at the CLI entry point therefore covers help output **and** runtime `print()` output with one mechanism. This is the load-bearing fact for strategy B (§8).

**[A]** Correction to the issue's framing — "stock Windows console = cp1252" is imprecise, and the precision changes who this fix helps:

- Since Python 3.6 (PEP 528), a **real** Windows console is written through the console wide-char API and `sys.stdout.encoding` reports `utf-8`. Interactive `sofer scan --help` on a stock Windows terminal therefore generally does *not* crash.
- The same process crashes when stdout is **not** a console object — redirected to a file or a pipe (`sofer scan --help > out.txt`, `| more`, PowerShell `Out-File`, IDE/CI capture) — because the stream then falls back to the ANSI code page (cp1252 on es-ES/en-US). It also crashes when `PYTHONIOENCODING` is set (`[R]`), or under `PYTHONLEGACYWINDOWSSTDIO=1`.
- **Confirm in `design` with a one-line probe** before writing user-facing framing, e.g.
  `PYTHONIOENCODING= uv run python -c "import sys;print(sys.stdout.encoding)"` with and without `> out.txt` on Windows.

**[A]** Consequence to keep in mind for the fix's *scope* justification: the crash is real, deterministic, and CI-reproducible (`PYTHONIOENCODING=cp1252` is enough), but its most common real-world trigger is **redirection/piping and wrapper-set `PYTHONIOENCODING`**, not plain interactive typing.

---

## 2. Corrected and extended evidence

The orchestrator's evidence items 1 and 2 are **confirmed**. Item 3 is **materially incomplete**; item 4 is **confirmed with one runner-up caveat**.

### 2.1 CORRECTION — the enumeration method misses escaped glyphs

**[S]** The repository is internally inconsistent about how non-ASCII is written:

- **Literal** glyphs (raw character in the source): `src/sofer/codebook.py` (`⚠`), `src/sofer/cli.py` (`→` in prints and help), `src/sofer/checks.py` (`≥`), `src/sofer/quality.py` (`✅`/`❌`).
- **Escaped** `\uXXXX` sequences (character only exists after parsing): `src/sofer/prepare.py`, `publish.py`, `profile.py`, `render.py`, `_converters.py`, `verification.py`, and **also `cli.py:77`, `cli.py:79`**.

**[S]** A scan that looks for literal non-ASCII characters in source text — which is what evidence item 3 appears to have done, since it reported only `cli.py:549/569` and `codebook.py:543…697` — cannot see `prepare.py:216` (`f"  \u26a0  PARITY FAIL: row count mismatch — "`) or `cli.py:77` (`f"\n  \u2717  Configuration errors \u2014 fix before {verb}:"`). Roughly **87% of the crash sites are escaped and were missed**.

**[S]** The correct enumeration required three complementary greps (all run in this session):

1. literal non-ASCII per file: `[^\x00-\x7F]`
2. escaped codepoints repo-wide: `\\u[0-9a-fA-F]{4}`
3. named risky glyph alphabet: `[⚠✗✓✅❌↑→↔≥─│├└•·⏱★☆⚡]`
4. executable-string filter: `(print\(|lines\.append\(|return |help=|description=|\.write\(|f")[^\n]*[^\x00-\x7F]`

Grep 4 is the authoritative one for "is this an executable string or a comment/docstring?" and its complete output is §3.3–§3.4 below.

### 2.2 CONFIRMED — the cp1252 repertoire split

**[S]/[A]** Against the standard cp1252 repertoire (ASCII + `0x80-0x9F` specials + Latin-1 `0xA0-0xFF`):

| Char | Codepoint | cp1252-encodable | Where |
| --- | --- | --- | --- |
| `—` | U+2014 | **yes** (`0x97`) | pervasive, all modules |
| `…` | U+2026 | **yes** (`0x85`) | `publish.py:303,310,408` |
| `→` | U+2192 | **no** | `cli.py:549,569,1072,1073,1429`; `publish.py:161,197` (escaped) |
| `↑` | U+2191 | **no** | `publish.py:161,197` (escaped) |
| `⚠` | U+26A0 | **no** | `codebook.py`, `_converters.py`, `prepare.py`, `profile.py`, `render.py`, `publish.py` |
| `✗` | U+2717 | **no** | `cli.py:77,79`, `prepare.py`, `profile.py`, `render.py`, `publish.py`, `verification.py` |
| `✓` | U+2713 | **no** | `publish.py`, `verification.py` |
| `≥` | U+2265 | **no** | `checks.py:131` |
| `✅`/`❌` | U+2705/U+274C | **no** | `quality.py:593,602` — **file-only, must not be touched** |
| `─` | U+2500 | **no** | comments and docstrings only ([S] grep 1: every hit is a `#`-comment or inside a docstring) |

This confirms the orchestrator's item 2 (only U+2192 in argparse) and item 4 (box-drawing `─`, `≥`-in-comments, `↔`, `✅`/`❌` are not console-bound) — **except** for two exceptions they classified safe:

- `checks.py:131` `≥` **is** executable and **does** reach stdout (§3.3).
- `quality.py:593,602` `✅`/`❌` are executable but **do not** reach the console (§4.1).

### 2.3 CONFIRMED and EXTENDED — runtime console sites are far wider than two

Evidence item 3 named 2 stdout sites in `cli.py` + 6 stderr sites in `codebook.py`. **[S]** The complete set is **62 `print()` call sites across 9 modules** (§3.3–§3.4). Notably:

- `cli.py:77-79` (`✗`) — the config-error prologue used by `validate`, `prepare`, and `publish`. **[S]** `_load_and_validate` is shared by all three (`cli.py:62-110`, callers at `cli.py:111`, `cli.py:120+`, `cli.py:230+`), so **`sofer validate <bad.toml>` crashes today** on cp1252, before any report.
- `checks.py:131` (`≥`) — reached through `report.errors` and rendered by `print_summary` (`checks.py:55`), i.e. `sofer validate` output.
- `verification.py:132` + printed at `verification.py:133` — `sofer prepare --verify` (documented in README) prints `✓ PASSED` / `✗ FAILED`.
- `publish.py:161,169,172,197,205,208` — the HF-upload progress lines.

### 2.4 NEW — the worst failure mode is in `publish`

**[S]** `src/sofer/publish.py:161-174` (`_hf_upload`) and `src/sofer/publish.py:197-209` (`_hf_upload_folder`):

```python
print(f"  \u2191  {label}  \u2192  {remote_path}")   # BEFORE the network call
target_api.upload_file(...)                        # the upload happens
print(f"  \u2713  {label}")                        # AFTER success
```

**[S]** A `UnicodeEncodeError` on the *first* line is benign (nothing uploaded). A `UnicodeEncodeError` on the success line (`\u2713`, after `upload_file` returned) produces a traceback and `rc=1` **for an upload that actually succeeded** — the user sees a failure, the dataset is published, and `sofer publish`'s documented `ok`/`fail` accounting never prints. Any fix must therefore be *exception-shaped* (never raise on encoding), not merely *literal-shaped*. This is the single strongest argument in the strategy comparison (§8).

### 2.5 NEW — the glyph alphabet is already inconsistent

**[S]** Two different arrows are emitted for the same conceptual relation:

- MOVE phase: ASCII `->` — `cli.py:474`, `cli.py:482`; `mcp_server.py:2256,2444,2481`.
- COPY/confirm phase: U+2192 — `cli.py:549`, `cli.py:569`.
- README documents only `-> raw/<rel>` (`README.md:320`), which corresponds to the MOVE phase only. The `→` variant is undocumented.

**[S]** Marker alphabet is likewise mixed: `⚠` / `✓` / `✗` / `X` / `!` / `[!]` / `[i]` / `[~]` / `OK` / `WARN` / `DRY RUN`. Examples: `_clean.py:228` emits `"  !  cache/ is shared tool-wide …"`; `model.py:476` emits `"  [!] Unknown quality check: …"`; `cli.py:432` emits `"  X  Config file not found: …"`.

**[A]** Therefore strategy A ("replace the offending characters") is not a 5-line fix if taken seriously — it is a glyph-alphabet normalization across ~62 sites in 9 modules. That is a scope decision, not an implementation detail.

---

## 3. Complete console-bound emission inventory

### 3.1 Argparse strings (`--help` / `--version`)

Rendered by argparse to **stdout** via `_print_message`. Only the *subparser's own* `--help` renders `description=`; the top-level `--help` renders only each subparser's short `help=`.

| Site | String kind | Offending char | cp1252? | Reachable |
| --- | --- | --- | --- | --- |
| `cli.py:1072` | `prepare` `description=` | U+2192 `→` | **no** | `sofer prepare --help` |
| `cli.py:1073` | `prepare` `description=` | U+2192 `→` | **no** | `sofer prepare --help` |
| `cli.py:1429` | `scan` `description=` | U+2192 `→` | **no** | `sofer scan --help` |
| `cli.py:1038-1046` | top-level `description=` | none (ASCII) | yes | `sofer --help` |
| `cli.py:1055`, `1070`, `1120`, `1193`, `1241`, `1297`, `1351`, `1410`, `1524` | subparser short `help=` | none (ASCII) | yes | `sofer --help` |
| `cli.py:1397` | `init --dry-run` help | U+2014 `—` | yes | `sofer init --help` |
| `cli.py:1417`, `1427`, `1433` | `scan` `description=` | U+2014 `—` | yes | `sofer scan --help` |
| `cli.py:1521`, `cli.py:1549` | `mcp …--dry-run` help | U+2014 `—` | yes | `sofer mcp … --help` |

**[S]** Total: **exactly 3 offending codepoints in exactly 2 subcommand help screens** — the orchestrator's item 2 is correct, with one refinement: for `scan` the U+2192 is at `cli.py:1429` only; `cli.py:1433` is an em dash (encodable). `cli.py:119` is a *docstring* mention, not argparse.

**[S]** **This is the root cause of the false-negative test** — see §6.1.

### 3.2 Runtime emission, `src/sofer/cli.py`

| Site | Stream | Char | cp1252? | Reachable |
| --- | --- | --- | --- | --- |
| `cli.py:77` | **stdout** | U+2717 `✗` | **no** | `validate`/`prepare`/`publish` with config errors — *normal, documented path* |
| `cli.py:79` | **stdout** | U+2717 `✗` | **no** | same, one line per error |
| `cli.py:549` | **stdout** | U+2192 `→` | **no** | `scan` Phase-2 confirm preview (no `--force`, interactive) |
| `cli.py:569` | **stdout** | U+2192 `→` | **no** | `scan --dry-run` copy preview |

### 3.3 Runtime emission, other modules (stdout)

| Module | Sites | Char | Stream |
| --- | --- | --- | --- |
| `checks.py` | `131` (rendered by `55`) | U+2265 `≥` | stdout |
| `verification.py` | `132` (rendered by `133`) | U+2713 `✓` / U+2717 `✗` | stdout |
| `_converters.py` | `148`, `230`, `236`, `242`, `285`, `290`, `294`, `309`, `344`, `362`, `381`, `388`, `478`, `531` | U+26A0 `⚠` | stdout |
| `prepare.py` | `216`, `223`, `230`, `318`, `325`, `548`, `760`, `795`, `822`, `831` | U+26A0 `⚠` | stdout |
| `prepare.py` | `700`, `735`, `786`, `888`, `916` | U+2717 `✗` | stdout |
| `publish.py` | `161`, `197` | U+2191 `↑` + U+2192 `→` | stdout |
| `publish.py` | `169`, `205` | U+2713 `✓` | stdout (**after** the upload — §2.4) |
| `publish.py` | `172`, `208`, `779`, `830` | U+2717 `✗` | stdout |
| `publish.py` | `765`, `856` | U+26A0 `⚠` | stdout |

### 3.4 Runtime emission, other modules (stderr)

| Module | Sites | Char |
| --- | --- | --- |
| `codebook.py` | `543`, `547`, `552`, `578`, `637`, `698` | U+26A0 `⚠` (literal glyph) |
| `profile.py` | `250`, `254`, `259`, `281` | U+26A0 `⚠` |
| `profile.py` | `331` | U+2717 `✗` |
| `render.py` | `219`, `223`, `228`, `250`, `303` | U+26A0 `⚠` |
| `render.py` | `311` | U+2717 `✗` |

**[S]** Aggregate: **62 print sites, 9 modules, 6 distinct non-cp1252 codepoints** (U+2191, U+2192, U+2265, U+26A0, U+2713, U+2717) plus 3 argparse `description=` lines.

### 3.5 Reachability summary by command (cp1252 console)

| Command | Crashes today? | Trigger |
| --- | --- | --- |
| `sofer --help`, `--version` | no | ASCII-only ([S] §3.1) |
| `sofer validate --help` | no | description ASCII |
| `sofer prepare --help` | **yes** | `cli.py:1072-1073` |
| `sofer scan --help` | **yes** | `cli.py:1429` |
| `sofer init/publish/codebook/profile/render/mcp --help` | no | ASCII + em dash |
| `sofer validate <cfg>` | **yes** if config errors (`cli.py:77-79`) or `min_files` violation (`checks.py:131`) | normal path |
| `sofer prepare <cfg>` | **yes** on many normal paths | `cli.py:77-79`, `prepare.py` ⚠/✗, `_converters.py` ⚠ |
| `sofer prepare --verify` | **yes** always | `verification.py:132` |
| `sofer scan` (interactive / `--dry-run`) | **yes** | `cli.py:549` / `cli.py:569` |
| `sofer codebook/profile/render --all-files` | **yes** on warning paths | stderr ⚠/✗ |
| `sofer publish --target hf` | **yes**, incl. **after a successful upload** | `publish.py:161-208` |
| MCP tools (`sofer-mcp`) | no | see §4.2 |

**[A]** The issue's claim that only the two help screens are affected is understated by a wide margin (62 runtime sites in 9 modules, reachable on ordinary paths including a post-success `publish`), while the orchestrator's evidence item 3 understated it by ~34 sites because of the escape-vs-literal gap (§2.1).

---

## 4. What is NOT console-bound (and why) — the docstring vs executable distinction

### 4.1 File writers — deliberately utf-8, must not change

**[S]** These contain non-cp1252 characters but write to **files** with an explicit encoding, so they are safe and are *not* part of the fix:

| Site | Char | Destination |
| --- | --- | --- |
| `quality.py:589` | U+2014 | `write_quality_report` → `path.write_text(..., encoding=config.OUTPUT_ENCODING)` (`quality.py:594`, `quality.py:629`) |
| `quality.py:593` | U+2705 `✅` | same |
| `quality.py:602` | U+274C `❌` | same |
| `codebook.py:754` | U+2014 | `codebook.md` index → written utf-8 |
| `repo_compliance.py:1074-1435` | U+2014 | Dataset Card / frontmatter → written utf-8 |

**[S]** `config.OUTPUT_ENCODING` defaults to `"utf-8"` (`config.py:43` region, `_DEFAULTS["output_encoding"]`) and is exposed in `pyproject.toml:127` under `[tool.sofer]` `# ── Encoding / IO ──`.

**[A]** **No site was found that is both printed to a console and written to a file.** The two channels use separate string construction everywhere inspected: `quality.py::write_quality_report` builds its own `lines: list[str]` and never prints; the console report is built separately in `checks.py::print_summary` from `report.errors/warnings/quality_results`. **This is the answer to the orchestrator's explicit question and it removes the "shared string" risk from the strategy space.** Confirm during `design` by inspecting `repo_compliance` card builders for any `print` of card text (none found in greps 1–4).

### 4.2 MCP server — captured, therefore not console-bound

**[S]** `mcp_server.py:388-409` — `_capture_output()` swaps `sys.stdout`/`sys.stderr` for `io.StringIO` around every tool body (`_tool_execution` lock at `mcp_server.py:375-386`). Domain-module prints therefore land in the envelope's `output` field, never on a console. The MCP path cannot raise `UnicodeEncodeError` from these sites, and `mcp_server.py` must stay byte-clean on stdout for JSON-RPC framing (`process-boundary` PB-01, `mcp-server` MSP-R01).

**[S]** The MCP-side non-ASCII in `mcp_server.py` is in `description=` docstrings/schema fields (U+2014, cp1252-safe) and in prompt templates (`mcp_server.py:2990-3050`, U+2014) — all transported as JSON, not console-encoded.

### 4.3 Comments and docstrings — not executable

**[S]** Greps 1 and 3 return many hits that are `#` comments or docstring prose: `cli.py:119,398,415,419,453,519,623-628,745-748`; `scanner.py:4,5,13,14,293,356`; `splits.py`; `_converters.py:4,43-46,60-67,80,374-375,560`; `_clean.py:14`; `_mirror.py`; `_csv_reader.py:6,47`; `_parquet_helpers.py:38`; `mcp_server.py:15,16` (box-drawing `──>` in the module docstring); `config.py:31,152`; `model.py:114,398`; `metadata.py:209`; `quality.py:13,176,183,533`; `prepare.py:40,81,190,343,512,517,696-918` (section banners); `checks.py:117,185`; `publish.py:105,284,688-867`; `verification.py:64-105`; `codebook.py:465,483,486,537,560,618,707,739`.

**[S]** `mcp_registration.py`, `semantic.py`, `pii.py`, `_patterns.py` (U+2194 `↔` in `_patterns.py:6` docstring), `_sentinels.py`, `_formats.py` — **zero** executable-string hits in greps 1, 2 and 3.

**[A]** These are safe **today** but they are a latent trap: the em-dash convention is pervasive in user-facing strings, and cp1252 *does* encode it, so a future contributor copying an em-dash line is fine while one copying a `⚠` line re-introduces the bug. That is the core "is the fix future-proof?" question for the strategy choice (§8).

---

## 5. Indirect (non-literal) vectors reaching the console

**[S]/[A]** These are *not* covered by rewriting our literals, and they are the second reason strategy A is incomplete:

1. **User-supplied argv echoed by argparse.** argparse renders the offending token in `error:` messages: `invalid choice: '<token>'`, `unrecognized arguments: <token>`. **[A]** `sofer init "café" --user a` is fine (é is cp1252 `0xE9`) but `sofer init "日本語" --user a` or `sofer scan --ext "…"` with any non-cp1252 token crashes in argparse's error writer. `tests/test_cli.py:1294` already pins the `invalid choice` message for the ASCII case.
2. **Parsed config values interpolated into our prints.** Every ⚠/✗ f-string interpolates `{local}`, `{path}`, `{exc}`, `{remote}`, `{cfg.readme}`, `{check_name}`. **[A]** A dataset directory whose name contains a non-cp1252 character (CJK, emoji, `≤`) makes `codebook.py:543` crash *even after a strategy-A literal cleanup*, because the offending codepoint comes from the filesystem, not from our source.
3. **Third-party exception text.** `_converters.py:344,362,381,388,478,531` and `codebook.py:578,637,698` print `{exc}` from pyarrow / openpyxl / huggingface_hub. **[A]** Library messages routinely contain smart quotes (U+2018/2019 — cp1252-safe) but `_csv_reader.py:88` and `quality.py:558` show the codebase already formats its own messages; third-party text is outside our control and cannot be audited by any literal scan.
4. **Exception tracebacks.** `main()` has no handler (§1), so any exception path runs `traceback.print_exception` through the same stdout/stderr — **[A]** a traceback containing a non-cp1252 `repr()` of a value crashes the reporting of a crash.
5. **Non-ASCII file *content* printed to stdout.** **[S]** `cli.py:240` `print(codebook)` prints the whole generated codebook markdown. `_build_markdown` currently contains only U+2014 (`codebook.py:335`) — safe — but the markdown embeds **header names and sample values from the dataset** (`codebook.py:310` region). **[A]** A CSV with non-cp1252 header/sample bytes therefore crashes `sofer codebook` on stdout.

**[A]** Vectors 1–5 are all "data-driven, not literal-driven". Only a boundary-level encoding guard (strategy B) covers them; a literal rewrite (strategy A) covers none.

---

## 6. OpenSpec capability mapping (this is the spec delta)

**[S]** Capabilities present under `openspec/specs/` (17): `cli`, `ci`, `codebook`, `coverage`, `mcp-registration`, `mcp-server`, `metadata`, `packaging`, `parquet-conversion`, `pii-detection`, `prepare`, `process-boundary`, `profile`, `publish`, `render`, `scan`, `semantic-type-inference`, `tool-config`.

### 6.1 PRIMARY — `process-boundary` PB-02 already specifies this, and is currently under-tested

**[S]** `openspec/specs/process-boundary/spec.md:57-77`:

> **### Requirement: CLI user-visible output via executable subprocess (PB-02)**
> Tests in `tests/test_cli.py` SHALL invoke `[sys.executable, "-m", "sofer.cli", ...]` … whenever the requirement concerns user-visible output; parser-level tests SHALL remain for dispatch semantics. **The cp1252 help SHALL run on the ubuntu CI matrix via `PYTHONIOENCODING=cp1252` with `encoding="cp1252", errors="strict"`, SHALL exit 0, and SHALL produce strict-decodable stdout.** Windows-only behavior SHALL skip without privileges rather than fail.
>
> **#### Scenario: cp1252 help on the ubuntu matrix** — GIVEN `PYTHONIOENCODING=cp1252` in the subprocess env WHEN `--help` runs THEN exit code SHALL be 0 and stdout SHALL strict-decode as cp1252

**[S]** The implementing test exists — `tests/test_cli.py:1269-1288` `TestSubprocessBoundary::test_help_strict_cp1252` — and **it passes**, because it runs only `["--help"]` (`test_cli.py:1280`), which never renders a `description=`. The bug lives exactly in the blind spot.

**[A]** This is a **spec-vs-test gap**, not a missing-spec: PB-02's prose ("the cp1252 help") reads as broader than the single scenario's `--help`. The delta therefore needs to:
- **Modify** PB-02's requirement prose to state that **every** subcommand's help (i.e. `sofer <cmd> --help` for all 9 subcommands + nested `mcp add/remove`) and the runtime console paths SHALL be cp1252-safe; and
- **Modify** the "cp1252 help on the ubuntu matrix" scenario so `--help` is parametrized over every subcommand, plus **add** a scenario for runtime output (see §6.2/§7).

### 6.2 SECONDARY — `cli` capability has no output-encoding requirement

**[S]** `openspec/specs/cli/spec.md` requirements: CLI-R01 upload removed / prepare+publish top-level; CLI-R02 help accurate for new commands; CLI-R03 profile+render top-level; CLI-R04 help for profile/render; CLI-R05 `--version`; CLI-R06 shared version resolver; CLI-R07 init raw/ + `--move-existing`; CLI-R08 help for `init --move-existing`; CLI-R09 `mcp add/remove` help; CLI-R10 machine-readable status JSON.

**[S]** **Nothing in the `cli` capability states anything about output text, character repertoire, encoding, or console safety.** In particular CLI-R02 (`cli/spec.md:47-62`) constrains *which flags are documented*, never *which characters are printed*.

**[A]** Two options for the `design` phase to weigh (a decision point, §9):
- **(i)** Add a new requirement `CLI-R11: Console output is encodable on any console` under `cli`, keeping PB-02 as the *test-boundary* requirement. Cleaner separation: `cli` owns "the CLI never crashes on an unencodable character"; `process-boundary` owns "the cp1252 subprocess test proves it".
- **(ii)** Modify PB-02 only and leave `cli` alone. Smaller delta, but the behavioral contract then lives in a test-boundary capability, which is architecturally odd given `process-boundary/spec.md:5` explicitly states "No production behavior is specified here".

**[S]** Note the trap: `cli/spec.md:47` (CLI-R02) itself contains `raw/→cache/→build/` with U+2192 **in spec prose**. Whichever strategy is chosen, the `design` phase must decide whether spec prose is held to the console-safe rule (recommendation: **no** — spec files are UTF-8 documents, not console streams; only *emitted* text is in scope). Otherwise every strategy becomes a repo-wide spec rewrite.

### 6.3 TERTIARY — `coverage` and `ci`

**[S]** `openspec/specs/coverage/spec.md` COV-01…COV-06; enforced by `scripts/check_core_coverage.sh`:
```bash
for f in cli scanner prepare publish; do
  uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m
done
```
and `AGENTS.md` rule 14 forbids `# pragma: no cover` in those four modules.

**[S]** `openspec/specs/ci/spec.md` CI-01 (TOTAL `fail_under = 90`, config-owned); `pyproject.toml` `[tool.coverage.report] fail_under = 90`; `scripts/check_core_coverage.sh` invoked by `.github/workflows/ci.yml:84-85`.

**[S]** CI matrix = `ubuntu-latest` + `windows-latest` × Python 3.10–3.14 (`.github/workflows/ci.yml:26-28`); the lint job runs mypy only on 3.13 (`.github/workflows/ci.yml:13-15`, and `AGENTS.md` rule 12). **`ci.yml` sets no global `PYTHONIOENCODING`** — the only cp1252 in the repo is the env inside `test_cli.py:1282`.

**[A]** Consequence: any new production lines inside `cli.py`/`prepare.py`/`publish.py` (strategies B and C both add a boundary helper; A touches only string literals) must be **fully executed by the suite** or COV-06 fails. See §7.3.

---

## 7. Test surface and how to express the cp1252 regression

### 7.1 Existing help/console test surface

**[S]** From `tests/test_cli.py`:

| Test | Line | Boundary | Encoding-sensitive? |
| --- | --- | --- | --- |
| `TestParser::test_help_shows_prepare_publish_not_upload` | `59-68` | in-process + `capsys` | **no** |
| `test_main_help_prints` | `208-215` | in-process `cli.main()` | **no** |
| `TestInitHelp::test_help_lists_flags` | `685-695` | in-process + `capsys` | **no** |
| `TestInitHelp::test_help_mentions_pipeline` | `697-705` | in-process + `capsys` | **no** |
| `TestPublishCleanParser::test_help_contains_clean_flags` | `930-939` | in-process + `capsys` | **no** |
| `TestProfileRenderParserHelp::test_help_lists_all_flags_profile/render` | `1036-1059` | in-process + `capsys` | **no** |
| `test_profile_and_render_appear_in_help` | `1112-1120` | in-process + `capsys` | **no** |
| `TestProfileRenderHelpText::test_profile/render_help_describes_*` | `1141-1159` | in-process + `capsys` | **no** |
| `TestMcpCliHelp::*` (4 tests) | `1168-1226` | in-process + `capsys` | **no** |
| `TestSubprocessBoundary::test_help_exits_zero_and_lists_every_subcommand` | `1262-1267` | **subprocess** (utf-8) | no |
| **`TestSubprocessBoundary::test_help_strict_cp1252`** | `1269-1288` | **subprocess, cp1252** | **yes — but only `--help`** |
| `TestSubprocessBoundary::test_unknown_command_exits_2` | `1290-1294` | subprocess (utf-8) | no |
| `test_main_guard_via_runpy` | `1440-1458` | in-process `runpy.run_module` | no |

**[S]** **Every `capsys`-based test is structurally incapable of catching this bug** — `capsys` replaces `sys.stdout` with an in-memory object whose encoding never fails, so argparse happily writes U+2192. Only the subprocess boundary can observe it, and the one cp1252 subprocess test uses the one invocation that has no offending character. This is exactly why the bug shipped with a green suite.

**[S]** The existing helper already does everything a regression test needs — `tests/conftest.py:180-216`:
```python
def run_cli(argv, *, cwd, env=None, encoding="utf-8", timeout=...)
    ... subprocess.run([sys.executable, "-m", "sofer.cli", *argv],
                       encoding=encoding, errors="strict", ...)
```
`errors="strict"` on the *decoding* side means a child that degraded to `?`/`\u2192` still decodes fine; what fails is a child that crashed (non-zero rc) or a child that emitted raw bytes not decodable as cp1252. `PB-09` (`process-boundary/spec.md:213-233`) mandates that this helper is shared, never re-implemented.

### 7.2 How to express the cp1252 regression (must not weaken the 100% mandate)

**[A]** Recommended shape — extend `TestSubprocessBoundary`, reusing `run_cli`, no new helper:

1. **Make the help test exhaustive.** Turn `SUBCOMMANDS` (`test_cli.py:1250-1260`) into the parameter set:
   ```python
   @pytest.mark.parametrize("argv", [["--help"], *([c, "--help"] for c in SUBCOMMANDS),
                                     ["mcp", "add", "--help"], ["mcp", "remove", "--help"]])
   def test_help_strict_cp1252(argv, tmp_path):
       result = run_cli(argv, cwd=tmp_path, env={"PYTHONIOENCODING": "cp1252"}, encoding="cp1252")
       assert result.returncode == 0, result.stderr
       result.stdout.encode("cp1252")     # pins the repertoire, not just decodability
   ```
   **[S]** This turns the suite **RED today** on at least `["prepare", "--help"]` and `["scan", "--help"]` (rc 1) — verified statically from `cli.py:1072/1073/1429`; the four `awaiting-orchestrator` executions are not needed to predict it.

2. **Add a runtime-output scenario** — the half PB-02 does not currently reach. Cheapest deterministic trigger with no external data and no network:
   - `sofer validate <malformed-or-config-error TOML>` → exercises `cli.py:77-79` (`✗`) and the `checks.py:131` (`≥`) path if `min_files` is violated. Assert `rc == 1` **and** `"Configuration errors" in result.stdout` **and** `result.stdout.encode("cp1252")`.
   - `sofer scan --dry-run <toml-with-a-loose-file>` → exercises `cli.py:569` (`→`). Assert `rc == 0` and `result.stdout.encode("cp1252")`.
   - Optionally `sofer prepare --verify` for `verification.py:132` (needs the `datasets` extra — **[A]** likely `pytest.importorskip`, and it is the only site whose coverage depends on an optional dependency).

3. **Keep the assertion repertoire-based, not glyph-based.** If the chosen strategy is B, the degraded text contains `?` or `\u2192`; asserting `"→" in result.stdout` would fail under B and under A. Assert **rc + encodability + a stable ASCII substring** (`"DRY RUN"`, `"Configuration errors"`) instead. This keeps the test valid for whichever strategy the humans pick.

### 7.3 Interaction with the 100% `cli.py`/`prepare.py`/`publish.py` mandate

**[S]** `AGENTS.md` rule 14 + `scripts/check_core_coverage.sh` + `openspec/specs/coverage/spec.md` COV-06: `cli.py`, `scanner.py`, `prepare.py`, `publish.py` must each measure **100.00%** line coverage under the full suite, with **zero** `# pragma: no cover`.

**[S]** `tests/test_cli.py:1440-1458` `test_main_guard_via_runpy` executes the `if __name__ == "__main__": main()` guard in-process via `runpy.run_module("sofer.cli", run_name="__main__")` with argv at `--help`.

**[A]** Implications per strategy:
- **Strategy A** (literals only) — no new lines in core modules; COV-06 unaffected. Cheapest on coverage.
- **Strategy B/C** (boundary guard) — adds lines **and at least one conditional branch** at the CLI entry, inside `cli.py` (a 100%-gated module). Every new line and both branch arms must be executed. The guard must be written so it is reachable from the existing suite:
  - `test_main_guard_via_runpy` (`runpy`, real `sys.stdout`) executes the *real-stdout* arm;
  - `test_main_help_prints` (`cli.main()` under `monkeypatch`/pytest capture) executes the *stream-without-`reconfigure`* arm, because pytest's captured stdout has no `reconfigure`. **[A]** This is actually convenient: pytest capture gives free coverage of the defensive arm. But it must be verified, not assumed, in `design`/`apply`.
  - **[A]** Whether `argparse`'s `--version`/`--help` `parser.exit()` path and the `sys.exit(args.func(args))` path both flow through the guard depends on whether the guard is placed before `_build_parser()` (recommended: `main()` line 1, after `config.reload(None)` or before it) — placing it anywhere later leaves `--help` uncovered.
- **[A]** `publish.py` needs no source change under any strategy *if* the strategy is boundary-level; under strategy A it changes only literals (§3.3) so no coverage delta.

**[S]** One more hard constraint: `AGENTS.md` rule 14 forbids pragmas, so a defensive `except (AttributeError, ValueError): pass` around `reconfigure` cannot be pragma-excluded — it must be genuinely executed by a test (see `test_main_help_prints` above).

---

## 8. Candidate strategies — behaviour and blast radius

Not choosing; presenting consequence-equivalent facts for the human decision (§9).

### Strategy A — Replace the offending characters with ASCII everywhere they are emitted

Change set: `→` → `->` (5 sites: `cli.py:549,569,1072,1073,1429` + `publish.py:161,197`), `↑` → `up`/removed (`publish.py:161,197`), `⚠` → the existing `[!]`/`WARN` alphabet (26 sites), `✗` → the existing `X` (13 sites), `✓` → `OK` (3 sites), `≥` → `>=` (`checks.py:131`).

| Dimension | Consequence |
| --- | --- |
| Windows legacy console / redirect | Always works — the byte stream is pure ASCII. Best possible `?`-free output. |
| UTF-8 terminal | **Loses** the glyphs. `⚠`/`✓`/`✗`/`↑`/`→` disappear for the majority of users (macOS, Linux, Windows Terminal, VS Code) to serve the minority. |
| Future-proof? | **No.** Any new `⚠` added tomorrow re-introduces the bug; nothing prevents it and no test in the *capsys* class can catch it (only the parametrized subprocess test would). |
| Indirect vectors (§5) | **No coverage.** Non-cp1252 filenames, argparse-echoed argv, third-party exception text, tracebacks, dataset content printed to stdout still crash. |
| Rule 1 (`pyproject` config surface) | **No** new config key needed — but also: nothing is made *configurable*, so a user who wants glyphs back has no switch. |
| Rule 7 / rule 13 (README sync) | Requires README/README_ES edits only if user-visible samples change. **[S]** README already documents `-> raw/<rel>` (`README.md:320` / `README_ES.md:332`), and no README sample shows `→`/`⚠`/✓/✗/↑ — so **possibly no README change**, a real advantage worth verifying in `design`. |
| Coverage (COV-06) | Neutral — literals only. |
| Exit codes / stdout bytes for existing tests | In-process `capsys` tests assert flag names and ASCII substrings — **[S]** unaffected. `test_codebook.py:611`, `test_profile.py:877,879` assert glyph-free substrings (`"Unsupported format"`, `"Skipping directory"`) — unaffected. |
| Blast radius | ~62 literals in 9 modules + 3 argparse strings. Realistically a **glyph-alphabet normalization** change (§2.5), which needs its own UX decision about the marker vocabulary. |

### Strategy B — Boundary encoding guard (degrade instead of crash), keep the glyphs

Change set: one helper called from `cli.main()` that reconfigures the active text streams so unencodable characters degrade, e.g. `sys.stdout.reconfigure(errors=<handler>)` / same for `sys.stderr`, guarded for streams that lack `reconfigure` (StringIO, pytest capture, closed streams).

| Dimension | Consequence |
| --- | --- |
| Windows legacy console / redirect | `rc = 0`, no traceback; the offending character renders as a replacement. **[A]** Under documented codec behaviour, `errors="replace"` renders U+2192 as `?`; `errors="backslashreplace"` renders it as the literal text `\u2192` (more honest, noisier). Both are cp1252-encodable, so the strict-decode assertions hold. |
| UTF-8 terminal | **Glyphs preserved exactly as today.** Only the failing console degrades. This is the only strategy with zero visual regression for the majority. |
| Future-proof? | **Yes for the class, not just the instances.** Any literal added tomorrow, *and* every indirect vector in §5 (filenames, argv echo, third-party exception text, printed dataset content) is covered by the same guard. |
| Indirect vectors (§5) | **All five covered, by construction.** |
| Rule 1 (`pyproject` config surface) | **Open question.** The *error handler* is a policy default. Rule 1 says tool-wide defaults belong in `pyproject.toml [tool.sofer]` / `config.py` — so a literal `errors="replace"` inside `cli.py` arguably violates it, and a new key (e.g. `console_encoding_errors = "replace"`) is the rule-compliant shape. That adds config surface + validation + a `tool-config` spec delta (`tool-config` TC-01… exists with a validation requirement at `tool-config/spec.md:315`). **This is the biggest cost of B and a decision point.** |
| `--help` coverage | **Covered.** argparse resolves `_sys.stdout` at call time, so a guard in `main()` before `_build_parser()` covers help. **[A]** Must place it *before* `parse_args()`, not after. |
| Rule 7 / rule 13 (README sync) | Only if the behaviour is documented (recommended: yes, a short "Console encoding" note in the Troubleshooting/Reference area of both READMEs). |
| Coverage (COV-06) | **Cost.** New lines in `cli.py` (100%-gated) + at least one defensive branch, no pragmas allowed. Needs `test_main_help_prints`-style coverage of the no-`reconfigure` arm (§7.3). |
| Exit codes / stdout bytes for existing tests | **[S]** In-process tests: unchanged (pytest's captured stream has no `reconfigure`, guard no-ops). Subprocess tests with default env: stdout is UTF-8, so `errors` is never consulted → byte-identical. `test_help_strict_cp1252`: stdout changes from *crash* to *degraded*, and the assertion `result.stdout.encode("cp1252")` passes. |
| Risk | A wrongly implemented guard (e.g. reconfiguring `sys.stdout` when it is not a `TextIOWrapper`, or reconfiguring the MCP-captured `StringIO`) could interfere with `mcp_server._capture_output` interleaving or with pytest capture. **[A]** Mitigated by guarding on the presence of `reconfigure` **and** never touching anything when the stream is not a `TextIOWrapper`; must be explicitly reviewed. Also: `PYTHONIOENCODING` set by a user who *wants* a hard failure loses that (arguably desirable) behaviour. |

### Strategy C — Hybrid (boundary guard + ASCII-safe help text)

**§3.1's 3 argparse codepoints** → ASCII **and** the B guard for runtime.

| Dimension | Consequence |
| --- | --- |
| Windows legacy console | Help screens are clean ASCII (no `?`/`\u2192` noise in the one place users read); runtime output degrades gracefully instead of crashing. |
| UTF-8 terminal | Help text loses 3 `→` glyphs (trivial, and `->` already exists two lines below the same screen — `cli.py:1427` uses `->` inside the very same `scan` description). Runtime glyphs preserved. |
| Future-proof? | **Yes.** Same class coverage as B; and help text (the highest-visibility surface, read by every new user on every platform) is additionally guaranteed ASCII, so a future edit can't regress the first impression even if the guard were mis-placed. |
| Indirect vectors | All five covered (by the guard). |
| Rule 1 | Same config-surface question as B. |
| Rule 7 / rule 13 | Needs README sync **only if** the `scan`/`prepare` help text is quoted (it is not — `README.md:320` quotes the ASCII `->`). Also a natural place to fix the `cli.py:1429` vs `cli.py:1427` intra-screen arrow inconsistency (§2.5). |
| Coverage (COV-06) | Same cost as B. |
| Blast radius | Smallest honest version of A (3 argparse strings) + B's guard. |

### Cross-cutting: what none of the three do

**[A]** None addresses `PYTHONUTF8`/UTF-8 mode, and none changes the *file* writers (which are already explicit-utf-8, §4.1). None changes the MCP path (§4.2).

---

## 9. Decision points that need a human product/scope decision

Each is a genuine product/scope call, not a technical detail. Options and consequences are consequence-equivalent.

**D1 — Whose output do we optimise?**
- (a) **Legacy-console-safe only (A)** — everyone sees ASCII; no `?`, but the majority loses the glyph vocabulary; indirect vectors remain unfixed.
- (b) **Graceful degradation (B)** — the majority keeps the glyphs; legacy consoles see a replacement character; the crash class is fixed.
- (c) **Hybrid (C)** — help screens ASCII, runtime graceful.
- *Consequence:* (a) is the only option with zero added `cli.py` lines and zero rule-1 question, and it leaves a documented class of crash open. (b)/(c) fix the class and introduce a config-surface question (D3).

**D2 — Is `⚠`/`✓`/`✗`/`↑` decoration worth keeping at all?**
- (a) Keep the glyph alphabet, make it safe (B/C).
- (b) Normalize to ASCII markers and adopt the already-dominant `[!]`/`X`/`OK`/`[i]` vocabulary (A, but done as a deliberate consistency change across ~62 sites).
- *Consequence:* (b) is a much larger review (touch `prepare.py`, `publish.py`, `profile.py`, `render.py`, `codebook.py`, `_converters.py`, `verification.py`, `checks.py`, `cli.py`) and its own UX argument; (a) is a smaller diff and keeps today's look. Note §2.5: the vocabulary is *already* inconsistent, so "keep as-is" means "keep the inconsistency".

**D3 — Does the chosen error handler become configurable (`[tool.sofer]`)?**
- (a) Hardcode one handler constant in `config.py` next to `OUTPUT_ENCODING` (rule 1 satisfied by location, no new TOML key, no `tool-config` spec delta).
- (b) Expose `console_encoding_errors = "replace"|"backslashreplace"` in `[tool.sofer]` with validation (full rule-1 compliance, but new config surface, a `tool-config` spec delta, and a `DatasetConfig`/`config._load_tool_config` validation arm to test).
- (c) Hardcode inline in `cli.py` (simplest, but arguably violates rule 1 — a tool-wide default in a function body).
- *Consequence:* (b) is the most "correct per AGENTS.md" and the most expensive; (a) is the pragmatic middle. Only relevant if B or C is chosen.

**D4 — Behaviour contract in `cli` or in `process-boundary`?** (see §6.2)
- (a) New `CLI-R11` under `cli` + modified PB-02 scenario. Clean ownership.
- (b) Modify PB-02 only. Smaller delta, but puts production behaviour in a capability whose own purpose statement (`process-boundary/spec.md:5`) says it specifies none.

**D5 — Scope of the runtime test.** 
- (a) Extend the cp1252 subprocess test to all subcommands' help **+** one runtime path (`scan --dry-run` or `validate` config-error).
- (b) Help only (mirrors today's PB-02 text most literally).
- *Consequence:* (b) leaves 62 runtime sites unguarded by regression tests — the exact failure mode that produced issue #161 (a green suite over a broken path).

**D6 — Do we fix `publish`'s post-success crash explicitly?** (§2.4) 
- (a) Rely on the general guard (B/C) — covered.
- (b) Also reorder/guard the success print specifically even under strategy A, so a successful upload can never report `rc=1`.
- *Consequence:* (b) adds lines to `publish.py` (100%-gated) and needs a coverage story; (a) is free under B/C but unavailable under A.

**D7 — Is spec prose in scope?** (§6.2 trap)
- (a) No — only *emitted* text is held to the console-safe rule.
- (b) Yes — then `cli/spec.md:47` (`raw/→cache/→build/`) and other spec files must also be ASCII-ified.
- *Consequence:* (b) turns any strategy into a spec-repository-wide edit with no user-visible benefit and conflicts with the UTF-8-artifact convention (`openspec/config.yaml` "English artifacts", `codebook/spec.md` etc.). Recommendation: (a). **This is also a trap for the test:** if (b) were chosen, a whole-repo ASCII check would be needed; under (a) the test must scan *emitted output only*, never source text.

**D8 — Windows-only gate or ubuntu-deterministic gate?**
- **[S]** PB-02 already settles this: run on the ubuntu matrix via `PYTHONIOENCODING=cp1252`, with Windows-only behaviour skipping rather than failing. Confirm no change is wanted. (Running the cp1252 test on `windows-latest` too is unnecessary and risks flake.)

---

## 10. Non-goals (candidates)

1. **Rewriting all glyphs across all modules** (including `quality.py` ✅/❌ and Dataset-Card prose) — those are file-bound and correct as UTF-8 (`§4.1`). Only under D2(b) does a broader normalization become in-scope, and then only for *console* markers.
2. **Forcing UTF-8 mode globally** (`PYTHONUTF8=1`, `sys.flags.utf8_mode`, re-exec) — changes process-wide semantics, alters `locale.getpreferredencoding` for everything (including file/dataset reads that the `data-quality` capability pins to `["utf-8-sig", "utf-8"]`), and is a much larger behaviour change than the reported bug.
3. **Changing `PYTHONIOENCODING`/`PYTHONLEGACYWINDOWSSTDIO` for the user** — we cannot and should not mutate the user's environment.
4. **Changing `config.OUTPUT_ENCODING`** (`pyproject.toml:127`) or any file-writer encoding — unrelated to console output; would break Dataset Cards/codebooks.
5. **Changing the MCP capture path** (`mcp_server._capture_output`) — StringIO cannot raise `UnicodeEncodeError`; no defect exists.
6. **Translating or reflowing help text, or changing `REPORT_LINE_WIDTH`/`REPORT_SUB_LINE_WIDTH`** (`pyproject.toml:117-118`).
7. **Installing/altering the Windows console code page from inside sofer** (`chcp`, `SetConsoleOutputCP`) — process-external, side-effectful, and outside a CLI's remit.
8. **Making the CLI's exit code depend on encoding failure** — the opposite of the fix.
9. **`errors="ignore"`** — silently drops characters; recommend explicitly excluding it from the strategy space (it turns a crash into silent data loss in the output).

---

## 11. Open questions / risks to carry into `design`

| # | Question | Why it matters |
| --- | --- | --- |
| Q1 | On Windows with redirection/piping, what **exactly** does `sys.stdout.encoding` report, and does `sofer scan --help > out.txt` crash there? | §1 — determines whether the user-facing narrative is "console" or "redirection/wrapper". Needs a one-line probe. Not verifiable in this phase (no shell). |
| Q2 | Does pytest's captured stdout expose `reconfigure`? | §7.3 — decides whether the defensive arm of the B/C guard is free coverage or needs a dedicated test. **[A]** Expected: no `reconfigure` on `EncodedFile`/`CaptureFixture`, so `test_main_help_prints` covers the no-op arm. |
| Q3 | Under B/C, is the guard placed **before** `_build_parser()`/`parse_args()`? | §3.1 — otherwise `--help` is not covered and the fix silently misses the issue's own symptom. |
| Q4 | Is any `repo_compliance` card string also printed? | §4.1 — greps found no shared console/file string; confirm by reading the card builders before finalizing strategy A's site list. |
| Q5 | Are there console sites reached only through MCP stdout leakage? | §4.2 — MSP-R01 requires no stray stdout bytes; the guard must not disturb `_capture_output`. |
| Q6 | Does `verification.py:132` (`prepare --verify`) need the `datasets` extra to be testable? | §7.2 item 3 — the only cp1252 site whose regression test may need `importorskip`. |
| Q7 | Should the `pyproject.toml` `[tool.sofer]` "Encoding / IO" group gain a console key? | §9 D3 — rule 1 compliance vs new config surface + `tool-config` spec delta. |
| Q8 | Does `README.md`/`README_ES.md` need any edit under each strategy? | **[S]** No README sample shows `→`/`⚠`/`✓`/`✗`/`↑`; `README.md:320` already shows `->`. Under A/C: likely no sync needed beyond a new doc note; under B: recommended short note. Rule 13 requires both files in the same change if a section is touched. |

---

## 12. Evidence appendix — exact greps/commands used in this phase

All greps were run against `C:/Users/elaze/Desktop/sofer` (read-only).

1. `[^\x00-\x7F]` in `src/sofer/cli.py` — full file, 90 hits (§1, §2.2, §3.1).
2. `→` in `src/` and `tests/` (§1, §2.5, §7.1).
3. `\\u[0-9a-fA-F]{4}` across `src/sofer` — 70 hits, **the decisive one** (§2.1, §3.2–§3.4).
4. `print\(|sys\.(stdout|stderr)\.write|console|_warn` across `src/sofer` — the stream census (§3.3–§3.4).
5. `[⚠✗✓✅❌↑→↔≥─│├└•·⏱★☆⚡]` across `src/sofer` — literal-glyph census, separating comments from code (§2.2, §4.3).
6. `(print\(|lines\.append\(|return |help=|description=|\.write\(|f")[^\n]*[^\x00-\x7F]` across `src/sofer` — the executable-string filter; its complete output is §3.3–§3.4 categories (§2.2).
7. `cp1252|PYTHONIOENCODING|encoding=` across `tests/` — found `tests/conftest.py:180-216` (`run_cli`) and `tests/test_cli.py:1269-1288` (§6.1, §7.1, §7.2).
8. `cp1252|run_cli|PYTHONIOENCODING` in `tests/test_cli.py` — the help-test census (§7.1).
9. `def test_.*help|"--help"` in `tests/test_cli.py` — proved every other help test is `capsys`-in-process (§7.1).
10. `encoding|cp1252|console|UTF-8|help text` across `openspec/specs` — found PB-02, CLI-R02, `data-quality` UTF-8-only chain, `tool-config` validation (§6).
11. `→|⚠|✗|✓|↑` in `README.md` and `README_ES.md` — many `→` in *documentation prose*; **none in CLI output samples** (§8, Q8).
12. `PYTHONIOENCODING|cp1252|coverage|python-version|matrix` in `.github/workflows/ci.yml` — no global cp1252; matrix 3.10–3.14 × ubuntu/windows (§6.3).
13. Reads: `src/sofer/cli.py` (`62-110`, `398-601`, `1026-1081`, `1348-1360`, `1544-1576`), `codebook.py` (`530-710`), `prepare.py` (`208-235`), `_converters.py` (`135-165`, `275-300`), `checks.py` (`40-84`, `120-150`), `verification.py` (`120-155`), `profile.py` (`325-340`), `render.py` (`296-315`), `publish.py` (`150-215`), `model.py` (`428-480`), `config.py` (`1-60`), `tests/conftest.py` (`170-230`), `openspec/specs/process-boundary/spec.md` (`40-130`), `openspec/specs/cli/spec.md` (`40-85`), `openspec/project.md`, `openspec/config.yaml`, `scripts/check_core_coverage.sh`.
14. **[R]** Not re-executable in this phase (no shell tool): `PYTHONIOENCODING=cp1252 uv run sofer scan --help` / `prepare --help`, and the Windows redirection probe (Q1).

**Net verdict of the exploration:** the reported bug is real and reproduced by source inspection; its *true* surface is **3 argparse description lines + 62 print sites across 9 modules**, of which the orchestrator's enumeration captured roughly 13% because most sites use `\uXXXX` escapes rather than literal glyphs; the crash class also covers five data-driven vectors that no literal rewrite can fix; the existing `process-boundary` PB-02 requirement already specifies cp1252 help safety and its implementing test (`test_cli.py:1269`) passes only because it exercises the one invocation with no offending character — a spec-vs-test blind spot, which is the most important thing the `proposal` must state.
