"""A tiny YAML subset loader/dumper used for tests.

This module provides ``safe_load`` and ``safe_dump`` helpers that support the
very small YAML surface area exercised in the unit tests.  It intentionally does
not aim to be feature complete; only mappings, sequences and scalar values
(strings, ints, floats, booleans and null) are implemented.  The goal is to keep
our test environment self contained without depending on PyYAML.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Any, Tuple


def safe_load(stream: Any) -> Any:
    if hasattr(stream, "read"):
        text = stream.read()
    else:
        text = str(stream)
    lines = _prepare_lines(text)
    if not lines:
        return {}
    value, _ = _parse_mapping(lines, 0, 0)
    return value


def safe_dump(data: Any, stream: Any | None = None, sort_keys: bool = True) -> str:
    if sort_keys and isinstance(data, dict):
        items = {k: data[k] for k in sorted(data)}
    else:
        items = data
    buf = StringIO()
    _write_value(items, buf, 0)
    output = buf.getvalue()
    if stream is not None:
        stream.write(output)
        return ""
    return output


@dataclass
class _Line:
    indent: int
    content: str


def _prepare_lines(text: str) -> list[_Line]:
    raw_lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        raw_lines.append((indent, raw.rstrip()))
    if not raw_lines:
        return []
    base_indent = min(indent for indent, _ in raw_lines)
    lines: list[_Line] = []
    for indent, raw in raw_lines:
        normalized_indent = indent - base_indent
        content = raw[base_indent:]
        lines.append(_Line(indent=normalized_indent, content=content))
    return lines


def _parse_mapping(lines: list[_Line], index: int, indent: int) -> Tuple[dict, int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise ValueError(f"Invalid indentation at line: {line.content}")
        key, value = _split_key_value(line.content)
        index += 1
        if value in ("|", ">"):
            block, index = _parse_block_scalar(lines, index, indent + 2)
            result[key] = block
        elif value is None:
            if index < len(lines):
                next_line = lines[index]
                if next_line.indent == indent + 2 and next_line.content.strip().startswith("- "):
                    seq, index = _parse_sequence(lines, index, indent + 2)
                    result[key] = seq
                    continue
            nested, index = _parse_mapping(lines, index, indent + 2)
            result[key] = nested
        else:
            result[key] = _parse_scalar(value)
    return result, index


def _parse_sequence(lines: list[_Line], index: int, indent: int) -> Tuple[list, int]:
    items: list[Any] = []
    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise ValueError(f"Invalid indentation at line: {line.content}")
        content = line.content.strip()
        if not content.startswith("- "):
            break
        item = content[2:].strip()
        index += 1
        if not item:
            nested, index = _parse_mapping(lines, index, indent + 2)
            items.append(nested)
        elif ":" in item:
            key, _, value = item.partition(":")
            mapping = {key.strip(): _parse_scalar(value.strip())}
            if index < len(lines) and lines[index].indent >= indent + 2:
                nested, index = _parse_mapping(lines, index, indent + 2)
                if isinstance(nested, dict):
                    mapping.update(nested)
            items.append(mapping)
        else:
            items.append(_parse_scalar(item))
    return items, index


def _split_key_value(content: str) -> Tuple[str, str | None]:
    stripped = content.strip()
    if ":" not in stripped:
        raise ValueError(f"Expected ':' in line: {content}")
    key, _, rest = stripped.partition(":")
    key = key.strip()
    rest = rest.strip()
    if rest == "":
        return key, None
    return key, rest


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        parts = [part.strip() for part in inner.split(",")]
        return [_parse_scalar_token(part) for part in parts]
    return _parse_scalar_token(value)


def _parse_block_scalar(lines: list[_Line], index: int, indent: int) -> Tuple[str, int]:
    chunks: list[str] = []
    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        # Remove indent spaces relative to block indent
        content = line.content
        relative = content[indent:] if content.startswith(" " * indent) else content.lstrip()
        chunks.append(relative)
        index += 1
    return "\n".join(chunks), index


def _parse_scalar_token(token: str) -> Any:
    lowered = token.lower()
    if lowered == "null":
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if token.startswith(("'", '"')) and token.endswith(("'", '"')):
        return token[1:-1]
    try:
        if "." in token:
            return float(token)
        return int(token)
    except ValueError:
        return token


def _write_value(value: Any, buf: StringIO, indent: int) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        for i, (key, val) in enumerate(value.items()):
            if isinstance(val, (dict, list)):
                buf.write(f"{prefix}{key}:\n")
                _write_value(val, buf, indent + 2)
            else:
                buf.write(f"{prefix}{key}: {_format_scalar(val)}\n")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                buf.write(f"{prefix}- \n")
                _write_value(item, buf, indent + 2)
            else:
                buf.write(f"{prefix}- {_format_scalar(item)}\n")
    else:
        buf.write(f"{prefix}{_format_scalar(value)}\n")


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\"", "\\\"")
        return f'"{escaped}"'
    raise TypeError(f"Unsupported type for dumping: {type(value)!r}")
