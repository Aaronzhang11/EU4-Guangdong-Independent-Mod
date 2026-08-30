#!/usr/bin/env python3
"""Apply the reviewed Dabie Mountains, Mount Tai and Weishan Lake patch.

The reviewed geometry is stored as a guarded before/after RGBA patch.  The
first run may build those compact assets from the user's 6400x2560 reference
bitmap; later runs need only the committed patch assets.  Only opaque patch
pixels are ever copied into the canonical provinces.bmp.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PLAN = ROOT / "planning/east_china_landmarks_b57"
PROVINCES = MAP / "provinces.bmp"
BACKUP = PLAN / "pre_b57_provinces.bmp"
BEFORE_PATCH = PLAN / "b57_before_patch.png"
AFTER_PATCH = PLAN / "b57_after_patch.png"
PREVIEW = PLAN / "b57_applied_preview.png"

MARKER = "GDD_B57_EAST_CHINA_LANDMARKS"
PATCH_BOX = (4550, 775, 4685, 925)
MOUNTAINS = {
    5354: ("Dabie Mountains", "大别山", (87, 9, 10)),
    5355: ("Mount Tai", "泰山", (27, 57, 174)),
}
WEISHAN = (4010, "Weishan Lake", "微山湖", (100, 14, 110))
FEATURE_COLOURS = {value[2] for value in MOUNTAINS.values()} | {WEISHAN[3]}

# name, RGB, source bbox, scale, target top-left.  Forward pixel mapping keeps
# every small component of the reviewed source silhouettes.
SOURCE_FEATURES = (
    ("大别山", (87, 9, 10), (4999, 873, 5075, 920), 0.82, (4577, 862)),
    ("泰山", (27, 57, 174), (5075, 794, 5106, 818), 0.80, (4639, 789)),
    ("微山湖", (100, 14, 110), (5070, 825, 5098, 848), 0.90, (4619, 814)),
)


def read_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGB"), dtype=np.uint8, copy=True)


def forward_scale(mask: np.ndarray, scale: float) -> np.ndarray:
    height, width = mask.shape
    new_height, new_width = round(height * scale), round(width * scale)
    result = np.zeros((new_height, new_width), dtype=bool)
    yy, xx = np.where(mask)
    target_y = np.floor((yy + 0.5) * new_height / height).astype(int)
    target_x = np.floor((xx + 0.5) * new_width / width).astype(int)
    result[target_y, target_x] = True
    return result


def components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    """Return four-way components as (y, x) pixel lists, largest first."""
    height, width = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    result: list[list[tuple[int, int]]] = []
    for start_y, start_x in zip(*np.where(mask)):
        start_y, start_x = int(start_y), int(start_x)
        if seen[start_y, start_x]:
            continue
        seen[start_y, start_x] = True
        stack = [(start_y, start_x)]
        group: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            group.append((y, x))
            for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and mask[next_y, next_x]
                    and not seen[next_y, next_x]
                ):
                    seen[next_y, next_x] = True
                    stack.append((next_y, next_x))
        result.append(group)
    return sorted(result, key=len, reverse=True)


def definition_metadata() -> dict[tuple[int, int, int], tuple[int, str]]:
    result: dict[tuple[int, int, int], tuple[int, str]] = {}
    for line in (MAP / "definition.csv").read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 5 and fields[0].isdigit():
            result[(int(fields[1]), int(fields[2]), int(fields[3]))] = (
                int(fields[0]),
                fields[4],
            )
    return result


def build_reviewed_patch(reference_path: Path) -> None:
    """Build the compact guarded patch from the reviewed source silhouettes."""
    base = read_rgb(BACKUP)
    reference = read_rgb(reference_path)
    if reference.shape[:2] != (2560, 6400):
        raise ValueError(f"Unexpected reference dimensions: {reference.shape[:2]}")

    feature_only = base.copy()
    affected: set[tuple[int, int, int]] = set()
    for _, colour, (x0, y0, x1, y1), scale, (target_x, target_y) in SOURCE_FEATURES:
        source_mask = np.all(reference[y0:y1, x0:x1] == colour, axis=2)
        mask = forward_scale(source_mask, scale)
        height, width = mask.shape
        target = feature_only[target_y : target_y + height, target_x : target_x + width]
        affected.update(map(tuple, np.unique(target[mask].reshape(-1, 3), axis=0)))
        target[mask] = colour

    x0, y0, x1, y1 = PATCH_BOX
    original = base[y0:y1, x0:x1].copy()
    adjusted = feature_only.copy()
    local = adjusted[y0:y1, x0:x1]
    metadata = definition_metadata()

    def count_groups(values: np.ndarray, colour: tuple[int, int, int]) -> int:
        return len(components(np.all(values == colour, axis=2)))

    original_counts = {colour: count_groups(original, colour) for colour in affected}
    # Remove only components newly cut off by the inserted mountain/lake pixels.
    # A component is given to a directly adjacent land province; a tiny pocket
    # fully enclosed by a mountain is absorbed into that mountain instead.
    for _ in range(300):
        candidate = None
        for colour in sorted(affected):
            groups = components(np.all(local == colour, axis=2))
            keep_count = original_counts[colour]
            if len(groups) > keep_count:
                fragment = min(groups[keep_count:], key=len)
                if candidate is None or len(fragment) < len(candidate[1]):
                    candidate = (colour, fragment)
        if candidate is None:
            break
        colour, fragment = candidate
        fragment_set = set(fragment)
        land_contacts: Counter[tuple[int, int, int]] = Counter()
        feature_contacts: Counter[tuple[int, int, int]] = Counter()
        for y, x in fragment:
            for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if not (0 <= next_y < local.shape[0] and 0 <= next_x < local.shape[1]):
                    continue
                if (next_y, next_x) in fragment_set:
                    continue
                neighbour = tuple(int(channel) for channel in local[next_y, next_x])
                if neighbour in FEATURE_COLOURS:
                    feature_contacts[neighbour] += 1
                    continue
                if neighbour == colour or neighbour not in metadata:
                    continue
                lower_name = metadata[neighbour][1].lower()
                if any(word in lower_name for word in ("reach", "lake", "sea", "river", "estuary")):
                    continue
                land_contacts[neighbour] += 1
        if land_contacts:
            replacement = land_contacts.most_common(1)[0][0]
        elif feature_contacts:
            replacement = feature_contacts.most_common(1)[0][0]
        else:
            raise ValueError(f"No safe neighbour for {colour} fragment of {len(fragment)} pixels")
        for y, x in fragment:
            local[y, x] = replacement
    else:
        raise ValueError("Province-fragment cleanup did not converge")

    # The reviewed adjustment must leave every affected playable province with
    # no more local components than it had before the patch.
    for colour in affected:
        before = count_groups(original, colour)
        after = count_groups(local, colour)
        if after > before:
            raise ValueError(f"New detached fragment remains for {colour}: {before} -> {after}")

    before_crop = base[y0:y1, x0:x1]
    after_crop = adjusted[y0:y1, x0:x1]
    changed = np.any(before_crop != after_crop, axis=2)
    before_rgba = np.dstack((before_crop, changed.astype(np.uint8) * 255))
    after_rgba = np.dstack((after_crop, changed.astype(np.uint8) * 255))
    Image.fromarray(before_rgba, mode="RGBA").save(BEFORE_PATCH)
    Image.fromarray(after_rgba, mode="RGBA").save(AFTER_PATCH)


def load_patch(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with Image.open(path) as image:
        rgba = np.array(image.convert("RGBA"), dtype=np.uint8, copy=True)
    return rgba[:, :, :3], rgba[:, :, 3] == 255


def apply_geometry() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    before_values, before_mask = load_patch(BEFORE_PATCH)
    after_values, after_mask = load_patch(AFTER_PATCH)
    if not np.array_equal(before_mask, after_mask):
        raise ValueError("Before/after patch masks differ")

    current = read_rgb(PROVINCES)
    x0, y0, x1, y1 = PATCH_BOX
    target = current[y0:y1, x0:x1]
    current_pixels = target[after_mask]
    before_pixels = before_values[after_mask]
    after_pixels = after_values[after_mask]
    allowed = np.all(current_pixels == before_pixels, axis=1) | np.all(current_pixels == after_pixels, axis=1)
    if not np.all(allowed):
        unexpected = np.where(~allowed)[0][:10]
        raise ValueError(f"Reviewed patch overlaps later map edits at {unexpected.tolist()}")
    target[after_mask] = after_pixels
    Image.fromarray(current, mode="RGB").save(PROVINCES, format="BMP")
    header = PROVINCES.read_bytes()[:54]
    if int.from_bytes(header[14:18], "little") != 40 or int.from_bytes(header[10:14], "little") != 54:
        raise ValueError("provinces.bmp does not use the required classic BMP header")
    return current, before_values, after_mask


def update_definitions() -> None:
    path = MAP / "definition.csv"
    records = {
        4010: (WEISHAN[3], WEISHAN[1]),
        **{province_id: (data[2], data[0]) for province_id, data in MOUNTAINS.items()},
    }
    output: list[str] = []
    seen: set[int] = set()
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in records:
            province_id = int(fields[0])
            colour, name = records[province_id]
            output.append(f"{province_id};{colour[0]};{colour[1]};{colour[2]};{name};x")
            seen.add(province_id)
        else:
            output.append(line)
    for province_id in sorted(set(records) - seen):
        colour, name = records[province_id]
        output.append(f"{province_id};{colour[0]};{colour[1]};{colour[2]};{name};x")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")


def block_bounds(text: str, name: str, start: int = 0, end: int | None = None) -> tuple[int, int]:
    limit = len(text) if end is None else end
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text[start:limit])
    if not match:
        raise ValueError(f"Missing block {name}")
    block_start = start + match.start()
    opening = start + match.end() - 1
    depth = 0
    for index in range(opening, limit):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return block_start, index + 1
    raise ValueError(f"Unclosed block {name}")


def add_marker_to_block(text: str, block: str, ids: tuple[int, ...], indent: str = "    ") -> str:
    text = re.sub(rf"(?m)^\s*.*# {MARKER}(?: .*)?\n?", "", text)
    start, end = block_bounds(text, block)
    insertion = text.rfind("}", start, end)
    line = f"{indent}{' '.join(map(str, ids))} # {MARKER}\n"
    return text[:insertion] + line + text[insertion:]


def add_marker_to_nested_block(text: str, outer: str, inner: str, ids: tuple[int, ...]) -> str:
    text = re.sub(rf"(?m)^\s*.*# {MARKER}(?: .*)?\n?", "", text)
    outer_start, outer_end = block_bounds(text, outer)
    inner_start, inner_end = block_bounds(text, inner, outer_start, outer_end)
    insertion = text.rfind("}", inner_start, inner_end)
    line = f"            {' '.join(map(str, ids))} # {MARKER}\n"
    return text[:insertion] + line + text[insertion:]


def update_map_lists() -> None:
    default_path = MAP / "default.map"
    default_text = default_path.read_text(encoding="latin-1")
    default_text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5356", default_text)
    lake_start, lake_end = block_bounds(default_text, "lakes")
    if not re.search(r"(?<!\d)4010(?!\d)", default_text[lake_start:lake_end]):
        raise ValueError("Reserved lake ID 4010 is not in default.map lakes")
    default_path.write_text(default_text, encoding="latin-1")

    climate_path = MAP / "climate.txt"
    climate_text = climate_path.read_text(encoding="latin-1")
    climate_path.write_text(
        add_marker_to_block(climate_text, "impassable", tuple(MOUNTAINS)),
        encoding="latin-1",
    )

    continent_path = MAP / "continent.txt"
    continent_text = continent_path.read_text(encoding="latin-1")
    continent_path.write_text(
        add_marker_to_block(continent_text, "asia", tuple(MOUNTAINS), indent="        "),
        encoding="latin-1",
    )

    terrain_path = MAP / "terrain.txt"
    terrain_text = terrain_path.read_text(encoding="latin-1")
    terrain_path.write_text(
        add_marker_to_nested_block(terrain_text, "mountain", "terrain_override", tuple(MOUNTAINS)),
        encoding="latin-1",
    )


def update_localisation() -> None:
    source = MOD / "localisation_source/010_gdd_b57_east_china_landmarks_readable_utf8.txt"
    source.write_text(
        "\n".join(
            (
                "l_english:",
                ' PROV4010:0 "微山湖"',
                ' PROV_ADJ4010:0 "微山湖"',
                ' PROV5354:0 "大别山"',
                ' PROV_ADJ5354:0 "大别山"',
                ' PROV5355:0 "泰山"',
                ' PROV_ADJ5355:0 "泰山"',
            )
        )
        + "\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file

    encode_file(source, MOD / "localisation/replace/010_gdd_b57_east_china_landmarks_l_english.yml")


def render_preview(bitmap: np.ndarray) -> None:
    crop = (4555, 775, 4680, 925)
    zoom = 6
    panel = Image.fromarray(bitmap[crop[1] : crop[3], crop[0] : crop[2]], mode="RGB")
    panel = panel.resize((panel.width * zoom, panel.height * zoom), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (800, 980), (20, 25, 31))
    canvas.paste(panel, (25, 55))
    draw = ImageDraw.Draw(canvas)
    try:
        title = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 28)
        label = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 19)
    except OSError:
        title = label = ImageFont.load_default()
    draw.text((25, 14), "B57：大别山、泰山与微山湖（实装图）", font=title, fill=(240, 244, 248))
    centres = {"泰山": (4651, 798), "微山湖": (4631, 825), "大别山": (4608, 882)}
    colours = {"泰山": (130, 174, 255), "微山湖": (225, 125, 230), "大别山": (255, 145, 140)}
    for name, (x, y) in centres.items():
        px = 25 + (x - crop[0]) * zoom
        py = 55 + (y - crop[1]) * zoom
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=colours[name], outline="white")
        draw.text((px + 10, py - 12), name, font=label, fill=colours[name], stroke_width=2, stroke_fill=(20, 25, 31))
    canvas.save(PREVIEW)


def validate(bitmap: np.ndarray, backup: np.ndarray, editable: np.ndarray) -> None:
    definitions: dict[int, tuple[int, int, int]] = {}
    colours: Counter[tuple[int, int, int]] = Counter()
    for line in (MAP / "definition.csv").read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 4 and fields[0].isdigit():
            province_id = int(fields[0])
            colour = (int(fields[1]), int(fields[2]), int(fields[3]))
            definitions[province_id] = colour
            colours[colour] += 1
    expected = {4010: WEISHAN[3], **{pid: data[2] for pid, data in MOUNTAINS.items()}}
    for province_id, colour in expected.items():
        if definitions.get(province_id) != colour or colours[colour] != 1:
            raise ValueError(f"Invalid definition for {province_id}: {definitions.get(province_id)}")
        if not np.any(np.all(bitmap == colour, axis=2)):
            raise ValueError(f"Province {province_id} has no bitmap pixels")

    x0, y0, x1, y1 = PATCH_BOX
    global_editable = np.zeros(bitmap.shape[:2], dtype=bool)
    global_editable[y0:y1, x0:x1] = editable
    changed = np.any(bitmap != backup, axis=2)
    exterior = changed & ~global_editable
    if np.any(exterior):
        raise ValueError(f"{int(exterior.sum())} pixels changed outside the reviewed patch")

    terrain_text = (MAP / "terrain.txt").read_text(encoding="latin-1")
    mountain_start, mountain_end = block_bounds(terrain_text, "mountain")
    nested_start, nested_end = block_bounds(terrain_text, "terrain_override", mountain_start, mountain_end)
    nested = terrain_text[nested_start:nested_end]
    for province_id in MOUNTAINS:
        if len(re.findall(rf"(?<!\d){province_id}(?!\d)", nested)) != 1:
            raise ValueError(f"Mountain {province_id} is not exactly once in mountain terrain_override")

    counts = {pid: int(np.all(bitmap == colour, axis=2).sum()) for pid, colour in expected.items()}
    expected_counts = {4010: 44, 5354: 431, 5355: 179}
    if counts != expected_counts:
        raise ValueError(f"Unexpected feature pixel counts: {counts}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, help="6400x2560 reviewed reference provinces.bmp")
    args = parser.parse_args()

    PLAN.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(PROVINCES, BACKUP)
    if not BEFORE_PATCH.exists() or not AFTER_PATCH.exists():
        if args.reference is None:
            raise SystemExit("Patch assets are missing; supply --reference on the first run")
        build_reviewed_patch(args.reference)

    bitmap, _, editable = apply_geometry()
    update_definitions()
    update_map_lists()
    update_localisation()
    backup = read_rgb(BACKUP)
    validate(bitmap, backup, editable)
    render_preview(bitmap)
    changed = int(np.any(bitmap != backup, axis=2).sum())
    print(
        "B57_EAST_CHINA_LANDMARKS_APPLIED "
        f"changed_pixels={changed} dabie=431 taishan=179 weishan=44 exterior=0"
    )


if __name__ == "__main__":
    main()
