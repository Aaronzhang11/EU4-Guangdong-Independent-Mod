#!/usr/bin/env python3
"""Apply the reviewed ten-province Liaoning workshop-geometry refinement."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/liaoning"
DRAFT = OUT / "liaoning_workshop_10_corrected_full_draft.bmp"
SOURCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
MARKER = "B27 Liaoning 10-province refinement"

# id: English, Chinese, colour, area, goods, development, culture, fort
PROVINCES = {
    726: ("Shenyang", "沈阳", (103, 76, 64), "liaoning_area", "cloth", (4, 4, 3), "gdd_khitan", True),
    5204: ("Liaoyang", "辽阳", (150, 117, 28), "liaoning_area", "iron", (5, 5, 5), "gdd_khitan", False),
    5205: ("Tieling", "铁岭", (255, 236, 11), "liaoning_area", "livestock", (2, 3, 3), "manchu", False),
    2112: ("Jiuliancheng", "九连城", (115, 210, 143), "liaoning_area", "fur", (2, 2, 3), "manchu", False),
    4652: ("Haicheng", "海城", (140, 69, 200), "liaoning_area", "grain", (3, 3, 2), "gdd_qi", False),
    2113: ("Gaizhou", "盖州", (193, 133, 132), "liaoning_area", "fish", (3, 3, 3), "gdd_qi", False),
    5206: ("Liaohetao", "辽河套", (165, 28, 167), "xi_liaoning_area", "grain", (3, 3, 2), "manchu", False),
    704: ("Ningyuan", "宁远", (100, 32, 255), "xi_liaoning_area", "salt", (3, 2, 3), "gdd_dongyi", True),
    5207: ("Guangning", "广宁", (216, 196, 193), "xi_liaoning_area", "livestock", (4, 3, 3), "gdd_yan", False),
    5209: ("Jinzhou", "锦州", (187, 198, 158), "xi_liaoning_area", "salt", (3, 4, 3), "gdd_dongyi", False),
}
NEW_IDS = {5204, 5205, 5206, 5207, 5209}
AREA_BLOCKS = {
    "liaoning_area": [726, 5204, 5205, 2112, 4652, 2113],
    "xi_liaoning_area": [5206, 704, 5207, 5209],
}
OWNER_BY_ID = {
    726: "LIO", 5204: "LIO", 5205: "LIO", 2112: "LIO", 4652: "LIO", 2113: "LIO",
    5206: "YAN", 5207: "YAN", 704: "WUZ", 5209: "WUZ",
}


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
    raise ValueError(f"Unclosed block {name}")


def replace_block(text: str, name: str, replacement: str):
    bounds = block_bounds(text, name)
    if bounds is None:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[:bounds[0]] + replacement.rstrip() + text[bounds[1]:]


def remove_marker_line(text: str):
    return re.sub(rf"(?m)^\s*.*# {re.escape(MARKER)}.*\n?", "", text)


def append_nested_ids(text: str, outer: str, nested: str, ids: set[int]) -> str:
    outer_bounds = block_bounds(text, outer)
    if outer_bounds is None:
        raise ValueError(f"Missing outer block {outer}")
    block = text[outer_bounds[0]:outer_bounds[1]]
    nested_bounds = block_bounds(block, nested)
    if nested_bounds is None:
        raise ValueError(f"Missing {nested} block in {outer}")
    nested_block = block[nested_bounds[0]:nested_bounds[1]]
    close = nested_block.rfind("}")
    insertion = "\n        " + " ".join(map(str, sorted(ids))) + f" # {MARKER}\n    "
    nested_block = nested_block[:close].rstrip() + insertion + nested_block[close:]
    block = block[:nested_bounds[0]] + nested_block + block[nested_bounds[1]:]
    return text[:outer_bounds[0]] + block + text[outer_bounds[1]:]


def update_bitmap():
    backup = OUT / "pre_liaoning_refinement_provinces.bmp"
    if not backup.exists():
        shutil.copy2(MAP / "provinces.bmp", backup)
    before = np.asarray(Image.open(backup).convert("RGB"))
    reviewed = np.asarray(Image.open(DRAFT).convert("RGB"))
    if before.shape != reviewed.shape:
        raise ValueError("Liaoning draft dimensions differ from formal map")
    changed = np.any(before != reviewed, axis=2)
    result = before.copy()
    result[changed] = reviewed[changed]
    Image.fromarray(result).save(MAP / "provinces.bmp", format="BMP")
    return result, int(changed.sum())


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


def update_areas_regions():
    path = MAP / "area.txt"
    text = path.read_text()
    for area, ids in AREA_BLOCKS.items():
        text = replace_block(text, area, f"{area} = {{ # {MARKER}\n    {' '.join(map(str, ids))}\n}}")
    path.write_text(text)

    path = MAP / "region.txt"
    text = path.read_text()
    if re.search(r"(?m)^\s*xi_liaoning_area\s*$", text) is None:
        text = text.replace("        liaoning_area\n", "        liaoning_area\n        xi_liaoning_area\n", 1)
    path.write_text(text)


def update_lists():
    new = " ".join(map(str, sorted(NEW_IDS)))

    path = MAP / "continent.txt"
    text = remove_marker_line(path.read_text())
    marker = "    5286 5287 5288 5289 5290 5291 5292 5293 5294 5295 5296 5297 5298 5299 5300 # B26 Gansu-Ningxia 23-province refinement"
    text = text.replace(marker, marker + f"\n    {new} # {MARKER}", 1)
    path.write_text(text)

    path = MOD / "common/tradenodes/00_tradenodes.txt"
    text = remove_marker_line(path.read_text())
    text = append_nested_ids(text, "girin", "members", {5204, 5205})
    text = append_nested_ids(text, "beijing", "members", {5206, 5207, 5209})
    path.write_text(text)

    path = MOD / "common/trade_companies/00_trade_companies.txt"
    text = remove_marker_line(path.read_text())
    marker = "        704 726 2112 2113 4652  #Liaoning"
    text = text.replace(marker, marker + f"\n        {new} # {MARKER}", 1)
    path.write_text(text)

    path = MAP / "climate.txt"
    text = remove_marker_line(path.read_text())
    marker = "    5286 5287 5288 5289 5290 5291 5292 5293 5294 5295 5296 5297 # B26 Gansu-Ningxia 23-province refinement"
    text = text.replace(marker, marker + f"\n    {new} # {MARKER}", 1)
    path.write_text(text)

    path = MAP / "terrain.txt"
    text = remove_marker_line(path.read_text())
    farmland_marker = "    5287 5291 5296 # B26 Gansu-Ningxia 23-province refinement farmlands"
    text = text.replace(farmland_marker, farmland_marker + f"\n    5204 # {MARKER} farmlands", 1)
    grass_marker = "    5286 5292 5295 # B26 Gansu-Ningxia 23-province refinement grasslands"
    text = text.replace(grass_marker, grass_marker + f"\n    5205 5206 5207 5209 # {MARKER} grasslands", 1)
    path.write_text(text)


def history_text(pid, data):
    name, _, _, _, goods, dev, culture, fort = data
    owner = OWNER_BY_ID[pid]
    lines = [
        f"# {pid} - {name}", "", f"owner = {owner}", f"controller = {owner}", f"add_core = {owner}",
        f"culture = {culture}", "religion = confucianism", f'capital = "{name}"',
        f"trade_goods = {goods}", f"base_tax = {dev[0]}", f"base_production = {dev[1]}",
        f"base_manpower = {dev[2]}", "is_city = yes",
    ]
    if pid == 726:
        lines.append("center_of_trade = 1")
    if fort:
        lines.append("fort_15th = yes")
    lines += ["discovered_by = chinese", "discovered_by = nomad_group", ""]
    return "\n".join(lines)


def update_histories():
    directory = MOD / "history/provinces"
    for pid, data in PROVINCES.items():
        for old in directory.glob(f"{pid} - *.txt"):
            old.unlink()
        (directory / f"{pid} - {data[0]}.txt").write_text(history_text(pid, data))


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
        x = float(np.median(xx))
        y = float(bitmap.shape[0] - np.median(yy))
        text = replace_block(text, str(pid), position_block(pid, name, x, y))
    path.write_text(text, encoding="latin-1")


def update_localisation():
    path = MOD / "localisation_source/gdd_b27_liaoning_refinement_utf8.txt"
    lines = ["l_english:"]
    for pid, (_, chinese, *_rest) in sorted(PROVINCES.items()):
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    lines += [
        ' liaoning_area:0 "辽东"', ' liaoning_area_name:0 "沈阳"', ' liaoning_area_adj:0 "辽东"',
        ' xi_liaoning_area:0 "辽西"', ' xi_liaoning_area_name:0 "广宁"', ' xi_liaoning_area_adj:0 "辽西"',
    ]
    path.write_text("\n".join(lines) + "\n")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(path, MOD / "localisation/gdd_b27_liaoning_refinement_l_english.yml")


def main():
    bitmap, changed = update_bitmap()
    update_definitions()
    update_areas_regions()
    update_lists()
    update_histories()
    update_positions(bitmap)
    update_localisation()
    print(f"LIAONING_APPLIED; PROVINCES:10; CHANGED:{changed}; COT:726=1")


if __name__ == "__main__":
    main()
