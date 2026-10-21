# sofer documentation

This directory holds the detailed reference that used to live in the README.
The two READMEs are the bilingual entry points; the technical documentation in
`docs/` is written in English only. Both READMEs link here in the same section
order.

## Reading paths

### CLI path

1. [Getting started](getting-started.md) — install, bootstrap, build and inspect
   a dataset package, with publication kept as a separate step.
2. [Dataset configuration](dataset-config.md) — the dataset TOML, `[meta]`,
   `[[file]]`, `[[check]]`, `[[quality]]`, and `raw/` → `cache/` → `build/`.
3. [CLI reference](cli.md) — commands, flags, `meta`, `mcp`, and examples.
4. [Data package](data-package.md) — formats, conversion, splits, validation,
   quality checks, codebooks, profiling, rendering, and verification.
5. [Tool-wide configuration](configuration.md) — `[tool.sofer]` defaults,
   discovery, and precedence.
6. [Troubleshooting](troubleshooting.md) — Windows notes, Hugging Face upload
   diagnostics, and assisted failure reporting.

### Agent path

1. [MCP server](mcp.md) — the canonical phased chain, tools, resources,
   prompts, arguments, and response contracts.
2. [Agent setup](agent-setup.md) — registration, environment forwarding,
   startup, roots, and request timeouts.
3. [Security](security.md) — path containment, approval phrase, visibility
   acknowledgments, credentials, and sensitive-host hardening.

## Project and contribution references

- [README](../README.md) — English entry point.
- [README_ES](../README_ES.md) — Spanish entry point with the same user-facing
  sections in the same order.
- [CONTRIBUTING](../CONTRIBUTING.md) — architecture, development setup,
  conventions, tests, and quality gates.
- [Tool-wide configuration](configuration.md) — the canonical reference for
  `[tool.sofer]`; detailed command and flag changes belong in
  [CLI reference](cli.md) and the other pages listed above.
