# Design — `2026-10-09-feat-mcp-hermes-adapter`

**Change** `2026-10-09-feat-mcp-hermes-adapter` (GitHub **#272**) · branch
`feat/272-mcp-hermes-adapter` from `dev@90ee69f` · store **hybrid**.

**Inputs read this phase, directly:** `proposal.md` of this change; `src/sofer/mcp_registration.py`
(registry, `read_config`, `build_entry`, `merge`, `remove_entry`, `atomic_write`,
`resolve_config_path`); `src/sofer/cli.py` (`_cmd_mcp_add`, `_cmd_mcp_remove`, the `mcp add`/`remove`
subparser help); `openspec/specs/mcp-registration/spec.md` (MCP-REG-01); `openspec/specs/cli/spec.md`
(CLI-R09); the archived deltas of `2026-10-09-feat-mcp-user-config-flag`.

**One-line outcome:** a fifth agent adapter whose config format is YAML, whose file is edited
surgically instead of rewritten, and whose single-scope nature is named on stderr rather than
refused.

---

## 1. Files and responsibilities

| File | Change |
| --- | --- |
| `src/sofer/_yaml.py` | **New.** YAML parse plus the surgical single-entry splice. Private helper module, in the `_toml.py` / `_csv_reader.py` family. |
| `src/sofer/mcp_registration.py` | `Adapter` gains `project_scope`; `ADAPTERS` gains `hermes`; `fmt` and `env` literals widen; `_infer_fmt`, `read_config` and `atomic_write` learn `yaml`; `resolve_config_path` honors `project_scope`; new `single_scope_note`. |
| `src/sofer/cli.py` | `mcp` / `mcp add` / `mcp remove` help text (rule 7); the single-scope note in both handlers. |
| `tests/test_yaml_edit.py` | **New.** The surgical writer's contract. |
| `tests/test_mcp_registration.py` | The registry-key-set and `fmt` guards, `Add all` / new-registry-entry tests, and a `TestHermesAdapter` class. |
| `tests/test_cli.py` | Help-text assertions and the single-scope note for `add` and `remove`. |

`scanner.py`, `prepare.py` and `publish.py` (the other rule-14 modules) are not touched.

## 2. The adapter row

```python
"hermes": {
    "fmt": "yaml",
    "key": "mcp_servers",
    "user_parts": (".hermes", "config.yaml"),
    "project_parts": (),            # unused: project_scope is False
    "command": "string",
    "adds_type_local": False,
    "env": "refs_braced",
    "delegates": False,
    "native_env": False,
    "native_scope": False,
    "user_env_dir": "HERMES_HOME",
    "project_scope": False,
},
```

Entry built by the existing `build_entry` with no new branch:

```yaml
mcp_servers:
  sofer:
    command: sofer-mcp
    cwd: /workspace/test
    env:
      HF_TOKEN: ${HF_TOKEN}
      SOFER_MCP_APPROVAL_PHRASE: ${SOFER_MCP_APPROVAL_PHRASE}
```

- `env="refs_braced"` reuses Pi's mode verbatim (`_present_env_keys` → `{k: "${k}"}`), so the
  allow-list of NAMES present in the environment is the only thing written.
- `_entries_equal("hermes", …)` follows the `refs`/`refs_braced` branch: raw `command`, `cwd` and the
  `env` mapping — which is why the `yaml` writer must round-trip `${HF_TOKEN}` as a **string** and not
  let any loader resolve it.
- `delegates=False` makes `probe_native("hermes")` return `False` (the existing `_delegates` gate), so
  both handlers go straight to the file edit and no new decline reason is needed.

`project_parts` is kept as an empty tuple so the `Adapter` shape stays uniform; `project_scope=False`
is the capability that is read, and the resolution guard (below) is the only consumer.

## 3. YAML plumbing (`fmt == "yaml"`)

- `Adapter["fmt"]: Literal["json", "toml", "yaml"]`.
- `_infer_fmt`: `.yaml` / `.yml` → `"yaml"`; `.toml` → `"toml"`; everything else → `"json"` (unchanged).
- `read_config`: the `yaml` branch parses with `yaml.safe_load`; an empty document (`None`) reads as
  `{}`, because an empty or comment-only `config.yaml` is valid and Hermes itself creates the file on
  first run. A non-mapping document raises `ValueError(f"config {path} is not a YAML mapping")`, the
  same shape as the JSON and TOML arms, so the caller exits 1 with no backup and no write.
- `atomic_write`: the `yaml` branch delegates to `_yaml.splice_entry`, then commits with the same
  `tmp` + `os.replace` sequence.

**The pre-write text.** The YAML branch must splice the document that is on disk *before* the write.
`atomic_write` receives the merged document and the format, so the branch re-reads `path` for the
pre-write text; when `path` does not exist it renders a fresh document. This is documented in the
function's docstring as the contract it is: the caller reaches `atomic_write` after the single `.bak`
backup and nothing mutates the file in between. The JSON and TOML branches are untouched (TOML's
comment-stripping behavior is declared, not a defect).

## 4. The surgical splice (`src/sofer/_yaml.py`)

```python
def splice_entry(text: str, key: str, name: str, doc: dict[str, Any]) -> str:
    """Return *text* with the *name* entry of the top-level *key* mapping replaced."""
```

Given the **pre-write text** and the **full merged document** (`merge` / `remove_entry` already
computed it), the function re-renders only the `key.name` subtree:

1. `yaml.compose(text)` locates the top-level `key` mapping node and, inside it, the `name` node.
   Node marks give the exact line range — no regex heuristics over YAML indentation, no dependency on
   quoting style.
2. **Entry present** → replace lines `[key_line, value_end)` of the `name` block with
   `yaml.safe_dump({name: entry}, sort_keys=False)` re-indented to the original key's indentation.
   `sort_keys=False` keeps `build_entry`'s insertion order (`command`, `cwd`, `env`).
3. **Entry absent, `key` present as a block mapping** → insert the rendered block at the end of the
   `key` mapping's span.
4. **`key` absent** → append a fresh block (`key:` + the rendered entry) at end of file, separated by
   one blank line, preserving any existing trailing newline.
5. **Removal whose result leaves the `key` mapping empty** → drop the whole `key` block, matching
   `remove_entry`'s existing semantics.
6. **`key` present in flow style** (`mcp_servers: {}`) → re-render that one `key` block in block style
   from the merged document. Bounded and documented: comments *inside* an exotic flow-style mapping
   are not preserved; comments and formatting everywhere else still are.

Every other line of `text` is copied verbatim. The function is pure (text in, text out), so its
contract is directly testable without a filesystem.

## 5. Single-scope resolution

`Adapter` gains `project_scope: bool` (D6). `resolve_config_path` reads it:

```python
if scope == "user" or not spec["project_scope"]:
    return <user resolution>          # --user-config, user_env_dir, Path.home()
return <project resolution>           # cwd / project_parts
```

`--user-config` stays ignored whenever the requested scope is `project` (D7): the declared file is a
user-scope concept, and a single-scope agent must not acquire a new meaning for it.

`single_scope_note(agent, scope, path) -> str | None` returns the note for a single-scope agent under
project scope, and `None` otherwise; `cli.py` prints it to stderr in both handlers, right after
`resolve_config_path`, so `--dry-run` sees it too. The note names the substitution and the resolved
file, e.g.:

```
  !  hermes reads a single user-scope config; --scope project has no separate file,
     using /home/u/.hermes/config.yaml
```

The same call site exists in `add` and `remove`, which keeps `cli.py` at its rule-14 100.00% floor
only if both are exercised — the tests cover both.

## 6. Test contract (the RED set)

| # | Contract |
| --- | --- |
| Y-1 | `splice_entry` replaces only the `sofer` entry: unrelated top-level keys, comments, sibling server entries and indentation are byte-identical |
| Y-2 | An absent `mcp_servers` key gets a fresh block appended; an absent `sofer` inside a block mapping is appended to that mapping |
| Y-3 | Removing the last server drops the `mcp_servers` block; removing one of two keeps the sibling verbatim |
| Y-4 | Flow-style `mcp_servers` is re-rendered in block style and still round-trips |
| Y-5 | `${HF_TOKEN}` (and a Windows-style `cwd`) survive as strings through write→read |
| Y-6 | `_infer_fmt` maps `.yaml`/`.yml`; `read_config` treats an empty/comment-only document as `{}` and raises `ValueError` on a non-mapping |
| Y-7 | `atomic_write(..., fmt="yaml")` keeps the pre-write text and is atomic (no `.tmp` left behind) |
| H-1 | `ADAPTERS["hermes"]` matches the row in §2 and the adapter key set includes `project_scope` |
| H-2 | `AGENT_NAMES` ends with `hermes`; `--agent` choices gain it; `--agent all` writes five configs, the fifth being `~/.hermes/config.yaml` |
| H-3 | `HERMES_HOME` replaces the home prefix (`$HERMES_HOME/config.yaml`), and the documented default is `~/.hermes/config.yaml` |
| H-4 | `build_entry("hermes", …)` yields `command` (string), absolute `cwd`, and `env` NAMES as `${KEY}` references; no value ever reaches the file |
| H-5 | `--scope project` resolves hermes to its user file, prints the note in `add` **and** `remove`, and ignores `--user-config` |
| H-6 | Idempotence: a second `add` leaves the file byte-identical, writes no `.bak`, and reports "already registered" |
| H-7 | `probe_native("hermes")` is `False` even when a fake `hermes` binary is on `PATH` |
| H-8 | The `--agent all` env warning still fires once (opencode only), and the forwarding agents include hermes |
| H-9 | CLI help: choices and description name hermes, the `${KEY}` form, YAML preservation and the single-scope note |

## 7. Verification strategy

Focused files first (`tests/test_yaml_edit.py`, `tests/test_mcp_registration.py`, `tests/test_cli.py`),
then the full gate set of `CONTRIBUTING.md`: `uv run pytest tests/ -q`, `ruff check`, `ruff format
--check`, `mypy src/ scripts/`, `pyright`, `coverage run -m pytest` with the TOTAL gate and
`scripts/check_core_coverage.sh` (the four rule-14 files at 100.00%), and
`scripts/check_test_mapping.py`. The independent verifier re-runs them and compares the branch tally
with the base tally, so the delta in collected tests is stated, not assumed.
