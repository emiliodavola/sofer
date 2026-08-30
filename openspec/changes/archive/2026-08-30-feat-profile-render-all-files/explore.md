# Exploration: feat-profile-render-all-files

> Change: `feat-profile-render-all-files` — GitHub #91
> Mode: hybrid (Engram + OpenSpec) | `capture_prompt: false`
> Date: 2026-08-30 | Source: `main` — direct codegraph + file reads

## Current State

### CLI surface (codebook/prepare vs profile/render)

| Command | Flag set | `--all-files`? | Positional | Source |
|---------|----------|---------------|------------|--------|
| `codebook` | `--output`, `--max-sample`, `--all-files`, `--config` | **yes** | optional `FILE` | `cli.py:833-878` |
| `prepare` | `--output`, `--all-files`, `--no-checks`, `--force`, `--verify` | **yes** (delegates to codebook) | `config` | `cli.py:708-757` |
| `profile` | `--output` | **no** | required `dataset` | `cli.py:880-904` |
| `render` | `--output` | **no** | required `package` | `cli.py:906-930` |

`codebook --all-files` and `prepare --all-files` iterate `[[file]]` entries from the TOML (validated via `DatasetConfig.from_toml`, placeholder `YOUR_USER` rejected, `generate_all` with collision handling). `profile`/`render` have no TOML awareness — single file/package only.

Evidence — `cli.py:853-903`:
```python
# profile: only dataset + --output
prf.add_argument("dataset", help="Path to dataset file...")
prf.add_argument("--output", help="Output directory for metadata.yaml...")
# render: only package + --output
rnd.add_argument("package", help="Path to metadata.yaml or dir...")
rnd.add_argument("--output", help="Output directory for README.md...")
# contrast codebook/prepare:
c.add_argument("--all-files", action="store_true", ...)
p.add_argument("--all-files", action="store_true", ...)
```

### profile/render write path — generic name + unconditional overwrite

```python
# src/sofer/profile.py:43, 123-126
_METADATA_FILENAME = "metadata.yaml"
out_dir = Path(output_dir) if output_dir is not None else dataset_path.parent
metadata_path = out_dir / _METADATA_FILENAME
metadata_path.write_text(serialize(meta), encoding="utf-8")  # no exists() check, no --force

# src/sofer/render.py:32-33, 68-71
_METADATA_FILENAME = "metadata.yaml"
_README_FILENAME = "README.md"
readme_path = out_dir / _README_FILENAME
readme_path.write_text(readme, encoding="utf-8")  # same
```

- Filename is **fixed** — not derived from `dataset_path.stem` (`contacts.csv` → `metadata.yaml`, not `contacts.metadata.yaml`).
- Default directory is the source's parent (or `--output DIR`) — no namespacing.
- No `FileExistsError` guard, no `--force` flag (unlike `codebook`/`prepare`/`publish` which expose `--force`).

### Single-file overwrite reproduction (confirmed)

```bash
# Two datasets sharing directory raw/
sofer profile raw/a.csv          # → raw/metadata.yaml  (a.csv's metadata)
sofer profile raw/b.csv          # → raw/metadata.yaml  — SILENTLY OVERWRITES a.csv's file
sofer profile raw/a.csv --output out  # → out/metadata.yaml
sofer profile raw/b.csv --output out  # → out/metadata.yaml — same collision

sofer render raw/                # resolves raw/metadata.yaml — only 1 of 2 survives
# No batch path: N profiles require N manual --output dirs
```

Tests confirm single-file overwrite is the **expected** current behavior:
- `tests/test_profile.py:test_output_dir_override` — asserts `--output` moves the single `metadata.yaml`, no collision test.
- `tests/test_render.py:test_output_dir_override` — same for `README.md`.
- No tests for `--all-files` or `FileExistsError` on either command.

### Config hardcode audit

`config.py` / `pyproject.toml:[tool.sofer]` expose ~25 tool-wide defaults (AGENTS.md rule 1). The following are **hardcoded literals** in `profile.py`/`render.py` that violate that rule if a batch layout is added without config extraction:

| Literal | Location | Should be | Status today |
|---------|----------|-----------|--------------|
| `_METADATA_FILENAME = "metadata.yaml"` | `profile.py:43`, `render.py:32` | `config.METADATA_FILENAME` / `pyproject.toml:metadata_filename` | hardcoded (acceptable for single-file but must be extracted for collision-safe variants like `<stem>.metadata.yaml`) |
| `_README_FILENAME = "README.md"` | `render.py:33` | `config.README_FILENAME` / `readme_filename` | hardcoded |
| Output layout `dataset.parent` / `metadata.parent` | `profile.py:123`, `render.py:68` | No dir config yet; proposal needs `profile_dir` / `render_dir` | no config keys exist |
| Encoding `"utf-8"` in `write_text` | `profile.py:126`, `render.py:71` | `config.OUTPUT_ENCODING` (codebook already uses it) | hardcoded, minor |

Existing config candidates that inform the new keys:
- `output_dir = "cache"` and `codebooks_dir = "codebooks"` — precedent: tool-wide output subdirs are config-driven and overridable via `pyproject.toml`.
- No `profile_dir` / `render_dir` / `metadata_filename` / `readme_filename` keys exist today — must be **added** to `config.py:_DEFAULTS` + `pyproject.toml:[tool.sofer]` (same pattern as `codebooks_dir`).

`codebook.py` itself still carries a residual hardcode (`_read_csv` defaults `";"`, `generate` defaults `";"`) but `generate_all` correctly resolves via `cfg.csv_delimiter`/`cfg.csv_encoding` (rule-3 fix). `profile.py` already follows the correct pattern: `config.CSV_DELIMITER`/`config.CSV_ENCODING` via `stream_csv`.

### MCP parity gap

- `mcp_server.py:876` `sofer_profile(dataset, output)` and `:928` `sofer_render(package, output)` — same single-file signature, no `all_files`/`force`. They do re-anchor `[tool.sofer]` per call (`_reload_tool_config`) and contain output via `_contained_path`, but inherit the overwrite bug.
- `sofer_codebook_all` (`mcp_server.py:826`) already implements batch with containment + `ValueError` collision handling — the pattern to align to.

## Affected Areas

- `src/sofer/cli.py` — add `--all-files` + `--force` + `--config` (for batch TOML) to `profile`/`render` subparsers; add `_cmd_profile`/`_cmd_render` batch branches (mirroring `_cmd_codebook` 179-201)
- `src/sofer/profile.py` — add `profile_all(cfg, output_dir?)` or extend `profile()` to batch; add collision-safe naming (`<stem>.metadata.yaml` vs `<output>/profiles/<rel-stem>.metadata.yaml`); add `FileExistsError` guard gated by `force`; read `config.PROFILE_DIR` (new)
- `src/sofer/render.py` — same for `render_all`; resolve `metadata.yaml` per entry; output `<stem>.README.md` or `renders/<rel-stem>.md`; `force` guard
- `src/sofer/config.py` — add `profile_dir`, `render_dir` (and optionally `metadata_filename`/`readme_filename`) to `_DEFAULTS` + module constants + `reload` binding
- `src/sofer/mcp_server.py` — extend `sofer_profile`/`sofer_render` signatures; add containment + batch helpers; add `generate_all_profiles` / `generate_all_renders` domain functions if split from single-file
- `pyproject.toml` — document `[tool.sofer] profile_dir` / `render_dir` defaults
- `openspec/specs/profile/spec.md`, `openspec/specs/render/spec.md` — new `PRF-05`/`RND-04` batch + `PRF-06`/`RND-05` collision guard requirements
- `openspec/specs/cli/spec.md` — extend `CLI-R03`/`CLI-R04` to cover new flags
- `tests/test_profile.py`, `tests/test_render.py`, `tests/test_cli.py` — collision, batch N-files, `--output` custom, `--force` guard, parity with `codebook --all-files`
- `tests/test_mcp_server.py` — new tool param coverage

## Approaches

### Alignment reference: `codebook --all-files` batch pattern (to replicate)

`codebook.generate_all(cfg, output_dir, delimiter, encoding)` (`codebook.py:387-565`):
1. Validate TOML (`cfg.validate()`, placeholder check).
2. First pass: collect valid entries (skip dirs/missing/unsupported with `⚠`).
3. Pre-compute `output_path = (codebooks_dir / rel_stem).with_suffix(".md")` where `rel_stem` is relative to `cache/` or `base_dir`.
4. Detect collisions: `output → [sources]`; partition into `colliding_locals`.
5. Write non-colliding first, then `raise ValueError` naming every colliding source (partial write + no root index — fail-loud).
6. Root index `codebook.md` only when no collisions.
7. Option B: `output_dir` override anchors relative dirs to `cfg._base_dir` (PRP-06), writes to `output_dir/codebooks/` + `output_dir/codebook.md`, never mutates `cache/`.

`prepare` reuses it via `output_dir=resolve_output_dir(cfg, args.output)` → `generate_all_codebooks(cfg, output_dir=...)`.

### Batch layout options — tradeoffs

| Option | Structure | Pros | Cons | Effort |
|--------|-----------|------|------|--------|
| **1. `profiles/` + `renders/` top-level shards** — `<output>/profiles/<stem>.metadata.yaml`, `<output>/renders/<stem>.README.md` | Two flat subdirs, one file per dataset | Clean separation (intermediate artifact vs doc); scannable `profiles/*.yaml`; aligns with `cache/codebooks/*.md`; no pollution of `docs/` which is often published | Two new top-level dirs; users wanting `docs/` must configure | Low |
| **2. `docs/profiles/` + `docs/renders/`** | Same but under `docs/` | Convention docs-as-code; all rendered docs in one tree | `metadata.yaml` is NOT a doc — mixing build artifacts with publishable docs confuses versioning/publishing; `docs/` often has its own tooling | Low (config variant of #1) |
| **3. `<output>/<stem>/metadata.yaml` + `<output>/<stem>/README.md`** | One folder per dataset | Very explicit, trivial `sofer render <stem>/`; avoids filename tricks | N `mkdir`s, deeper paths, less scannable, duplicates stems across nesting | Medium |
| **4. Stem-qualified flat files** — `raw/contacts.metadata.yaml` / `raw/contacts.README.md` | No new dirs, just `<stem>.*` names | Minimal change, fixes collision without new dirs | Still pollutes `raw/` with N files; doesn't solve batch UX (no `--all-files`); `raw/` is source tree | Low |

**Recommendation: Option 1 as default, with `profile_dir`/`render_dir` configurable** — satisfies Option 2 via `profile_dir = "docs/profiles"` without code change; Option 4 as single-file guard (write `<stem>.metadata.yaml` when collision would occur) is a compatible enhancement, not mutually exclusive.

Collision granularity: include subpath when TOML has `raw/Labels/etiquetas_a.csv` vs `raw/etiquetas_a.csv` — use `rel_stem` (relative to `cache/` or `base_dir`) not just `Path.stem`, identical to `codebook`'s `rel_stem = local.relative_to(data_dir) or base_dir` logic. This prevents `a/b.csv` and `c/b.csv` → `b.metadata.yaml` collision. Codebook detects it; profile/render must do the same.

`--force` semantics to match `codebook`/`prepare`: without `--force`, `FileExistsError` with actionable message (`use --force to overwrite`); with `--force`, overwrite. In batch mode, `generate_all` pattern is "write non-colliding, then raise `ValueError` for colliding group" — for single-file, just refuse before write.

### Detailed option comparison for the decision

| Approach | Pros | Cons | Complexity |
|----------|------|------|------------|
| **A. Add `--all-files` + `profiles/`/`renders/` shards + `--force` guard (recommended)** — CLI `--all-files` (TOML positional, requires `[[file]]`), `config.profile_dir`/`render_dir`, `profile_all`/`render_all` with `rel_stem` collision map, `FileExistsError` without `--force` | Full parity with `codebook`/`prepare`; collision-safe by construction; configurable (docs vs cache); backward compat (single-file path unchanged unless flagged) | Two new TOML keys + two new domain functions; MCP update | Medium |
| **B. Minimal: only `--force` guard + stem-qualified single-file names** — `contacts.metadata.yaml` / `contacts.README.md` next to source, no batch, no new dirs | Smallest diff; fixes silent overwrite immediately | Leaves batch gap unsolved; still requires N manual invocations; N files in `raw/` | Low |
| **C. Per-dataset folders `<output>/<stem>/`** | Strongest isolation; natural `render <stem>/` | Most filesystem churn; breaks `codebooks` flat-file convention | Medium-High |

## Recommendation

**Go with Approach A** (Option 1 layout + configurable dirs).

Rationale:
- Directly reuses the proven `codebook.generate_all` machinery (pre-compute, collision map, partial-write-then-raise, Option B `output_dir` anchoring) — lowest risk, most testable via existing collision tests.
- Fixes both reported problems at once (missing batch + silent overwrite) without breaking single-file compat: `--all-files` is opt-in, existing `sofer profile raw/a.csv` path is untouched (except it now refuses to overwrite without `--force`, which is the correct fail-loud fix — document as breaking-but-safe in release notes).
- Config-driven dirs (`profile_dir = "profiles"`, `render_dir = "renders"` in `[tool.sofer]`) make Option 2 (`docs/profiles`) a one-line TOML edit, not a code fork.

## Risks

- **Overwrite behavior change is semver-visible**: single-file without `--force` now errors instead of overwriting. Mitigate: call out in `0.x` minor release notes (pre-1.0 breaking allowed but must be documented), add migration hint in error message (`use --force to overwrite <path>`).
- **Collision detection diverges from `codebook` if `rel_stem` logic is not reused verbatim** — copy `data_dir = base_dir / config.OUTPUT_DIR` + `rel_stem = local.relative_to(data_dir) or base_dir` + `PurePath.suffixes` replacement exactly; otherwise `a/b.csv` vs `c/b.csv` collides silently again.
- **MCP containment regression**: config-derived `profile_dir`/`render_dir` must pass `_validate_output_targets` (like `codebooks_dir` already does at `mcp_server.py:326-368`), else `output_dir = "../../evil"` escapes the server root. Add both keys to `_validate_output_targets` and `_reload_tool_config` coverage.
- **TOML `local` paths outside `cache/`** — `rel_stem` fallback to `base_dir` must be tested (e.g. `local = "raw/DPTO.csv"` vs `local = "../other/data.csv"`); already covered in `codebook` but needs regression tests for profile/render.
- **Spec/test drift**: `profile/spec.md` and `render/spec.md` currently document only `PRF-01..04` / `RND-01..03` single-file; new `PRF-05`/`RND-04` (batch) + `PRF-06`/`RND-05` (force guard) must be added before code, else AGENTS.md rule 6 (spec → test parity) is violated and CI's skipped-spec count grows.
- **Tool-wide vs per-dataset config precedence**: `pyproject.toml:[tool.sofer] profile_dir` is tool-wide; if a future per-dataset `[meta] profile_dir` is desired, precedence must be explicit (tool-wide default, per-dataset override) — defer to avoid over-design in this change.

## Ready for Proposal

**Yes — with GO.**

Orchestrator should proceed to `sdd-propose` for `feat-profile-render-all-files`. Tell the user: exploration validated the reported gap on `main`, reproduced the overwrite, confirmed the `codebook --all-files` pattern is directly reusable, and identified the config/MCP/spec surfaces that must move together. No blocking unknowns; the batch layout decision (profiles/renders + configurable) is settled in this artifact.

Field the next question with one option only — the GO/NO-GO above.

---
*Teams: `src/sofer/cli.py:880-930`, `profile.py:43,123-126`, `render.py:32-71`, `config.py:_DEFAULTS`, `codebook.py:387-565`, `mcp_server.py:876,928`, `pyproject.toml:[tool.sofer]`, `tests/test_profile.py`, `tests/test_render.py`, `tests/test_cli.py`, `openspec/specs/{profile,render,cli}/spec.md` — all read via codegraph + direct reads 2026-08-30.*
