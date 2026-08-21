#!/usr/bin/env python3
"""Reconcile land adjacency after the user-drawn northern Zhe-Min segment.

EU4 derives ordinary land adjacency from provinces.bmp.  This transaction
therefore preserves the user's pixels, verifies the intended blocked and open
routes, removes only explicit adjacencies that would bypass the mountain, and
records the resulting topology for future reruns.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PROVINCES = MAP / "provinces.bmp"
ADJACENCIES = MAP / "adjacencies.csv"
OLD_BITMAP = ROOT / "planning/fujian_impassable_registration_b65/pre_b65_provinces.bmp"
OUT = ROOT / "planning/zhemin_northern_segment_b66"
BACKUP_BITMAP = OUT / "pre_b66_provinces.bmp"
BACKUP_ADJACENCIES = OUT / "pre_b66_adjacencies.csv"
PREVIEW = OUT / "b66_adjacency_preview.png"
MANIFEST = OUT / "batch_manifest.json"

MARKER = "GDD_B66_ZHEMIN_ADJACENCY_RECONCILIATION"
MOUNTAIN_ID = 5378
MOUNTAIN_RGB = (64, 130, 53)
EXPECTED_NEW_SEGMENT_PIXELS = 166
EXPECTED_NEW_SEGMENT_BBOX = [4662, 912, 4694, 937]

# The new Tiantai/Kuocang-style northern segment removes these old shortcuts.
BLOCKED_PAIRS = {
    (2148, 4951): "绍兴—台州",
    (2148, 5005): "绍兴—宁海",
    (2150, 4951): "金华—台州",
    (2150, 5007): "金华—处州",
    (4951, 5006): "台州—义乌",
}

# These form the intended coastal and western routes around the barrier.
OPEN_PAIRS = {
    (2148, 2149): "绍兴—明州",
    (2148, 5006): "绍兴—义乌",
    (2149, 5005): "明州—宁海",
    (4951, 5005): "台州—宁海",
    (4951, 5007): "台州—处州",
    (4956, 5007): "衢州—处州",
    (2150, 4956): "金华—衢州",
    (2150, 5006): "金华—义乌",
}

AFFECTED_PROVINCES = {2148, 2149, 2150, 4951, 4956, 5005, 5006, 5007}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGB"), dtype=np.uint8, copy=True)


def definitions() -> dict[int, tuple[tuple[int, int, int], str]]:
    result: dict[int, tuple[tuple[int, int, int], str]] = {}
    with (MAP / "definition.csv").open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[int(row[0])] = (tuple(map(int, row[1:4])), row[4])
    return result


def mask_for(values: np.ndarray, rgb: tuple[int, int, int]) -> np.ndarray:
    return np.all(values == rgb, axis=2)


def bbox(mask: np.ndarray) -> list[int]:
    yy, xx = np.where(mask)
    return [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]


def component_sizes(mask: np.ndarray) -> list[int]:
    seen = np.zeros(mask.shape, dtype=bool)
    sizes: list[int] = []
    for sy, sx in zip(*np.where(mask), strict=True):
        if seen[sy, sx]:
            continue
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        size = 0
        while stack:
            y, x = stack.pop()
            size += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def border_count(
    values: np.ndarray,
    first_rgb: tuple[int, int, int],
    second_rgb: tuple[int, int, int],
) -> int:
    first = mask_for(values, first_rgb)
    second = mask_for(values, second_rgb)
    return int(
        np.sum((first[:, :-1] & second[:, 1:]) | (second[:, :-1] & first[:, 1:]))
        + np.sum((first[:-1, :] & second[1:, :]) | (second[:-1, :] & first[1:, :]))
    )


def remove_bypass_adjacencies() -> list[str]:
    lines = ADJACENCIES.read_text(encoding="latin-1").splitlines()
    output: list[str] = []
    removed: list[str] = []
    blocked = {tuple(sorted(pair)) for pair in BLOCKED_PAIRS}
    for line in lines:
        fields = line.split(";")
        if len(fields) >= 2:
            try:
                pair = tuple(sorted((int(fields[0]), int(fields[1]))))
            except ValueError:
                pair = (-1, -1)
            if pair in blocked:
                removed.append(line)
                continue
        output.append(line)
    ADJACENCIES.write_text("\n".join(output) + "\n", encoding="latin-1")
    return removed


def render_preview(before: np.ndarray, after: np.ndarray) -> None:
    crop = (4645, 895, 4710, 950)
    zoom = 8
    size = ((crop[2] - crop[0]) * zoom, (crop[3] - crop[1]) * zoom)
    left = Image.fromarray(before).crop(crop).resize(size, Image.Resampling.NEAREST)
    right = Image.fromarray(after).crop(crop).resize(size, Image.Resampling.NEAREST)
    gap = 24
    header = 105
    canvas = Image.new("RGB", (left.width * 2 + gap, left.height + header), (20, 25, 31))
    canvas.paste(left, (0, header))
    canvas.paste(right, (left.width + gap, header))
    draw = ImageDraw.Draw(canvas)
    try:
        title = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 24)
        detail = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 15)
    except OSError:
        title = detail = ImageFont.load_default()
    draw.text((16, 12), "B66：浙闽山脉北段与浙江邻接", font=title, fill=(240, 244, 248))
    draw.text((16, 49), "左：加山前　　右：当前地图（新增 166 px）", font=detail, fill=(188, 245, 194))
    draw.text((16, 75), "阻断 5 条旧捷径；沿海与浙西绕行通道保留", font=detail, fill=(210, 218, 226))
    canvas.save(PREVIEW)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not OLD_BITMAP.exists():
        raise SystemExit("B65 pre-registration bitmap is missing")
    if not BACKUP_BITMAP.exists():
        shutil.copy2(PROVINCES, BACKUP_BITMAP)
    if not BACKUP_ADJACENCIES.exists():
        shutil.copy2(ADJACENCIES, BACKUP_ADJACENCIES)

    before = read_rgb(OLD_BITMAP)
    current = read_rgb(PROVINCES)
    province_data = definitions()
    before_hash = sha256(PROVINCES)
    old_mountain = mask_for(before, MOUNTAIN_RGB)
    new_mountain = mask_for(current, MOUNTAIN_RGB)
    added = new_mountain & ~old_mountain
    removed = old_mountain & ~new_mountain
    if int(added.sum()) != EXPECTED_NEW_SEGMENT_PIXELS or bbox(added) != EXPECTED_NEW_SEGMENT_BBOX:
        raise ValueError(
            f"Unexpected northern segment geometry: pixels={int(added.sum())}, bbox={bbox(added)}"
        )
    if removed.any():
        raise ValueError("Existing Zhe-Min mountain pixels were removed")

    affected_connectivity = {}
    for province_id in sorted(AFFECTED_PROVINCES):
        sizes = component_sizes(mask_for(current, province_data[province_id][0]))
        affected_connectivity[str(province_id)] = sizes
        if len(sizes) != 1:
            raise ValueError(f"Affected playable province {province_id} is fragmented: {sizes}")

    blocked_report = {}
    for pair, name in BLOCKED_PAIRS.items():
        old_count = border_count(before, province_data[pair[0]][0], province_data[pair[1]][0])
        current_count = border_count(current, province_data[pair[0]][0], province_data[pair[1]][0])
        if old_count <= 0 or current_count != 0:
            raise ValueError(f"Blocked route {name} has unexpected counts {old_count} -> {current_count}")
        blocked_report[name] = {"province_pair": list(pair), "before": old_count, "after": current_count}

    open_report = {}
    for pair, name in OPEN_PAIRS.items():
        old_count = border_count(before, province_data[pair[0]][0], province_data[pair[1]][0])
        current_count = border_count(current, province_data[pair[0]][0], province_data[pair[1]][0])
        if current_count <= 0:
            raise ValueError(f"Required pass {name} was closed")
        open_report[name] = {"province_pair": list(pair), "before": old_count, "after": current_count}

    removed_rows = remove_bypass_adjacencies()
    if sha256(PROVINCES) != before_hash:
        raise RuntimeError("Adjacency reconciliation unexpectedly changed provinces.bmp")
    render_preview(before, current)
    MANIFEST.write_text(
        json.dumps(
            {
                "batch": "B66_zhemin_northern_segment_adjacency_reconciliation",
                "marker": MARKER,
                "status": "implemented",
                "mountain_id": MOUNTAIN_ID,
                "mountain_rgb": list(MOUNTAIN_RGB),
                "new_segment": {
                    "pixels": int(added.sum()),
                    "bbox": bbox(added),
                    "components": component_sizes(added),
                },
                "bitmap_pixels_changed_by_script": 0,
                "blocked_direct_land_routes": blocked_report,
                "preserved_direct_land_routes": open_report,
                "affected_playable_connectivity": affected_connectivity,
                "removed_explicit_bypass_rows": removed_rows,
                "validation_notes": {
                    "province_2149_localisation": (
                        "明州的 PROV/PROV_ADJ 已由 localisation/replace/"
                        "002_gdd_b44_worldview_toponyms_l_english.yml 提供；"
                        "audit_eu4_mod.py 仅使用非递归 glob，故会产生假阳性"
                    ),
                    "east_zhejiang_area": (
                        "长国(5004)为岛屿，通过既有明州—长国海峡连接；"
                        "crossing_connected 属于预期结构"
                    ),
                },
                "backups": {
                    "bitmap": str(BACKUP_BITMAP),
                    "adjacencies": str(BACKUP_ADJACENCIES),
                },
                "canonical_bitmap_sha256": before_hash,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"B66_ZHEMIN_ADJACENCY_RECONCILED blocked={len(BLOCKED_PAIRS)} "
        f"open={len(OPEN_PAIRS)} removed_explicit={len(removed_rows)} bitmap_pixels_changed=0"
    )


if __name__ == "__main__":
    main()
