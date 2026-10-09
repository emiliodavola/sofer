"""YAML parsing and surgical single-entry editing for MCP config files.

Private helper module in the ``_toml`` / ``_csv_reader`` family: it backs the
``fmt == "yaml"`` branch of :mod:`sofer.mcp_registration`. The writer is
*surgical* -- it re-renders only the ``<key>.<name>`` entry that changed and
copies every other line of the pre-write document verbatim -- so comments, key
order and indentation elsewhere survive an ``mcp add`` / ``mcp remove``.

:func:`splice_entry` locates the entry's line span from :func:`yaml.compose`
node marks rather than from regex heuristics over indentation, so quoting style
and the indentation of untouched lines cannot be misread. Two bounded cases
rewrite a whole ``key`` block instead of a single entry: a flow-style ``key``
mapping (``key: {}`` or ``key: {a: {b: c}}``) is re-rendered in block style,
and a ``key`` whose value is not a mapping at all is replaced wholesale.
Comments *inside* those rewritten blocks are not preserved; comments and
formatting everywhere else still are.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import yaml
from yaml.error import Mark
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

_YAML_INDENT = 2
"""Nesting width for :func:`yaml.safe_dump` block output."""

_YAML_WIDTH = 4096
"""Line width passed to :func:`yaml.safe_dump` so scalars are never wrapped."""


def load(text: str) -> dict[str, Any]:
    """Parse *text* as a YAML mapping.

    An empty or comment-only document parses as ``{}``: Hermes itself creates
    an empty ``config.yaml`` on first run, so that must not be an error.

    Args:
        text: Full YAML document text.

    Returns:
        The parsed top-level mapping.

    Raises:
        ValueError: When the document's root is not a mapping (for example a
            sequence or a bare scalar). The message names the expected shape.
        yaml.YAMLError: When *text* is not valid YAML.
    """
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(
            "YAML document is not a mapping: expected a top-level mapping of "
            f"config keys, got {type(data).__name__}"
        )
    return data


def dump(doc: dict[str, Any]) -> str:
    """Render *doc* as a full block-style YAML document.

    Used only when there is no pre-write text to splice into. Insertion order
    is preserved (``sort_keys=False``), non-ASCII is emitted literally and the
    result ends with a trailing newline.

    Args:
        doc: Document mapping to render.

    Returns:
        The rendered document text.
    """
    return _render(doc)


def splice_entry(text: str, key: str, name: str, doc: dict[str, Any]) -> str:
    """Return *text* with the *name* entry of the top-level *key* mapping updated.

    The desired outcome is read from *doc*: when ``doc[key][name]`` exists the
    entry is replaced (or inserted), and when it is absent the entry is
    removed. Only the entry's own lines are re-rendered; every other line of
    *text* -- comments, key order, indentation, sibling entries -- is copied
    verbatim.

    Args:
        text: Pre-write YAML document text.
        key: Top-level mapping that holds the entries (for example
            ``"mcp_servers"``).
        name: Entry name to update (for example ``"sofer"``).
        doc: Full merged document the result must parse to.

    Returns:
        The updated document text.
    """
    target = doc.get(key)
    servers: dict[str, Any] = target if isinstance(target, dict) else {}
    entry_present = name in servers

    ending = _line_ending(text)
    lines = text.splitlines(keepends=True)
    located = _find_child(yaml.compose(text), key)

    if located is None:
        if not entry_present:
            return text
        block = _with_ending(_render({key: {name: servers[name]}}), ending)
        return _append_block(text, block, ending)

    key_node, value_node = located
    if not isinstance(value_node, MappingNode) or value_node.flow_style:
        return _replace_key_block(lines, key_node, value_node, key, doc, ending)

    name_nodes = _find_child(value_node, name)
    if entry_present:
        if name_nodes is None:
            return _insert_entry(lines, value_node, name, servers[name], ending)
        name_key, name_value = name_nodes
        return _replace_entry(lines, name_key, name_value, name, servers[name], ending)

    if name_nodes is None:
        return text
    name_key, name_value = name_nodes
    if key in doc and servers:
        return _remove_entry_only(lines, name_key, name_value)
    return _remove_key_block(lines, key_node, value_node)


def _line_ending(text: str) -> str:
    """Return the line ending to render edited blocks with.

    A document that uses CRLF anywhere keeps CRLF; otherwise (including a
    fresh document with no line breaks yet) the render uses LF. Untouched
    lines are copied verbatim regardless, so this only governs the lines the
    splice itself produces.
    """
    return "\r\n" if "\r\n" in text else "\n"


def _with_ending(block: str, ending: str) -> str:
    """Return *block* (rendered with LF) re-joined with *ending*."""
    return block if ending == "\n" else block.replace("\n", ending)


def _render(mapping: Mapping[str, Any]) -> str:
    """Render *mapping* as block-style YAML with a trailing newline."""
    return yaml.safe_dump(
        dict(mapping),
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        indent=_YAML_INDENT,
        width=_YAML_WIDTH,
    )


def _find_child(node: Node | None, name: str) -> tuple[Node, Node] | None:
    """Return the ``(key, value)`` node pair named *name*, or ``None``."""
    if not isinstance(node, MappingNode):
        return None
    for child_key, child_value in node.value:
        if isinstance(child_key, ScalarNode) and child_key.value == name:
            return child_key, child_value
    return None


def _content_end(node: Node) -> Mark:
    """Return the end mark of *node*'s last actual content.

    A block mapping's own ``end_mark`` points at the *next* token (a sibling
    key, the next top-level key, or EOF), which can sit past blank lines. This
    descends to the deepest last scalar so the returned mark is the true end
    of the entry's own text.
    """
    if isinstance(node, MappingNode) and not node.flow_style:
        return _content_end(node.value[-1][1])
    if isinstance(node, SequenceNode) and not node.flow_style:
        return _content_end(node.value[-1])
    return node.end_mark


def _indent_block(text: str, indent: int) -> str:
    """Prefix every non-blank line of *text* with *indent* spaces."""
    prefix = " " * indent
    return "".join(
        (prefix + line) if line.strip() else line for line in text.splitlines(keepends=True)
    )


def _entry_block(name: str, entry: Any, indent: int, ending: str) -> list[str]:
    """Render ``{name: entry}`` as block lines indented by *indent* spaces."""
    block = _with_ending(_render({name: entry}), ending)
    return _indent_block(block, indent).splitlines(keepends=True)


def _replace_entry(
    lines: list[str], name_key: Node, name_value: Node, name: str, entry: Any, ending: str
) -> str:
    """Replace the existing *name* entry's own lines; return the new text."""
    start = name_key.start_mark.line
    end = _content_end(name_value).line + 1
    block = _entry_block(name, entry, name_key.start_mark.column, ending)
    return "".join(lines[:start] + block + lines[end:])


def _insert_entry(lines: list[str], value_node: Node, name: str, entry: Any, ending: str) -> str:
    """Append a new *name* entry to the *value_node* block mapping."""
    indent = value_node.value[0][0].start_mark.column
    at = _content_end(value_node).line + 1
    block = _entry_block(name, entry, indent, ending)
    return "".join(lines[:at] + block + lines[at:])


def _remove_entry_only(lines: list[str], name_key: Node, name_value: Node) -> str:
    """Delete the *name* entry's own lines, keeping the surrounding block."""
    start = name_key.start_mark.line
    end = _content_end(name_value).line + 1
    return "".join(lines[:start] + lines[end:])


def _remove_key_block(lines: list[str], key_node: Node, value_node: Node) -> str:
    """Delete the whole top-level *key* block (its mapping became empty)."""
    start = key_node.start_mark.line
    end = _content_end(value_node).line + 1
    return "".join(lines[:start] + lines[end:])


def _replace_key_block(
    lines: list[str], key_node: Node, value_node: Node, key: str, doc: dict[str, Any], ending: str
) -> str:
    """Re-render a flow-style (or non-mapping) *key* block in block style.

    The span end comes from :func:`_content_end`, not the node's own
    ``end_mark``: a block sequence's ``end_mark`` points at the following
    top-level token, so ``end_mark.line + 1`` would delete that line.
    """
    start = key_node.start_mark.line
    end = _content_end(value_node).line + 1
    target = doc.get(key)
    if isinstance(target, dict) and target:
        replacement = _with_ending(_render({key: target}), ending).splitlines(keepends=True)
    else:
        replacement = []
    return "".join(lines[:start] + replacement + lines[end:])


def _append_block(text: str, block: str, ending: str) -> str:
    """Append *block* at end of file, separated by one blank line."""
    if not text.strip():
        return block
    body = text.rstrip("\r\n")
    return body + ending + ending + block
