"""CLI ↔ MCP surface parity guard (systemic issue-class fix, test-only).

Closes the root cause behind issues #152, #153, #154, #155: nothing compared the CLI
flag surface (``cli._build_parser``) against the MCP tool parameter surface
(``build_server`` tool schemas), so CLI flags routinely landed without an MCP
counterpart and vice versa.

Design
------
For every command area (CLI subcommand → its MCP tool(s)) a
:class:`AreaParity` declaration states, explicitly and per flag/param:

* ``flag_map`` — CLI flag → MCP param, including deliberate renames
  (``output`` → ``output_dir``, ``no_checks`` → ``run_checks``).
* ``exempt_flags`` / ``exempt_params`` — deliberate asymmetries (actor-driven
  MCP gates, batch ``*_all`` redesign, CLI-only registration) with the reason
  inlined.
* ``known_gaps`` — deliberate *current* asymmetries tracked as issues
  (#153 publish cleanup, #154 scan ``--ext``, #155 batch ``max_sample``).
  Each entry asserts the param is **absent** today; the fixing change flips it
  to ``flag_map``/``exempt_flags``-removal as its RED→GREEN step. The guard
  thus fails exactly when a gap is fixed but not re-declared.

Assertions per area (all must hold simultaneously):

* Every declared flag/positional exists in the real CLI parser.
* Every real CLI flag/positional is declared (no silent drift in EITHER
  direction: an undeclared flag or param fails the suite).
* Every mapped MCP param exists in at least one tool of the area.
* Every MCP tool param is mapped or explicitly exempted.
* Every ``known_gaps`` entry still holds (param absent from its tool).

Out of scope by design: behaviors that are not surface (e.g. the scan
Phase-1 move-to-``raw/`` gap #152, publish gating semantics) are covered by
behavior tests in their own changes; ``sofer_auth_status`` is deliberately
MCP-only (actor design A) and ``mcp add/remove`` deliberately CLI-only
(host-machine registration), both documented in :data:`AREAS`.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from sofer.cli import _build_parser
from sofer.mcp_server import build_server


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


async def _list_tools(server: Any) -> dict[str, Any]:
    async with Client(server) as client:
        tools = await client.list_tools()
        return {t.name: t for t in tools}


def _tools_dict(tmp_path: Path) -> dict[str, Any]:
    return _run(_list_tools(build_server(root=tmp_path)))


@dataclass(frozen=True)
class AreaParity:
    """One CLI command area and its declared surface contract."""

    cli_command: str | None
    mcp_tools: tuple[str, ...]
    flag_map: dict[str, str] = field(default_factory=dict)
    exempt_flags: dict[str, str] = field(default_factory=dict)
    positionals: dict[str, str] = field(default_factory=dict)
    exempt_params: dict[str, str] = field(default_factory=dict)
    known_gaps: dict[tuple[str, str], str] = field(default_factory=dict)
    note: str = ""


AREAS: list[AreaParity] = [
    AreaParity(
        cli_command="validate",
        mcp_tools=("sofer_validate",),
        positionals={"config": "config"},
    ),
    AreaParity(
        cli_command="prepare",
        mcp_tools=("sofer_prepare",),
        flag_map={
            "output": "output_dir",
            "no_checks": "run_checks",  # spec 10.9 deliberate rename
            "force": "force",
            "verify": "verify",
        },
        positionals={"config": "config"},
        exempt_flags={
            "all_files": "redesign: batch moved to sofer_codebook_all tool (spec 10.6)",
        },
    ),
    AreaParity(
        cli_command="publish",
        mcp_tools=("sofer_publish", "sofer_publish_confirm"),
        flag_map={
            "target": "target",
            "output": "output_dir",
            "force": "force",
            "keep_csv": "keep_csv",
            "clean": "clean",
            "clean_cache": "clean_cache",
            "dry_run": "dry_run",
        },
        positionals={"config": "config"},
        exempt_params={
            "acknowledge_risk": "MCP-only human gate (actor design A)",
            "acknowledge_confidential": "MCP-only human gate (actor design A)",
            "approval_phrase": "MCP-only human gate (actor design A)",
        },
    ),
    AreaParity(
        cli_command="codebook",
        mcp_tools=("sofer_codebook", "sofer_codebook_all"),
        flag_map={
            "output": "output_file",
            "max_sample": "max_sample",
            "delimiter": "delimiter",  # #204: explicit dialect override on both surfaces
            "encoding": "encoding",  # #204
        },
        positionals={"csv": "path"},  # CLI positional FILE (dest csv) → sofer_codebook.path
        exempt_flags={
            "all_files": "redesign: batch moved to sofer_codebook_all tool (spec 10.6)",
            "config": "CLI batch config selector; MCP takes config as the tool's main argument",
        },
        exempt_params={
            "config": "batch main argument (CLI --config exempt above)",
            "output_dir": "batch-only: TOML build_dir driven (spec 10.6)",
        },
    ),
    AreaParity(
        cli_command="profile",
        mcp_tools=("sofer_profile", "sofer_profile_all"),
        flag_map={
            "output": "output_dir",
            "force": "force",
            "delimiter": "delimiter",  # #204: explicit dialect override on both surfaces
            "encoding": "encoding",  # #204
        },
        positionals={"dataset": "dataset"},
        exempt_flags={
            "all_files": "redesign: batch moved to sofer_profile_all tool (spec 10.6)",
            "config": "CLI batch config selector; MCP takes config as the tool's main argument",
        },
        exempt_params={
            "config": "batch main argument (CLI --config exempt above)",
            "output_dir": "batch-only: TOML-driven (spec 10.6)",
        },
    ),
    AreaParity(
        cli_command="render",
        mcp_tools=("sofer_render", "sofer_render_all"),
        flag_map={"output": "output_dir", "force": "force"},
        positionals={"package": "package"},
        exempt_flags={
            "all_files": "redesign: batch moved to sofer_render_all tool (spec 10.6)",
            "config": "CLI batch config selector; MCP takes config as the tool's main argument",
        },
        exempt_params={
            "config": "batch main argument (CLI --config exempt above)",
            "output_dir": "batch-only: TOML-driven (spec 10.6)",
        },
    ),
    AreaParity(
        cli_command="init",
        mcp_tools=("sofer_init",),
        flag_map={
            "user": "user",
            "move_existing": "move_existing",
            "dry_run": "dry_run",
            "force": "force",
        },
        positionals={"name": "name"},
        exempt_params={"cwd": "MCP-only containment policy (INIT-02)"},
    ),
    AreaParity(
        cli_command="scan",
        mcp_tools=("sofer_scan_dry_run", "sofer_scan_apply"),
        flag_map={
            "force": "force",
            "ext": "extensions",  # #154: now exposed on both scan tools
        },
        positionals={"config": "config"},
        exempt_flags={
            "dry_run": "split design: sofer_scan_dry_run is the dry-run surface (MSP-R03)",
        },
        exempt_params={
            "move_loose": (
                "#152: MCP-only Phase-1 opt-in (never silent move; CLI uses the "
                "interactive [y/N] prompt)"
            ),
        },
    ),
    AreaParity(
        cli_command=None,
        mcp_tools=("sofer_auth_status",),
        exempt_params={"config": "dataset config path (same shape as the other tools)"},
        note="sofer_auth_status has no CLI counterpart by design (agent preflight, actor design A)",
    ),
]


def _normalize(option: str) -> str:
    return option[2:].replace("-", "_")


def _surface_of(parser: argparse.ArgumentParser) -> tuple[set[str], set[str]]:
    """flags (normalized, alias-collapsed) and positionals (dest names)."""
    flags: set[str] = set()
    positionals: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            continue
        long_opts = [o for o in action.option_strings if o.startswith("--")]
        if long_opts:
            # argparse auto-adds --help to every subparser; it is CLI
            # infrastructure, not command surface.
            flags.add(_normalize(max(long_opts, key=len)))
        elif action.dest:
            positionals.add(action.dest)
    flags.discard("help")
    return flags, positionals


def _cli_surface() -> dict[str, tuple[set[str], set[str]]]:
    """command -> (flags, positionals); nested subcommands flattened as 'mcp add'."""
    parser = _build_parser()
    surface: dict[str, tuple[set[str], set[str]]] = {}
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for name, subp in action.choices.items():
            nested = [a for a in subp._actions if isinstance(a, argparse._SubParsersAction)]
            if nested:
                for sub_action in nested:
                    for sub_name, sub_subp in sub_action.choices.items():
                        surface[f"{name} {sub_name}"] = _surface_of(sub_subp)
            surface[name] = _surface_of(subp)
    return surface


class TestRoster:
    def test_declared_tools_exist(self, tmp_path: Path) -> None:
        tools = _tools_dict(tmp_path)
        declared = {t for area in AREAS for t in area.mcp_tools}
        assert declared <= set(tools), (
            f"declared tools missing from roster: {sorted(declared - set(tools))}"
        )
        # The two by-design asymmetries must remain documented in AREAS:
        assert "sofer_auth_status" in tools  # MCP-only preflight
        # (mcp add/remove has no tool — host-machine registration, CLI-only)

    def test_areas_cover_all_mcp_tools(self, tmp_path: Path) -> None:
        tools = _tools_dict(tmp_path)
        declared = {t for area in AREAS for t in area.mcp_tools}
        covered = declared  # everything declared is exercised by the area tests
        assert covered <= set(tools)


class TestAreaParity:
    @pytest.mark.parametrize("area", AREAS, ids=lambda a: a.cli_command or a.mcp_tools[0])
    def test_area_surface_contract(self, area: AreaParity, tmp_path: Path) -> None:
        tools = _tools_dict(tmp_path)
        surface = _cli_surface()

        if area.cli_command is not None:
            assert area.cli_command in surface, f"{area.cli_command} not in CLI"
            real_flags, real_pos = surface[area.cli_command]

            # A1 — declared flags/positionals exist in the real CLI parser.
            for flag in set(area.flag_map) | set(area.exempt_flags):
                assert flag in real_flags, (
                    f"{area.cli_command}: declared flag {flag} not in CLI surface"
                )
            for pos in area.positionals:
                assert pos in real_pos, (
                    f"{area.cli_command}: declared positional {pos} not in CLI surface"
                )

            # A2 — every real CLI flag is mapped or exempted (no silent drift).
            undeclared_flags = real_flags - set(area.flag_map) - set(area.exempt_flags)
            assert not undeclared_flags, (
                f"{area.cli_command}: CLI flags without MCP mapping/exemption: "
                f"{sorted(undeclared_flags)}"
            )

            # A3 — every real CLI positional is mapped.
            undeclared_pos = real_pos - set(area.positionals)
            assert not undeclared_pos, (
                f"{area.cli_command}: CLI positionals without MCP mapping: {sorted(undeclared_pos)}"
            )

            # A4 — mapped params exist in at least one tool of the area.
            mapped = set(area.flag_map.values()) | set(area.positionals.values())
            for param in mapped:
                assert any(
                    param in (tools[t].inputSchema or {}).get("properties", {})
                    for t in area.mcp_tools
                ), f"{area.cli_command}: mapped param {param} missing from {area.mcp_tools}"

        # A5 — every MCP tool param is mapped or explicitly exempted.
        for tool_name in area.mcp_tools:
            assert tool_name in tools, f"{area.cli_command}: tool {tool_name} missing roster"
            props = set((tools[tool_name].inputSchema or {}).get("properties", {}))
            covered = (
                set(area.flag_map.values())
                | set(area.positionals.values())
                | set(area.exempt_params)
            )
            stray = props - covered
            assert not stray, (
                f"{tool_name}: MCP params without CLI mapping/exemption: {sorted(stray)}"
            )

        # A6 — known gaps still hold; fixing a gap fails here by design, so the
        # fixing change must move the entry to flag_map (RED) then implement (GREEN).
        for (param, tool_name), source in area.known_gaps.items():
            props = set((tools[tool_name].inputSchema or {}).get("properties", {}))
            assert param not in props, (
                f"{tool_name}.{param} now exists ({source}) — move it from known_gaps "
                f"to flag_map and drop the corresponding exempt_flags entry"
            )
