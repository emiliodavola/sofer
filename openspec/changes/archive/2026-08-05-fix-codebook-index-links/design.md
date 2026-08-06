# Design: Fix Codebook Index Links and YOUR_USER Placeholder

## Technical Approach

Two independent bug fixes, no shared state:

1. **Root index link paths**: Change relative-path anchor in `generate_all()` from `base_dir` to `data_dir`, aligning codebook links with uploader staging (`codebooks/` not `data/codebooks/`).
2. **Placeholder rejection**: Add known-placeholder detection in `validate()` (case-insensitive on user-part before `/`) and hook `validate()` into `_cmd_codebook()`.

Both are surgical, single-concern changes. No new dependencies, no schema changes.

## Architecture Decisions

| Decision | Choice | Alternatives Rejected | Rationale |
|----------|--------|----------------------|-----------|
| Link anchor base | `out_path.relative_to(data_dir)` | (a) strip `data/` prefix with string ops; (b) change uploader to include `data/` prefix | `data_dir` already exists at line 387. String ops are fragile. Option (b) is a bigger break — the uploader convention is established. |
| Placeholder detection placement | In `validate()`, before regex check | (a) separate function; (b) CLI-only check | Inline keeps it co-located with the repo_id regex. CLI-only is wrong — library callers need protection too. |
| Error exit strategy | `_cmd_codebook()` calls `cfg.validate()`, prints to stderr, returns 1 | (a) raise exception; (b) use `exit()` directly | Matches existing `_cmd_codebook()` error patterns (lines 126-133 for TOML parse failures). |
| Placeholder set | `{"YOUR_USER", "YOUR_ORG", "your-username", "YOUR_ORGANIZATION"}` — case-insensitive on `user` part | Just `YOUR_USER` | User reported multiple template patterns. Covering all prevents reopening this bug. |
| Auto-resolution | Not implemented | `HfApi().whoami()` | Adds network + auth dependency. Deferred to future iteration. |

## Data Flow

### Change 1: Link generation (before → after)

```
BEFORE:
  out_path = data/codebooks/f.md
  rel = out_path.relative_to(base_dir)          → data/codebooks/f.md
  index writes [data/codebooks/f.md](data/codebooks/f.md)

  Uploader stages: codebooks/f.md          ← MISMATCH → 404 on HF

AFTER:
  out_path = data/codebooks/f.md
  rel = out_path.relative_to(data_dir)          → codebooks/f.md
  index writes [codebooks/f.md](codebooks/f.md)

  Uploader stages: codebooks/f.md          ← MATCH
```

### Change 2: Validation gate (before → after)

```
BEFORE:
  _cmd_codebook → from_toml → generate_all_codebooks
                                  └ emits "Repository: YOUR_USER/dataset" silently

AFTER:
  _cmd_codebook → from_toml → validate()
                              ├ errors? → stderr + exit 1
                              └ no errors → generate_all_codebooks
```

Validation order in `validate()`: **placeholders first**, then regex. If a placeholder is found, it reports directly without a confusing regex error on top.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/codebook.py:496` | Modify 1 line | `relative_to(base_dir)` → `relative_to(data_dir)` |
| `src/sofer/model.py:439-443` | Insert ~8 lines | Placeholder check before regex in `validate()` |
| `src/sofer/cli.py:125-131` | Insert ~5 lines | Call `cfg.validate()` after `from_toml`, exit 1 on errors |
| `tests/test_codebook.py:549` | Modify 1 line | `data/codebooks/f.md` → `codebooks/f.md` |
| `tests/test_model.py:218-222` | Insert 5 test methods | Placeholder rejection scenarios |
| `tests/test_cli.py` | Add 2 tests | CLI validates before generation, valid config still works |

## Implementation Details

### model.py — placeholder check (insert after line 439 `errors: list[str] = []`)

```python
_PLACEHOLDERS = frozenset({"your_user", "your_org", "your-username", "your_organization"})
user_part = self.repo_id.split("/", 1)[0]
if user_part.lower() in _PLACEHOLDERS:
    errors.append(
        f"repo_id contains placeholder '{user_part}'. "
        "Replace it with your Hugging Face username."
    )
```

The existing regex check at line 442 runs only if no placeholder was found.

### cli.py — validate gate (insert after line 125, before `generate_all_codebooks`)

```python
        errors = cfg.validate()
        if errors:
            for err in errors:
                print(f"Error: {err}", file=sys.stderr)
            return 1
```

### codebook.py — link fix (replace line 496)

```python
        rel = out_path.relative_to(data_dir).as_posix()
```

## Test Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit — model | Placeholder repo_ids rejected | 4 new `TestValidate` methods: `YOUR_USER`, `YOUR_ORG`, `your-username`, `YOUR_ORGANIZATION` — each constructs `DatasetConfig(name="x", repo_id="PLACEHOLDER/repo")` and asserts error in `validate()` |
| Unit — model | Placeholder also rejected with suffix (e.g. `your-username/sub/project`) | One edge-case test with multi-segment repo path |
| Unit — model | Valid repo_id still passes | Existing `test_valid_repo_id` covers this |
| Unit — codebook | Root index links match uploader paths | Update `test_root_index_has_correct_links`: change assertion from `data/codebooks/f.md` to `codebooks/f.md` |
| Integration — CLI | `_cmd_codebook` validates before generation | New test: TOML with `YOUR_USER/dataset` → exit code 1 + stderr contains placeholder message |
| Integration — CLI | Valid config still generates | Existing CLI codebook tests ensure no regression |

## Rollback Plan

Three line reverts, no data migration:
1. `codebook.py:496` — restore `relative_to(base_dir)`
2. `model.py:439-443` — remove placeholder block
3. `cli.py:125-131` — remove `validate()` call

Test assertions revert in the same commit.

## Open Questions

None. Both changes are well-specified with explicit line references and test scenarios.
