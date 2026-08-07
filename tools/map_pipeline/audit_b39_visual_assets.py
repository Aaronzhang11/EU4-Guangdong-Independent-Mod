#!/usr/bin/env python3
"""Audit B39/B41 terrain and tree rendering assets without mutating the mod."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import numpy as np
from PIL import Image

import apply_b39_daming_terrain_visual_assets as b39


REPORT = b39.OUT / "visual_asset_audit.json"
LOGS = Path("/Users/xinanyapiao/Documents/Paradox Interactive/Europa Universalis IV/logs")


def braced_body(text: str, marker: str) -> str:
    start = text.index(marker) + len(marker)
    depth = 1
    index = start
    while index < len(text) and depth:
        depth += (text[index] == "{") - (text[index] == "}")
        index += 1
    if depth:
        raise ValueError(f"Unclosed block: {marker}")
    return text[start:index - 1]


def line_ids(lines: list[str], pattern: str) -> list[int]:
    result = []
    regex = re.compile(pattern)
    for line in lines:
        match = regex.search(line)
        if match:
            result.append(int(match.group(1)))
    return sorted(set(result))


def main() -> None:
    terrain_text = (b39.MAP / "terrain.txt").read_text(encoding="cp1252", errors="replace")
    terrain_body = braced_body(terrain_text, "\nterrain = {")
    terrain_defined = set(map(int, re.findall(
        r"\bcolor\s*=\s*\{\s*(\d+)\s*\}", terrain_body
    )))
    terrain_values = np.asarray(Image.open(b39.MAP / "terrain.bmp"))
    terrain_used = set(map(int, np.unique(terrain_values).tolist()))
    terrain_undefined = sorted(terrain_used - terrain_defined)

    tree_image = Image.open(b39.MAP / "trees.bmp")
    tree_values = np.asarray(tree_image)
    tree_used = set(map(int, np.unique(tree_values).tolist()))
    tree_undefined = sorted(tree_used - set(b39.TREE_VALID_INDICES))
    _, _, water = b39.core_fade_and_water()
    water_fraction = np.asarray(
        Image.fromarray(water.astype(np.uint8) * 255, mode="L").resize(
            b39.TREE_TARGET_SIZE, Image.Resampling.BOX
        ),
        dtype=np.float32,
    ) / 255.0
    water_cells = water_fraction > b39.TREE_WATER_FRACTION_LIMIT
    tree_water_cells = int(((tree_values != 0) & water_cells).sum())

    seasonal = {}
    for name in b39.SEASONAL:
        path = b39.MAP / "terrain" / name
        data = path.read_bytes()
        if data[:4] != b"DDS ":
            raise ValueError(f"Not a DDS file: {path}")
        _, height, width, _, _, mipmaps = struct.unpack_from("<6I", data, 8)
        fourcc = data[84:88].decode("ascii", errors="replace")
        values = np.asarray(Image.open(path).convert("RGBA"))
        near_white = np.all(values[:, :, :3] >= b39.SOURCE_BLANK_THRESHOLD, axis=2)
        seasonal[name] = {
            "size": [width, height],
            "fourcc": fourcc,
            "mipmaps": mipmaps,
            "near_white_water_pixels": int((near_white & water).sum()),
            "nonopaque_pixels": int((values[:, :, 3] != 255).sum()),
        }

    direct_copy_mismatches = []
    for name in b39.COPIED_TERRAIN_ASSETS:
        source = b39.SOURCE / "map/terrain" / name
        target = b39.MAP / "terrain" / name
        if b39.sha256(source) != b39.sha256(target):
            direct_copy_mismatches.append(name)

    graphics_lines = (LOGS / "graphics.log").read_text(errors="replace").splitlines()
    error_lines = (LOGS / "error.log").read_text(errors="replace").splitlines()
    mapobject16 = sum("mapobject_16 failed to load" in line for line in graphics_lines)
    tree_index_errors = sum("Failed to find tree terrain associated" in line for line in error_lines)
    invalid_port_ids = line_ids(graphics_lines, r"Invalid port location for province (\d+)")
    invalid_origin_ids = line_ids(graphics_lines, r"Province (\d+) has invalid origin")
    other_load_failures = [
        line for line in graphics_lines
        if "failed to load" in line.lower() and "mapobject_16" not in line
    ]

    static_pass = (
        tree_image.mode == "P"
        and tree_image.size == b39.TREE_TARGET_SIZE
        and not tree_undefined
        and tree_water_cells == 0
        and not terrain_undefined
        and not direct_copy_mismatches
        and all(
            item["size"] == list(b39.TARGET_SIZE)
            and item["fourcc"] == "DXT3"
            and item["mipmaps"] == 13
            and item["near_white_water_pixels"] == 0
            and item["nonopaque_pixels"] == 0
            for item in seasonal.values()
        )
    )
    report = {
        "batch": "B41 visual asset audit",
        "static_pass": static_pass,
        "trees": {
            "mode": tree_image.mode,
            "size": list(tree_image.size),
            "expected_size": list(b39.TREE_TARGET_SIZE),
            "used_indices": sorted(tree_used),
            "undefined_indices": tree_undefined,
            "water_tree_cells": tree_water_cells,
        },
        "terrain": {
            "used_indices": sorted(terrain_used),
            "defined_indices": sorted(terrain_defined),
            "undefined_indices": terrain_undefined,
        },
        "seasonal_colormaps": seasonal,
        "direct_copy_mismatches": direct_copy_mismatches,
        "pre_fix_logs": {
            "log_timestamp_note": "Logs predate B41; rerun the game to confirm runtime clearance.",
            "mapobject_16_failures": mapobject16,
            "tree_terrain_index_errors": tree_index_errors,
            "invalid_port_location_ids": invalid_port_ids,
            "invalid_origin_ids": invalid_origin_ids,
            "other_graphics_load_failures": other_load_failures,
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"B41_VISUAL_AUDIT; PASS:{int(static_pass)}; "
        f"TREE_UNDEFINED:{len(tree_undefined)}; TREE_WATER:{tree_water_cells}; "
        f"TERRAIN_UNDEFINED:{len(terrain_undefined)}; DIRECT_MISMATCH:{len(direct_copy_mismatches)}"
    )
    print(REPORT)
    if not static_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
