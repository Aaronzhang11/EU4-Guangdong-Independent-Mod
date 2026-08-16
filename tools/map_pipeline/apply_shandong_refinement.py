#!/usr/bin/env python3
"""Apply the reviewed 17-province Shandong draft to the mod."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
DRAFT = ROOT / "planning/shandong/shandong_geojson_historical_17_full_draft.bmp"

PROVINCES = [
    (5101, "Linqing", "临清", (201, 79, 74), "cloth", 4, 6, 3),
    (5102, "Dezhou", "德州", (78, 121, 189), "grain", 3, 3, 3),
    (2138, "Wuding", "武定", (106, 168, 79), "salt", 3, 4, 3),
    (5103, "Dongchang", "东昌", (190, 122, 54), "grain", 3, 3, 3),
    (691, "Jinan", "济南", (128, 95, 170), "paper", 6, 6, 3),
    (5104, "Linzi", "临淄", (220, 151, 43), "chinaware", 4, 5, 3),
    (5105, "Qingzhou", "青州", (55, 157, 176), "grain", 4, 5, 3),
    (2139, "Laizhou", "莱州", (215, 106, 157), "iron", 4, 4, 3),
    (690, "Dengzhou", "登州", (139, 121, 88), "fish", 4, 4, 3),
    (5106, "Ninghai", "宁海", (70, 175, 128), "fish", 3, 3, 2),
    (5107, "Jiaozhou", "胶州", (170, 91, 187), "salt", 4, 4, 3),
    (5108, "Taian", "泰安", (57, 105, 200), "grain", 3, 3, 3),
    (2140, "Yanzhou", "兖州", (214, 128, 77), "grain", 5, 4, 4),
    (5109, "Qufu", "曲阜", (79, 142, 91), "paper", 5, 4, 3),
    (5110, "Jining", "济宁", (202, 84, 118), "cloth", 5, 5, 4),
    (5111, "Caozhou", "曹州", (112, 133, 55), "grain", 3, 3, 4),
    (5112, "Yizhou", "沂州", (48, 148, 164), "livestock", 3, 3, 3),
]
CULTURE_BY_ID = {
    5101: "gdd_zhongyuan",
    5102: "gdd_qi",
    2138: "gdd_qi",
    5103: "gdd_zhongyuan",
    691: "gdd_qi",
    5104: "gdd_qi",
    5105: "gdd_qi",
    2139: "gdd_qi",
    690: "gdd_qi",
    5106: "gdd_qi",
    5107: "gdd_qi",
    5108: "gdd_qi",
    2140: "gdd_qi",
    5109: "gdd_qi",
    5110: "gdd_zhongyuan",
    5111: "gdd_zhongyuan",
    5112: "gdd_qi",
}

OLD_COLORS = {(98, 132, 0), (226, 134, 64), (86, 118, 240), (145, 24, 24), (238, 254, 148)}
NEW_COLORS = {p[3] for p in PROVINCES}


def mask_for(arr, colors):
    result = np.zeros(arr.shape[:2], dtype=bool)
    for color in colors:
        result |= np.all(arr == color, axis=2)
    return result


def replace_brace_block(text, key, replacement):
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        return text + "\n" + replacement + "\n"
    start = match.start()
    brace = text.find("{", match.start())
    depth = 0
    end = brace
    for end in range(brace, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                end += 1
                break
    return text[:start] + replacement + text[end:]


def apply_geometry():
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB")).copy()
    reviewed = np.asarray(Image.open(DRAFT).convert("RGB"))
    mask = mask_for(current, OLD_COLORS | NEW_COLORS) | mask_for(reviewed, NEW_COLORS)
    current[mask] = reviewed[mask]
    Image.fromarray(current).save(MAP / "provinces.bmp", format="BMP")
    return current


def update_definition():
    path = MAP / "definition.csv"
    lines = path.read_text(encoding="latin-1").splitlines()
    records = {p[0]: p for p in PROVINCES}
    seen = set()
    out = []
    for line in lines:
        fields = line.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in records:
            pid, name, _, (r, g, b), *_ = records[int(fields[0])]
            out.append(f"{pid};{r};{g};{b};{name};x")
            seen.add(pid)
        else:
            out.append(line)
    for pid, name, _, (r, g, b), *_ in PROVINCES:
        if pid not in seen:
            out.append(f"{pid};{r};{g};{b};{name};x")
    path.write_text("\n".join(out) + "\n", encoding="latin-1")


def update_map_lists():
    area_path = MAP / "area.txt"
    area = area_path.read_text()
    replacement = """luxi_area = {
    5101 5102 5103 5111
}

qizhou_area = {
    2138 691 5104 5105
}

denglai_area = {
    2139 690 5106 5107
}

lunan_area = {
    5108 2140 5109 5110 5112
}"""
    for key in ("shandong_area", "luxi_area", "qizhou_area", "denglai_area", "lunan_area"):
        while re.search(rf"(?m)^\s*{key}\s*=\s*\{{", area):
            area = replace_brace_block(area, key, "")
    area = area.rstrip() + "\n\n" + replacement + "\n"
    area_path.write_text(area)

    region_path = MAP / "region.txt"
    region = region_path.read_text()
    region = region.replace(
        "        shandong_area",
        "        luxi_area\n        qizhou_area\n        denglai_area\n        lunan_area",
    )
    region_path.write_text(region)

    continent_path = MAP / "continent.txt"
    continent = continent_path.read_text()
    marker = "        5096 5097 5098 5099 5100 # B19 Fujian 13-province refinement"
    if "5101 5102 5103 5104" not in continent:
        continent = continent.replace(marker, marker + "\n        5101 5102 5103 5104 5105 5106 5107 5108 5109 5110 5111 5112 # B20 Shandong refinement")
    continent_path.write_text(continent)

    node_path = MOD / "common/tradenodes/00_tradenodes.txt"
    nodes = node_path.read_text()
    marker = "        690 691 702 2138 2139 2140 2114 2747 703 1816 2136 4194 695 696 2137 4195 704 726 2112 2113 693 694 697 2177 2178 4233 4652 4671 4670"
    if "5101 5102 5103 5104 5105 5106" not in nodes:
        nodes = nodes.replace(marker, marker + "\n        5101 5102 5103 5104 5105 5106 5107 5108 5109 5110 5111 5112 # B20 Shandong")
    node_path.write_text(nodes)

    default_path = MAP / "default.map"
    default = default_path.read_text()
    default = re.sub(r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5113", default)
    default_path.write_text(default)


def update_histories():
    history_dir = MOD / "history/provinces"
    for pid, name, _, _, goods, tax, prod, manpower in PROVINCES:
        for old in history_dir.glob(f"{pid} - *.txt"):
            old.unlink()
        text = f"""# {pid} - {name}

owner = MNG
controller = MNG
add_core = MNG
culture = {CULTURE_BY_ID[pid]}
religion = confucianism
capital = \"{name}\"
trade_goods = {goods}
base_tax = {tax}
base_production = {prod}
base_manpower = {manpower}
is_city = yes
discovered_by = chinese
discovered_by = nomad_group
"""
        (history_dir / f"{pid} - {name}.txt").write_text(text)


def update_positions(bitmap):
    path = MAP / "positions.txt"
    text = path.read_text(encoding="latin-1")
    for pid, name, _, color, *_ in PROVINCES:
        yy, xx = np.nonzero(np.all(bitmap == color, axis=2))
        x = float(np.median(xx))
        y = float(2048 - np.median(yy))
        block = f"""#{name} - Shandong 17-province refinement
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
        text = replace_brace_block(text, str(pid), block)
    path.write_text(text, encoding="latin-1")


def update_localisation():
    path = MOD / "localisation_source/gdd_b20_shandong_map_readable_utf8.txt"
    lines = ["l_english:"]
    for pid, _, chinese, *_ in PROVINCES:
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    lines += [
        ' luxi_area:0 "鲁西"', ' luxi_area_name:0 "东昌"', ' luxi_area_adj:0 "鲁西"',
        ' qizhou_area:0 "齐州"', ' qizhou_area_name:0 "济南"', ' qizhou_area_adj:0 "齐州"',
        ' denglai_area:0 "登莱"', ' denglai_area_name:0 "登州"', ' denglai_area_adj:0 "登莱"',
        ' lunan_area:0 "鲁南"', ' lunan_area_name:0 "曲阜"', ' lunan_area_adj:0 "鲁南"',
    ]
    path.write_text("\n".join(lines) + "\n")


def main():
    bitmap = apply_geometry()
    update_definition()
    update_map_lists()
    update_histories()
    update_positions(bitmap)
    update_localisation()
    print("SHANDONG_REFINEMENT_APPLIED:17")


if __name__ == "__main__":
    main()
