#!/usr/bin/env bash
# COV-06 / AGENTS.md rule 14: per-file scoped 100% gates for the CLI core.
# coverage.py cannot express a per-file floor in config, so each core module gets
# its own scoped invocation. --fail-under=100 is a fixed policy constant, never a
# tunable floor — the config-owned TOTAL gate (ci CI-01: 90) is untouched and
# enforced by the flag-free `coverage report -m` step in the same job.
set -euo pipefail
for f in cli scanner prepare publish; do
  uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m
done