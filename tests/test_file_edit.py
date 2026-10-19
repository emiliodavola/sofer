"""``[[file]]`` editing through the MCP surface (issue #344).

Covers the surgical editor (:mod:`sofer.file_edit`) and ``sofer_file_set``:
the tool that makes the template's recursive folder shape, ``column_types``
and the other ``[[file]]`` keys reachable from the tool surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import _make_dataset, call_tool
from fastmcp import Client

from sofer import _toml, file_edit
from sofer.mcp_server import build_server
from sofer.model import DatasetConfig


def _call(server: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    return call_tool(server, name, args).data


def _write_doc(root: Path) -> Path:
    """Write a comment-bearing dataset TOML with two flat entries."""
    path = root / "dataset.toml"
    path.write_text(
        "\n".join(
            [
                "# leading guidance comment",
                "[dataset]",
                'name = "test-ds"',
                'repo_id = "user/test-ds"',
                "",
                "[meta]",
                'description = "d"',
                "",
                "# files below",
                "[[file]]",
                'local = "a.csv"',
                'remote = "a.csv"',
                "",
                "[[file]]",
                'local = "b.csv"',
                'remote = "b.csv"',
                "",
                "# trailing guidance comment",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


class TestApplyFileEdit:
    """The editor replaces only the ``[[file]]`` region."""

    def test_replaces_entries_and_preserves_every_other_byte(self, tmp_path) -> None:
        path = _write_doc(tmp_path)
        before = path.read_text(encoding="utf-8")

        updated = file_edit.apply_file_edit(
            before,
            [
                {"local": "data.csv", "remote": "data.csv", "column_types": {"id": "string"}},
                {"local": "Labels", "remote": "Labels/", "recursive": True},
            ],
        )

        assert updated.startswith("# leading guidance comment\n[dataset]")
        assert "# files below" in updated
        assert "# trailing guidance comment" in updated
        parsed = _toml.loads(updated)
        assert parsed["dataset"]["name"] == "test-ds"
        assert parsed["meta"]["description"] == "d"
        assert parsed["file"] == [
            {"local": "data.csv", "remote": "data.csv", "column_types": {"id": "string"}},
            {"local": "Labels", "remote": "Labels/", "recursive": True},
        ]

    def test_missing_file_array_is_appended(self, tmp_path) -> None:
        text = '[dataset]\nname = "x"\nrepo_id = "u/x"\n\n[meta]\ndescription = "d"\n'
        updated = file_edit.apply_file_edit(text, [{"local": "a.csv", "remote": "a.csv"}])
        assert _toml.loads(updated)["file"] == [{"local": "a.csv", "remote": "a.csv"}]
        assert updated.startswith(text)

    def test_unknown_key_is_refused(self, tmp_path) -> None:
        path = _write_doc(tmp_path)
        with pytest.raises(file_edit.FileEditError, match="unknown key"):
            file_edit.apply_file_edit(
                path.read_text(encoding="utf-8"),
                [{"local": "a.csv", "remote": "a.csv", "bogus": True}],
            )

    def test_column_type_vocabulary_is_enforced(self, tmp_path) -> None:
        path = _write_doc(tmp_path)
        with pytest.raises(file_edit.FileEditError, match="column_types"):
            file_edit.apply_file_edit(
                path.read_text(encoding="utf-8"),
                [{"local": "a.csv", "remote": "a.csv", "column_types": {"id": "int64"}}],
            )

    def test_non_contiguous_entries_are_refused(self, tmp_path) -> None:
        text = "\n".join(
            [
                "[dataset]",
                'name = "x"',
                'repo_id = "u/x"',
                "",
                "[[file]]",
                'local = "a.csv"',
                'remote = "a.csv"',
                "",
                "[meta]",
                'description = "d"',
                "",
                "[[file]]",
                'local = "b.csv"',
                'remote = "b.csv"',
                "",
            ]
        )
        with pytest.raises(file_edit.FileEditError, match="contiguous"):
            file_edit.apply_file_edit(text, [{"local": "a.csv", "remote": "a.csv"}])

    def test_set_files_dry_run_leaves_the_file_untouched(self, tmp_path) -> None:
        path = _write_doc(tmp_path)
        before = path.read_text(encoding="utf-8")

        result = file_edit.set_files(
            path, [{"local": "new.csv", "remote": "new.csv"}], dry_run=True
        )

        assert result.changed is True
        assert path.read_text(encoding="utf-8") == before

    def test_set_files_writes_atomically(self, tmp_path) -> None:
        path = _write_doc(tmp_path)

        result = file_edit.set_files(
            path, [{"local": "new.csv", "remote": "new.csv"}], dry_run=False
        )

        assert result.changed is True
        assert _toml.loads(path.read_text(encoding="utf-8"))["file"] == [
            {"local": "new.csv", "remote": "new.csv"}
        ]
        assert not (tmp_path / "dataset.toml.tmp").exists()


class TestSoferFileSet:
    """``sofer_file_set`` is the MCP half of the writable ``[[file]]`` surface."""

    def test_writes_recursive_folder_and_column_types(self, tmp_path) -> None:
        _make_dataset(tmp_path)
        labels = tmp_path / "Labels"
        labels.mkdir()
        (labels / "a.csv").write_text("x;y\n1;2\n", encoding="utf-8-sig")
        server = build_server(root=tmp_path)

        envelope = _call(
            server,
            "sofer_file_set",
            {
                "config": "dataset.toml",
                "entries": [
                    {
                        "local": "data.csv",
                        "remote": "data.csv",
                        "column_types": {"col_a": "string"},
                    },
                    {"local": "Labels", "remote": "Labels/", "recursive": True},
                ],
            },
        )

        assert envelope["ok"] is True, envelope
        assert envelope["changed"] is True
        assert envelope["entries"] == 2
        cfg = DatasetConfig.from_toml(tmp_path / "dataset.toml")
        assert [entry.recursive for entry in cfg.files] == [False, True]
        assert cfg.files[0].column_types == {"col_a": "string"}

    def test_dry_run_writes_nothing(self, tmp_path) -> None:
        toml_path = _make_dataset(tmp_path)
        before = toml_path.read_text(encoding="utf-8")
        server = build_server(root=tmp_path)

        envelope = _call(
            server,
            "sofer_file_set",
            {
                "config": "dataset.toml",
                "entries": [{"local": "data.csv", "remote": "data.csv"}],
                "dry_run": True,
            },
        )

        assert envelope["ok"] is True, envelope
        assert envelope["dry_run"] is True
        assert toml_path.read_text(encoding="utf-8") == before

    def test_unknown_key_is_refused(self, tmp_path) -> None:
        _make_dataset(tmp_path)
        server = build_server(root=tmp_path)

        envelope = _call(
            server,
            "sofer_file_set",
            {
                "config": "dataset.toml",
                "entries": [{"local": "data.csv", "remote": "data.csv", "bogus": 1}],
            },
        )

        assert envelope["ok"] is False, envelope
        assert "unknown key" in envelope["message"]

    def test_local_outside_root_is_refused(self, tmp_path) -> None:
        _make_dataset(tmp_path)
        outside = tmp_path.parent / "outside.csv"
        outside.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        server = build_server(root=tmp_path)

        envelope = _call(
            server,
            "sofer_file_set",
            {
                "config": "dataset.toml",
                "entries": [{"local": "../outside.csv", "remote": "outside.csv"}],
            },
        )

        assert envelope["ok"] is False, envelope
        assert "resolves outside the server root" in envelope["message"]

    def test_folder_and_file_remote_collision_is_refused(self, tmp_path) -> None:
        _make_dataset(tmp_path)
        labels = tmp_path / "Labels"
        labels.mkdir()
        (labels / "a.csv").write_text("x;y\n1;2\n", encoding="utf-8-sig")
        server = build_server(root=tmp_path)

        envelope = _call(
            server,
            "sofer_file_set",
            {
                "config": "dataset.toml",
                "entries": [
                    {"local": "Labels", "remote": "Labels/", "recursive": True},
                    {"local": "Labels/a.csv", "remote": "Labels/a.csv"},
                ],
            },
        )

        assert envelope["ok"] is False, envelope
        assert "remote" in envelope["message"]

    def test_empty_entries_refuse_to_erase_registrations(self, tmp_path) -> None:
        _make_dataset(tmp_path)
        server = build_server(root=tmp_path)

        envelope = _call(server, "sofer_file_set", {"config": "dataset.toml", "entries": []})

        assert envelope["ok"] is False, envelope
        assert "[[" in envelope["message"]

    def test_roster_reaches_nineteen_tools(self, tmp_path) -> None:
        server = build_server(root=tmp_path)

        async def _names() -> set[str]:
            async with Client(server) as client:
                return {tool.name for tool in await client.list_tools()}

        import asyncio

        names = asyncio.run(_names())
        assert "sofer_file_set" in names
        assert len(names) == 19
