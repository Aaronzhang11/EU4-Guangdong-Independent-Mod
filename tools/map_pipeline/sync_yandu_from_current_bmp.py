#!/usr/bin/env python3
"""Recenter Yandu map objects after manual provinces.bmp edits."""

from collections import deque
from pathlib import Path
import re

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "guangdong_independent_practice/map"

PROVINCES = [
    (5113, "Changping", (36, 183, 73)),
    (5114, "Miyun", (210, 64, 142)),
    (1816, "Yan", (89, 177, 232)),
    (5115, "Tongzhou", (241, 116, 35)),
    (5116, "Zhuozhou", (132, 74, 218)),
    (695, "Hejian", (227, 142, 0)),
]


def safest_pixel(mask):
    """Return the land pixel furthest from the province boundary."""
    yy, xx = np.nonzero(mask)
    y0, y1 = max(0, int(yy.min()) - 1), min(mask.shape[0] - 1, int(yy.max()) + 1)
    x0, x1 = max(0, int(xx.min()) - 1), min(mask.shape[1] - 1, int(xx.max()) + 1)
    local = mask[y0:y1 + 1, x0:x1 + 1]
    distance = np.full(local.shape, -1, dtype=np.int16)
    queue = deque()
    for y in range(local.shape[0]):
        for x in range(local.shape[1]):
            if not local[y, x]:
                distance[y, x] = 0
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < local.shape[1] and 0 <= ny < local.shape[0] and distance[ny, nx] < 0:
                distance[ny, nx] = distance[y, x] + 1
                queue.append((nx, ny))
    distance[~local] = -1
    sy, sx = np.unravel_index(np.argmax(distance), distance.shape)
    return x0 + int(sx), y0 + int(sy)


def replace_block(text, pid, replacement):
    match = re.search(rf"(?m)^\s*{pid}\s*=\s*\{{", text)
    if not match:
        return text.rstrip() + "\n\n" + replacement + "\n"
    start = match.start()
    brace = text.find("{", match.start())
    depth = 0
    for end in range(brace, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                return text[:start] + replacement + text[end + 1:]
    raise ValueError(pid)


def main():
    bitmap = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    positions_path = MAP / "positions.txt"
    positions = positions_path.read_text(encoding="latin-1")
    for pid, name, color in PROVINCES:
        mask = np.all(bitmap == color, axis=2)
        x, bitmap_y = safest_pixel(mask)
        y = 2048 - bitmap_y
        block = f"""#{name} - synced to manually edited Yandu bitmap
{pid}={{
    position={{
        {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} 0.000 0.000
    }}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 1.000 0.000 0.000 0.000 0.000
    }}
}}"""
        positions = replace_block(positions, pid, block)
        print(f"{pid}:{name}:{x},{bitmap_y}")
    positions_path.write_text(positions, encoding="latin-1")


if __name__ == "__main__":
    main()
