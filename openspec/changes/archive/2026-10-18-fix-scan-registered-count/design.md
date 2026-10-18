# Design — `2026-10-18-fix-scan-registered-count`

> **Change** `2026-10-18-fix-scan-registered-count` (issue **#345**) · branch
> `fix/345-scan-registered-count` from `dev@c68e090` · store **hybrid**.

---

## 1. The defect, precisely

Both MCP scan tools and the CLI measure the registration count as a difference of
list lengths, with the baseline captured **before** `merge_entries` strips the
`sofer_init` placeholders:

```python
# mcp_server.py:2838-2840 (sofer_scan_dry_run) — same shape at :2979-2981 (sofer_scan_apply)
before = len(raw_toml.get("file", []))                    # 2 — raw/example.csv, raw/example/
merged = merge_entries(discovered, raw_toml, base_dir, data_dir)
registered = len(merged.get("file", [])) - before         # 65 + 2 - 2 - 2 = 63
```

```python
# cli.py:645-649
before_count = len(raw_toml.get("file", []))
raw_toml = merge_entries(discovered, raw_toml, base_dir, data_dir)
after_count = len(raw_toml.get("file", []))
new_count = after_count - before_count                     # same off-by-2
```

and the strip lives inside the merge:

```python
# scanner.py:434-444 — "Strip template entries left over from sofer init"
raw_toml["file"] = [
    e
    for e in raw_toml.get("file", [])
    if not str(e.get("local", "")).startswith("TODO:")
    and not str(e.get("local", "")).startswith("raw/example")
]
```

The arithmetic would be right if `before` were taken after the strip. It is not, so
the two stripped placeholders are subtracted from a result that never contained
them. Reproduced on two corpora (65 and 103 loose files → 63 and 101 reported).

`merge_entries` already computes the honest number and discards it
(`scanner.py:471`, `added += 1`) and returns only the mutated TOML dict.

## 2. Why not "measure `before` after the strip"

That was #345's first option, and it is rejected: it makes three call sites
responsible for knowing that `merge_entries` mutates its input as a side effect,
and any future caller repeats the same mistake. The count is a fact about the
merge, so the merge reports it (#345's own preference: *"The second is the honest
one"*).

## 3. The shape of the fix

```python
def merge_entries_counted(
    discovered: list[Path],
    raw_toml: dict[str, Any],
    base_dir: Path,
    data_dir: Path,
) -> tuple[dict[str, Any], int]:
    """Add [[file]] entries for each discovered file; return (toml, added)."""
    # ...existing body, ending with:  return raw_toml, added


def merge_entries(discovered, raw_toml, base_dir, data_dir) -> dict[str, Any]:
    """Backward-compatible wrapper: the merged TOML only."""
    merged, _added = merge_entries_counted(discovered, raw_toml, base_dir, data_dir)
    return merged
```

One implementation, two signatures. `merge_entries` keeps its exact contract, so
the ~20 test call sites and `cli.py`'s import stay valid without edits; the three
counting sites opt into the counted form.

| surface | before | after |
| --- | --- | --- |
| `sofer_scan_dry_run` | `len(merged) - before` | `added` from the merge |
| `sofer_scan_apply` | `len(merged) - before` | `added` from the merge |
| `cli scan` (`Registered N`, dry-run preview) | `after_count - before_count` | `added` from the merge |

## 4. Contract this pins

`registered` / `Registered N` = **entries appended by this call**.

- A greenfield `sofer_init` tree with N loose supported files → `N` (#345's
  expected behaviour, `65` in its example).
- An idempotent re-scan over the same tree → `0`.
- The dry run and the apply agree, because both read the same number from the
  same merge.

The tool schemas gain a `description` on `registered` stating exactly this, so an
agent reading `tools/list` does not have to infer the semantics (AGENTS rule 7).

## 5. Files touched

| file | why |
| --- | --- |
| `src/sofer/scanner.py` | `merge_entries_counted` + wrapper (100% coverage gate) |
| `src/sofer/mcp_server.py` | two counting sites; `registered` schema descriptions |
| `src/sofer/cli.py` | one counting site, two printouts (100% coverage gate) |
| `tests/test_scanner.py` | the counted API, incl. the strip interaction |
| `tests/test_mcp_server.py` | greenfield count, dry-run parity, idempotent re-scan |
| `tests/test_cli.py` | `Registered N` on an init-style TOML |
| `openspec/specs/scan/spec.md`, `openspec/specs/mcp-server/spec.md` | the counting rule + scenarios |

## 6. Risk

Nothing durable is mutated: the same TOML is written by the same merge as today,
and only the reported integer changes. The two 100% gates (`scanner.py`,
`cli.py`) are the real constraint — every new branch must be exercised by a real
assertion, not a line-touching test.
