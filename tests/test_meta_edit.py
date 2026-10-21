"""Unit tests for the surgical ``[meta]`` editor (issue #323).

Covers the key registry against the model's own read list, the three locator
questions the regex cannot answer (a ``[meta]`` header, an assignment and a
value end inside an open multi-line value), the single-line value contract, the
never-write-unparseable-TEXT guarantee, and the file-level idempotency and
refusal behaviour of :func:`sofer.meta_edit.set_meta`.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from sofer import _atomic, _toml, meta_edit
from sofer.cli import _INIT_TEMPLATE
from sofer.meta_edit import META_KEYS, MetaEditError, apply_meta_edit
from sofer.model import DatasetConfig

_MINIMAL = '[dataset]\nname = "x"\nrepo_id = "u/x"\n'

_VALUE_BY_KIND: dict[str, object] = {"text": "value", "list": ["a", "b"], "flag": True}


def _template() -> str:
    """Return a rendered ``sofer init`` template — comments included."""
    return _INIT_TEMPLATE.format(name="demo", user="someone")


def _without_meta_block(text: str) -> list[str]:
    """Return *text*'s lines with the ``[meta]`` block removed.

    Deliberately independent of ``meta_edit``'s own locators: it finds the
    header by literal match and ends the block at the next ``[``-prefixed line,
    which is what makes the "only the table changed" assertion meaningful.
    """
    lines = text.splitlines()
    start = lines.index("[meta]")
    end = next(index for index in range(start + 1, len(lines)) if lines[index].startswith("["))
    return lines[:start] + lines[end:]


def _parse(text: str) -> dict:
    """Parse *text* as TOML, asserting it is valid."""
    return _toml.loads(text)


class TestRegistry:
    """The registry is the settable surface, in both directions."""

    def test_every_registry_key_is_read_by_the_model(self, tmp_path: Path) -> None:
        """Forward guard: each registered key lands in its model attribute."""
        assert META_KEYS, "the registry cannot be empty"
        for key, kind in META_KEYS.items():
            value = _VALUE_BY_KIND[kind]
            literal = meta_edit.format_meta_value(kind, value)
            path = tmp_path / f"{key}.toml"
            path.write_text(f"{_MINIMAL}\n[meta]\n{key} = {literal}\n", encoding="utf-8")
            cfg = DatasetConfig.from_toml(path)
            assert getattr(cfg, key) == value, key

    def test_the_model_reads_no_key_the_registry_omits(self) -> None:
        """Reverse guard: a ``meta.get`` the registry misses could never be set."""
        source = inspect.getsource(DatasetConfig.from_toml)
        read = set(re.findall(r'meta\.get\("([a-z_]+)"', source))
        assert read == set(META_KEYS)

    def test_the_four_placeholder_keys_are_registered(self) -> None:
        """The four the #288 gate names are part of the surface (issue #323)."""
        assert {"description", "license", "source", "tags"} <= set(META_KEYS)

    def test_an_unknown_key_is_refused_and_names_the_known_ones(self) -> None:
        with pytest.raises(MetaEditError, match="unknown \\[meta\\] key 'nope'"):
            apply_meta_edit(_MINIMAL, {"nope": "x"})

    def test_a_value_of_the_wrong_kind_is_refused(self) -> None:
        with pytest.raises(MetaEditError, match="\\[meta\\] tags: expected a list of strings"):
            apply_meta_edit(_MINIMAL, {"tags": "not-a-list"})

    def test_a_flag_key_requires_a_boolean(self) -> None:
        with pytest.raises(MetaEditError, match="confidential: expected true or false"):
            apply_meta_edit(_MINIMAL, {"confidential": "yes"})


class TestFormatting:
    """Values are single-line TOML literals."""

    def test_text_is_a_basic_string_with_escaped_newlines(self) -> None:
        assert meta_edit.format_meta_value("text", "a\nb") == '"a\\nb"'

    def test_lists_are_inline_arrays(self) -> None:
        assert meta_edit.format_meta_value("list", ["a", "b"]) == '["a", "b"]'
        assert meta_edit.format_meta_value("list", []) == "[]"

    def test_unicode_is_written_literally(self) -> None:
        assert meta_edit.format_meta_value("text", "ñandú") == '"ñandú"'


class TestParseMetaValue:
    """The inverse reading for the one textual surface (CLI ``--set``)."""

    def test_text_is_verbatim_including_commas_and_equals(self) -> None:
        assert meta_edit.parse_meta_value("description", "a, b = c") == "a, b = c"

    def test_lists_split_on_commas_and_drop_empty_items(self) -> None:
        assert meta_edit.parse_meta_value("tags", "a, b") == ["a", "b"]
        assert meta_edit.parse_meta_value("tags", "") == []
        assert meta_edit.parse_meta_value("tags", "a,, b") == ["a", "b"]

    def test_flags_accept_the_two_spellings_case_insensitively(self) -> None:
        assert meta_edit.parse_meta_value("confidential", "TRUE") is True
        assert meta_edit.parse_meta_value("confidential", " false ") is False

    def test_a_bad_boolean_names_the_accepted_spellings(self) -> None:
        with pytest.raises(MetaEditError, match="expected 'true' or 'false', got 'yes'"):
            meta_edit.parse_meta_value("confidential", "yes")

    def test_an_unknown_key_is_refused(self) -> None:
        with pytest.raises(MetaEditError, match=r"unknown \[meta\] key 'nope'"):
            meta_edit.parse_meta_value("nope", "x")


class TestApplyMetaEdit:
    """The pure edit: only ``[meta]`` moves, and the result always parses."""

    def test_only_the_meta_block_changes(self) -> None:
        before = _template()
        after = apply_meta_edit(
            before,
            {
                "description": "Real description",
                "license": "MIT",
                "source": "Some org",
                "tags": ["a"],
            },
        )
        assert _without_meta_block(after) == _without_meta_block(before)
        meta = _parse(after)["meta"]
        assert meta["description"] == "Real description"
        assert meta["license"] == "MIT"
        assert meta["source"] == "Some org"
        assert meta["tags"] == ["a"]

    def test_the_comment_guidance_survives_the_edit(self) -> None:
        before = _template()
        after = apply_meta_edit(before, {"description": "x"})
        comments_before = [line for line in before.splitlines() if line.startswith("#")]
        comments_after = [line for line in after.splitlines() if line.startswith("#")]
        assert comments_after == comments_before

    def test_missing_keys_are_appended_inside_the_table(self) -> None:
        after = apply_meta_edit(_template(), {"curation_rationale": "por qué"})
        document = _parse(after)
        assert document["meta"]["curation_rationale"] == "por qué"
        # It landed in [meta], not in the last [[file]] entry.
        assert "curation_rationale" not in document["file"][-1]

    def test_an_empty_values_mapping_is_a_no_op(self) -> None:
        text = _template()
        assert apply_meta_edit(text, {}) == text

    def test_a_source_value_containing_a_prefix_is_written_as_given(self) -> None:
        after = apply_meta_edit(_template(), {"source": "TODO: but intentional"})
        assert _parse(after)["meta"]["source"] == "TODO: but intentional"

    def test_a_multiline_value_is_replaced_over_its_whole_range(self) -> None:
        text = f'{_MINIMAL}\n[meta]\ndescription = """\nlinea uno\nlinea dos\n"""\ntags = ["a"]\n'
        after = apply_meta_edit(text, {"description": "nuevo"})
        assert 'description = "nuevo"' in after
        assert "linea uno" not in after
        assert _parse(after)["meta"]["tags"] == ["a"]

    def test_a_meta_looking_line_inside_a_string_is_not_the_table(self) -> None:
        text = f'{_MINIMAL}\n[nota]\ntexto = """\n[meta]\n"""\n\n[meta]\ndescription = "viejo"\n'
        after = apply_meta_edit(text, {"description": "nuevo"})
        assert 'texto = """\n[meta]\n"""' in after
        assert _parse(after)["nota"]["texto"] == "[meta]\n"
        assert _parse(after)["meta"]["description"] == "nuevo"

    def test_an_assignment_line_inside_an_open_value_is_not_the_key(self) -> None:
        text = (
            f'{_MINIMAL}\n[meta]\nnotas = """\ndescription = "falso"\n"""\ndescription = "viejo"\n'
        )
        after = apply_meta_edit(text, {"description": "nuevo"})
        assert 'description = "falso"' in after
        assert _parse(after)["meta"]["notas"] == 'description = "falso"\n'
        assert _parse(after)["meta"]["description"] == "nuevo"

    def test_a_document_without_meta_gains_one_at_the_end(self) -> None:
        text = f'{_MINIMAL}\n[[file]]\nlocal = "raw/a.csv"\nremote = "a.csv"\n'
        after = apply_meta_edit(text, {"description": "d"})
        document = _parse(after)
        assert document["meta"]["description"] == "d"
        assert document["file"][0]["local"] == "raw/a.csv"

    def test_a_multiline_value_is_written_on_one_line(self) -> None:
        before = _template()
        after = apply_meta_edit(before, {"description": "uno\ndos"})
        assert len(after.splitlines()) == len(before.splitlines())
        assert _parse(after)["meta"]["description"] == "uno\ndos"

    def test_reapplying_the_same_values_is_byte_identical(self) -> None:
        once = apply_meta_edit(_template(), {"description": "x", "tags": ["a"]})
        twice = apply_meta_edit(once, {"description": "x", "tags": ["a"]})
        assert twice == once

    def test_a_no_op_edit_does_not_normalize_a_missing_trailing_newline(self) -> None:
        text = f'{_MINIMAL}\n[meta]\ndescription = "x"'
        assert apply_meta_edit(text, {"description": "x"}) == text

    def test_an_unparseable_document_is_refused(self) -> None:
        with pytest.raises(MetaEditError, match="not a valid TOML document"):
            apply_meta_edit("[meta\ndescription = ", {"description": "x"})

    def test_meta_declared_as_a_scalar_is_refused(self) -> None:
        text = f"meta = 5\n{_MINIMAL}"
        with pytest.raises(MetaEditError, match="'meta' is declared as int, not a table"):
            apply_meta_edit(text, {"description": "x"})

    def test_a_scalar_meta_inside_another_table_does_not_block_the_table(self) -> None:
        """``[dataset] meta = 5`` is an unrelated key, not our table."""
        text = f"{_MINIMAL}meta = 5\n"
        after = apply_meta_edit(text, {"description": "x"})
        assert _parse(after)["meta"]["description"] == "x"
        assert _parse(after)["dataset"]["meta"] == 5


class TestSetMeta:
    """The file-level API: atomic, idempotent, and total on refusal."""

    def _dataset(self, tmp_path: Path, text: str | None = None) -> Path:
        path = tmp_path / "dataset.toml"
        path.write_text(text if text is not None else _template(), encoding="utf-8")
        return path

    def test_it_writes_the_value_and_reports_the_key(self, tmp_path: Path) -> None:
        path = self._dataset(tmp_path)
        result = meta_edit.set_meta(path, {"description": "Real"})
        assert result.changed is True
        assert result.written == ("description",)
        assert result.unchanged == ()
        assert result.dry_run is False
        assert _parse(path.read_text(encoding="utf-8"))["meta"]["description"] == "Real"

    def test_a_second_call_with_the_same_values_writes_nothing(self, tmp_path: Path) -> None:
        path = self._dataset(tmp_path)
        meta_edit.set_meta(path, {"description": "Real"})
        first = path.read_bytes()
        result = meta_edit.set_meta(path, {"description": "Real"})
        assert result.changed is False
        assert result.written == ()
        assert result.unchanged == ("description",)
        assert path.read_bytes() == first

    def test_a_dry_run_reports_the_plan_and_writes_nothing(self, tmp_path: Path) -> None:
        path = self._dataset(tmp_path)
        before = path.read_bytes()
        result = meta_edit.set_meta(path, {"description": "Real"}, dry_run=True)
        assert result.changed is True
        assert result.dry_run is True
        assert result.text != before.decode("utf-8")
        assert path.read_bytes() == before

    def test_mixed_written_and_unchanged_keys_are_both_reported(self, tmp_path: Path) -> None:
        path = self._dataset(tmp_path)
        meta_edit.set_meta(path, {"description": "Real", "license": "MIT"})
        result = meta_edit.set_meta(path, {"description": "Real", "license": "Apache-2.0"})
        assert result.written == ("license",)
        assert result.unchanged == ("description",)

    def test_a_refusal_leaves_the_file_byte_identical(self, tmp_path: Path) -> None:
        path = self._dataset(tmp_path)
        before = path.read_bytes()
        with pytest.raises(MetaEditError):
            meta_edit.set_meta(path, {"unknown_key": "x"})
        assert path.read_bytes() == before

    def test_an_unreadable_file_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MetaEditError, match="cannot read"):
            meta_edit.set_meta(tmp_path / "missing.toml", {"description": "x"})

    def test_a_failed_replace_removes_the_temporary_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = self._dataset(tmp_path)
        before = path.read_bytes()

        def _boom(*args: object, **kwargs: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(_atomic.os, "replace", _boom)
        with pytest.raises(MetaEditError, match="cannot write"):
            meta_edit.set_meta(path, {"description": "Real"})
        assert path.read_bytes() == before
        assert not list(tmp_path.glob("*.tmp"))

    def test_a_preexisting_tmp_sibling_survives_a_real_write(self, tmp_path: Path) -> None:
        """Issue #365: the writer owns a unique temp file, not `<dest>.tmp`."""
        path = self._dataset(tmp_path)
        sibling = path.with_name(path.name + ".tmp")
        sibling.write_bytes(b"pre-existing staging file")

        meta_edit.set_meta(path, {"description": "Real"})

        assert sibling.read_bytes() == b"pre-existing staging file"
        assert meta_edit.read_meta(path)["description"] == "Real"

    def test_read_meta_returns_the_table_or_an_empty_mapping(self, tmp_path: Path) -> None:
        assert meta_edit.read_meta(self._dataset(tmp_path))["license"].startswith("TODO")
        bare = tmp_path / "bare.toml"
        bare.write_text(_MINIMAL, encoding="utf-8")
        assert meta_edit.read_meta(bare) == {}


class TestBuildPredatesWrite:
    """The informational note for a build tree older than the write (D7)."""

    def test_no_build_tree_means_no_note(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        path.write_text(f'{_MINIMAL}\n[meta]\ndescription = "x"\n', encoding="utf-8")
        cfg = DatasetConfig.from_toml(path)
        assert meta_edit.build_predates_write(cfg, path) is None

    def test_an_existing_build_tree_is_named_not_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        path.write_text(f'{_MINIMAL}\n[meta]\ndescription = "x"\n', encoding="utf-8")
        (tmp_path / "build").mkdir()
        cfg = DatasetConfig.from_toml(path)
        note = meta_edit.build_predates_write(cfg, path)
        assert note is not None
        assert "predates this write" in note
        assert "sofer_prepare" in note


class TestBytePreservation:
    """A real write touches the ``[meta]`` value and nothing else.

    Both cases here are the independent verifier's findings, and neither was
    covered before: the editor's own tests compared bytes only on the no-op and
    ``--dry-run`` paths, where no write happens at all. The first draft read and
    wrote through the universal-newline default, so on Windows an LF document
    came back all-CRLF (and on POSIX a CRLF document came back all-LF), and the
    trailing blank lines collapsed. Bytes are asserted with ``read_bytes`` so the
    test cannot be fooled by the same translation it is checking for.
    """

    @staticmethod
    def _write(path: Path, content: bytes) -> None:
        path.write_bytes(content)

    def test_a_real_write_preserves_crlf_and_every_other_byte(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        before = (
            b'# a comment\r\n[dataset]\r\nname = "d"\r\nrepo_id = "u/d"\r\n\r\n'
            b'[meta]\r\ndescription = "old"\r\ntags = ["a"]\r\n'
        )
        self._write(path, before)
        result = meta_edit.set_meta(path, {"description": "New"})
        assert result.changed is True
        assert path.read_bytes() == before.replace(b'"old"', b'"New"')

    def test_a_real_write_preserves_lf_on_any_platform(self, tmp_path: Path) -> None:
        """The Windows host is the one that would rewrite this file."""
        path = tmp_path / "dataset.toml"
        before = b'# c\n[dataset]\nname = "d"\nrepo_id = "u/d"\n\n[meta]\ndescription = "old"\n'
        self._write(path, before)
        meta_edit.set_meta(path, {"description": "New"})
        after = path.read_bytes()
        assert after == before.replace(b'"old"', b'"New"')
        assert b"\r\n" not in after

    def test_trailing_blank_lines_survive(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        before = b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n[meta]\ndescription = "old"\n\n\n'
        self._write(path, before)
        meta_edit.set_meta(path, {"description": "New"})
        assert path.read_bytes() == before.replace(b'"old"', b'"New"')

    def test_a_missing_trailing_newline_stays_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        before = b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n[meta]\ndescription = "old"'
        self._write(path, before)
        meta_edit.set_meta(path, {"description": "New"})
        assert path.read_bytes() == before.replace(b'"old"', b'"New"')

    def test_an_inserted_key_uses_the_document_line_ending(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        before = (
            b'[dataset]\r\nname = "d"\r\nrepo_id = "u/d"\r\n\r\n[meta]\r\ndescription = "old"\r\n'
        )
        self._write(path, before)
        meta_edit.set_meta(path, {"license": "MIT"})
        after = path.read_bytes()
        assert after.startswith(before)
        assert after.endswith(b'license = "MIT"\r\n')
        # Every LF is part of a CRLF, so the inserted line did not mix endings.
        assert after.count(b"\r\n") == after.count(b"\n")

    def test_an_inserted_key_terminates_an_unterminated_last_line(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        before = b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n[meta]\ndescription = "old"'
        self._write(path, before)
        meta_edit.set_meta(path, {"license": "MIT"})
        after = path.read_bytes()
        assert after == before + b'\nlicense = "MIT"\n'

    def test_a_quoted_key_is_replaced_in_its_canonical_form(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        before = b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n[meta]\n"description" = "old"\n'
        self._write(path, before)
        meta_edit.set_meta(path, {"description": "New"})
        assert path.read_bytes() == before.replace(b'"description" = "old"', b'description = "New"')

    def test_a_quoted_table_header_is_the_same_table(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        before = b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n["meta"]\ndescription = "old"\n'
        self._write(path, before)
        meta_edit.set_meta(path, {"description": "New"})
        assert path.read_bytes() == before.replace(b'"old"', b'"New"')


class TestValueEqualityDecides:
    """The editor writes a VALUE; it is not a formatter (second verifier round).

    Comparing the line's bytes made an equal value in another spelling look like
    a change: `changed: true` with `written: []`, a `"wrote: "` message, and a
    first run that rewrote the author's line — contradicting the promise that
    re-running with the values the file already holds writes nothing. Comparing
    the parsed value closes it, and the byte-level consequences of that decision
    (a value that ended the file stays unterminated) are pinned here too.
    """

    def test_an_equal_value_in_another_spelling_is_not_rewritten(self, tmp_path: Path) -> None:
        for spelling in (
            b'description = """New"""',
            b'"description" = "New"',
            b'description="New"',
            b"description  =  'New'",
        ):
            path = tmp_path / "dataset.toml"
            before = b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n[meta]\n' + spelling + b"\n"
            path.write_bytes(before)
            result = meta_edit.set_meta(path, {"description": "New"})
            assert result.changed is False, spelling
            assert result.written == (), spelling
            assert result.unchanged == ("description",), spelling
            assert path.read_bytes() == before, spelling

    def test_a_changed_value_is_still_written_in_the_canonical_form(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        before = b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n[meta]\ndescription = """old"""\n'
        path.write_bytes(before)
        result = meta_edit.set_meta(path, {"description": "New"})
        assert result.written == ("description",)
        assert path.read_bytes() == before.replace(b'"""old"""', b'"New"')

    def test_a_multiline_value_at_eof_keeps_the_missing_terminator(self, tmp_path: Path) -> None:
        path = tmp_path / "dataset.toml"
        before = b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n[meta]\ndescription = """\nline2"""'
        path.write_bytes(before)
        meta_edit.set_meta(path, {"description": "New"})
        assert path.read_bytes() == (
            b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n[meta]\ndescription = "New"'
        )

    def test_a_spaced_or_quoted_header_is_the_same_table(self, tmp_path: Path) -> None:
        for header in (b"[ meta ]", b'[ "meta" ]', b"[\tmeta\t]"):
            path = tmp_path / "dataset.toml"
            before = (
                b'[dataset]\nname = "d"\nrepo_id = "u/d"\n\n' + header + b'\ndescription = "old"\n'
            )
            path.write_bytes(before)
            meta_edit.set_meta(path, {"description": "New"})
            assert path.read_bytes() == before.replace(b'"old"', b'"New"'), header

    def test_a_dotted_or_inline_meta_table_is_refused_not_corrupted(self, tmp_path: Path) -> None:
        """Shapes the editor does not address: the refusal is total and named.

        Note the position: AFTER ``[dataset]`` the same lines are keys *of*
        ``[dataset]``, so the append is correct there and no refusal applies.
        """
        for before in (
            b'meta = { description = "old" }\n[dataset]\nname = "d"\nrepo_id = "u/d"\n',
            b'meta.description = "old"\n[dataset]\nname = "d"\nrepo_id = "u/d"\n',
            b'meta = {}\n[dataset]\nname = "d"\nrepo_id = "u/d"\n',
        ):
            path = tmp_path / "dataset.toml"
            path.write_bytes(before)
            with pytest.raises(MetaEditError, match="without a \\[meta\\] table header"):
                meta_edit.set_meta(path, {"description": "New"})
            assert path.read_bytes() == before

    def test_a_meta_key_of_another_table_is_not_our_table(self, tmp_path: Path) -> None:
        """``[dataset] meta = {...}`` is an unrelated key, not a declaration."""
        path = tmp_path / "dataset.toml"
        before = b'[dataset]\nname = "d"\nrepo_id = "u/d"\nmeta = { description = "no" }\n'
        path.write_bytes(before)
        meta_edit.set_meta(path, {"description": "New"})
        after = path.read_bytes()
        assert after.startswith(before)
        assert after.endswith(b'[meta]\ndescription = "New"\n')


# ── Posture authorization through the writer (#338) ───────────────────────────


class TestPostureAuthorizationOnWrite:
    """An explicit confidentiality opt-out must carry its reason, in one state."""

    def _toml(self, tmp_path: Path, meta_extra: str = "") -> Path:
        p = tmp_path / "ds.toml"
        p.write_text(
            '[dataset]\nname = "ds"\nrepo_id = "u/ds"\n\n[meta]\ndescription = "d"\n' + meta_extra,
            encoding="utf-8",
        )
        return p

    def test_confidential_false_alone_is_refused(self, tmp_path: Path) -> None:
        path = self._toml(tmp_path)
        with pytest.raises(MetaEditError, match="confidentiality_reason"):
            meta_edit.set_meta(path, {"confidential": False})
        assert "confidential" not in path.read_text(encoding="utf-8")

    def test_both_keys_in_one_call_are_accepted(self, tmp_path: Path) -> None:
        path = self._toml(tmp_path)
        meta_edit.set_meta(
            path, {"confidential": False, "confidentiality_reason": "public statistics"}
        )
        text = path.read_text(encoding="utf-8")
        assert "confidential = false" in text
        assert 'confidentiality_reason = "public statistics"' in text

    def test_an_existing_reason_satisfies_the_write(self, tmp_path: Path) -> None:
        path = self._toml(tmp_path, 'confidentiality_reason = "public statistics"\n')
        meta_edit.set_meta(path, {"confidential": False})
        assert "confidential = false" in path.read_text(encoding="utf-8")

    def test_clearing_the_reason_while_false_is_refused(self, tmp_path: Path) -> None:
        path = self._toml(tmp_path, 'confidential = false\nconfidentiality_reason = "x"\n')
        with pytest.raises(MetaEditError, match="confidentiality_reason"):
            meta_edit.set_meta(path, {"confidentiality_reason": ""})
        assert 'confidentiality_reason = "x"' in path.read_text(encoding="utf-8")

    def test_keeping_confidential_true_needs_no_reason(self, tmp_path: Path) -> None:
        path = self._toml(tmp_path)
        meta_edit.set_meta(path, {"confidential": True})
        assert "confidential = true" in path.read_text(encoding="utf-8")
