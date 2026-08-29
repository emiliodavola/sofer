## Summary

<!-- One paragraph: what problem this solves and how. -->

## Changes

<!-- Per-area breakdown. Use tables for multi-file changes. -->

| Area | What changed |
|------|-------------|

## Verification

<!-- Copy-paste the actual command output, not placeholders. -->

```
$ uv run pytest tests/ -q
... NNN passed ...

$ uv run ruff check src/ tests/
All checks passed!

$ uv run mypy src/
Success: no issues found
```

## Files changed

| File | Lines (+/−) | Description |
|------|------------|-------------|

## SDD artifacts

<!-- If this change followed SDD, link or list the artifacts. -->

Archived at `openspec/changes/archive/<date>-<change>/`

Specs updated: `openspec/specs/<domain>/spec.md`

## Checklist

- [ ] `uv run pytest tests/ -q` — all passing
- [ ] `uv run ruff check src/ tests/` — clean
- [ ] `uv run ruff format --check src/ tests/` — clean
- [ ] `uv run mypy src/` — clean
- [ ] New behaviour covered by tests
- [ ] README updated if CLI surface changed
- [ ] README_ES.md updated if a translated README section changed
- [ ] Related issues linked (`Closes #N`)
