# Delta for publish

## ADDED Requirements

### Requirement: Build cleanup on successful publish (PUB-11)

`sofer publish --clean` (default off) MUST delete the resolved build directory only after a successful `hf` upload where `fail == 0`. The system MUST NOT delete on `--dry-run`, quality-gate block, or upload failure. For `--target local` the system MUST NOT delete unless `--clean` is explicitly given; then it MUST delete the `--output` destination, not the source build. The build path MUST be resolved via `resolve_output_dir(cfg, --output)` so `--output` overrides are honored. `--clean` alone MUST be build-only; deletion of `cache/` (`config.OUTPUT_DIR` anchored to `cfg._base_dir`, shared tool-wide) MUST require opt-in `--clean-cache` (or `--clean --all`), warning that siblings share it.

#### Scenario: Successful hf publish with --clean deletes build

- GIVEN `build/` exists and `publish --target hf --clean` succeeds with `fail == 0`
- WHEN upload completes
- THEN `build/` (resolved via `resolve_output_dir`) SHALL be removed

#### Scenario: --clean --clean-cache deletes build and cache

- GIVEN `build/` and `cache/` exist and `publish --target hf --clean --clean-cache` succeeds
- WHEN upload completes
- THEN both `build/` and `cache/` SHALL be removed

#### Scenario: Dry-run with --clean does not delete

- GIVEN `publish --dry-run --clean` invoked
- WHEN diff/split report prints
- THEN neither `build/` nor `cache/` SHALL be removed

#### Scenario: Quality-gate block does not delete

- GIVEN quality gate fails and `--clean` was given
- WHEN `publish` exits 1 without upload
- THEN neither `build/` nor `cache/` SHALL be removed

#### Scenario: Upload failure does not delete

- GIVEN `upload_folder` raises and `--clean` was given
- WHEN `publish` exits 1
- THEN neither `build/` nor `cache/` SHALL be removed

#### Scenario: Local target without explicit --clean does not delete

- GIVEN `publish --target local --output ./out` without `--clean`
- WHEN command completes with exit 0
- THEN neither `./out/` nor `build/`/`cache/` SHALL be removed

#### Scenario: Local target with explicit --clean deletes destination

- GIVEN `publish --target local --output ./out --clean` succeeds
- WHEN command completes
- THEN `./out/` SHALL be removed and source `build/` SHALL remain

#### Scenario: Custom --output build cleanup anchored correctly

- GIVEN `publish --target hf --output ./staging --clean` succeeds
- WHEN upload completes
- THEN `./staging/` SHALL be removed and `cfg._base_dir / "cache"` SHALL remain unless `--clean-cache` given
