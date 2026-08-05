# Delta for repo-compliance — Upload Overwrite Bypass

## ADDED Requirements

### Requirement: RC-C02 — Auto-Generated Files Bypass Overwrite Protection

The upload pipeline SHALL always overwrite auto-generated compliance files on the
Hugging Face Hub without interactive confirmation. These files are programmatically
produced by `upload()` and are never hand-authored, so protecting them from overwrite
adds friction with no user benefit.

The auto-generated set SHALL consist of:

| File / Pattern | Check |
|----------------|-------|
| `README.md` | Exact match (lowercased) |
| `LICENSE` | Exact match (lowercased) |
| `codebook.md` (root index) | Exact match (lowercased) |
| `codebooks/**/*.md` (per-file RC-C01) | Path prefix `codebooks/` |

When any of these files already exist on the Hub, the upload SHALL proceed without
prompting the user, even when `force=False`.

#### Scenario: README.md always uploaded even when it already exists on Hub

- GIVEN `existing_files` on Hub includes `README.md`
- AND `force=False`
- WHEN `upload(cfg)` is called
- THEN `_check_overwrite_protection` SHALL NOT include `readme.md` in its protected set
- AND `README.md` SHALL be uploaded unconditionally

#### Scenario: LICENSE always uploaded even when it already exists on Hub

- GIVEN `existing_files` on Hub includes `LICENSE`
- AND `force=False`
- WHEN `upload(cfg)` is called
- THEN `_check_overwrite_protection` SHALL NOT include `license` in its protected set
- AND `LICENSE` SHALL be uploaded unconditionally

#### Scenario: Root codebook index always uploaded when it exists on Hub

- GIVEN `existing_files` on Hub includes `codebook.md`
- AND the local `codebook.md` exists on disk
- WHEN `upload(cfg)` is called
- THEN `codebook.md` SHALL be uploaded without overwrite protection

#### Scenario: Per-file codebooks always uploaded when they exist on Hub

- GIVEN `existing_files` on Hub includes `codebooks/DPTO.md`
- AND `data/codebooks/DPTO.md` exists locally
- WHEN `upload(cfg)` is called
- THEN `codebooks/DPTO.md` SHALL be uploaded without overwrite protection

#### Scenario: Advisory printed when codebooks are missing locally

- GIVEN `codebook.md` does NOT exist on disk
- AND `data/codebooks/` directory is absent or empty
- WHEN `upload(cfg)` is called
- THEN the function SHALL print: `"Run 'sofer codebook --all-files' first to generate codebooks."`
- AND the upload SHALL proceed normally for all other files (no error)
