"""Enforce the spec↔test evidence contract for `## Test Mapping` tables.

Capabilities: `test-mapping-contract` (TMC-01..TMC-05) and `mapping-checker`
(MC-01..MC-07). Run as ``uv run python scripts/check_test_mapping.py`` from the
repository root (or pass ``--repo-root`` for a fixture tree). The checker:

1. enumerates every ``openspec/specs/*/spec.md`` and classifies it **mapped**
   when its ``## Test Mapping`` section introduces at least one data row,
   **unmapped** otherwise (MC-01);
2. for each mapped spec, requires every ``#### Scenario:`` heading to appear in
   exactly one data row and every data row to begin its Verification cell with
   exactly one ``test:`` / ``verify:`` prefix (TMC-01..TMC-04, MC-02, MC-04);
3. resolves every ``test:`` reference through pytest **collect-only** — file
   existence plus collected node-id membership; test bodies never execute
   (MC-03);
4. cross-checks ``openspec/test-mapping-registry.md`` against the tree as a
   bijection: the mapped and registered sets are disjoint and together equal
   the full spec set (MC-05).

Exit code 0 on a clean tree, non-zero with the full offender list otherwise.
The checker is deterministic, runs offline, and modifies no repository file
(MC-06).
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ── Defaults and grammar constants (no in-body magic values, AGENTS rule 1) ──
DEFAULT_SPECS_ROOT = "openspec/specs"
DEFAULT_REGISTRY = "openspec/test-mapping-registry.md"
SPEC_FILENAME = "spec.md"
REPO_ROOT_PARENT_INDEX = 1

TEST_MAPPING_HEADING = "## Test Mapping"
SPEC_TABLE_HEADER = ("Req", "Scenario", "Verification")
REGISTRY_TABLE_HEADER = ("Spec", "Reason")

SCENARIO_RE = re.compile(r"^\s*####\s+Scenario:\s*(?P<name>.+?)\s*$")
SEPARATOR_CELL_RE = re.compile(r"^:?-{2,}:?$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
# A repository-relative POSIX path token: no whitespace, no shell metacharacters,
# no colon (so no drive letter and no second prefix). Threat Matrix hardening.
PATH_TOKEN_RE = re.compile(r"^[A-Za-z0-9._/-]+$")

PREFIX_TEST = "test:"
PREFIX_VERIFY = "verify:"
PREFIXES = (PREFIX_TEST, PREFIX_VERIFY)
NODE_SEPARATOR = "::"

SCENARIO_COLUMN = 1
VERIFICATION_COLUMN = 2
EXPECTED_SPEC_COLUMNS = 3
EXPECTED_REGISTRY_COLUMNS = 2

FAILURE_MARKER = "FAIL"
INFO_MARKER = "INFO"


@dataclass(frozen=True)
class TableRow:
    """One parsed Markdown table data row.

    Attributes:
        line_number: 1-based line number in the source file.
        cells: The row's cell texts, stripped of surrounding whitespace.
    """

    line_number: int
    cells: tuple[str, ...]


@dataclass(frozen=True)
class ParsedTable:
    """A parsed Markdown table.

    Attributes:
        header: The header row's cells.
        rows: The data rows after the header and separator.
    """

    header: tuple[str, ...]
    rows: tuple[TableRow, ...]


@dataclass(frozen=True)
class TestReference:
    """A well-formed ``test:`` reference awaiting collection.

    Attributes:
        spec: The owning spec directory name.
        line_number: 1-based line of the referencing row.
        path: Repository-relative POSIX test path.
        node: Optional ``::name`` selector, or ``None`` for a path-only ref.
    """

    spec: str
    line_number: int
    path: str
    node: str | None


@dataclass
class SpecRecord:
    """A spec file and its parsed Test Mapping table (or ``None``).

    Attributes:
        name: The spec directory name under ``openspec/specs``.
        text: The full spec text.
        table: The parsed Test Mapping table, or ``None`` when absent.
    """

    name: str
    text: str
    table: ParsedTable | None

    @property
    def mapped(self) -> bool:
        """Whether the spec's Test Mapping section introduces a data row."""
        return self.table is not None and bool(self.table.rows)


def _default_repo_root() -> Path:
    """Resolve the repository root from this script's location.

    Returns:
        The repository root (the parent of the ``scripts/`` directory).
    """
    return Path(__file__).resolve().parents[REPO_ROOT_PARENT_INDEX]


def _read_lines(path: Path) -> list[str]:
    """Read a UTF-8 file into its lines (newline-stripped, never ``\\n`` kept).

    Args:
        path: The file to read.

    Returns:
        The file's lines without trailing newline characters.
    """
    return path.read_text(encoding="utf-8").splitlines()


def _split_row(line: str) -> tuple[str, ...]:
    """Split a Markdown table line into stripped cells.

    Args:
        line: A raw table line beginning and ending with ``|``.

    Returns:
        The cell texts, outer pipes removed and each cell stripped.
    """
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return tuple(cell.strip() for cell in stripped.split("|"))


def _is_separator(cells: tuple[str, ...]) -> bool:
    """Whether a row is a Markdown header separator (``---`` cells).

    Args:
        cells: The row's cells.

    Returns:
        True when every non-empty cell matches the separator grammar.
    """
    return all(SEPARATOR_CELL_RE.match(cell) for cell in cells if cell)


def _parse_table(lines: list[str], start: int) -> ParsedTable | None:
    """Parse the first Markdown table at or after ``start``.

    Args:
        lines: The file's lines.
        start: Index to begin scanning from.

    Returns:
        The parsed table, or ``None`` when no table line is found. The header
        is the first table line; a separator row is recognised structurally and
        never treated as a data row (TMC-04).
    """
    collected: list[TableRow] = []
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if not collected:
            if stripped.startswith("|"):
                collected.append(TableRow(index + 1, _split_row(lines[index])))
            continue
        if stripped.startswith("|"):
            collected.append(TableRow(index + 1, _split_row(lines[index])))
        else:
            break
    if not collected:
        return None
    header = collected[0].cells
    body = (
        collected[2:]
        if len(collected) >= 2 and _is_separator(collected[1].cells)
        else collected[1:]
    )
    return ParsedTable(header=header, rows=tuple(body))


def _find_heading(lines: list[str], heading: str) -> int | None:
    """Find the index of an exact (stripped) heading line.

    Args:
        lines: The file's lines.
        heading: The heading text to match after stripping.

    Returns:
        The line index, or ``None`` when the heading is absent.
    """
    for index, line in enumerate(lines):
        if line.strip() == heading:
            return index
    return None


def _scenario_headings(lines: list[str]) -> list[str]:
    """Collect the ``#### Scenario:`` heading names in a spec.

    Args:
        lines: The file's lines.

    Returns:
        The heading names in file order (duplicates preserved).
    """
    names: list[str] = []
    for line in lines:
        match = SCENARIO_RE.match(line)
        if match:
            names.append(match.group("name"))
    return names


def _load_specs(specs_root: Path) -> list[SpecRecord]:
    """Enumerate and parse every spec under ``specs_root``.

    Args:
        specs_root: The directory holding one ``*/spec.md`` per spec.

    Returns:
        The spec records, sorted by spec directory name.
    """
    records: list[SpecRecord] = []
    for spec_dir in sorted(p for p in specs_root.iterdir() if p.is_dir()):
        spec_file = spec_dir / SPEC_FILENAME
        if not spec_file.is_file():
            continue
        lines = _read_lines(spec_file)
        heading_index = _find_heading(lines, TEST_MAPPING_HEADING)
        table = _parse_table(lines, heading_index + 1) if heading_index is not None else None
        records.append(SpecRecord(name=spec_dir.name, text="\n".join(lines), table=table))
    return records


def _validate_verification_cell(
    spec: str,
    line_number: int,
    cell: str,
    references: list[TestReference],
    failures: list[str],
) -> None:
    """Validate one Verification cell and queue a ``test:`` ref for collection.

    Args:
        spec: The owning spec name.
        line_number: The row's 1-based line number.
        cell: The Verification cell text.
        references: Mutable accumulator of well-formed ``test:`` references.
        failures: Mutable accumulator of human-readable failure messages.
    """
    stripped = cell.strip()
    prefix = next((candidate for candidate in PREFIXES if stripped.startswith(candidate)), None)
    if prefix is None:
        failures.append(
            f"{spec}:{line_number}: Verification cell has no {PREFIX_TEST}/{PREFIX_VERIFY} prefix"
        )
        return
    reference = stripped[len(prefix) :].strip()
    if not reference:
        failures.append(f"{spec}:{line_number}: empty {prefix} reference")
        return
    if reference.startswith(PREFIX_TEST) or reference.startswith(PREFIX_VERIFY):
        failures.append(f"{spec}:{line_number}: more than one evidence prefix")
        return
    if prefix == PREFIX_TEST:
        _validate_test_reference(spec, line_number, reference, references, failures)


def _validate_test_reference(
    spec: str,
    line_number: int,
    reference: str,
    references: list[TestReference],
    failures: list[str],
) -> None:
    """Validate a ``test:`` reference and queue it for pytest collection.

    The reference is the first whitespace-delimited token of the cell remainder
    (the preserved evidence prose may follow). The token must be a
    repository-relative POSIX path with at most one ``::`` selector (TMC-02).

    Args:
        spec: The owning spec name.
        line_number: The row's 1-based line number.
        reference: The text after the ``test:`` prefix.
        references: Mutable accumulator of well-formed references.
        failures: Mutable accumulator of failure messages.
    """
    tokens = reference.split()
    token = tokens[0] if tokens else ""
    if not token:
        failures.append(f"{spec}:{line_number}: empty {PREFIX_TEST} reference")
        return
    parts = token.split(NODE_SEPARATOR)
    if len(parts) > 2:
        failures.append(
            f"{spec}:{line_number}: {PREFIX_TEST} reference has more than one "
            f"{NODE_SEPARATOR} selector"
        )
        return
    path = parts[0]
    node = parts[1] if len(parts) == 2 else None
    if not path:
        failures.append(f"{spec}:{line_number}: {PREFIX_TEST} reference has an empty path")
        return
    if (
        path.startswith("/")
        or "\\" in path
        or WINDOWS_DRIVE_RE.match(path)
        or not PATH_TOKEN_RE.match(path)
    ):
        failures.append(
            f"{spec}:{line_number}: {PREFIX_TEST} reference is not a "
            f"repository-relative POSIX path: {path}"
        )
        return
    if node is not None and not node:
        failures.append(f"{spec}:{line_number}: {PREFIX_TEST} reference has an empty node selector")
        return
    references.append(TestReference(spec=spec, line_number=line_number, path=path, node=node))


def _collect_node_ids(
    repo_root: Path, base_cmd: list[str], files: list[str]
) -> tuple[set[str], str | None]:
    """Collect pytest node ids for the referenced files (never execution).

    Args:
        repo_root: The directory pytest runs from.
        base_cmd: The interpreter command prefix (e.g. ``python -m pytest``).
        files: Repository-relative test file paths to collect.

    Returns:
        A ``(node_ids, error)`` pair; ``error`` is a message when pytests could
        not be invoked, otherwise ``None``.
    """
    command = [
        *base_cmd,
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
        *files,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
    except OSError as exc:  # pragma: no cover - environment-dependent
        return set(), f"could not run pytest collection: {exc}"
    node_ids: set[str] = set()
    for line in completed.stdout.splitlines():
        candidate = line.strip().replace("\\", "/")
        if NODE_SEPARATOR in candidate and not candidate.startswith("="):
            node_ids.add(candidate)
    return node_ids, None


def _resolve_test_references(
    repo_root: Path,
    base_cmd: list[str],
    references: list[TestReference],
    failures: list[str],
) -> None:
    """Resolve queued ``test:`` references against the tree and pytest.

    Validates path containment and existence first, then collects the distinct
    surviving files once and checks node-id membership (MC-03).

    Args:
        repo_root: The repository root.
        base_cmd: The pytest invocation prefix.
        references: The well-formed ``test:`` references to resolve.
        failures: Mutable accumulator of failure messages.
    """
    resolved_root = repo_root.resolve()
    by_file: dict[str, list[TestReference]] = {}
    for reference in references:
        target = (repo_root / reference.path).resolve()
        if not target.is_relative_to(resolved_root):
            failures.append(
                f"{reference.spec}:{reference.line_number}: {PREFIX_TEST} reference escapes "
                f"the repository root: {reference.path}"
            )
            continue
        if not target.is_file():
            failures.append(
                f"{reference.spec}:{reference.line_number}: {PREFIX_TEST} test file does not "
                f"exist: {reference.path}"
            )
            continue
        by_file.setdefault(reference.path, []).append(reference)
    if not by_file:
        return
    node_ids, error = _collect_node_ids(repo_root, base_cmd, sorted(by_file))
    if error is not None:
        failures.append(error)
        return
    file_nodes: dict[str, set[str]] = {}
    for node_id in node_ids:
        file_nodes.setdefault(node_id.split(NODE_SEPARATOR)[0], set()).add(node_id)
    for path, refs in by_file.items():
        collected = file_nodes.get(path, set())
        for reference in refs:
            if reference.node is None:
                if not collected:
                    failures.append(
                        f"{reference.spec}:{reference.line_number}: test file collects no "
                        f"items: {path}"
                    )
            elif f"{path}{NODE_SEPARATOR}{reference.node}" not in collected:
                failures.append(
                    f"{reference.spec}:{reference.line_number}: node id not collected by pytest: "
                    f"{path}{NODE_SEPARATOR}{reference.node}"
                )


def _validate_mapped_spec(
    record: SpecRecord,
    references: list[TestReference],
    failures: list[str],
) -> None:
    """Validate one mapped spec's table: prefixes, refs, and the bijection.

    Args:
        record: The mapped spec record.
        references: Mutable accumulator of ``test:`` references.
        failures: Mutable accumulator of failure messages.
    """
    assert record.table is not None
    if record.table.header != SPEC_TABLE_HEADER:
        failures.append(
            f"{record.name}: Test Mapping header must be exactly "
            f"{' | '.join(SPEC_TABLE_HEADER)}, found {' | '.join(record.table.header)}"
        )
    lines = record.text.splitlines()
    headings = _scenario_headings(lines)
    row_counts: dict[str, int] = {}
    for row in record.table.rows:
        if len(row.cells) != EXPECTED_SPEC_COLUMNS:
            failures.append(
                f"{record.name}:{row.line_number}: data row must carry "
                f"{EXPECTED_SPEC_COLUMNS} columns, found {len(row.cells)}"
            )
            continue
        scenario = row.cells[SCENARIO_COLUMN]
        verification = row.cells[VERIFICATION_COLUMN]
        if not any(cell for cell in row.cells):
            failures.append(f"{record.name}:{row.line_number}: empty row")
            continue
        if not scenario:
            failures.append(f"{record.name}:{row.line_number}: empty Scenario cell")
        if not verification:
            failures.append(f"{record.name}:{row.line_number}: empty Verification cell")
        else:
            _validate_verification_cell(
                record.name, row.line_number, verification, references, failures
            )
        if scenario:
            row_counts[scenario] = row_counts.get(scenario, 0) + 1
    heading_counts: dict[str, int] = {}
    for heading in headings:
        heading_counts[heading] = heading_counts.get(heading, 0) + 1
    for heading, count in heading_counts.items():
        mapped = row_counts.get(heading, 0)
        if mapped == 0:
            failures.append(f"{record.name}: scenario has no mapping row: {heading!r}")
        elif mapped > 1:
            failures.append(f"{record.name}: scenario is mapped by {mapped} rows: {heading!r}")
    for scenario in row_counts:
        if scenario not in heading_counts:
            failures.append(
                f"{record.name}: row names a scenario that does not exist: {scenario!r}"
            )


def _validate_registry(
    registry_path: Path,
    records: list[SpecRecord],
    failures: list[str],
) -> None:
    """Validate the registry↔tree bijection and non-empty reasons (MC-05).

    Args:
        registry_path: Path to ``openspec/test-mapping-registry.md``.
        records: Every spec record under ``openspec/specs``.
        failures: Mutable accumulator of failure messages.
    """
    if not registry_path.is_file():
        failures.append(f"registry file does not exist: {registry_path}")
        return
    lines = _read_lines(registry_path)
    table = _parse_table(lines, 0)
    if table is None:
        failures.append("registry carries no Markdown table")
        return
    if table.header != REGISTRY_TABLE_HEADER:
        failures.append(
            f"registry header must be exactly {' | '.join(REGISTRY_TABLE_HEADER)}, "
            f"found {' | '.join(table.header)}"
        )
    entries: dict[str, int] = {}
    for row in table.rows:
        if len(row.cells) != EXPECTED_REGISTRY_COLUMNS:
            failures.append(
                f"registry:{row.line_number}: entry must carry {EXPECTED_REGISTRY_COLUMNS} columns"
            )
            continue
        spec, reason = row.cells
        if not spec:
            failures.append(f"registry:{row.line_number}: entry has an empty Spec cell")
            continue
        if spec in entries:
            failures.append(f"registry:{row.line_number}: duplicate entry for spec {spec!r}")
            continue
        entries[spec] = row.line_number
        if not reason:
            failures.append(f"registry:{row.line_number}: entry for {spec!r} has an empty reason")
    mapped = {record.name for record in records if record.mapped}
    unmapped = {record.name for record in records if not record.mapped}
    for spec in sorted(unmapped):
        if spec not in entries:
            failures.append(f"unmapped spec is not registered: {spec}")
    for spec in sorted(entries):
        if spec in mapped:
            failures.append(f"registry lists a spec that carries a Test Mapping table: {spec}")
        elif spec not in unmapped:
            failures.append(f"registry lists an unknown spec: {spec}")


def _report(records: list[SpecRecord], failures: list[str]) -> int:
    """Print the re-derived scenario inventory and the failure list.

    Args:
        records: Every spec record under ``openspec/specs``.
        failures: All accumulated failure messages.

    Returns:
        0 when ``failures`` is empty, 1 otherwise.
    """
    for record in records:
        count = len(_scenario_headings(record.text.splitlines()))
        state = "mapped" if record.mapped else "unmapped"
        print(f"{INFO_MARKER}: {record.name}: {count} scenario(s), {state}")
    if not failures:
        print("OK: test-mapping contract holds")
        return 0
    for failure in failures:
        print(f"{FAILURE_MARKER}: {failure}")
    print(f"{FAILURE_MARKER}: {len(failures)} violation(s) found")
    return 1


def _build_parser() -> argparse.ArgumentParser:
    """Build the checker's argument parser.

    Returns:
        The configured parser.
    """
    parser = argparse.ArgumentParser(
        prog="check_test_mapping.py",
        description="Enforce the spec Test Mapping contract and registry bijection.",
    )
    parser.add_argument(
        "--repo-root", default=None, help="Repository root (default: resolved from this script)."
    )
    parser.add_argument(
        "--specs-root",
        default=DEFAULT_SPECS_ROOT,
        help="Specs directory, relative to the repo root.",
    )
    parser.add_argument(
        "--registry", default=DEFAULT_REGISTRY, help="Registry path, relative to the repo root."
    )
    parser.add_argument(
        "--collect-only-cmd",
        default=None,
        help=(
            "Pytest command prefix for collection "
            "(default: the running interpreter's 'python -m pytest')."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the test-mapping checker over a repository tree.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        The process exit code: 0 when compliant, 1 otherwise.
    """
    args = _build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else _default_repo_root()
    specs_root = Path(args.specs_root)
    if not specs_root.is_absolute():
        specs_root = repo_root / specs_root
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = repo_root / registry_path
    base_cmd = (
        shlex.split(args.collect_only_cmd, posix=(os.name != "nt"))
        if args.collect_only_cmd
        else [sys.executable, "-m", "pytest"]
    )

    failures: list[str] = []
    records = _load_specs(specs_root)
    references: list[TestReference] = []
    for record in records:
        if record.mapped:
            _validate_mapped_spec(record, references, failures)
    _resolve_test_references(repo_root, base_cmd, references, failures)
    _validate_registry(registry_path, records, failures)
    return _report(records, failures)


if __name__ == "__main__":
    raise SystemExit(main())
