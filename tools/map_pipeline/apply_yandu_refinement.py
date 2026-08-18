#!/usr/bin/env python3
"""Apply the reviewed five-province mountain-border Yandu refinement."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
DRAFT = ROOT / "planning/beijing/yandu_mountain_border_5_full_draft.bmp"

PROVINCES = [
    (5113, "Changping", "昌平", (36, 183, 73), "grain", 4, 3, 3),
    (5114, "Miyun", "密云", (210, 64, 142), "iron", 3, 4, 3),
    (1816, "Ji", "蓟", (89, 177, 232), "cloth", 7, 7, 4),
    (5115, "Tongzhou", "通州", (241, 116, 35), "grain", 5, 5, 3),
    (5116, "Zhuozhou", "涿州", (132, 74, 218), "iron", 4, 4, 3),
]

# Keep the dependency's exact history filename so this mod shadows it in the
# EU4 virtual filesystem even though the province's in-game name is now Ji.
HISTORY_FILENAMES = {1816: "1816 - Beijing.txt"}


def replace_block(text, key, replacement):
    match = re.search(rf"(?m)^\s*{re.escape(str(key))}\s*=\s*\{{", text)
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
    raise ValueError(key)


def apply_geometry():
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB")).copy()
    reviewed = np.asarray(Image.open(DRAFT).convert("RGB"))
    changed = np.any(current != reviewed, axis=2)
    current[changed] = reviewed[changed]
    Image.fromarray(current).save(MAP / "provinces.bmp", format="BMP")
    return current


def update_definition():
    path = MAP / "definition.csv"
    rows = path.read_text(encoding="latin-1").splitlines()
    records = {p[0]: p for p in PROVINCES}
    # The old misplaced Beijing province becomes Hejian after the relocation.
    records[695] = (695, "Hejian", "河间", (227, 142, 0), "grain", 4, 4, 3)
    seen = set()
    output = []
    for row in rows:
        fields = row.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in records:
            pid, name, _, color, *_ = records[int(fields[0])]
            output.append(f"{pid};{color[0]};{color[1]};{color[2]};{name};x")
            seen.add(pid)
        else:
            output.append(row)
    for pid, name, _, color, *_ in PROVINCES:
        if pid not in seen:
            output.append(f"{pid};{color[0]};{color[1]};{color[2]};{name};x")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")


def update_area_region():
    path = MAP / "area.txt"
    text = path.read_text()
    text = re.sub(r"(?s)(hebei_area\s*=\s*\{.*?)(\b1816\b\s*)", r"\1", text, count=1)
    block = """yandu_area = {
    5113 5114 1816 5115 5116
}"""
    text = replace_block(text, "yandu_area", block)
    path.write_text(text)

    path = MAP / "region.txt"
    text = path.read_text()
    if "        yandu_area" not in text:
        text = text.replace("        hebei_area", "        hebei_area\n        yandu_area", 1)
    path.write_text(text)


def update_lists():
    path = MAP / "continent.txt"
    text = path.read_text()
    marker = "        5101 5102 5103 5104 5105 5106 5107 5108 5109 5110 5111 5112 # B20 Shandong refinement"
    if "5113 5114 5115 5116 # B21 Yandu" not in text:
        text = text.replace(marker, marker + "\n        5113 5114 5115 5116 # B21 Yandu refinement")
    path.write_text(text)

    path = MOD / "common/tradenodes/00_tradenodes.txt"
    text = path.read_text()
    marker = "        5101 5102 5103 5104 5105 5106 5107 5108 5109 5110 5111 5112 # B20 Shandong"
    if "5113 5114 5115 5116 # B21 Yandu" not in text:
        text = text.replace(marker, marker + "\n        5113 5114 5115 5116 # B21 Yandu")
    path.write_text(text)

    path = MAP / "default.map"
    text = path.read_text()
    text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5117", text)
    path.write_text(text)


def history_text(pid, name, goods, tax, production, manpower):
    return f"""# {pid} - {name}

owner = MNG
controller = MNG
add_core = MNG
culture = gdd_yan
religion = confucianism
capital = \"{name}\"
trade_goods = {goods}
base_tax = {tax}
base_production = {production}
base_manpower = {manpower}
is_city = yes
discovered_by = chinese
discovered_by = nomad_group
"""


def update_histories():
    directory = MOD / "history/provinces"
    records = PROVINCES + [(695, "Hejian", "河间", (227, 142, 0), "grain", 4, 4, 3)]
    for pid, name, _, _, goods, tax, production, manpower in records:
        desired = directory / HISTORY_FILENAMES.get(pid, f"{pid} - {name}.txt")
        for old in directory.glob(f"{pid} - *.txt"):
            if old != desired:
                old.unlink()
        desired.write_text(history_text(pid, name, goods, tax, production, manpower))


def update_positions(bitmap):
    path = MAP / "positions.txt"
    text = path.read_text(encoding="latin-1")
    for pid, name, _, color, *_ in PROVINCES:
        yy, xx = np.nonzero(np.all(bitmap == color, axis=2))
        x, y = float(np.median(xx)), float(2048 - np.median(yy))
        block = f"""#{name} - Yandu five-province refinement
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
        text = replace_block(text, pid, block)
    path.write_text(text, encoding="latin-1")


def update_localisation():
    path = MOD / "localisation_source/gdd_b21_yandu_map_readable_utf8.txt"
    lines = ["l_english:"]
    for pid, _, chinese, *_ in PROVINCES:
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    lines += [
        ' PROV695:0 "河间"', ' PROV_ADJ695:0 "河间"',
        ' yandu_area:0 "燕都"', ' yandu_area_name:0 "燕"', ' yandu_area_adj:0 "燕都"',
    ]
    path.write_text("\n".join(lines) + "\n")


def main():
    bitmap = apply_geometry()
    update_definition()
    update_area_region()
    update_lists()
    update_histories()
    update_positions(bitmap)
    update_localisation()
    print("YANDU_REFINEMENT_APPLIED:5")


if __name__ == "__main__":
    main()
