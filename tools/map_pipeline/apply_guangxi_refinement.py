#!/usr/bin/env python3
"""Apply the reviewed fourteen-province Guangxi refinement."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/guangxi"
DRAFT = OUT / "guangxi_workshop_14_full_draft.bmp"
MARKER = "B28 Guangxi 14-province refinement"

# id: English, Chinese, colour, area, goods, development, culture
PROVINCES = {
    1840: ("Guilin", "桂林", (208, 138, 79), "guangxi_area", "silk", (4, 4, 2), "zhuang"),
    2163: ("Liuzhou", "柳州", (67, 62, 128), "guangxi_area", "salt", (3, 3, 2), "zhuang"),
    5200: ("Pingle", "平乐", (83, 24, 236), "guangxi_area", "iron", (2, 2, 2), "zhuang"),
    5208: ("Quanzhou", "全州", (227, 142, 44), "guangxi_area", "grain", (2, 2, 2), "zhuang"),
    4959: ("Qingyuan", "庆远", (22, 216, 219), "guidong_area", "livestock", (2, 2, 3), "zhuang"),
    5201: ("Sien", "思恩", (162, 74, 195), "guidong_area", "tropical_wood", (2, 2, 2), "zhuang"),
    2162: ("Wuzhou", "梧州", (68, 78, 64), "guidong_area", "copper", (3, 4, 2), "cantonese"),
    4954: ("Xunzhou", "浔州", (152, 52, 251), "guidong_area", "grain", (2, 3, 2), "cantonese"),
    5202: ("Yuzhou", "玉林", (195, 84, 100), "guidong_area", "grain", (2, 2, 2), "cantonese"),
    2164: ("Nanning", "南宁", (67, 70, 192), "youjiang_area", "grain", (3, 3, 2), "zhuang"),
    664: ("Sicheng", "泗城", (94, 80, 255), "youjiang_area", "tea", (1, 2, 2), "zhuang"),
    4960: ("Zhenan", "镇安", (182, 187, 245), "youjiang_area", "sugar", (1, 2, 2), "zhuang"),
    5203: ("Siming", "思明", (50, 52, 170), "youjiang_area", "spices", (1, 2, 2), "zhuang"),
    5210: ("Tianzhou", "田州", (69, 166, 112), "youjiang_area", "iron", (2, 2, 2), "zhuang"),
}
NEW_IDS = {5200, 5201, 5202, 5203, 5208, 5210}
AREA_BLOCKS = {
    "guangxi_area": [1840, 2163, 5200, 5208],
    "guidong_area": [4959, 5201, 2162, 4954, 5202],
    "youjiang_area": [2164, 664, 4960, 5203, 5210],
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


def absorb_minor_components(bitmap):
    """Fold three workshop-geometry crumbs into their touching neighbours."""
    transfers = {
        2162: 5200,  # detached eastern Wuzhou fragment -> Pingle
        664: 5210,   # one-pixel Sicheng spur -> Tianzhou
        5210: 4959,  # two isolated Tianzhou pixels -> Qingyuan
    }
    result = bitmap.copy()
    for source_id, target_id in transfers.items():
        source_colour = PROVINCES[source_id][2]
        target_colour = PROVINCES[target_id][2]
        mask = np.all(bitmap == source_colour, axis=2)
        seen = np.zeros(mask.shape, dtype=bool)
        components = []
        for y, x in zip(*np.where(mask)):
            if seen[y, x]:
                continue
            cells = []
            queue = deque([(int(y), int(x))])
            seen[y, x] = True
            while queue:
                cy, cx = queue.popleft()
                cells.append((cy, cx))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = cy + dy, cx + dx
                    if (0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1]
                            and mask[ny, nx] and not seen[ny, nx]):
                        seen[ny, nx] = True
                        queue.append((ny, nx))
            components.append(cells)
        if len(components) <= 1:
            continue
        largest = max(components, key=len)
        for cells in components:
            if cells is largest:
                continue
            yy, xx = zip(*cells)
            result[np.array(yy), np.array(xx)] = target_colour
    return result


def update_bitmap():
    backup = OUT / "pre_guangxi_refinement_provinces.bmp"
    if not backup.exists():
        shutil.copy2(MAP / "provinces.bmp", backup)
    before = np.asarray(Image.open(backup).convert("RGB"))
    reviewed = np.asarray(Image.open(DRAFT).convert("RGB"))
    reviewed = absorb_minor_components(reviewed)
    Image.fromarray(reviewed).save(DRAFT, format="BMP")
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    if before.shape != reviewed.shape or current.shape != reviewed.shape:
        raise ValueError("Guangxi draft dimensions differ from formal map")
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


def update_areas_regions():
    path = MAP / "area.txt"
    text = path.read_text()
    for area, ids in AREA_BLOCKS.items():
        block = f"{area} = {{ # {MARKER}\n    {' '.join(map(str, ids))}\n}}"
        text = replace_block(text, area, block)
    path.write_text(text)

    path = MAP / "region.txt"
    text = path.read_text()
    if re.search(r"(?m)^\s*guidong_area\s*$", text) is None:
        text = text.replace("        guangxi_area\n", "        guangxi_area\n        guidong_area\n", 1)
    path.write_text(text)


def append_after_marker(path: Path, marker: str, ids: str):
    text = remove_marker_line(path.read_text())
    if marker not in text:
        raise ValueError(f"Insertion marker not found in {path}: {marker}")
    path.write_text(text.replace(marker, marker + f"\n    {ids} # {MARKER}", 1))


def update_lists():
    new = " ".join(map(str, sorted(NEW_IDS)))
    append_after_marker(
        MAP / "continent.txt",
        "    5204 5205 5206 5207 5209 # B27 Liaoning 10-province refinement",
        new,
    )
    append_after_marker(
        MOD / "common/tradenodes/00_tradenodes.txt",
        "        4942 4943 4944 4945 4946 4947 4948 4949 4954 4955 4959 4960 4961 4982 4983 4996 4997 4998 4999 5000 5001 # B01 Guangdong, P02 Guangxi/Taiwan and B07 Hunan",
        new,
    )
    append_after_marker(
        MOD / "common/trade_companies/00_trade_companies.txt",
        "        4942 4943 4944 4945 4946 4947 4948 4949 4954 4955 4959 4960 4961 4982 4983 4996 4997 4998 4999 5000 5001 # B01 Guangdong, P02 Guangxi/Taiwan and B07 Hunan",
        new,
    )

    path = MAP / "climate.txt"
    text = remove_marker_line(path.read_text())
    tropical_marker = "    5301 5302 5303 5304 # B27 Hainan five-province refinement"
    first = text.find(tropical_marker)
    if first < 0:
        raise ValueError("Tropical climate marker not found")
    text = text[:first] + text[first:].replace(
        tropical_marker, tropical_marker + f"\n    {new} # {MARKER} tropical", 1
    )
    monsoon_marker = "    5242 5243 5244 5245 5246 5247 5248 5251 5252 5249 5250 5255 5256 5253 5254 # B23 Shanxi 20-province refinement"
    if monsoon_marker not in text:
        raise ValueError("Monsoon climate marker not found")
    text = text.replace(monsoon_marker, monsoon_marker + f"\n    {new} # {MARKER} monsoon", 1)
    path.write_text(text)

    path = MAP / "terrain.txt"
    text = remove_marker_line(path.read_text())
    hill_marker = "    5289 5290 5294 # B26 Gansu-Ningxia 23-province refinement hills"
    high_marker = "    5242 5244 5246 5247 5251 5252 5255 5256 # B23 Shanxi 20-province refinement highlands"
    if hill_marker not in text or high_marker not in text:
        raise ValueError("Terrain insertion marker not found")
    text = text.replace(hill_marker, hill_marker + f"\n    5200 5202 5208 # {MARKER} hills", 1)
    text = text.replace(high_marker, high_marker + f"\n    5201 5203 5210 # {MARKER} highlands", 1)
    path.write_text(text)


def history_text(pid, data):
    name, _, _, _, goods, dev, culture = data
    owner = "NUN" if pid in {4960, 5201, 5203} else "MNG"
    lines = [
        f"# {pid} - {name}", "", f"owner = {owner}", f"controller = {owner}", f"add_core = {owner}",
    ]
    lines += [
        f"culture = {culture}", "religion = confucianism", f'capital = "{name}"',
        f"trade_goods = {goods}", f"base_tax = {dev[0]}", f"base_production = {dev[1]}",
        f"base_manpower = {dev[2]}", "is_city = yes",
    ]
    if pid == 2162:
        lines.append("center_of_trade = 1")
    lines += ["discovered_by = chinese", ""]
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
    path = MOD / "localisation_source/gdd_b28_guangxi_refinement_utf8.txt"
    lines = ["l_english:"]
    for pid, (_, chinese, *_rest) in sorted(PROVINCES.items()):
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    lines += [
        ' guangxi_area:0 "桂北"', ' guangxi_area_name:0 "桂林"', ' guangxi_area_adj:0 "桂北"',
        ' guidong_area:0 "桂东"', ' guidong_area_name:0 "梧州"', ' guidong_area_adj:0 "桂东"',
        ' youjiang_area:0 "桂西"', ' youjiang_area_name:0 "南宁"', ' youjiang_area_adj:0 "桂西"',
    ]
    path.write_text("\n".join(lines) + "\n")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(path, MOD / "localisation/gdd_b28_guangxi_map_l_english.yml")


def render_preview(bitmap):
    scope = np.zeros(bitmap.shape[:2], dtype=bool)
    for data in PROVINCES.values():
        scope |= np.all(bitmap == data[2], axis=2)
    yy, xx = np.where(scope)
    pad = 7
    x0, x1 = max(0, int(xx.min()) - pad), min(bitmap.shape[1], int(xx.max()) + pad + 1)
    y0, y1 = max(0, int(yy.min()) - pad), min(bitmap.shape[0], int(yy.max()) + pad + 1)
    crop = bitmap[y0:y1, x0:x1]
    Image.fromarray(crop).save(OUT / "guangxi_14_formal_crop.bmp", format="BMP")

    scale = 7
    local_scope = scope[y0:y1, x0:x1]
    boundary = np.zeros(local_scope.shape, dtype=bool)
    boundary[1:] |= local_scope[1:] & np.any(crop[1:] != crop[:-1], axis=2)
    boundary[:, 1:] |= local_scope[:, 1:] & np.any(crop[:, 1:] != crop[:, :-1], axis=2)
    shown = np.asarray(Image.fromarray(crop).resize(
        (crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST
    )).copy()
    shown[np.repeat(np.repeat(boundary, scale, axis=0), scale, axis=1)] = (32, 32, 32)
    map_image = Image.fromarray(shown)

    font_path = next((p for p in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ) if Path(p).exists()), None)
    title_font = ImageFont.truetype(font_path, 28) if font_path else ImageFont.load_default()
    body_font = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default()
    small_font = ImageFont.truetype(font_path, 15) if font_path else ImageFont.load_default()
    sidebar = 570
    canvas = Image.new("RGB", (map_image.width + sidebar, max(760, map_image.height)), (248, 247, 243))
    canvas.paste(map_image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    lx = map_image.width + 24
    draw.text((lx, 20), "广西十四省 · 正式实装", fill=(24, 24, 24), font=title_font)
    draw.text((lx, 60), "桂北四省 · 桂东五省 · 桂西五省", fill=(75, 75, 75), font=small_font)
    area_order = ["guangxi_area", "guidong_area", "youjiang_area"]
    ordered = [pid for area in area_order for pid, data in PROVINCES.items() if data[3] == area]
    for index, pid in enumerate(ordered):
        name, chinese, colour, _area, _goods, dev, _culture = PROVINCES[pid]
        col, row = index // 7, index % 7
        tx, ty = lx + col * 270, 105 + row * 52
        draw.rectangle((tx, ty + 3, tx + 23, ty + 26), fill=colour, outline=(38, 38, 38))
        draw.text((tx + 32, ty), f"{index + 1:02d} {chinese} · {sum(dev)}", fill=(30, 30, 30), font=body_font)
        py, px = np.where(np.all(bitmap == colour, axis=2))
        cx = int((np.median(px) - x0) * scale)
        cy = int((np.median(py) - y0) * scale)
        draw.text((cx, cy), str(index + 1), anchor="mm", fill=(12, 12, 12),
                  stroke_width=3, stroke_fill=(255, 255, 255), font=body_font)
    draw.text((lx, 510), "总发展度：94", fill=(45, 45, 45), font=body_font)
    draw.text((lx, 546), "一级贸易中心：梧州", fill=(45, 45, 45), font=body_font)
    draw.text((lx, 582), "广西外边界未改动", fill=(75, 75, 75), font=small_font)
    canvas.save(OUT / "guangxi_14_formal_preview.png")


def main():
    before, bitmap, changed = update_bitmap()
    update_definitions()
    update_areas_regions()
    update_lists()
    update_histories()
    update_positions(bitmap)
    update_localisation()
    render_preview(bitmap)
    print(
        f"GUANGXI_APPLIED; PROVINCES:14; CHANGED:{int(changed.sum())}; "
        f"OUTSIDE_CHANGED:{int(np.count_nonzero(np.any(before != bitmap, axis=2) & ~changed))}; "
        "DEVELOPMENT:94; COT:2162=1"
    )


if __name__ == "__main__":
    main()
