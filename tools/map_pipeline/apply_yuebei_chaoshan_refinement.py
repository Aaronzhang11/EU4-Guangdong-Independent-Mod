#!/usr/bin/env python3
"""Split Lianzhou and Puning, then organise Yuebei, Dongjiang and Chaoshan."""

from __future__ import annotations

from collections import deque
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/guangdong"
MARKER = "B30 Yuebei-Chaoshan refinement"
PARENTS = {
    2158: ((65, 46, 176), ("韶关", (4577, 998)), ("连州", (4558, 990))),
    2156: ((146, 81, 81), ("潮州", (4626, 1004)), ("普宁", (4624, 1020))),
}
# id: English, Chinese, colour, goods, development, culture, owner, extra core
PROVINCES = {
    2158: ("Shaoguan", "韶关", (65, 46, 176), "iron", (2, 3, 1), "hakka", "GDD", "HUA"),
    5216: ("Lianzhou", "连州", (69, 150, 92), "livestock", (2, 2, 1), "hakka", "GDD", "HUA"),
    2156: ("Chaozhou", "潮州", (146, 81, 81), "chinaware", (3, 3, 2), "chimin", "MNG", "MIN"),
    5217: ("Puning", "普宁", (213, 91, 149), "grain", (2, 3, 1), "chimin", "MNG", "MIN"),
    4949: ("Haifeng", "海丰", (67, 219, 198), "salt", (1, 1, 1), "chimin", "GDD", "YUE"),
}
NEW_IDS = [5216, 5217]


def block_bounds(text, name):
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        return None
    start, brace, depth = match.start(), text.find("{", match.start()), 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise ValueError(f"Unclosed block {name}")


def replace_block(text, name, replacement):
    bounds = block_bounds(text, name)
    if bounds is None:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[:bounds[0]] + replacement.rstrip() + text[bounds[1]:]


def remove_marker_line(text):
    return re.sub(rf"(?m)^\s*.*# {re.escape(MARKER)}.*\n?", "", text)


def nearest(mask, seed):
    x, y = seed
    if mask[y, x]:
        return x, y
    yy, xx = np.where(mask)
    i = np.argmin((xx - x) ** 2 + (yy - y) ** 2)
    return int(xx[i]), int(yy[i])


def split_parent(mask, seeds):
    owner = np.full(mask.shape, -1, dtype=np.int8)
    distance = np.full(mask.shape, 32767, dtype=np.int16)
    queue = deque()
    for label, seed in enumerate(seeds):
        x, y = nearest(mask, seed)
        owner[y, x], distance[y, x] = label, 0
        queue.append((x, y, label))
    while queue:
        x, y, label = queue.popleft()
        nd = int(distance[y, x]) + 1
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0]
                    and mask[ny, nx] and nd < distance[ny, nx]):
                owner[ny, nx], distance[ny, nx] = label, nd
                queue.append((nx, ny, label))
    return owner


def apply_geometry():
    backup = OUT / "pre_yuebei_chaoshan_provinces.bmp"
    if not backup.exists():
        shutil.copy2(MAP / "provinces.bmp", backup)
    before = np.asarray(Image.open(backup).convert("RGB"))
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    reviewed = before.copy()
    sizes = {}
    assignments = [(2158, 5216), (2156, 5217)]
    for (parent_id, (parent_colour, first, second)), ids in zip(PARENTS.items(), assignments):
        mask = np.all(before == parent_colour, axis=2)
        labels = split_parent(mask, (first[1], second[1]))
        reviewed[labels == 0] = PROVINCES[ids[0]][2]
        reviewed[labels == 1] = PROVINCES[ids[1]][2]
        sizes[first[0]] = int(np.count_nonzero(labels == 0))
        sizes[second[0]] = int(np.count_nonzero(labels == 1))
    changed = np.any(before != reviewed, axis=2)
    result = current.copy()
    result[changed] = reviewed[changed]
    Image.fromarray(result).save(MAP / "provinces.bmp", format="BMP")
    Image.fromarray(result).save(OUT / "yuebei_chaoshan_full_applied.bmp", format="BMP")
    return before, result, changed, sizes


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
    text = replace_block(text, "guangdong_area", f"guangdong_area = {{ # {MARKER}\n    2158 5216 4948\n}}")
    text = replace_block(text, "dongjiang_area", f"dongjiang_area = {{ # {MARKER}\n    2157 5214 5215 4944\n}}")
    text = replace_block(text, "chaoshan_area", f"chaoshan_area = {{ # {MARKER}\n    2156 5217 4949\n}}")
    path.write_text(text)

    path = MAP / "region.txt"
    text = path.read_text()
    if re.search(r"(?m)^\s*chaoshan_area\s*$", text) is None:
        text = text.replace("        dongjiang_area\n", "        dongjiang_area\n        chaoshan_area\n", 1)
    path.write_text(text)


def append_line(path, marker, ids):
    text = remove_marker_line(path.read_text())
    if marker not in text:
        raise ValueError(f"Insertion marker missing from {path}")
    path.write_text(text.replace(marker, marker + f"\n    {ids} # {MARKER}", 1))


def update_memberships():
    ids = " ".join(map(str, NEW_IDS))
    for path in (
        MAP / "continent.txt",
        MOD / "common/tradenodes/00_tradenodes.txt",
        MOD / "common/trade_companies/00_trade_companies.txt",
    ):
        append_line(path, "    5214 5215 # B29 Huizhou 3-province refinement", ids)

    path = MAP / "climate.txt"
    text = remove_marker_line(path.read_text())
    for suffix in ("tropical", "monsoon"):
        marker = f"    5214 5215 # B29 Huizhou 3-province refinement {suffix}"
        if marker not in text:
            raise ValueError(f"Climate marker missing: {suffix}")
        text = text.replace(marker, marker + f"\n    {ids} # {MARKER} {suffix}", 1)
    path.write_text(text)

    path = MAP / "terrain.txt"
    text = remove_marker_line(path.read_text())
    hill_marker = "    5214 5215 # B29 Huizhou 3-province refinement hills"
    farm_marker = "    5204 # B27 Liaoning 10-province refinement farmlands"
    if hill_marker not in text or farm_marker not in text:
        raise ValueError("Terrain marker missing")
    text = text.replace(hill_marker, hill_marker + f"\n    5216 # {MARKER} hills", 1)
    text = text.replace(farm_marker, farm_marker + f"\n    5217 # {MARKER} farmlands", 1)
    path.write_text(text)


def timeline_for(pid):
    files = list((MOD / "history/provinces").glob(f"{pid} - *.txt"))
    if not files:
        return ""
    text = files[0].read_text()
    match = re.search(r"(?m)^(?:1514|1595)\.1\.1\s*=", text)
    return text[match.start():] if match else ""


def history_text(pid, data, timeline):
    name, _, _, goods, dev, culture, owner, extra_core = data
    lines = [
        f"# {pid} - {name}", "", f"owner = {owner}", f"controller = {owner}",
        "add_core = MNG", "add_core = GDD", f"add_core = {extra_core}",
        f"culture = {culture}", "religion = confucianism", f'capital = "{name}"',
        f"trade_goods = {goods}", "hre = no", f"base_tax = {dev[0]}",
        f"base_production = {dev[1]}", f"base_manpower = {dev[2]}", "is_city = yes",
    ]
    if pid == 4949:
        lines += ["fort_15th = yes"]
    lines += ["", "discovered_by = chinese", "discovered_by = nomad_group", ""]
    if timeline:
        lines.append(timeline.rstrip())
    return "\n".join(lines) + "\n"


def update_histories():
    shaoguan_timeline = timeline_for(2158)
    chaozhou_timeline = timeline_for(2156)
    haifeng_timeline = timeline_for(4949)
    timelines = {2158: shaoguan_timeline, 5216: shaoguan_timeline,
                 2156: chaozhou_timeline, 5217: chaozhou_timeline, 4949: haifeng_timeline}
    directory = MOD / "history/provinces"
    for pid, data in PROVINCES.items():
        for old in directory.glob(f"{pid} - *.txt"):
            old.unlink()
        (directory / f"{pid} - {data[0]}.txt").write_text(history_text(pid, data, timelines[pid]))


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
        text = replace_block(text, str(pid), position_block(
            pid, name, float(np.median(xx)), float(bitmap.shape[0] - np.median(yy))))
    path.write_text(text, encoding="latin-1")


def update_localisation():
    source = MOD / "localisation_source/gdd_b30_yuebei_chaoshan_map_readable_utf8.txt"
    lines = ["l_english:"]
    for pid, (_name, chinese, *_rest) in sorted(PROVINCES.items()):
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    lines += [
        ' guangdong_area:0 "粤北"', ' guangdong_area_name:0 "韶关"', ' guangdong_area_adj:0 "粤北"',
        ' chaoshan_area:0 "潮汕"', ' chaoshan_area_name:0 "潮州"', ' chaoshan_area_adj:0 "潮汕"',
        ' dongjiang_area:0 "东江"', ' dongjiang_area_name:0 "惠州"', ' dongjiang_area_adj:0 "东江"',
    ]
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(source, MOD / "localisation/gdd_b30_yuebei_chaoshan_map_l_english.yml")


def font(size):
    for candidate in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def render_preview(bitmap, sizes):
    crop = bitmap[970:1040, 4545:4645]
    Image.fromarray(crop).save(OUT / "yuebei_chaoshan_applied_crop.bmp", format="BMP")
    scale = 9
    map_image = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (map_image.width + 530, max(700, map_image.height)), (248, 247, 243))
    canvas.paste(map_image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    lx = map_image.width + 24
    draw.text((lx, 20), "粤北、潮汕细化 · 正式实装", fill=(24, 24, 24), font=font(27))
    lines = [
        ("粤北", "韶关 · 连州 · 南雄"),
        ("潮汕", "潮州 · 普宁 · 海丰"),
        ("东江", "惠州 · 河源 · 龙川 · 梅州"),
    ]
    for i, (area, members) in enumerate(lines):
        y = 90 + i * 86
        draw.text((lx, y), area, fill=(28, 28, 28), font=font(21))
        draw.text((lx, y + 37), members, fill=(70, 70, 70), font=font(16))
    draw.text((lx, 385), f"连州：{sizes['连州']}像素", fill=(55, 55, 55), font=font(17))
    draw.text((lx, 420), f"普宁：{sizes['普宁']}像素", fill=(55, 55, 55), font=font(17))
    draw.text((lx, 475), "东莞、香港及广东外边界未改动", fill=(60, 85, 60), font=font(16))
    canvas.save(OUT / "yuebei_chaoshan_applied_preview.png")


def main():
    _before, bitmap, changed, sizes = apply_geometry()
    update_definitions()
    update_areas_region()
    update_memberships()
    update_histories()
    update_positions(bitmap)
    update_localisation()
    render_preview(bitmap, sizes)
    print(f"YUEBEI_CHAOSHAN_APPLIED; CHANGED:{int(changed.sum())}; SIZES:{sizes}; OUTSIDE_CHANGED:0")


if __name__ == "__main__":
    main()
