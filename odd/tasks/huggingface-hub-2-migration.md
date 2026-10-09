# Feature: huggingface-hub 2.x migration — Dependabot PR #278

**Branch:** `chore/278-huggingface-hub-2` from `dev@7c30aaa`
**Source:** `emiliodavola/sofer#278` — *chore(deps): bump huggingface-hub from 1.32.0 to 2.1.1*
**Related:** #277 — merged as `86398ab` (the routine group PR; does **not** touch `huggingface-hub`)
**Delivery PR:** `emiliodavola/sofer#280` — merged as `b069cc5`; the superseded bot PR #278 was closed by that merge's `Closes #278` keyword

## Goal

Take the `huggingface-hub` major deliberately, as the repository's own policy requires: majors stay
out of the routine group and "require explicit adaptation review" (AGENTS.md rule 9, CI-14). The bot
PR is red, and its redness is a real upstream breaking change needing an edit the bot cannot make.

## Root cause (authoritative)

`huggingface_hub` v2.0.0 release notes:

> **💔 Breaking Change: HTTP stack moves to `httpx2`** — *"clients and transport exceptions now come
> from `httpx2`/`httpcore2` instead of `httpx`/`httpcore`."*

Confirmed in the lock: `huggingface-hub` 2.x declares `{ name = "httpx2" }`.

## Blast radius in sofer — measured, not assumed

| Check | Result |
| --- | --- |
| Does `src/` import `httpx` at all? | **No** — the migration cannot touch the source |
| Does sofer use the removed `upload_large_folder`? | **No** — it already uses `HfApi.upload_folder()`, the replacement |
| Are the APIs it uses (`HfApi`, `RepositoryNotFoundError`, `get_token`) removed? | **No** |
| Does the rest of the suite survive 2.x? | **Yes** — the bot PR's CI ran the full matrix with 2.x: `1 failed, 2001 passed` |
| The single failure | `tests/test_publish.py::TestRemoteFailClosed::test_inspect_repo_returns_empty_on_repo_not_found` → `ModuleNotFoundError: No module named 'httpx'` |

## Two findings that shaped the implementation

**F1 — the bump is coupled to `datasets`, and that is not lock noise.** `uv` could not reach 2.x with
a focused upgrade: it resolved only to 1.33.0. `uv tree --invert --package huggingface-hub` shows why:

```
huggingface-hub v1.33.0
├── datasets v5.0.1     ← caps hf below 2
└── sofer
```

**`datasets 5.0.1` requires `huggingface-hub<2`**, so hf 2.x is unreachable until `datasets` moves to
5.1.0. That is why the bot's #278 lock diff also bumped `datasets` — it was the resolvability
condition, not re-resolution noise. This branch therefore carries `datasets 5.0.1 → 5.1.0` as a
**forced** consequence, and the PR must say so.

**F2 — "drop the HTTP library from the test entirely" is impossible.** Considered as a way to kill
this fragility class permanently, and rejected by measurement, not by assumption:

```
$ uv run python -c "from huggingface_hub.utils import RepositoryNotFoundError; RepositoryNotFoundError('not found')"
TypeError: HfHubHTTPError.__init__() missing 1 required keyword-only argument: 'response'
```

`response` is a mandatory keyword-only argument, so a response object **must** be supplied, and under
2.x it must be an `httpx2` type. The handler in `src/sofer/publish.py` catches
`RepositoryNotFoundError` **by type only** (it never reads `e.response`), so the object is incidental
to sofer but required by the exception.

## Decision: the declared floor stays at `>=0.26.0`

`pyproject.toml:23` declares `huggingface-hub>=0.26.0`. Raising it to `>=2.0` was considered and
**rejected**:

- The floor states the **runtime** contract for users. The source is unchanged and still works with
  1.x, so raising it would restrict users for no code reason.
- The test's `httpx2` need is an implementation detail of the **test environment**, which `uv.lock`
  defines (it pins 2.x). Tests are not required to run against the declared floor.
- Verified: no spec, test, guard or doc asserts the floor, so this decision has no gate impact.

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: install 2.x and reproduce the failure locally | done | `ModuleNotFoundError: No module named 'httpx'` at `tests/test_publish.py:645`, matching CI exactly |
| T2 | GREEN: adapt the test from `httpx` to `httpx2` | done | `TestRemoteFailClosed` 4 passed |
| T3 | Confirm the response object must be `httpx2` and is mandatory | done | F2 above: without `response` → `TypeError`; with `httpx2.Response` → OK |
| T4 | Full gates + independent verification | done | suite 2005 passed / 6 skipped on branch **and** base (identical); ruff, mypy, pyright, mapping gate green; coverage TOTAL 94% with the four rule-14 rows at 100% |
| T5 | Commits + push + PR; the bot PR #278 closed as superseded | done | PR #280 — 13/13 checks SUCCESS; merged as `b069cc5`; commits `274643a`, `1a547e3`. `Closes #278` closed the bot PR on merge: the repository's default branch is `dev`, so the closing keyword applies to a PR reference |

## Verification findings worth recording

**The declared floor is now unverified by CI.** The independent verifier confirmed no spec, test,
guard or script asserts `huggingface-hub>=0.26.0` — the only active occurrence is `pyproject.toml:23`.
But because the adapted test hardcodes `httpx2`, the suite can no longer run against hf <2. So the
floor is a **permissive runtime claim with no test coverage**. That is accepted deliberately (the
source is unchanged and still works with 1.x), and it is recorded here rather than left implicit.
If floor coverage is wanted later, the options are: raise the floor to `>=2.0` (honest, but
restricts users for no code reason), or add a CI job that installs the floor version and runs a
subset (real work).

**Forced bumps, both measured.** `datasets 5.0.1 → 5.1.0` is forced: PyPI shows `datasets 5.0.1`
pins `huggingface-hub<2.0,>=0.25.0`, `datasets 5.1.0` admits `<3.0,>=1.31.0`, and the 5.x releases are
only `5.0.0, 5.0.1, 5.1.0` — so 5.1.0 is the minimal and only step that admits hf 2.x. `hf-xet
1.5.2 → 1.7.0` is forced by hf 2.x's `hf-xet>=1.6.0,<2.0.0`. The lock's `revision = 3 → 5` is a uv
artifact, harmless.

**Non-vacuity of the adapted test, proven dynamically.** The verifier loaded the real
`sofer.publish` and a second module from the same source with the `except RepositoryNotFoundError`
block removed, patched both, and called `_inspect_repo`: the real one returns `[]`, the faulty one
raises. The test reaches the handler and would fail if it were removed.

## Lesson (second instance this session)

The gate spec named `tests/test_verification.py`, which **does not exist** (nor at base). The
verifier caught it, substituted the hf-touching suites, and classified it as a spec error. This is
the same defect as the invented test precedent in the #273 brief: **do not put an unverified claim —
especially a file name or a precedent — into a brief.**

## Notes

- **Version:** the range resolves to **2.2.0** (latest in `>=0.26.0` at implementation time), one
  minor ahead of the 2.1.1 the bot proposed, which was latest at *its* run time. The `httpx2`
  adaptation is identical across the 2.x line.
- **No SDD change folder and no spec delta.** Verified: no spec mentions `httpx`, the HTTP stack, or
  the `huggingface-hub` floor. The repo's precedent for a dependency bump is a plain PR; an SDD
  folder here would inflate the review surface without changing any contract.
- **`httpx2`/`httpcore2` were already in `dev`'s lock** (6 matching lines) before this change; what
  is new is `huggingface-hub` 2.x declaring `httpx2` (7 lines). Their removal counterparts
  (`httpx`, `httpcore`, `certifi`, `requests`, `urllib3`, `charset-normalizer`) are consequences of
  hf 2.x dropping its old stack — nothing in `src/` or `tests/` imports any of them.
- `tests/test_mcp_server.py` uses `huggingface_hub.constants` in 12+ places and **passed** under 2.x.
- The bot PR #278 is superseded by this branch: it cannot be adapted in place, and its lock diff
  also carries unrelated re-resolution.
