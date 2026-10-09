"""Tests for ``sofer._yaml`` -- the surgical YAML config splice.

Contract under test (design §4, cases Y-1..Y-5): :func:`sofer._yaml.splice_entry`
re-renders only the named entry of a top-level ``key`` mapping and copies every
other line of the pre-write document verbatim, so comments, key order and
indentation elsewhere survive an ``mcp add`` / ``mcp remove``. The module also
owns YAML parsing (:func:`load`) and whole-document rendering (:func:`dump`).
"""

from __future__ import annotations

import pytest

from sofer import _yaml


def _entry(cwd: str = "/proj") -> dict[str, object]:
    """Return the desired ``sofer`` entry shape a ``refs``/``refs_braced`` agent builds."""
    return {
        "command": "sofer-mcp",
        "cwd": cwd,
        "env": {"HF_TOKEN": "${HF_TOKEN}"},
    }


class TestLoad:
    def test_empty_document_is_empty_mapping(self) -> None:
        assert _yaml.load("") == {}

    def test_comment_only_document_is_empty_mapping(self) -> None:
        assert _yaml.load("# only a comment\n# and another\n") == {}

    def test_non_mapping_document_raises(self) -> None:
        with pytest.raises(ValueError, match="mapping"):
            _yaml.load("- 1\n- 2\n")
        with pytest.raises(ValueError, match="mapping"):
            _yaml.load("just a scalar\n")

    def test_mapping_loads(self) -> None:
        assert _yaml.load("a: 1\n") == {"a": 1}


class TestDump:
    def test_block_style_and_trailing_newline(self) -> None:
        text = _yaml.dump({"mcp_servers": {"sofer": _entry()}})
        assert text.endswith("\n")
        assert "mcp_servers:\n  sofer:\n" in text
        assert "${HF_TOKEN}" in text

    def test_round_trips_document(self) -> None:
        doc = {"mcp_servers": {"sofer": _entry()}}
        assert _yaml.load(_yaml.dump(doc)) == doc


class TestSpliceReplace:
    def test_replaces_only_named_entry(self) -> None:
        original = (
            "# leading comment\n"
            "project: demo  # inline comment\n"
            "\n"
            "mcp_servers:\n"
            "  other:\n"
            "    command: other-mcp\n"
            "    cwd: /other\n"
            "  sofer:\n"
            "    command: old\n"
            "\n"
            "foo: 1\n"
        )
        doc = {
            "project": "demo",
            "mcp_servers": {
                "other": {"command": "other-mcp", "cwd": "/other"},
                "sofer": _entry(),
            },
            "foo": 1,
        }

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        # Untouched regions are byte-identical: prefix up to the entry, suffix from `foo`.
        assert result.startswith(original[: original.index("  sofer:")])
        assert result.endswith(original[original.index("foo: 1") :])
        # Comments, sibling entry, key order and indentation survive verbatim.
        assert "# leading comment\n" in result
        assert "project: demo  # inline comment\n" in result
        assert "  other:\n    command: other-mcp\n    cwd: /other\n" in result
        assert result.index("other:") < result.index("sofer:")
        # Only the named entry changed.
        assert "command: old" not in result
        assert _yaml.load(result) == doc

    def test_replacement_keeps_following_top_level_key(self) -> None:
        original = "before: 1\n\nmcp_servers:\n  sofer:\n    command: old\n\nafter: 2\n"
        doc = {"before": 1, "mcp_servers": {"sofer": _entry()}, "after": 2}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert result.startswith("before: 1\n\n")
        assert result.endswith("\n\nafter: 2\n")
        assert _yaml.load(result) == doc


class TestSpliceInsert:
    def test_absent_key_appends_fresh_block(self) -> None:
        original = "# cfg\nother: 1\n"
        doc = {"other": 1, "mcp_servers": {"sofer": _entry()}}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert result.startswith("# cfg\nother: 1\n\n")
        assert "mcp_servers:\n  sofer:\n" in result
        assert _yaml.load(result) == doc

    def test_absent_name_appends_to_existing_mapping(self) -> None:
        original = "mcp_servers:\n  other:\n    command: other-mcp\n"
        doc = {
            "mcp_servers": {
                "other": {"command": "other-mcp"},
                "sofer": _entry(),
            }
        }

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert "  other:\n    command: other-mcp\n" in result
        assert result.index("other:") < result.index("sofer:")
        assert _yaml.load(result) == doc

    def test_absent_key_on_comment_only_appends(self) -> None:
        original = "# only comments\n"
        doc = {"mcp_servers": {"sofer": _entry()}}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert result.startswith("# only comments\n\n")
        assert _yaml.load(result) == doc

    def test_absent_key_on_empty_text_appends(self) -> None:
        doc = {"mcp_servers": {"sofer": _entry()}}

        result = _yaml.splice_entry("", "mcp_servers", "sofer", doc)

        assert result.startswith("mcp_servers:\n")
        assert _yaml.load(result) == doc


class TestSpliceRemove:
    def test_removing_last_entry_drops_whole_block(self) -> None:
        original = "mcp_servers:\n  sofer:\n    command: sofer-mcp\n    cwd: /proj\n"

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", {})

        assert "mcp_servers" not in result
        assert "sofer" not in result
        assert result.strip() == ""

    def test_removing_one_of_two_keeps_sibling_verbatim(self) -> None:
        original = (
            "mcp_servers:\n"
            "  sofer:\n"
            "    command: sofer-mcp\n"
            "  other:\n"
            "    command: other-mcp\n"
            "    cwd: /other\n"
        )
        doc = {"mcp_servers": {"other": {"command": "other-mcp", "cwd": "/other"}}}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert "  other:\n    command: other-mcp\n    cwd: /other\n" in result
        assert "sofer" not in result
        assert _yaml.load(result) == doc

    def test_removing_absent_entry_is_noop(self) -> None:
        original = "mcp_servers:\n  other:\n    command: other-mcp\n"
        doc = {"mcp_servers": {"other": {"command": "other-mcp"}}}

        assert _yaml.splice_entry(original, "mcp_servers", "sofer", doc) == original

    def test_removing_flow_key_drops_block(self) -> None:
        assert _yaml.splice_entry("mcp_servers: {}\n", "mcp_servers", "sofer", {}) == ""


class TestSpliceFlowStyle:
    def test_empty_flow_mapping_rendered_block(self) -> None:
        original = "mcp_servers: {}\n"
        doc = {"mcp_servers": {"sofer": _entry()}}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert result.startswith("mcp_servers:\n")
        assert "{}" not in result
        assert _yaml.load(result) == doc

    def test_replaces_block_sequence_entry(self) -> None:
        original = "mcp_servers:\n  sofer:\n    - a\n    - b\n"
        doc = {"mcp_servers": {"sofer": _entry()}}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert "- a" not in result
        assert _yaml.load(result) == doc

    def test_populated_flow_mapping_merged_in_block_style(self) -> None:
        original = "mcp_servers: {time: {command: x}}\n"
        doc = {"mcp_servers": {"time": {"command": "x"}, "sofer": _entry()}}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert result.splitlines()[0] == "mcp_servers:"
        assert "mcp_servers: {" not in result
        assert _yaml.load(result) == doc


class TestSpliceNonMappingKey:
    """A block ``key`` whose value is not a mapping must not eat the next line."""

    def test_block_sequence_keeps_next_top_level_key(self) -> None:
        original = "mcp_servers:\n  - a\n  - b\nother: 1\n"
        doc = {"mcp_servers": {"sofer": _entry()}, "other": 1}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert result.endswith("other: 1\n")
        assert "  - a" not in result
        assert _yaml.load(result) == doc

    def test_block_sequence_at_eof_without_trailing_newline(self) -> None:
        original = "mcp_servers:\n  - a\n  - b"
        doc = {"mcp_servers": {"sofer": _entry()}}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert result.endswith("\n")
        assert "  - a" not in result
        assert _yaml.load(result) == doc

    def test_block_sequence_keeps_following_nested_block(self) -> None:
        original = "mcp_servers:\n  - a\n  - b\nother:\n  nested:\n    command: keep\n"
        doc = {
            "mcp_servers": {"sofer": _entry()},
            "other": {"nested": {"command": "keep"}},
        }

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert "other:\n  nested:\n    command: keep\n" in result
        assert "  - a" not in result
        assert _yaml.load(result) == doc


class TestStringRoundTrip:
    def test_env_reference_and_windows_cwd_survive(self) -> None:
        windows_cwd = r"C:\Users\a\data"
        doc = {"mcp_servers": {"sofer": _entry(cwd=windows_cwd)}}

        result = _yaml.splice_entry("# windows user\n", "mcp_servers", "sofer", doc)

        loaded = _yaml.load(result)
        assert loaded == doc
        assert loaded["mcp_servers"]["sofer"]["env"]["HF_TOKEN"] == "${HF_TOKEN}"
        assert loaded["mcp_servers"]["sofer"]["cwd"] == windows_cwd

    def test_dump_load_keeps_reference_string(self) -> None:
        doc = {"mcp_servers": {"sofer": _entry()}}

        text = _yaml.dump(doc)

        assert "${HF_TOKEN}" in text
        assert _yaml.load(text) == doc


class TestLineEndings:
    """Splicing must preserve the document's ``\\n`` vs ``\\r\\n`` convention."""

    def test_splice_crlf_keeps_crlf_everywhere(self) -> None:
        original = (
            "# lead\r\n"
            "mcp_servers:\r\n"
            "  other:\r\n"
            "    command: other\r\n"
            "  sofer:\r\n"
            "    command: old\r\n"
            "other: 1\r\n"
        )
        doc = {
            "mcp_servers": {
                "other": {"command": "other"},
                "sofer": _entry(),
            },
            "other": 1,
        }

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert "# lead\r\n" in result
        assert result.endswith("other: 1\r\n")
        assert "  sofer:\r\n    command: sofer-mcp\r\n" in result
        # No bare LF anywhere: every line break is CRLF.
        assert "\n" not in result.replace("\r\n", "")
        assert _yaml.load(result) == doc

    def test_splice_lf_has_no_carriage_return(self) -> None:
        original = "mcp_servers:\n  sofer:\n    command: old\n"
        doc = {"mcp_servers": {"sofer": _entry()}}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert "\r" not in result
        assert _yaml.load(result) == doc

    def test_append_crlf_uses_crlf_separator(self) -> None:
        original = "# cfg\r\nother: 1\r\n"
        doc = {"other": 1, "mcp_servers": {"sofer": _entry()}}

        result = _yaml.splice_entry(original, "mcp_servers", "sofer", doc)

        assert "# cfg\r\nother: 1\r\n\r\nmcp_servers:\r\n" in result
        assert "\n" not in result.replace("\r\n", "")
        assert _yaml.load(result) == doc

    def test_dump_ends_with_single_lf(self) -> None:
        text = _yaml.dump({"a": 1})

        assert text.endswith("\n")
        assert not text.endswith("\r\n")
        assert "\r" not in text
