#!/usr/bin/env python3
"""Apply the reviewed B58 Korea 39-province refinement transaction.

The geometry is stored as a compact guarded before/after patch.  The script
keeps the existing Korean area keys, preserves all nineteen peninsula IDs and
Jeju, adds nineteen playable IDs, and adds two impassable mountain IDs.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PLAN = ROOT / "planning/korea_refinement_b58"
PROVINCES_BMP = MAP / "provinces.bmp"
BEFORE_PATCH = PLAN / "b58_before_patch.png"
AFTER_PATCH = PLAN / "b58_after_patch.png"
MANIFEST = PLAN / "b58_manifest.json"
PREVIEW = PLAN / "b58_applied_preview.png"

MARKER = "GDD_B58_KOREA_39_PROVINCES"
KOREA_AREAS = (
    "pyongan_area", "hamgyeong_area", "western_korea_area",
    "eastern_korea_area", "south_korea_area",
)
PARENT_AREA = {
    1845: "pyongan_area", 2744: "pyongan_area", 4232: "pyongan_area",
    732: "hamgyeong_area", 2742: "hamgyeong_area", 2743: "hamgyeong_area",
    733: "western_korea_area", 735: "western_korea_area", 4230: "western_korea_area", 4231: "western_korea_area",
    734: "eastern_korea_area", 736: "eastern_korea_area", 2694: "eastern_korea_area", 2745: "eastern_korea_area", 4227: "eastern_korea_area",
    737: "south_korea_area", 1013: "south_korea_area", 4228: "south_korea_area", 4229: "south_korea_area",
}
PARENT_TERRAIN = {
    735: "farmlands", 2745: "farmlands",
    733: "hills", 2694: "hills", 2742: "hills", 2744: "hills", 4229: "hills", 4231: "hills",
    732: "mountain", 734: "mountain", 2743: "mountain", 4232: "mountain",
    737: "grasslands", 1013: "grasslands", 1845: "grasslands", 4227: "grasslands", 4230: "grasslands",
    736: "highlands", 4228: "highlands",
}
CLIMATE_BLOCKS = ("mild_winter", "normal_winter", "severe_winter", "mild_monsoon", "normal_monsoon")


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def rgb_image(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGB"), dtype=np.uint8, copy=True)


def block_bounds(text: str, name: str):
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        return None
    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return match.start(), index + 1
    raise ValueError(f"Unclosed block: {name}")


def replace_block(text: str, name: str, replacement: str) -> str:
    bounds = block_bounds(text, name)
    if bounds is None:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[:bounds[0]] + replacement.rstrip() + text[bounds[1]:]


def remove_marker_lines(text: str) -> str:
    return re.sub(rf"(?m)^.*{re.escape(MARKER)}.*\n?", "", text)


def append_to_block(text: str, name: str, ids: list[int], indent: str = "    ") -> str:
    if not ids:
        return text
    bounds = block_bounds(text, name)
    if bounds is None:
        raise ValueError(f"Missing block: {name}")
    block = text[bounds[0]:bounds[1]]
    close = block.rfind("}")
    line = f"\n{indent}{' '.join(map(str, sorted(ids)))} # {MARKER}\n"
    block = block[:close].rstrip() + line + block[close:]
    return text[:bounds[0]] + block + text[bounds[1]:]


def append_nested(text: str, outer: str, nested: str, ids: list[int]) -> str:
    if not ids:
        return text
    outer_bounds = block_bounds(text, outer)
    if outer_bounds is None:
        raise ValueError(f"Missing outer block: {outer}")
    outer_block = text[outer_bounds[0]:outer_bounds[1]]
    nested_bounds = block_bounds(outer_block, nested)
    if nested_bounds is None:
        raise ValueError(f"Missing {nested} in {outer}")
    nested_block = outer_block[nested_bounds[0]:nested_bounds[1]]
    close = nested_block.rfind("}")
    nested_block = nested_block[:close].rstrip() + f"\n        {' '.join(map(str, sorted(ids)))} # {MARKER}\n    " + nested_block[close:]
    outer_block = outer_block[:nested_bounds[0]] + nested_block + outer_block[nested_bounds[1]:]
    return text[:outer_bounds[0]] + outer_block + text[outer_bounds[1]:]


def apply_guarded_patch(manifest):
    current = rgb_image(PROVINCES_BMP)
    before_rgba = np.asarray(Image.open(BEFORE_PATCH).convert("RGBA"))
    after_rgba = np.asarray(Image.open(AFTER_PATCH).convert("RGBA"))
    x0, y0, x1, y1 = manifest["patch_box"]
    if before_rgba.shape != after_rgba.shape or before_rgba.shape[:2] != (y1 - y0, x1 - x0):
        raise ValueError("Guarded patch dimensions disagree with the manifest")
    mask = before_rgba[:, :, 3] > 0
    if not np.array_equal(mask, after_rgba[:, :, 3] > 0):
        raise ValueError("Before/after patch alpha masks differ")
    target = current[y0:y1, x0:x1]
    before = before_rgba[:, :, :3]
    after = after_rgba[:, :, :3]
    compatible = np.all(target == before, axis=2) | np.all(target == after, axis=2)
    conflicts = mask & ~compatible
    if conflicts.any():
        raise ValueError(f"Guarded patch overlaps {int(conflicts.sum())} unknown pixels")
    changed = mask & np.any(target != after, axis=2)
    target[mask] = after[mask]
    Image.fromarray(current).save(PROVINCES_BMP, format="BMP")
    return current, int(changed.sum()), mask


def update_definitions(manifest):
    definitions = {}
    for record in manifest["provinces"]:
        definitions[record["id"]] = (record["english"], tuple(record["rgb"]))
    for pid, data in manifest["mountains"].items():
        definitions[int(pid)] = (data["english"], tuple(data["rgb"]))
    path = MAP / "definition.csv"
    rows = path.read_text(encoding="latin-1").splitlines()
    output, seen = [], set()
    for row in rows:
        fields = row.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in definitions:
            pid = int(fields[0])
            name, rgb = definitions[pid]
            output.append(f"{pid};{rgb[0]};{rgb[1]};{rgb[2]};{name};x")
            seen.add(pid)
        else:
            output.append(row)
    for pid, (name, rgb) in sorted(definitions.items()):
        if pid not in seen:
            output.append(f"{pid};{rgb[0]};{rgb[1]};{rgb[2]};{name};x")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")

    path = MAP / "default.map"
    text = path.read_text(encoding="latin-1")
    current = int(re.search(r"(?m)^max_provinces\s*=\s*(\d+)", text).group(1))
    required = max(definitions) + 1
    if current < required:
        text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", f"max_provinces = {required}", text, count=1)
    path.write_text(text, encoding="latin-1")


def update_areas(manifest):
    grouped = defaultdict(list)
    for record in manifest["provinces"]:
        grouped[PARENT_AREA[record["parent_id"]]].append(record["id"])
    grouped["south_korea_area"].append(manifest["jeju_id"])
    path = MAP / "area.txt"
    text = path.read_text(encoding="latin-1")
    for area in KOREA_AREAS:
        ids = " ".join(map(str, sorted(grouped[area])))
        text = replace_block(text, area, f"{area} = {{ # {MARKER}; existing area retained\n    {ids}\n}}")
    path.write_text(text, encoding="latin-1")


def update_map_memberships(manifest):
    records = manifest["provinces"]
    new_records = [record for record in records if record["id"] in manifest["new_playable_ids"]]
    new_ids = sorted(record["id"] for record in new_records)
    mountain_ids = sorted(map(int, manifest["mountains"]))

    path = MAP / "continent.txt"
    text = remove_marker_lines(path.read_text(encoding="latin-1"))
    text = append_to_block(text, "asia", new_ids + mountain_ids)
    path.write_text(text, encoding="latin-1")

    path = MAP / "climate.txt"
    text = remove_marker_lines(path.read_text(encoding="latin-1"))
    for climate in CLIMATE_BLOCKS:
        bounds = block_bounds(text, climate)
        if bounds is None:
            continue
        existing_ids = set(map(int, re.findall(r"\b\d+\b", text[bounds[0]:bounds[1]])))
        inherited = [record["id"] for record in new_records if record["parent_id"] in existing_ids]
        text = append_to_block(text, climate, inherited)
    text = append_to_block(text, "impassable", mountain_ids)
    path.write_text(text, encoding="latin-1")

    path = MAP / "terrain.txt"
    text = remove_marker_lines(path.read_text(encoding="latin-1"))
    by_terrain = defaultdict(list)
    for record in new_records:
        by_terrain[PARENT_TERRAIN[record["parent_id"]]].append(record["id"])
    by_terrain["mountain"].extend(mountain_ids)
    categories_bounds = block_bounds(text, "categories")
    if categories_bounds is None:
        raise ValueError("Missing terrain categories block")
    categories = text[categories_bounds[0]:categories_bounds[1]]
    for terrain, ids in by_terrain.items():
        categories = append_nested(categories, terrain, "terrain_override", ids)
    text = text[:categories_bounds[0]] + categories + text[categories_bounds[1]:]
    path.write_text(text, encoding="latin-1")


def update_trade(manifest):
    # B73 is the terminal owner of all Korean trade-node and charter-company
    # membership.  B58 must not put newly created Korean provinces back into
    # Nippon when an older map batch is replayed.
    return None


def history_path(pid: int) -> Path:
    matches = sorted((MOD / "history/provinces").glob(f"{pid} - *.txt"))
    if len(matches) != 1:
        raise ValueError(f"Expected one local history for {pid}, found {len(matches)}")
    return matches[0]


def first_value(text: str, key: str, default: str | None = None) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^#\n]+)", text)
    if match:
        return match.group(1).strip()
    if default is None:
        raise ValueError(f"Missing history field: {key}")
    return default


def replace_first_value(text: str, key: str, value: str) -> str:
    pattern = rf"(?m)^(\s*{re.escape(key)}\s*=\s*)[^#\n]+"
    if re.search(pattern, text):
        return re.sub(pattern, rf"\g<1>{value}", text, count=1)
    return text.rstrip() + f"\n{key} = {value}\n"


def new_history(record, parent_text: str) -> str:
    lines = [
        f"# {record['id']} - {record['english']} - {MARKER}", "",
        f"owner = {first_value(parent_text, 'owner', 'KOR')}",
        f"controller = {first_value(parent_text, 'controller', 'KOR')}",
        f"culture = {first_value(parent_text, 'culture', 'korean')}",
        f"religion = {first_value(parent_text, 'religion', 'confucianism')}",
        f"capital = \"{record['english']}\"",
        f"trade_goods = {first_value(parent_text, 'trade_goods', 'grain')}",
        "hre = no",
        f"base_tax = {record['development'][0]}",
        f"base_production = {record['development'][1]}",
        f"base_manpower = {record['development'][2]}",
        "is_city = yes",
        f"add_core = {first_value(parent_text, 'add_core', 'KOR')}",
    ]
    discoveries = re.findall(r"(?m)^\s*discovered_by\s*=\s*([A-Za-z0-9_]+)", parent_text)
    for discovery in dict.fromkeys(discoveries[:2]):
        lines.append(f"discovered_by = {discovery}")
    for field in ("add_local_autonomy", "add_nationalism"):
        value = first_value(parent_text, field, "")
        if value:
            lines.append(f"{field} = {value}")
    lines.append("")
    return "\n".join(lines)


def update_histories(manifest):
    new_ids = set(manifest["new_playable_ids"])
    parent_texts = {pid: history_path(pid).read_text(encoding="latin-1") for pid in PARENT_AREA}
    for record in manifest["provinces"]:
        pid = record["id"]
        if pid in new_ids:
            path = MOD / "history/provinces" / f"{pid} - {record['english']}.txt"
            path.write_text(new_history(record, parent_texts[record["parent_id"]]), encoding="latin-1")
            continue
        path = history_path(pid)
        text = path.read_text(encoding="latin-1")
        text = re.sub(r"(?m)^#.*$", f"# {pid} - {record['english']} - {MARKER}", text, count=1)
        for key, value in zip(("base_tax", "base_production", "base_manpower"), record["development"]):
            text = replace_first_value(text, key, str(value))
        if re.search(r"(?m)^\s*capital\s*=", text):
            text = replace_first_value(text, "capital", f'"{record["english"]}"')
        else:
            text = re.sub(r"(?m)^(\s*religion\s*=.*)$", rf"\1\ncapital = \"{record['english']}\"", text, count=1)
        path.write_text(text, encoding="latin-1")


def position_block(pid: int, name: str, x: float, y: float) -> str:
    values = " ".join(f"{value:.3f}" for value in ([x, y] * 6 + [0.0, 0.0]))
    return f'''# {name} - {MARKER}
{pid}={{
    position={{
        {values}
    }}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 1.000 0.000 0.000 0.000 0.000
    }}
}}'''


def update_positions(manifest, bitmap):
    path = MAP / "positions.txt"
    text = remove_marker_lines(path.read_text(encoding="latin-1"))
    for record in manifest["provinces"]:
        rgb = tuple(record["rgb"])
        ys, xs = np.where(np.all(bitmap == rgb, axis=2))
        if not len(xs):
            raise ValueError(f"No pixels for position {record['id']}")
        cx, cy = xs.mean(), ys.mean()
        nearest = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
        x = float(xs[nearest])
        y = float(bitmap.shape[0] - ys[nearest])
        text = replace_block(text, str(record["id"]), position_block(record["id"], record["english"], x, y))
    path.write_text(text, encoding="latin-1")


def update_localisation(manifest):
    source = MOD / "localisation_source/011_gdd_b58_korea_refinement_readable_utf8.txt"
    lines = ["l_english:"]
    records = list(manifest["provinces"]) + [{
        "id": manifest["jeju_id"], "chinese": "济州",
    }]
    for record in sorted(records, key=lambda item: item["id"]):
        lines.append(f' PROV{record["id"]}:0 "{record["chinese"]}"')
        lines.append(f' PROV_ADJ{record["id"]}:0 "{record["chinese"]}"')
    for pid, data in sorted(manifest["mountains"].items(), key=lambda item: int(item[0])):
        lines.append(f' PROV{pid}:0 "{data["chinese"]}"')
        lines.append(f' PROV_ADJ{pid}:0 "{data["chinese"]}"')
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(source, MOD / "localisation/replace/011_gdd_b58_korea_refinement_l_english.yml")


def render_preview(bitmap, manifest):
    crop = (4725, 650, 4880, 875)
    scale = 5
    panel = Image.fromarray(bitmap).crop(crop).resize(((crop[2] - crop[0]) * scale, (crop[3] - crop[1]) * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (panel.width + 60, panel.height + 110), (35, 37, 43))
    canvas.paste(panel, (30, 75))
    draw = ImageDraw.Draw(canvas)
    font_candidates = (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    )
    font_path = next((candidate for candidate in font_candidates if Path(candidate).exists()), None)
    font = ImageFont.truetype(font_path, 28) if font_path else ImageFont.load_default()
    draw.text((canvas.width // 2, 34), "B58 朝鲜：39 个可玩省份、2 条不可通行山脉", font=font, fill=(245, 245, 245), anchor="mm")
    canvas.save(PREVIEW)


def validate_target(bitmap, manifest, editable_mask):
    definition_rows = {}
    rgb_rows = defaultdict(list)
    for line in (MAP / "definition.csv").read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 4 and fields[0].isdigit():
            pid = int(fields[0]); rgb = tuple(map(int, fields[1:4]))
            definition_rows[pid] = rgb; rgb_rows[rgb].append(pid)
    for record in manifest["provinces"]:
        pid, rgb = record["id"], tuple(record["rgb"])
        if definition_rows.get(pid) != rgb or rgb_rows[rgb] != [pid]:
            raise ValueError(f"Definition mismatch for {pid}")
        if not np.any(np.all(bitmap == rgb, axis=2)):
            raise ValueError(f"Zero-pixel playable province {pid}")
        history_path(pid)
    for pid_text, data in manifest["mountains"].items():
        pid, rgb = int(pid_text), tuple(data["rgb"])
        if definition_rows.get(pid) != rgb or rgb_rows[rgb] != [pid]:
            raise ValueError(f"Mountain definition mismatch for {pid}")
    if int(editable_mask.sum()) != manifest["editable_pixels"]:
        raise ValueError("Editable pixel count drift")
    max_provinces = int(re.search(r"(?m)^max_provinces\s*=\s*(\d+)", (MAP / "default.map").read_text()).group(1))
    if max(definition_rows) >= max_provinces:
        raise ValueError("max_provinces is not an exclusive upper bound")


def main():
    manifest = load_manifest()
    bitmap, changed, editable_mask = apply_guarded_patch(manifest)
    update_definitions(manifest)
    update_areas(manifest)
    update_map_memberships(manifest)
    update_trade(manifest)
    update_histories(manifest)
    update_positions(manifest, bitmap)
    update_localisation(manifest)
    render_preview(bitmap, manifest)
    validate_target(bitmap, manifest, editable_mask)
    total_dev = sum(sum(record["development"]) for record in manifest["provinces"]) + 3
    print(f"B58_KOREA_APPLIED; playable=39; new_playable=19; mountains=2; changed_pixels={changed}; total_development={total_dev}")


if __name__ == "__main__":
    main()
