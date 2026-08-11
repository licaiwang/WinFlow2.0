from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

_KEY_VALUE_RE = re.compile(r"^([^:#]+?)\s*:\s*(.*)$")
_LIST_ITEM_RE = re.compile(r"^-\s*(.*)$")


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for idx, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:idx].rstrip()
    return line.rstrip()


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if text == "":
        return None
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    lower = text.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in {"null", "none", "~"}:
        return None
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text)
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\.\d+)", text):
        return float(text)
    return text


def _split_indent(line: str) -> Tuple[int, str]:
    expanded = line.expandtabs(2)
    stripped = expanded.lstrip(" ")
    return len(expanded) - len(stripped), stripped


def _merge_mapping_list(items: List[Any]) -> Any:
    """Collapse ``[{K:V}, ...]`` into ``{K:V, ...}`` when every item is a 1-key map."""
    if not items:
        return items
    merged: Dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict) or len(item) != 1:
            return items
        key, value = next(iter(item.items()))
        merged[key] = value
    return merged


def parse_yml(path: Union[str, Path]) -> Dict[str, Any]:
    """Parse a simplified YAML-style config file into a dict."""
    path = Path(path)
    if not path.exists():
        return {}

    root: Dict[str, Any] = {}
    # Stack of (indent, container) where container is dict or list.
    stack: List[Tuple[int, Any]] = [(-1, root)]

    with path.open(encoding="utf-8") as fp:
        for lineno, raw_line in enumerate(fp, start=1):
            line = _strip_comment(raw_line.rstrip("\n"))
            if not line.strip():
                continue

            indent, content = _split_indent(line)

            while len(stack) > 1 and indent <= stack[-1][0]:
                finished = stack.pop()[1]
                if isinstance(finished, list):
                    parent = stack[-1][1]
                    if isinstance(parent, dict):
                        for key, value in list(parent.items()):
                            if value is finished:
                                parent[key] = _merge_mapping_list(finished)
                                break

            container = stack[-1][1]

            list_match = _LIST_ITEM_RE.match(content)
            if list_match:
                if not isinstance(container, list):
                    raise ValueError(
                        f"{path}:{lineno}: list item outside a list context: {content!r}"
                    )
                item_raw = list_match.group(1).strip()
                if not item_raw:
                    nested: Dict[str, Any] = {}
                    container.append(nested)
                    stack.append((indent, nested))
                    continue
                kv = _KEY_VALUE_RE.match(item_raw)
                if kv:
                    key = kv.group(1).strip()
                    value_raw = kv.group(2).strip()
                    if value_raw == "":
                        nested = {}
                        container.append({key: nested})
                        stack.append((indent, nested))
                    else:
                        container.append({key: _parse_scalar(value_raw)})
                else:
                    container.append(_parse_scalar(item_raw))
                continue

            kv = _KEY_VALUE_RE.match(content)
            if not kv:
                raise ValueError(f"{path}:{lineno}: expected key: value, got {content!r}")

            key = kv.group(1).strip()
            value_raw = kv.group(2).strip()

            if not isinstance(container, dict):
                raise ValueError(
                    f"{path}:{lineno}: mapping entry outside a mapping context: {content!r}"
                )

            if value_raw == "":
                placeholder: List[Any] = []
                container[key] = placeholder
                stack.append((indent, placeholder))
                continue

            container[key] = _parse_scalar(value_raw)

    while len(stack) > 1:
        finished = stack.pop()[1]
        if isinstance(finished, list):
            parent = stack[-1][1]
            if isinstance(parent, dict):
                for key, value in list(parent.items()):
                    if value is finished:
                        parent[key] = _merge_mapping_list(finished)
                        break

    return root
