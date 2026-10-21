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

$ uv run ruff check src/ tests/ scripts/
All checks passed!

$ uv run mypy src/ scripts/
Success: no issues found

$ uv run pyright
0 errors, 0 warnings
```

## Files changed

| File | Lines (+/−) | Description |
|------|------------|-------------|

## Artifacts and evidence

<!-- Optional: link the issue and any evidence that exists. -->

Issue: #N

<!-- Only when the change uses OpenSpec: name the specs touched and the archive path. -->

Archived at `openspec/changes/archive/<date>-<change>/`

Specs updated: `openspec/specs/<domain>/spec.md`

## Checklist

- [ ] `uv run pytest tests/ -q` — all passing
- [ ] `uv run ruff check src/ tests/ scripts/` — clean
- [ ] `uv run ruff format --check src/ tests/` — clean
- [ ] `uv run mypy src/ scripts/` — clean
- [ ] `uv run pyright` — clean (pyright gate, `[tool.pyright]`)
- [ ] New behaviour covered by tests
- [ ] Coverage gate met — `uv run coverage report -m` ≥ 90% (CI enforces `fail_under = 90`)
- [ ] README updated if CLI surface changed
- [ ] README_ES.md updated in the same commit whenever README.md changed
- [ ] Related issues linked (`Closes #N`)
