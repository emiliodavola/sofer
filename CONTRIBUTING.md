# Contributing to sofer

Thanks for taking the time to contribute! :rocket:

## Getting started

1. **Fork** the repository and clone your fork.
2. Create a branch for your change (`feat/my-feature` or `fix/bug-description`).
3. Set up the environment:

```bash
uv sync
pre-commit install
```

4. Make your changes, add tests, and ensure `uv run pytest` passes.

## Development conventions

### Code style

This project uses **ruff** for linting and formatting. Configuration is in `ruff.toml` at the repo root. Run `ruff check` and `ruff format` before committing — the pre-commit hook does this automatically.

### Type checking

We use **mypy** in strict mode. Run `mypy src/` to check types. The CI will reject PRs that don't type-check.

### Commit messages

Use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
feat(compliance): add split detection to upload pipeline
fix(encoding): reject non-UTF-8 files in quality check
```

Prefixes: `feat`, `fix`, `docs`, `test`, `ci`, `chore`, `refactor`.

## Pull requests

- Open a PR against the `dev` branch.
- Fill the PR template — describe what, why, and how.
- Link related issues (`Closes #N`).
- PRs need at least one approving review before merge.

## Testing

- Run `uv run pytest` for the full suite.
- Add tests for new behaviour in the appropriate `tests/` file.
- Target: no drop in coverage.

## Reporting bugs

Use the issue template and include:
- Steps to reproduce
- Expected vs actual behaviour
- `sofer --version` output
- Relevant TOML config (sanitised)

## Questions?

Open a [discussion](https://github.com/emiliodavola/data-uploader/discussions) or reach out in an issue.
