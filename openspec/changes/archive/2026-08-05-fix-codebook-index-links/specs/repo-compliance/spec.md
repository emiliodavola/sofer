# Delta for Repo-Compliance

## ADDED Requirements

### Requirement: Placeholder Rejection in Validation (RC-R01)

The `validate()` function SHALL reject `repo_id` values containing known
placeholder patterns that indicate the user has not configured a real Hugging
Face repository. Rejected patterns include case-insensitive matches for
`YOUR_USER`, `YOUR_ORG`, `your-username`, and `YOUR_ORGANIZATION`. The system
MUST print a clear error message identifying the rejected placeholder to
stderr and return with exit code 1. Valid `user/dataset` repo_ids that do not
match any placeholder pattern SHALL continue to pass validation unchanged.

#### Scenario: YOUR_USER placeholder rejected

- GIVEN a DatasetConfig with `repo_id = "YOUR_USER/dataset"`
- WHEN `validate()` is called
- THEN an error SHALL be returned identifying `YOUR_USER` as a placeholder
- AND the message SHALL instruct the user to replace it with their actual HF username

#### Scenario: YOUR_ORG placeholder rejected

- GIVEN a DatasetConfig with `repo_id = "YOUR_ORG/dataset"`
- WHEN `validate()` is called
- THEN an error SHALL be returned identifying `YOUR_ORG` as a placeholder

#### Scenario: Lowercase your-username placeholder rejected

- GIVEN a DatasetConfig with `repo_id = "your-username/dataset"`
- WHEN `validate()` is called
- THEN an error SHALL be returned identifying `your-username` as a placeholder

#### Scenario: Valid user/dataset still passes

- GIVEN a DatasetConfig with `repo_id = "alice/my-dataset"`
- WHEN `validate()` is called
- THEN validation SHALL pass without error

#### Scenario: _cmd_codebook calls validate before generation

- GIVEN a TOML config with `repo_id = "YOUR_USER/dataset"`
- WHEN `sofer codebook --config dataset.toml --all-files` executes
- THEN `validate()` SHALL be called before `generate_all_codebooks()`
- AND the command SHALL exit with code 1
- AND the error message SHALL print to stderr
