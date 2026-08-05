# Design: Overwrite Bypass for Auto-Generated Compliance Files

## Technical Approach

Remove auto-generated files (`README.md`, `LICENSE`, `codebook.md`, `codebooks/**/*.md`)
from `_check_overwrite_protection`. When missing locally, codebooks produce a single
advisory instead of silent skip. No new dependencies, no architecture changes.

## Architecture Decisions

### Decision: static auto-generated set vs registry

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `_AUTO_GENERATED: frozenset[str]` constant in `uploader.py` | Simple, 3 exact filenames + 1 prefix; easy to audit | ✅ Chosen |
| Registry decorator / config key | Overkill for 4 patterns; adds indirection without value | Rejected |

**Rationale**: Auto-generated compliance files are a closed, known set. A module-level
`frozenset` is zero-allocation, grep-friendly, and trivially unit-testable.

### Decision: codebook advisory placement

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Check at upload loop (lines 981–996) | Contextual but may fire multiple times | Rejected |
| Single check in `upload()` before the upload phase | One advisory, no repetition | ✅ Chosen |

**Rationale**: The advisory describes a pre-requisite (run `codebook --all-files` first).
Repeating it per file is noise. Check once, print once, uploaded-or-skipped afterward.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/uploader.py` | Modify | Add `_AUTO_GENERATED` constant (line ~40); modify `_check_overwrite_protection` (~lines 447–488) to skip auto-generated files; add advisory check in `upload()` before RC-C01 loop (~line 980) |
| `tests/test_uploader.py` | Modify | 2 new tests: `test_readme_license_always_uploaded`, `test_missing_codebooks_advisory` |
| `src/sofer/uploader.py` | Modify | Update `force` param docstring (line 705) — remove README.md / LICENSE reference |

## Data Flow

```
upload() → _check_overwrite_protection(existing_files, force)
              ↓
          skip if filename ∈ _AUTO_GENERATED or prefix matches "codebooks/"
              ↓
          (no prompt, no skip — always upload)
```

Codebook advisory (single check before RC-C01 upload block):

```
os.path.exists("codebook.md") ∧ ("data/codebooks/" is absent or empty)
    → print advisory
    → proceed with upload (codebooks skipped silently as before)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_check_overwrite_protection` returns ∅ for README.md/LICENSE | Mock `existing_files`, assert empty protected set |
| Unit | Missing codebook advisory printed | Mock `os.path.exists`, capture stdout, assert advisory line |

## Migration / Rollout

No migration required. Pure behavioral change — existing callers need no code changes.
Rollback: revert the two changes in `uploader.py`.
