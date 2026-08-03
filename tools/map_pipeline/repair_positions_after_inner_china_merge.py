#!/usr/bin/env python3
"""Restore the full positions table and repair displaced city/unit points."""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/positions"
PATH_IN_GIT = "guangdong_independent_practice/map/positions.txt"
PRE_TRUNCATION_REF = "63e8b6e^"
MARKER = "B31 full positions recovery"


def block_bounds(text: str, province_id: int):
    match = re.search(rf"(?m)^\s*{province_id}\s*=\s*\{{", text)
    if not match:
        return None
    start = match.start()
    brace = text.find("{", match.start())
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise ValueError(f"Unclosed positions block {province_id}")


def extract_blocks(text: str):
    result = {}
    duplicates = []
    for match in re.finditer(r"(?m)^\s*(\d+)\s*=\s*\{", text):
        province_id = int(match.group(1))
        start = match.start()
        brace = text.find("{", match.start())
        depth, end = 0, None
        for i in range(brace, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise ValueError(f"Unclosed positions block {province_id}")
        if province_id in result:
            duplicates.append(province_id)
        result[province_id] = text[start:end]
    return result, duplicates


def replace_block(text: str, province_id: int, block: str):
    bounds = block_bounds(text, province_id)
    if bounds is None:
        return text.rstrip() + f"\n\n#{MARKER}\n" + block.rstrip() + "\n"
    return text[:bounds[0]] + block.rstrip() + text[bounds[1]:]


def definitions(path: Path):
    by_id, by_colour = {}, {}
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 5 and fields[0].isdigit():
            province_id = int(fields[0])
            colour = tuple(map(int, fields[1:4]))
            by_id[province_id] = (colour, fields[4])
            by_colour[colour] = province_id
    return by_id, by_colour


def playable_ids(path: Path, definitions_by_id):
    text = re.sub(r"#.*", "", path.read_text(encoding="latin-1"))
    return {
        int(value) for value in re.findall(r"(?<![\w.])(\d+)(?![\w.])", text)
        if int(value) in definitions_by_id
    }


def position_pairs(block: str):
    match = re.search(r"(?ms)\bposition\s*=\s*\{(.*?)\}", block)
    if not match:
        return []
    values = list(map(float, re.findall(r"-?\d+(?:\.\d+)?", match.group(1))))
    return list(zip(values[0::2], values[1::2]))


def format_position(pairs):
    values = []
    for x, y in pairs:
        values.extend((f"{x:.3f}", f"{y:.3f}"))
    return "    position={\n        " + " ".join(values) + "\n    }"


def set_position_pairs(block: str, pairs):
    replacement = format_position(pairs)
    changed, count = re.subn(r"(?ms)\s*position\s*=\s*\{.*?\}", "\n" + replacement, block, count=1)
    if count != 1:
        raise ValueError("Positions block has no position array")
    return changed


def default_block(province_id: int, name: str, x: float, y: float):
    pairs = [(x, y)] * 6 + [(0.0, 0.0)]
    return f'''{province_id}={{
{format_position(pairs)}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 1.000 0.000 0.000 0.000 0.000
    }}
}}'''


def largest_component(mask: np.ndarray):
    seen = np.zeros(mask.shape, dtype=bool)
    best = []
    for sy, sx in zip(*np.where(mask)):
        if seen[sy, sx]:
            continue
        cells = []
        queue = deque([(int(sy), int(sx))])
        seen[sy, sx] = True
        while queue:
            y, x = queue.popleft()
            cells.append((y, x))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if (0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1]
                        and mask[ny, nx] and not seen[ny, nx]):
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        if len(cells) > len(best):
            best = cells
    result = np.zeros(mask.shape, dtype=bool)
    if best:
        yy, xx = zip(*best)
        result[np.array(yy), np.array(xx)] = True
    return result


def safe_point(coords, bitmap_height: int):
    yy, xx = coords
    y0, y1 = int(yy.min()) - 1, int(yy.max()) + 1
    x0, x1 = int(xx.min()) - 1, int(xx.max()) + 1
    local = np.zeros((y1 - y0 + 1, x1 - x0 + 1), dtype=bool)
    local[yy - y0, xx - x0] = True
    component = largest_component(local)

    distance = np.zeros(component.shape, dtype=np.int16)
    queue = deque()
    for y, x in zip(*np.where(component)):
        boundary = any(
            not (0 <= y + dy < component.shape[0] and 0 <= x + dx < component.shape[1]
                 and component[y + dy, x + dx])
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
        )
        if boundary:
            distance[y, x] = 1
            queue.append((int(y), int(x)))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if (0 <= ny < component.shape[0] and 0 <= nx < component.shape[1]
                    and component[ny, nx] and distance[ny, nx] == 0):
                distance[ny, nx] = distance[y, x] + 1
                queue.append((ny, nx))
    deepest = np.argwhere(distance == distance.max())
    component_points = np.argwhere(component)
    centre = component_points.mean(axis=0)
    chosen = deepest[np.argmin(np.sum((deepest - centre) ** 2, axis=1))]
    bitmap_y, bitmap_x = int(chosen[0] + y0), int(chosen[1] + x0)
    return float(bitmap_x), float(bitmap_height - bitmap_y)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    positions_path = MAP / "positions.txt"
    backup_path = OUT / "pre_positions_repair_truncated.txt"
    if not backup_path.exists():
        shutil.copy2(positions_path, backup_path)

    base_result = subprocess.run(
        ["git", "show", f"{PRE_TRUNCATION_REF}:{PATH_IN_GIT}"],
        cwd=ROOT, check=True, stdout=subprocess.PIPE,
    )
    base_text = base_result.stdout.decode("latin-1")
    # Always rebuild from the original truncated overlay so reruns can refine
    # validation policy without retaining an earlier repair's generated points.
    current_text = backup_path.read_text(encoding="latin-1")
    current_blocks, current_duplicates = extract_blocks(current_text)
    if current_duplicates:
        raise ValueError(f"Duplicate blocks in current truncated file: {current_duplicates}")

    merged = base_text
    for province_id, block in sorted(current_blocks.items()):
        merged = replace_block(merged, province_id, block)

    definitions_by_id, id_by_colour = definitions(MAP / "definition.csv")
    playable = playable_ids(MAP / "area.txt", definitions_by_id)
    bitmap = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    height = bitmap.shape[0]
    packed = ((bitmap[:, :, 0].astype(np.uint32) << 16)
              | (bitmap[:, :, 1].astype(np.uint32) << 8)
              | bitmap[:, :, 2].astype(np.uint32))
    present_keys = set(map(int, np.unique(packed)))

    def owners_at(pair):
        x, game_y = pair
        bitmap_y = height - game_y
        xs = {int(np.floor(x)), int(np.ceil(x))}
        ys = {int(np.floor(bitmap_y)), int(np.ceil(bitmap_y))}
        owners = set()
        for px in xs:
            for py in ys:
                if 0 <= px < bitmap.shape[1] and 0 <= py < bitmap.shape[0]:
                    owner = id_by_colour.get(tuple(map(int, bitmap[py, px])))
                    if owner is not None:
                        owners.add(owner)
        return owners

    def point_inside(province_id, pair):
        return province_id in owners_at(pair)

    merged_blocks, merged_duplicates = extract_blocks(merged)
    if merged_duplicates:
        raise ValueError(f"Duplicate blocks after merge: {merged_duplicates}")

    missing_before, city_bad_before, unit_bad_before = [], [], []
    repair_ids = set()
    for province_id in sorted(playable):
        pairs = position_pairs(merged_blocks.get(province_id, ""))
        if len(pairs) < 2:
            missing_before.append(province_id)
            repair_ids.add(province_id)
            continue
        if not point_inside(province_id, pairs[0]):
            city_bad_before.append(province_id)
            repair_ids.add(province_id)
        if not point_inside(province_id, pairs[1]):
            unit_bad_before.append(province_id)
            repair_ids.add(province_id)

    keys = []
    id_for_key = {}
    for province_id in sorted(repair_ids):
        colour = definitions_by_id[province_id][0]
        key = (colour[0] << 16) | (colour[1] << 8) | colour[2]
        keys.append(key)
        id_for_key[key] = province_id
    target_mask = np.isin(packed, np.array(keys, dtype=np.uint32)) if keys else np.zeros(packed.shape, bool)
    all_y, all_x = np.where(target_mask)
    all_keys = packed[all_y, all_x]
    coordinates = {}
    for key in np.unique(all_keys):
        hit = all_keys == key
        coordinates[id_for_key[int(key)]] = (all_y[hit], all_x[hit])

    generated, adjusted, empty = [], [], []
    for province_id in sorted(repair_ids):
        coords = coordinates.get(province_id)
        if coords is None or not len(coords[0]):
            empty.append(province_id)
            continue
        x, y = safe_point(coords, height)
        old_block = merged_blocks.get(province_id)
        if old_block is None or len(position_pairs(old_block)) < 2:
            block = default_block(province_id, definitions_by_id[province_id][1], x, y)
            generated.append(province_id)
        else:
            pairs = position_pairs(old_block)
            while len(pairs) < 7:
                pairs.append((0.0, 0.0))
            # Preserve every valid legacy anchor.  City and unit points are
            # independent: repairing one must not silently relocate the other.
            if not point_inside(province_id, pairs[0]):
                pairs[0] = (x, y)
            if not point_inside(province_id, pairs[1]):
                pairs[1] = (x, y)
            block = set_position_pairs(old_block, pairs[:7])
            adjusted.append(province_id)
        merged = replace_block(merged, province_id, block)
        merged_blocks[province_id] = block

    positions_path.write_text(merged.rstrip() + "\n", encoding="latin-1")

    final_blocks, duplicates = extract_blocks(positions_path.read_text(encoding="latin-1"))
    missing_after, city_bad_after, unit_bad_after = [], [], []
    for province_id in sorted(playable):
        colour = definitions_by_id[province_id][0]
        key = (colour[0] << 16) | (colour[1] << 8) | colour[2]
        if key not in present_keys:
            continue
        pairs = position_pairs(final_blocks.get(province_id, ""))
        if len(pairs) < 2:
            missing_after.append(province_id)
            continue
        if not point_inside(province_id, pairs[0]):
            city_bad_after.append(province_id)
        if not point_inside(province_id, pairs[1]):
            unit_bad_after.append(province_id)

    report = {
        "source_ref": PRE_TRUNCATION_REF,
        "base_blocks": len(extract_blocks(base_text)[0]),
        "preserved_post_merge_blocks": len(current_blocks),
        "final_blocks": len(final_blocks),
        "playable_ids": len(playable),
        "before": {
            "missing": len(missing_before),
            "city_outside": len(city_bad_before),
            "unit_outside": len(unit_bad_before),
            "missing_ids": missing_before,
            "city_outside_ids": city_bad_before,
            "unit_outside_ids": unit_bad_before,
        },
        "repaired": {"generated": generated, "adjusted": adjusted},
        "empty_unrepairable": empty,
        "after": {
            "duplicate_blocks": duplicates,
            "missing_nonempty": missing_after,
            "city_outside_nonempty": city_bad_after,
            "unit_outside_nonempty": unit_bad_after,
        },
    }
    (OUT / "positions_repair_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    if duplicates or missing_after or city_bad_after or unit_bad_after:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
