# Feature: quality-peak-memory — issue #326

**Branch:** `fix/326-validate-peak-memory` from `dev@4189b93`. **Issue:** `emiliodavola/sofer#326`
**Delivery PR:** (this PR) → `dev`. **Workflow:** ODD only — no `openspec/changes/` folder (L2).
**Risk:** none — a bounded read whose judged bytes are unchanged (D1, D7), pinned by
`tests/test_quality.py::TestEncodingProbePeak`; no data, security, contract, concurrency or delivery
surface is touched, and no versioning file is on this branch (L3).

## Goal

`sofer validate`'s quality pass peaked at ≈1× the corpus: 44.0 MiB on a 31.2 MiB CSV, 160.1 MiB on a
160.0 MiB one. The #290 fix is real (the 16.1 GB climb is gone), but the property it is credited with —
per-row memory independent of the dataset size — did not hold above ~60 MiB. #326 asked for the
allocation to be named first, then bounded, then pinned by a test. All three are delivered.

## Specs

S1 (issue #326 §"Proposed solution" 1, verbatim): "**Identify the allocation first.**
`tracemalloc.take_snapshot()` taken at the peak rather than at the end, with
`snapshot.statistics(\"traceback\")`, will name the site. A sampling thread that snapshots when
`get_traced_memory()` is highest is the cheapest instrument."

S2 (issue #326 §"Proposed solution" 2, verbatim): "**Then bound it**, if the site is a per-row
accumulator that can be streamed or chunked."

S3 (issue #326 §"Proposed solution" 3, verbatim): "**Whatever the outcome, pin it.** A test asserting
the peak is flat across two corpus sizes would have caught this; nothing today does."

S4 (`openspec/specs/data-quality/spec.md` §1.2, verbatim): "**Bounded per-row memory (issue #290)** —
the `empty_columns` state is a per-column boolean, the `duplicates` hash table is capped at
`quality_max_dup_tracking`, and the finding lists stop growing at their report limits; per-row memory
SHALL be independent of the dataset size."

S5 (issue #326 §"Why it matters", verbatim): "The #290 fix is real — it removed the 16.1 GB climb — but
the property it is credited with (\"validate/prepare can now run on multi-GB datasets\") holds only if
~1× the corpus fits in memory. A 10 GB corpus should be assumed to need ~10 GB of RAM, which is a
different claim from a fixed budget, and the difference decides whether a multi-GB run is feasible at
all."

S6 (`openspec/specs/data-quality/spec.md` §1.2, the sentence the fix falsifies, verbatim): "Until the
allocator is identified, a corpus of N bytes should be assumed to need on the order of N bytes of RAM,
and the root cause is filed separately."

S7 (`AGENTS.md` rule 3, verbatim): "The most critical bug pattern we've seen: code that uses a
hardcoded default instead of reading from the user's TOML config."

S8 (`openspec/specs/data-quality/spec.md` §4.9, the requirement the code violated, verbatim):
"The system MUST verify each text-eligible (`.csv`/`.tsv`, case-insensitive) file is decodable via
`[\"utf-8-sig\", \"utf-8\"]` by reading `config.PROBE_CHUNK_BYTES` (8 KB) and trying
`chunk.decode(enc)` in order."

**Outcome per spec:** S1–S3 delivered. S4 restored. S5's premise removed. S6 corrected in the spec.
S7 honoured (the width is still `config.PROBE_CHUNK_BYTES`, read at call time). S8's requirement was
already written as intended behaviour — the code was the gap.

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | The fix is the bounded read §4.9 **already required**, not a redesign of the probe. | §4.9 says "by reading `config.PROBE_CHUNK_BYTES` (8 KB)" (S8); the code read the whole file and sliced. Three lines change and the bytes judged stay the same, so every §4.9 scenario keeps its verdict. |
| D2 | The width stays `config.PROBE_CHUNK_BYTES`, read at call time — never a literal `8192`. | S7 + §4.9; `QualityValidator.run()` already re-reads config values per call, so `config.reload()` must move the probe width too. |
| D3 | The pin is a **peak-flatness** test with a tiny `max_sample` and `full_scan = "never"`. | With the shipped `max_sample = 100 000` the capped sample state (~34 MiB) masks a small corpus's probe term entirely (measured: 300 000 and 1 000 000 rows both peak at 37.07 MiB). A tiny cap makes every capped accumulator saturate within a few hundred rows, leaving the uncapped read as the only term that can grow with the corpus. |
| D4 | No new tracked measurement script: the spec cites the tracked generator plus the method. | The issue asks to identify, bound and pin; the durable pin is the test. A second script would duplicate the corpus generator of `scripts/measure_quality_scan_rss.py` (AGENTS.md rule 4). The diagnosis instrument lives in `tmp/` (gitignored) and its commands and outputs are recorded below. |
| D5 | The **residual budget is recorded, not hidden**: after the fix the peak is flat but its constant belongs to `max_sample` (~37 MiB at the 100 000 default, mostly `format_consistency` samples). | S4 requires independence from the dataset size, not a particular constant, and the constant is config-owned. Named in the spec so "flat" is not read as "small". |
| D6 | Versioning stays off this branch. | L3, and rule 12: the version is derived from the tag at release time, so a fix PR carries none of it. |
| D7 | One observable difference is accepted and named: a file whose read fails **after** the first `probe_chunk_bytes` no longer produces the probe's `Cannot read` finding. | It is still reported as a `fail` by the streaming pass (`_process_file` catches `(OSError, csv.Error)` and emits `corrupt_records: Cannot read '<file>': <exc>`), so publish is blocked either way; the probe can no longer report an I/O error it did not encounter. |

## #326 — measured (S1, S2, S5)

Instrument (scratch, `tmp/`, gitignored): the corpus generator of
`scripts/measure_quality_scan_rss.py` plus a sampling thread that snapshots when `get_traced_memory()`
is highest — the issue's own S1 recipe. Config: the script's bounded case
(`quality_full_scan = "never"`, `quality_max_dup_tracking = 10 000`), `max_sample` at its shipped
100 000 default.

**The site, named.** On the 2 000 000-row / 63.38 MiB corpus the pre-fix peak's top statistic is a
single `Path.read_bytes` frame:

```text
  full (shipped code)              peak=   63.41 MiB
       63.38 MiB  ...\Lib\pathlib\_abc.py:626        <- Path.read_bytes
  probe_only (encoding check)      peak=   63.39 MiB   csv=63.38 MiB
```

The probe on its own allocates 1:1 the file size: 63.39 MiB on a 63.38 MiB CSV and 31.17 MiB on a
31.16 MiB one. On the fixed code the same probe peaks at **0.02 MiB**.

**The peak, flat.** Same instrument, same corpora, before and after:

| Corpus | CSV size | peak `tracemalloc`, pre-#326 | peak `tracemalloc`, post-#326 |
| --- | --- | --- | --- |
| 300 000 rows | 9.3 MiB | 37.07 MiB | 37.07 MiB |
| 1 000 000 rows | 31.2 MiB | 37.07 MiB | 37.07 MiB |
| 2 000 000 rows | 63.4 MiB | 63.41 MiB | 37.07 MiB |

The 2 000 000-row case falls from 63.41 to 37.07 MiB, and what is left is the capped state the
`max_sample` default owns (`_csv_reader.py:124` 28.44 MiB of retained field strings +
`quality.py:367` 5.71 MiB of list storage), which saturates instead of following the corpus (D5).

## Tasks

| # | Task | Spec | Route | State | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Name the allocation: peak-time `tracemalloc` snapshot at two corpus sizes | S1 S5 | inline | done | `tmp/profile_quality_peak.py` (scratch): top site `pathlib/_abc.py:626` = 63.38 MiB of a 63.41 MiB peak; probe alone 63.39 MiB on a 63.38 MiB CSV |
| T2 | RED: a test asserting the peak does not track the corpus size | S3 S4 | inline | done | `uv run pytest tests/test_quality.py::TestEncodingProbePeak -q` → `assert (3500467 - 75549) < 1048576` |
| T3 | Bound the site, reading the probe width from config | S2 S7 S8 | inline | done | `src/sofer/quality.py` bounded read; `uv run pytest tests/test_quality.py -q` → 84 passed |
| T4 | Regressions: encoding-validation behaviour unchanged, full suite green | S4 S8 | inline | done | `uv run pytest tests/test_quality.py -q` → 85 passed (2 new tests); `uv run pytest tests/ -q` → 2240 passed, 9 skipped |
| T5 | Correct the falsified spec evidence with re-measured numbers | S5 S6 | inline | done | `openspec/specs/data-quality/spec.md` §1.2 (clause, evidence row, measurement record) and §4.9 (requirement + scenario + evidence) |
| T6 | Gates (ruff/format/mypy/pyright/check_test_mapping), commit, PR | — | inline | done | gates below; `b7e8a74` (fix + tests) and this record's commit; delivery PR: this PR → `dev` |

## Delivery

- Gates: `uv run ruff check src/ tests/ scripts/` (pass), `uv run ruff format --check src/ tests/`
  (75 files formatted), `uv run mypy src/ scripts/` (no issues, 38 files), `uv run pyright` (0 errors,
  1 pre-existing `_toml.py` `tomli` warning), `uv run python scripts/check_test_mapping.py` (contract
  holds), `uv run pytest tests/ -q` (2240 passed, 9 skipped), coverage gates (`uv run coverage run -m
  pytest` → 2240 passed in 141.5 s; `uv run coverage report -m` → TOTAL 94% against the config-owned
  floor of 90; `bash scripts/check_core_coverage.sh` → 100% in each of cli, scanner, prepare, publish).
- Work-unit commits: `b7e8a74` (`fix(quality): bound the encoding probe so the pass's peak stops
  tracking the corpus`) and `4645770` (`docs(quality): record the #326 allocation and correct the
  data-quality evidence`).
- Delivery PR: https://github.com/emiliodavola/sofer/pull/330 → `dev`.

## Log

L1 (user, verbatim): "implementá todos los issues de tipo bug, volvé con el PR subido, yo lo autorizo,
usá ODD no SDD"

L2 (user, verbatim): "una rama aparte para el versionado!" → resolved by one focused question: only the
fix travels on this branch; no `CITATION.cff`/tag/release work is done here (D6).

L3 (this session, scope check): the only **open** issue labelled `type:bug` is #326. #316, #325, #293,
#289 and the other bug-labelled issues are closed, so "todos los issues de tipo bug" resolves to one.

L4 (this session, claim checked before believing it): `src/sofer/quality.py` had exactly one
`read_bytes()` call site, at the encoding probe, and `pyproject.toml` declares the probe's width as
`probe_chunk_bytes = 8192` with the comment "An 8 KB probe like encoding_validation is deliberately
absent" from the row-requiring set — the design assumed an 8 KB read while the code read the file.

L5 (this session, instrumented): the probe alone peaks at 1:1 the CSV (31.17 MiB / 31.16 MiB), and on
the 2 000 000-row corpus the pre-fix peak's top frame is `Path.read_bytes` — S1 satisfied by
measurement, not by reading the code.

L6 (this session, RED then GREEN): `assert (3500467 - 75549) < 1048576` before the fix; the same test
passes after it, and the 2 000 000-row peak drops 63.41 → 37.07 MiB with the probe at 0.02 MiB.
