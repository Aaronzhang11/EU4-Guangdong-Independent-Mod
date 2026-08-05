#!/usr/bin/env python3
"""Minimally align Liuhe/Jiangning visual position slots with provinces.bmp."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POSITIONS = ROOT / "guangdong_independent_practice/map/positions.txt"
MARKER = "B39 Jiangning position alignment"

# Land slots: city, unit, province text, trade, battle.
# Port slots remain on the Lower Yangtze river province.
TARGETS = {
    1821: {"land": (4660.0, 1179.0), "port": (4654.0, 1185.0)},  # Liuhe
    5056: {"land": (4652.0, 1186.0), "port": (4657.0, 1180.0)},  # Jiangning/Nanjing
}


def block_bounds(text: str, province_id: int) -> tuple[int, int]:
    match = re.search(rf"(?m)^[ \t]*{province_id}[ \t]*=[ \t]*\{{", text)
    if not match:
        raise ValueError(f"Missing positions block {province_id}")
    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        depth += (text[index] == "{") - (text[index] == "}")
        if depth == 0:
            return match.start(), index + 1
    raise ValueError(f"Unclosed positions block {province_id}")


def position_pairs(block: str) -> list[tuple[float, float]]:
    match = re.search(r"(?ms)\bposition\s*=\s*\{(.*?)\}", block)
    if not match:
        raise ValueError("Missing position array")
    values = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", match.group(1))]
    if len(values) != 14:
        raise ValueError(f"Expected 14 position values, found {len(values)}")
    return list(zip(values[0::2], values[1::2]))


def replace_positions(block: str, pairs: list[tuple[float, float]]) -> str:
    values = " ".join(f"{value:.3f}" for pair in pairs for value in pair)
    replacement = "position={\n        " + values + "\n    }"
    output, count = re.subn(r"(?ms)\bposition\s*=\s*\{.*?\}", replacement, block, count=1)
    if count != 1:
        raise ValueError("Could not replace position array")
    return output


def apply_target(text: str, province_id: int) -> str:
    start, end = block_bounds(text, province_id)
    block = text[start:end]
    pairs = position_pairs(block)
    target = TARGETS[province_id]
    for slot in (0, 1, 2, 4, 5):
        pairs[slot] = target["land"]
    pairs[3] = target["port"]
    block = replace_positions(block, pairs)
    return text[:start] + block + text[end:]


def main() -> None:
    text = POSITIONS.read_text(encoding="cp1252", errors="strict")
    for province_id in TARGETS:
        text = apply_target(text, province_id)
    POSITIONS.write_text(text, encoding="cp1252")
    print(f"{MARKER}; PROVINCES:{','.join(map(str, TARGETS))}; FIELDS:position-only")


if __name__ == "__main__":
    main()
