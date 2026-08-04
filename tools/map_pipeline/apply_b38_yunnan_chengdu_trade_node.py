#!/usr/bin/env python3
"""Place every modern-Yunnan province exclusively in the Chengdu trade node."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
PATH = MOD / "common/tradenodes/00_tradenodes.txt"
MARKER = "B38 Yunnan Chengdu trade-node consistency"

YUNNAN = {
    660, 661, 662, 663, 675, 2165, 2166, 2167,
    5224, 5225, 5226, 5227, 5228, 5229,
    5230, 5231, 5232, 5233, 5234, 5235, 5236, 5237, 5238, 5239,
    5240, 5241,
}


def block_bounds(text: str, key: str, start_at: int = 0) -> tuple[int, int]:
    match = re.search(rf"(?m)^[ \t]*{re.escape(key)}[ \t]*=[ \t]*\{{", text[start_at:])
    if not match:
        raise ValueError(f"Missing block: {key}")
    start = start_at + match.start()
    brace = text.find("{", start)
    depth = 0
    for index in range(brace, len(text)):
        depth += (text[index] == "{") - (text[index] == "}")
        if depth == 0:
            return start, index + 1
    raise ValueError(f"Unclosed block: {key}")


def remove_ids(body: str) -> str:
    pattern = re.compile(r"(?<!\d)(?:" + "|".join(map(str, sorted(YUNNAN, reverse=True))) + r")(?!\d)")
    output = []
    for line in body.splitlines():
        if f"# {MARKER}" in line:
            continue
        code, separator, comment = line.partition("#")
        indent = code[:len(code) - len(code.lstrip(" \t"))]
        content = pattern.sub("", code[len(indent):])
        code = indent + re.sub(r"[ \t]{2,}", " ", content).rstrip()
        if not code.strip() and separator and "Yunnan" in comment:
            continue
        line = code + ((" #" + comment) if separator else "")
        if line.strip():
            output.append(line)
    return "\n".join(output)


def update_node(text: str, node: str, add: bool) -> str:
    start, end = block_bounds(text, node)
    block = text[start:end]
    nested_start, nested_end = block_bounds(block, "members")
    open_brace = block.find("{", nested_start)
    close_brace = nested_end - 1
    body = remove_ids(block[open_brace + 1:close_brace]).rstrip()
    if add:
        body += "\n        " + " ".join(map(str, sorted(YUNNAN))) + f" # {MARKER}"
    body = "\n" + body + "\n    "
    block = block[:open_brace + 1] + body + block[close_brace:]
    return text[:start] + block + text[end:]


def node_names(text: str) -> list[str]:
    return re.findall(r"(?m)^([a-z0-9_]+)\s*=\s*\{", text)


def member_ids(text: str, node: str) -> set[int]:
    start, end = block_bounds(text, node)
    block = text[start:end]
    nested_start, nested_end = block_bounds(block, "members")
    body = re.sub(r"#.*", "", block[nested_start:nested_end])
    return {int(value) for value in re.findall(r"\b\d+\b", body)}


def verify(text: str) -> None:
    nodes = node_names(text)
    owners = {pid: [node for node in nodes if pid in member_ids(text, node)] for pid in YUNNAN}
    bad = {pid: values for pid, values in owners.items() if values != ["chengdu"]}
    if bad:
        raise ValueError(f"Yunnan trade-node owners are not exclusively Chengdu: {bad}")


def main() -> None:
    text = PATH.read_text(encoding="cp1252", errors="strict")
    nodes = node_names(text)
    # Only touch nodes that currently contain Yunnan members. Work from the end
    # so replacing one block cannot invalidate another block's offsets.
    affected = [node for node in nodes if YUNNAN & member_ids(text, node)]
    if "chengdu" not in affected:
        affected.append("chengdu")
    for node in reversed(affected):
        text = update_node(text, node, node == "chengdu")
    verify(text)
    PATH.write_text(text, encoding="cp1252")
    print(f"{MARKER}; PROVINCES:{len(YUNNAN)}; NODE:chengdu")


if __name__ == "__main__":
    main()
