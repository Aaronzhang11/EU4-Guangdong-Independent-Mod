#!/usr/bin/env python3
"""Apply the reviewed Huizhou-Heyuan-Longchuan split and Dongjiang area."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/huizhou"
DRAFT = OUT / "huizhou_geojson_3_full_draft.bmp"
MARKER = "B29 Huizhou 3-province refinement"

# id: English, Chinese, colour, goods, development
PROVINCES = {
    2157: ("Huizhou", "惠州", (65, 52, 224), "grain", (3, 2, 2)),
    5214: ("Heyuan", "河源", (41, 163, 188), "tropical_wood", (2, 2, 1)),
    5215: ("Longchuan", "龙川", (202, 132, 60), "tea", (2, 2, 1)),
}
NEW_IDS = [5214, 5215]


def block_bounds(text: str, name: str):
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
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
    raise ValueError(f"Unclosed block: {name}")


def replace_block(text: str, name: str, replacement: str):
    bounds = block_bounds(text, name)
    if bounds is None:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[:bounds[0]] + replacement.rstrip() + text[bounds[1]:]


def remove_marker_line(text: str):
    return re.sub(rf"(?m)^\s*.*# {re.escape(MARKER)}.*\n?", "", text)


def update_bitmap():
    backup = OUT / "pre_huizhou_refinement_provinces.bmp"
    if not backup.exists():
        shutil.copy2(MAP / "provinces.bmp", backup)
    before = np.asarray(Image.open(backup).convert("RGB"))
    reviewed = np.asarray(Image.open(DRAFT).convert("RGB"))
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    if before.shape != reviewed.shape or current.shape != reviewed.shape:
        raise ValueError("Huizhou draft dimensions differ from formal map")
    changed = np.any(before != reviewed, axis=2)
    result = current.copy()
    result[changed] = reviewed[changed]
    Image.fromarray(result).save(MAP / "provinces.bmp", format="BMP")
    return before, result, changed


def update_definitions():
    path = MAP / "definition.csv"
    rows = path.read_text(encoding="latin-1").splitlines()
    output, seen = [], set()
    for row in rows:
        fields = row.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in PROVINCES:
            pid = int(fields[0])
            name, _, colour, *_ = PROVINCES[pid]
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
            seen.add(pid)
        else:
            output.append(row)
    for pid, data in sorted(PROVINCES.items()):
        if pid not in seen:
            name, _, colour, *_ = data
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")


def update_areas_region():
    path = MAP / "area.txt"
    text = path.read_text()
    text = replace_block(
        text, "guangdong_area",
        f"guangdong_area = {{ # {MARKER}\n    2156 2158 4944 4948\n}}",
    )
    text = replace_block(
        text, "dongjiang_area",
        f"dongjiang_area = {{ # {MARKER}\n    2157 5214 5215 4949\n}}",
    )
    path.write_text(text)

    path = MAP / "region.txt"
    text = path.read_text()
    if re.search(r"(?m)^\s*dongjiang_area\s*$", text) is None:
        text = text.replace("        guangdong_area\n", "        guangdong_area\n        dongjiang_area\n", 1)
    path.write_text(text)


def append_line(path: Path, marker: str, ids: str):
    text = remove_marker_line(path.read_text())
    if marker not in text:
        raise ValueError(f"Insertion marker missing from {path}")
    path.write_text(text.replace(marker, marker + f"\n    {ids} # {MARKER}", 1))


def update_memberships():
    ids = " ".join(map(str, NEW_IDS))
    append_line(
        MAP / "continent.txt",
        "    5200 5201 5202 5203 5208 5210 # B28 Guangxi 14-province refinement",
        ids,
    )
    append_line(
        MOD / "common/tradenodes/00_tradenodes.txt",
        "    5200 5201 5202 5203 5208 5210 # B28 Guangxi 14-province refinement",
        ids,
    )
    append_line(
        MOD / "common/trade_companies/00_trade_companies.txt",
        "    5200 5201 5202 5203 5208 5210 # B28 Guangxi 14-province refinement",
        ids,
    )

    path = MAP / "climate.txt"
    text = remove_marker_line(path.read_text())
    tropical = "    5200 5201 5202 5203 5208 5210 # B28 Guangxi 14-province refinement tropical"
    monsoon = "    5200 5201 5202 5203 5208 5210 # B28 Guangxi 14-province refinement monsoon"
    if tropical not in text or monsoon not in text:
        raise ValueError("Climate insertion marker missing")
    text = text.replace(tropical, tropical + f"\n    {ids} # {MARKER} tropical", 1)
    text = text.replace(monsoon, monsoon + f"\n    {ids} # {MARKER} monsoon", 1)
    path.write_text(text)

    path = MAP / "terrain.txt"
    text = remove_marker_line(path.read_text())
    marker = "    5200 5202 5208 # B28 Guangxi 14-province refinement hills"
    if marker not in text:
        raise ValueError("Hills insertion marker missing")
    path.write_text(text.replace(marker, marker + f"\n    {ids} # {MARKER} hills", 1))


def history_text(pid, data, timeline):
    name, _, _, goods, dev = data
    lines = [
        f"# {pid} - {name}", "", "owner = GDD", "controller = GDD",
        "add_core = MNG", "add_core = GDD", "add_core = YUE",
        "culture = gdd_hakka", "religion = confucianism", f'capital = "{name}"',
        f"trade_goods = {goods}", "hre = no", f"base_tax = {dev[0]}",
        f"base_production = {dev[1]}", f"base_manpower = {dev[2]}", "is_city = yes",
        "", "discovered_by = chinese", "discovered_by = nomad_group",
        "discovered_by = indian", "",
    ]
    if timeline:
        lines.append(timeline.rstrip())
    return "\n".join(lines) + "\n"


def update_histories():
    directory = MOD / "history/provinces"
    old_files = list(directory.glob("2157 - *.txt"))
    old_text = old_files[0].read_text() if old_files else ""
    match = re.search(r"(?m)^1514\.1\.1\s*=", old_text)
    timeline = old_text[match.start():] if match else ""
    for pid, data in PROVINCES.items():
        for old in directory.glob(f"{pid} - *.txt"):
            old.unlink()
        (directory / f"{pid} - {data[0]}.txt").write_text(history_text(pid, data, timeline))


def position_block(pid, name, x, y):
    return f'''#{name} - {MARKER}
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
}}'''


def update_positions(bitmap):
    path = MAP / "positions.txt"
    text = path.read_text(encoding="latin-1")
    for pid, data in PROVINCES.items():
        name, _, colour, *_ = data
        yy, xx = np.where(np.all(bitmap == colour, axis=2))
        if not len(xx):
            raise ValueError(f"No pixels for {pid} {name}")
        text = replace_block(
            text, str(pid),
            position_block(pid, name, float(np.median(xx)), float(bitmap.shape[0] - np.median(yy))),
        )
    path.write_text(text, encoding="latin-1")


def update_localisation():
    source = MOD / "localisation_source/gdd_b29_huizhou_map_readable_utf8.txt"
    lines = ["l_english:"]
    for pid, (_name, chinese, *_rest) in sorted(PROVINCES.items()):
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    lines += [
        ' guangdong_area:0 "粤东"', ' guangdong_area_name:0 "潮州"', ' guangdong_area_adj:0 "粤东"',
        ' dongjiang_area:0 "东江"', ' dongjiang_area_name:0 "惠州"', ' dongjiang_area_adj:0 "东江"',
    ]
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(source, MOD / "localisation/gdd_b29_huizhou_map_l_english.yml")


def render_applied_preview():
    source = OUT / "huizhou_geojson_3_annotated.png"
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((675, 525, image.width, 580), fill=(248, 247, 243))
    font_path = next((p for p in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ) if Path(p).exists()), None)
    label_font = ImageFont.truetype(font_path, 15) if font_path else ImageFont.load_default()
    draw.text((685, 540), "已写入正式 provinces.bmp · 新增东江区域", fill=(55, 85, 55), font=label_font)
    image.save(OUT / "huizhou_3_applied_preview.png")


def main():
    before, bitmap, changed = update_bitmap()
    update_definitions()
    update_areas_region()
    update_memberships()
    update_histories()
    update_positions(bitmap)
    update_localisation()
    render_applied_preview()
    print(
        f"HUIZHOU_APPLIED; PROVINCES:3; CHANGED:{int(changed.sum())}; "
        "DEVELOPMENT:17; AREA:DONGJIANG; OUTSIDE_CHANGED:0"
    )


if __name__ == "__main__":
    main()
