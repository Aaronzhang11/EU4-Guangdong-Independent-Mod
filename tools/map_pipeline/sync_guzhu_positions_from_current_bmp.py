#!/usr/bin/env python3
"""Recenter Guzhu map objects after manual province-border edits.

This transaction treats the current provinces.bmp as read-only authority.  It
updates only the position blocks for Yongping (4194) and Linyuguan (5211),
while recording the geometry and rendering a review preview.
"""

from __future__ import annotations

import argparse
import csv
from collections import deque
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PLANNING = ROOT / "planning/guzhu_positions_b63"
MARKER = "GDD_B63_GUZHU_POSITION_SYNC"
TARGETS = {
    4194: {"name": "Yongping", "rgb": (94, 52, 48)},
    5211: {"name": "Linyuguan", "rgb": (169, 93, 189)},
}
POSITION_KINDS = (
    "city_and_fort",
    "standing_unit",
    "province_text",
    "port",
    "trade_route",
    "combat_unit",
    "trade_wind",
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def definitions() -> tuple[dict[int, tuple[int, int, int]], dict[tuple[int, int, int], int]]:
    by_id: dict[int, tuple[int, int, int]] = {}
    by_rgb: dict[tuple[int, int, int], int] = {}
    with (MAP / "definition.csv").open(encoding="latin-1", newline="") as stream:
        for row in csv.reader(stream, delimiter=";"):
            try:
                province_id = int(row[0])
                rgb = tuple(int(value) for value in row[1:4])
            except (ValueError, IndexError):
                continue
            by_id[province_id] = rgb
            by_rgb[rgb] = province_id
    return by_id, by_rgb


def sea_ids() -> set[int]:
    text = (MAP / "default.map").read_text(encoding="latin-1")
    match = re.search(r"sea_starts\s*=\s*\{(.*?)\}", text, re.DOTALL)
    if not match:
        raise ValueError("default.map has no sea_starts block")
    uncommented = "\n".join(line.split("#", 1)[0] for line in match.group(1).splitlines())
    return {int(value) for value in re.findall(r"\d+", uncommented)}


def connected_components(mask: np.ndarray) -> list[int]:
    seen = np.zeros(mask.shape, dtype=bool)
    components: list[int] = []
    for start_y, start_x in zip(*np.nonzero(mask)):
        if seen[start_y, start_x]:
            continue
        stack = [(int(start_y), int(start_x))]
        seen[start_y, start_x] = True
        size = 0
        while stack:
            y, x = stack.pop()
            size += 1
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if (
                    0 <= ny < mask.shape[0]
                    and 0 <= nx < mask.shape[1]
                    and mask[ny, nx]
                    and not seen[ny, nx]
                ):
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        components.append(size)
    return sorted(components, reverse=True)


def interior_pixels(mask: np.ndarray) -> tuple[list[tuple[int, int, int]], tuple[float, float]]:
    yy, xx = np.nonzero(mask)
    if not len(xx):
        raise ValueError("empty province mask")
    x0, x1 = int(xx.min()) - 1, int(xx.max()) + 2
    y0, y1 = int(yy.min()) - 1, int(yy.max()) + 2
    local = mask[y0:y1, x0:x1]
    distance = np.full(local.shape, -1, dtype=np.int16)
    queue: deque[tuple[int, int]] = deque()
    for y in range(local.shape[0]):
        for x in range(local.shape[1]):
            if not local[y, x]:
                distance[y, x] = 0
                queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if (
                0 <= ny < local.shape[0]
                and 0 <= nx < local.shape[1]
                and distance[ny, nx] < 0
            ):
                distance[ny, nx] = distance[y, x] + 1
                queue.append((ny, nx))
    pixels = [
        (int(distance[y, x]), x + x0, y + y0)
        for y, x in zip(*np.nonzero(local))
    ]
    return pixels, (float(xx.mean()), float(yy.mean()))


def safest_pixel(
    pixels: list[tuple[int, int, int]], centroid: tuple[float, float]
) -> tuple[int, int]:
    max_depth = max(depth for depth, _, _ in pixels)
    candidates = [entry for entry in pixels if entry[0] == max_depth]
    cx, cy = centroid
    _, x, y = min(
        candidates,
        key=lambda entry: ((entry[1] - cx) ** 2 + (entry[2] - cy) ** 2, entry[2], entry[1]),
    )
    return int(x), int(y)


def secondary_pixel(
    pixels: list[tuple[int, int, int]],
    city: tuple[int, int],
    other_cities: list[tuple[int, int]],
) -> tuple[int, int]:
    max_depth = max(depth for depth, _, _ in pixels)
    candidates = [entry for entry in pixels if entry[0] >= max(2, max_depth - 1)]

    def score(entry: tuple[int, int, int]) -> tuple[float, int, float, int, int]:
        depth, x, y = entry
        separation = min((x - ox) ** 2 + (y - oy) ** 2 for ox, oy in other_cities)
        city_distance = (x - city[0]) ** 2 + (y - city[1]) ** 2
        return separation, depth, city_distance, -y, -x

    _, x, y = max(candidates, key=score)
    return int(x), int(y)


def nearest_mask_pixel(
    pixels: list[tuple[int, int, int]], point: tuple[float, float]
) -> tuple[int, int]:
    px, py = point
    _, x, y = min(
        pixels,
        key=lambda entry: ((entry[1] - px) ** 2 + (entry[2] - py) ** 2, -entry[0]),
    )
    return int(x), int(y)


def port_pixel(
    bitmap: np.ndarray,
    mask: np.ndarray,
    rgb_to_id: dict[tuple[int, int, int], int],
    water_ids: set[int],
) -> tuple[tuple[int, int], int]:
    coast: list[tuple[int, int, int, int, int]] = []
    for y, x in zip(*np.nonzero(mask)):
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = int(y + dy), int(x + dx)
            neighbour_id = rgb_to_id.get(tuple(int(value) for value in bitmap[ny, nx]))
            if neighbour_id in water_ids:
                coast.append((int(x), int(y), nx, ny, int(neighbour_id)))
    if not coast:
        raise ValueError("target province no longer touches a sea province")
    mean_x = sum(entry[0] for entry in coast) / len(coast)
    mean_y = sum(entry[1] for entry in coast) / len(coast)
    land_x, land_y, sea_x, sea_y, sea_id = min(
        coast,
        key=lambda entry: (
            (entry[0] - mean_x) ** 2 + (entry[1] - mean_y) ** 2,
            entry[3],
            entry[2],
        ),
    )
    del land_x, land_y
    return (sea_x, sea_y), sea_id


def derive_layouts(bitmap: np.ndarray) -> dict[int, dict[str, object]]:
    by_id, by_rgb = definitions()
    water_ids = sea_ids()
    geometry: dict[int, dict[str, object]] = {}
    cities: dict[int, tuple[int, int]] = {}

    for province_id, spec in TARGETS.items():
        if by_id.get(province_id) != spec["rgb"]:
            raise ValueError(f"{province_id}: definition RGB drift")
        mask = np.all(bitmap == spec["rgb"], axis=2)
        components = connected_components(mask)
        if len(components) != 1:
            raise ValueError(f"{province_id}: fragmented mask {components}")
        pixels, centroid = interior_pixels(mask)
        city = safest_pixel(pixels, centroid)
        cities[province_id] = city
        yy, xx = np.nonzero(mask)
        geometry[province_id] = {
            "mask": mask,
            "pixels_with_depth": pixels,
            "centroid": centroid,
            "city": city,
            "pixel_count": int(len(xx)),
            "bbox": [int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())],
            "components": components,
        }

    for province_id, data in geometry.items():
        other_cities = [point for other_id, point in cities.items() if other_id != province_id]
        unit = secondary_pixel(data["pixels_with_depth"], data["city"], other_cities)
        text = nearest_mask_pixel(data["pixels_with_depth"], data["centroid"])
        port, sea_id = port_pixel(bitmap, data["mask"], by_rgb, water_ids)
        data["points_bitmap"] = [data["city"], unit, text, port, text, unit, text]
        data["port_sea_id"] = sea_id
    return geometry


def block_bounds(text: str, province_id: int) -> tuple[int, int]:
    match = re.search(rf"(?m)^\s*{province_id}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"positions.txt has no block for {province_id}")
    id_line_start = text.rfind("\n", 0, match.start()) + 1
    start = id_line_start
    previous_end = id_line_start - 1
    if previous_end > 0:
        previous_start = text.rfind("\n", 0, previous_end) + 1
        if text[previous_start:previous_end].lstrip().startswith("#"):
            start = previous_start
    brace = text.find("{", match.start())
    depth = 0
    for end in range(brace, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                if end + 1 < len(text) and text[end + 1] == "\n":
                    end += 1
                return start, end + 1
    raise ValueError(f"positions.txt block {province_id} is unbalanced")


def format_block(province_id: int, points_bitmap: list[tuple[int, int]], height: int) -> str:
    spec = TARGETS[province_id]
    points_game = [(x, height - y) for x, y in points_bitmap]
    coordinates = " ".join(f"{x:.3f} {y:.3f}" for x, y in points_game)
    return f"""#{spec['name']} - {MARKER}
{province_id}={{
    position={{
        {coordinates}
    }}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 1.000 0.000 0.000 0.000 0.000
    }}
}}
"""


def current_points(text: str, province_id: int, height: int) -> list[tuple[int, int]]:
    match = re.search(
        rf"(?ms)^\s*{province_id}\s*=\s*\{{.*?position\s*=\s*\{{(.*?)\}}",
        text,
    )
    if not match:
        raise ValueError(f"positions.txt has no position list for {province_id}")
    values = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", match.group(1))]
    if len(values) != 14:
        raise ValueError(f"{province_id}: expected 14 position values, got {len(values)}")
    return [(round(x), height - round(y)) for x, y in zip(values[::2], values[1::2])]


def render_preview(bitmap: np.ndarray, layouts: dict[int, dict[str, object]]) -> None:
    min_x = min(data["bbox"][0] for data in layouts.values()) - 8
    min_y = min(data["bbox"][1] for data in layouts.values()) - 8
    max_x = max(data["bbox"][2] for data in layouts.values()) + 9
    max_y = max(data["bbox"][3] for data in layouts.values()) + 9
    scale = 24
    crop = Image.fromarray(bitmap[min_y:max_y, min_x:max_x]).resize(
        ((max_x - min_x) * scale, (max_y - min_y) * scale),
        Image.Resampling.NEAREST,
    )
    draw = ImageDraw.Draw(crop)
    font_path = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
    font = ImageFont.truetype(str(font_path), 18) if font_path.exists() else ImageFont.load_default()
    colours = {
        "city_and_fort": "#ffe066",
        "standing_unit": "#ffffff",
        "province_text": "#ff9f43",
        "port": "#46d9ff",
    }
    for province_id, data in layouts.items():
        for kind, (x, y) in zip(POSITION_KINDS[:4], data["points_bitmap"][:4]):
            px = (x - min_x) * scale
            py = (y - min_y) * scale
            colour = colours[kind]
            radius = 7 if kind == "city_and_fort" else 5
            draw.ellipse(
                (px - radius, py - radius, px + radius, py + radius),
                fill=colour,
                outline="black",
                width=2,
            )
            draw.text(
                (px + 8, py - 9),
                f"{province_id} {kind}",
                fill=colour,
                stroke_width=3,
                stroke_fill="black",
                font=font,
            )
    PLANNING.mkdir(parents=True, exist_ok=True)
    crop.save(PLANNING / "positions_preview.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    bitmap_path = MAP / "provinces.bmp"
    image = Image.open(bitmap_path)
    if image.mode != "RGB":
        raise ValueError(f"provinces.bmp must remain RGB, got {image.mode}")
    bitmap = np.asarray(image)
    height, width = bitmap.shape[:2]
    bitmap_hash = file_sha256(bitmap_path)
    layouts = derive_layouts(bitmap)
    positions_path = MAP / "positions.txt"
    positions = positions_path.read_text(encoding="latin-1")

    if args.check:
        for province_id, data in layouts.items():
            actual = current_points(positions, province_id, height)
            if actual != data["points_bitmap"]:
                raise ValueError(
                    f"{province_id}: stale positions; expected {data['points_bitmap']}, got {actual}"
                )
        print(f"checked Guzhu positions for {','.join(map(str, TARGETS))}")
        return

    PLANNING.mkdir(parents=True, exist_ok=True)
    backup_path = PLANNING / "positions_before_blocks.txt"
    if not backup_path.exists():
        snapshots = []
        for province_id in TARGETS:
            start, end = block_bounds(positions, province_id)
            snapshots.append(positions[start:end].rstrip())
        backup_path.write_text("\n\n".join(snapshots) + "\n", encoding="latin-1")

    for province_id, data in layouts.items():
        start, end = block_bounds(positions, province_id)
        positions = (
            positions[:start]
            + format_block(province_id, data["points_bitmap"], height)
            + positions[end:]
        )
    positions_path.write_text(positions, encoding="latin-1")
    if file_sha256(bitmap_path) != bitmap_hash:
        raise ValueError("provinces.bmp changed during position-only transaction")

    render_preview(bitmap, layouts)
    manifest = {
        "batch": MARKER,
        "purpose": "Recenter Guzhu city/fort, unit, text, port, trade and combat anchors after manual borders.",
        "bitmap": {
            "path": str(bitmap_path.relative_to(ROOT)),
            "sha256": bitmap_hash,
            "size": [width, height],
            "editable_pixel_mask": "none; current target masks are read-only authority",
            "locked_exterior": "entire provinces.bmp",
            "changed_pixels_by_batch": 0,
            "exterior_changed_pixels": 0,
        },
        "map_membership_policy": {
            "area": "dong_hebei_area (unchanged)",
            "region": "north_china_region (unchanged)",
            "history": "unchanged",
            "trade_and_terrain": "unchanged",
        },
        "backup": str(backup_path.relative_to(ROOT)),
        "preview": str((PLANNING / "positions_preview.png").relative_to(ROOT)),
        "targets": {},
    }
    for province_id, data in layouts.items():
        manifest["targets"][str(province_id)] = {
            "name": TARGETS[province_id]["name"],
            "rgb": list(TARGETS[province_id]["rgb"]),
            "pixel_count": data["pixel_count"],
            "bbox": data["bbox"],
            "components_4way": data["components"],
            "port_sea_id": data["port_sea_id"],
            "positions_bitmap": {
                kind: list(point)
                for kind, point in zip(POSITION_KINDS, data["points_bitmap"])
            },
            "positions_game": {
                kind: [point[0], height - point[1]]
                for kind, point in zip(POSITION_KINDS, data["points_bitmap"])
            },
        }
    (PLANNING / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "synced Guzhu positions: "
        + ", ".join(
            f"{province_id} city={data['city']} port={data['points_bitmap'][3]}"
            for province_id, data in layouts.items()
        )
    )


if __name__ == "__main__":
    main()
