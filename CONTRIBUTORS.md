# Contributors

`sofer` is maintained by [Emilio Dávola](https://github.com/emiliodavola).

This file records credit by the kind of work contributed. It is not a claim of
authorship: see [`CITATION.cff`](CITATION.cff) for how to cite the software.

## Bug reports and reproductions

- **[@BurningmanAuer](https://github.com/BurningmanAuer)** — reported the seven
  defects fixed in v0.7.1, each with a minimal synthetic fixture, the exact MCP
  calls and the observed envelopes, which is what made every one of them
  verifiable and testable:
  - #393 — a CSV fallback left the Dataset Card advertising a Parquet the
    package did not contain.
  - #394 — batch profiling ignored the dataset's own CSV dialect.
  - #395 — ragged CSV rows produced different missing-value denominators in the
    profile and the codebook.
  - #396 — `sofer_profile_all` reported success when every input failed to read.
  - #397 — a source outside the config directory was reported as an output
    collision.
  - #398 — the codebook index write masked the underlying read failure.
  - #399 — `min_unique` was accepted and never enforced.

## How to be added

Contributions of any kind are welcome: a reproduction, a failing test, a
documentation fix or code. If you contributed and are not listed here, open an
issue or a pull request and ask — being left out is an omission, not a judgement.
