# Design — `2026-10-18-fix-manifest-publishable-intermediate`

> **Change** `2026-10-18-fix-manifest-publishable-intermediate` (issue **#346**) ·
> branch `fix/346-manifest-publishable-intermediate` from `dev@d07557e` · store
> **hybrid**.

---

## 1. The defect, measured before the fix

Scratch probe on a prepared tree (card, license, parquet, one codebook page, plus
`cache/profiles` and `cache/renders` as `profile_all`/`render_all` write them),
against the pre-fix `sofer.manifest`:

```
declared artifacts:      7
classification present:  False
profile  entry:           path='profiles/' status=optional      <- the layers exist in cache/
render   entry:           path='renders/' status=optional
staged by _copy_package: 4 -> ['LICENSE', 'README.md', 'codebooks/data.md', 'data.parquet']
publishable():           absent -- a reader must know which types are local-only
```

Every symptom of #346 is here at once: two entries that describe a path nobody
writes to, a declared list that cannot be compared with the delivery, and no field
that separates the delivery set from the local-only layers.

## 2. Two axes, not one

The manifest answers two different questions and had only one field for them:

| axis | values | question |
| --- | --- | --- |
| `classification` (new) | `publishable`, `intermediate` | does this artifact belong to the delivery at all? |
| `status` (existing) | `staged`, `expected`, `optional`, `missing` | is it here, and does its absence block? |

They are independent: an intermediate layer that exists is `staged` and still never
uploaded. Collapsing them into one field would lose the blocking rule PUB-12
requires (`missing` + required ⇒ block), which is why this is additive.

The identity that makes the manifest trustworthy is derived, not stored:

```
delivered()  ==  classification == publishable  AND  status == staged  AND  path is a FILE path
```

and `test_delivered_set_is_the_staged_set` asserts it against the real
`_copy_package` output on the same tree, while
`test_recursive_tree_is_a_directory_entry_never_a_delivered_file` pins the
directory case.

Why the third term exists: a recursive remote is recorded as ONE entry, and its
files are enumerated by the copy path, not by the manifest. Without the file-path
restriction the identity was false on recursive trees — an independent verifier
showed `delivered()` containing `assets` and an empty `empty` while the staged set
held `assets/a.txt` and `assets/nested/b.txt`: the empty tree stated an upload of
zero files as one delivered artifact, which is the overstatement #346 is about.
Directory entries therefore carry a trailing slash (the marker `codebooks/`,
`profiles/` and `renders/` already used) and are excluded from the delivered set.

Why not "publishable() is the delivery set": an absent optional artifact
(`codebook.md` before an `--all-files` prepare) is publishable in principle and is
not delivered. The first version of this change made `publishable()` the delivery
set and the probe reported `publishable 5 vs staged 4` — the same class of
overstatement as #346, caught before the commit. `publishable()` is the
classification query; `delivered()` is the identity.

## 3. The probe

```python
layer_dir = next(
    (candidate for candidate in (base / config.OUTPUT_DIR / dir_name, base / dir_name)
     if candidate.is_dir()),
    None,
)
```

The artifact cache is where the pipeline writes (`profile.py:264-270`,
`write_root = data_dir`); the dataset root stays supported because an explicit run
can put them there. The recorded path is relative to the root, so `cache/profiles/x`
and `profiles/x` are distinguishable, and a cache path outside the root falls back
to the absolute POSIX path instead of raising `ValueError` inside `prepare`.

## 4. Compatibility

- `to_dict` gains one key; `from_dict` defaults it to `publishable`, so manifests
  written by `0.6.1` load unchanged and the JSON roundtrip stays byte-stable.
- Only `required_missing()` is consumed outside the module (the dry-run warning at
  `publish.py:453-457` and the confirm gate at `:946-949`), and intermediate entries
  are never `missing`, so the delivery path needs no change.
- `test_build_manifest_optional_profile_intermediate` (a layer at the dataset root)
  keeps passing: the root is still probed.

## 5. Files touched

| file | why |
| --- | --- |
| `src/sofer/manifest.py` | `ArtifactClass`, the field, `publishable()`, `intermediate()`, `delivered()`, the probe |
| `tests/test_manifest.py` | five new tests, including the delivered-equals-staged identity |
| `openspec/specs/publish/spec.md` | PUB-12 clause + three scenarios |
| `openspec/changes/.../specs/publish/spec.md` | the delta |

## 6. Risk

The manifest is a consumed format, so the change is additive by construction: one
new key with a defaulted read, no renames, no status changes, and the blocking rule
untouched. `publish.py` (a 100% coverage module) is not modified.
