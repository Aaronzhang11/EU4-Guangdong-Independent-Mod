#!/usr/bin/env python3
"""Apply the reviewed B31 Han land-contiguous area reorganisation."""

from __future__ import annotations

import re
import shutil
import sys
import colorsys
from pathlib import Path

import audit_area_connectivity as audit
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/area_contiguity"
MARKER = "B31 Han land-contiguous area reorganisation"

# Province -> destination area. Every moved province is first removed from all
# area blocks, making reruns idempotent even after partial prior execution.
MOVES = {
    5087: "aba_area",                 # Wenchuan
    5092: "songmao_area",             # Ruoergai
    660: "dianxinan_area",            # Banna
    5239: "dianxinan_area",           # Mengla
    2165: "diannan_area",             # Simao
    5237: "diannan_area",             # Zhenyuan
    4982: "hunan_area",               # Yuezhou
    4983: "southwest_hunan_area",     # Baoqing
    681: "hanjiang_xiangyun_area",    # Yiling
    5010: "jingyi_shinan_area",       # Anlu
    5013: "jingyi_shinan_area",       # Shizhou
    5028: "chongqing_area",           # Kuizhou
    5272: "changan_area",             # Shangzhou
    696: "south_hebei_area",          # Baoding: connects Yizhou to Zhending
    5066: "huining_area",             # Wuhu
    5278: "longnan_area",             # Jingning
    5291: "xi_shaanxi_area",          # Gongchang
    5059: "jianghuai_area",           # Shouzhou
    2175: "dean_qihuang_area",        # Xinyang
    1821: "huaiyang_tongtai_area",    # Jiangning
}
if (ROOT / "planning/chuandongbei_chongqing_b46/batch_manifest.json").exists():
    # B46 places Kuizhou in the dedicated Xiajiang area.  The older B31 move
    # remains valid only before the reviewed second Sichuan refinement exists.
    MOVES.pop(5028, None)

EMPTY_REFERENCES = {692, 5298}  # Huaiqing and Guazhou have no bitmap pixels.

LOCALISATION_UPDATES = {
    "gdd_b10_hubei_map_readable_utf8.txt": {
        "jingyi_shinan_area": "荆夔",
        "jingyi_shinan_area_name": "荆州",
        "jingyi_shinan_area_adj": "荆夔",
    },
    "gdd_b14_henan_map_readable_utf8.txt": {
        "hebei_zhangwei_area": "彰卫",
        "hebei_zhangwei_area_name": "彰德",
        "hebei_zhangwei_area_adj": "彰卫",
    },
    "gdd_b26_gansu_ningxia_map_readable_utf8.txt": {
        "west_gansu_area": "玉沙",
        "west_gansu_area_name": "沙州",
        "west_gansu_area_adj": "玉沙",
    },
}


def block_bounds(text: str, key: str) -> tuple[int, int]:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"Missing area block: {key}")
    depth = 1
    index = match.end()
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    if depth:
        raise ValueError(f"Unclosed area block: {key}")
    return match.start(), index


def replace_block(text: str, key: str, ids: list[int]) -> str:
    start, end = block_bounds(text, key)
    body = f"{key} = {{ # {MARKER}\n    {' '.join(map(str, ids))}\n}}"
    return text[:start] + body + text[end:]


def update_areas() -> None:
    path = MAP / "area.txt"
    backup = OUT / "pre_b31_area.txt"
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="cp1252", errors="strict")
    parsed = audit.blocks(text, "_area")
    memberships = {key: audit.area_ids(body) for key, body in parsed.items()}
    targets = set(MOVES.values())

    for province_id in set(MOVES) | EMPTY_REFERENCES:
        for area, ids in memberships.items():
            if province_id in ids:
                memberships[area] = [value for value in ids if value != province_id]
                targets.add(area)

    for province_id, destination in MOVES.items():
        if destination not in memberships:
            raise ValueError(f"Missing destination area: {destination}")
        memberships[destination].append(province_id)

    for area in sorted(targets):
        text = replace_block(text, area, memberships[area])
    path.write_text(text, encoding="cp1252")


def update_localisation() -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file

    source_dir = MOD / "localisation_source"
    target_dir = MOD / "localisation"
    for filename, updates in LOCALISATION_UPDATES.items():
        source = source_dir / filename
        backup = OUT / f"pre_b31_{filename}"
        if not backup.exists():
            shutil.copy2(source, backup)
        text = source.read_text(encoding="utf-8")
        for key, value in updates.items():
            pattern = rf'(?m)^(\s*{re.escape(key)}:\d*\s+")[^"]*("\s*)$'
            text, count = re.subn(pattern, rf'\g<1>{value}\g<2>', text)
            if count != 1:
                raise ValueError(f"Expected one localisation key {key}, found {count}")
        source.write_text(text, encoding="utf-8")
        generated = target_dir / filename.replace("_readable_utf8.txt", "_l_english.yml")
        encode_file(source, generated)


def verify_unique_memberships() -> None:
    text = (MAP / "area.txt").read_text(encoding="cp1252", errors="strict")
    parsed = audit.blocks(text, "_area")
    owners: dict[int, set[str]] = {}
    for area, body in parsed.items():
        for province_id in audit.area_ids(body):
            owners.setdefault(province_id, set()).add(area)
    duplicates = {province_id: areas for province_id, areas in owners.items() if len(areas) != 1}
    if duplicates:
        raise ValueError(f"Duplicate area memberships: {duplicates}")
    for province_id, destination in MOVES.items():
        if owners.get(province_id) != {destination}:
            raise ValueError(f"Province {province_id} did not land in {destination}")
    for province_id in EMPTY_REFERENCES:
        if province_id in owners:
            raise ValueError(f"Empty province {province_id} remains in an area")


def render_preview() -> None:
    area_text = (MAP / "area.txt").read_text(encoding="cp1252", errors="strict")
    areas = {key: audit.area_ids(body) for key, body in audit.blocks(area_text, "_area").items()}
    region_text = (MAP / "region.txt").read_text(encoding="cp1252", errors="replace")
    region_blocks = audit.blocks(region_text, "_region")
    han_areas = sorted({
        area
        for region in audit.HAN_REGIONS
        for area in re.findall(r"\b[A-Za-z0-9_]+_area\b", audit.clean(region_blocks.get(region, "")))
    })
    by_id, _by_color = audit.definitions()
    bitmap = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    crop_box = (4300, 650, 4750, 1120)
    x0, y0, x1, y1 = crop_box
    crop = bitmap[y0:y1, x0:x1]
    packed = (
        (crop[:, :, 0].astype(np.uint32) << 16)
        | (crop[:, :, 1].astype(np.uint32) << 8)
        | crop[:, :, 2].astype(np.uint32)
    )
    review = np.full(crop.shape, (224, 221, 211), dtype=np.uint8)
    for index, area in enumerate(han_areas):
        hue = (index * 0.61803398875) % 1.0
        rgb = tuple(round(value * 255) for value in colorsys.hsv_to_rgb(hue, 0.52, 0.86))
        colors = np.array([by_id[pid] for pid in areas.get(area, []) if pid in by_id], dtype=np.uint32)
        if colors.size:
            review[np.isin(packed, colors)] = rgb

    # Retain all province edges; highlight moved province edges in white.
    boundaries = np.zeros(packed.shape, dtype=bool)
    horizontal = packed[:, 1:] != packed[:, :-1]
    vertical = packed[1:] != packed[:-1]
    boundaries[:, 1:] |= horizontal
    boundaries[:, :-1] |= horizontal
    boundaries[1:] |= vertical
    boundaries[:-1] |= vertical
    review[boundaries] = (55, 56, 58)
    moved_colors = np.array([by_id[pid] for pid in MOVES if pid in by_id], dtype=np.uint32)
    moved = np.isin(packed, moved_colors)
    moved_edge = moved & boundaries
    review[moved_edge] = (248, 246, 232)

    scale = 2
    shown = Image.fromarray(review).resize((review.shape[1] * scale, review.shape[0] * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 500, max(shown.height, 940)), (244, 242, 236))
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 27)
    body = ImageFont.truetype(font_path, 17)
    small = ImageFont.truetype(font_path, 15)
    px = shown.width + 24
    draw.text((px, 22), "B31 汉地区域陆地连通重排", font=title, fill=(30, 31, 33))
    draw.text((px, 66), "同色＝同一区域；深线＝省界；白线＝本次移动省份", font=small, fill=(68, 69, 71))
    notes = [
        "• 易州保留冀南，保定构成陆地走廊",
        "• 湖南三组联动，湘中与湘西南岭各四省",
        "• 阿坝—松茂、滇南—滇西南保持数量均衡",
        "• 荆夔、汉水襄郧、巴东按陆地边界重排",
        "• 芜湖转入徽宁，皖江保留连续核心",
        "• 商州转长安；静宁与巩昌互换",
        "• 清除怀庆、瓜州两个空省份区域引用",
    ]
    y = 125
    for note in notes:
        draw.text((px, y), note, font=body, fill=(47, 48, 50))
        y += 38
    draw.text((px, 430), "全量结果", font=title, fill=(30, 31, 33))
    draw.text((px, 480), "普通汉地大陆区域：全部陆地连续", font=body, fill=(42, 88, 58))
    draw.text((px, 518), "天然例外：昌国群岛、武汉三镇", font=body, fill=(108, 77, 40))
    draw.text((px, 556), "正式 provinces.bmp：0 像素改动", font=body, fill=(42, 88, 58))
    draw.text((px, 610), "本图为区域归属预览，不是 provinces.bmp。", font=small, fill=(75, 76, 78))
    canvas.save(OUT / "b31_han_area_contiguity_preview.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    update_areas()
    update_localisation()
    verify_unique_memberships()
    render_preview()
    print(f"{MARKER}; MOVED:{len(MOVES)}; EMPTY_REMOVED:{len(EMPTY_REFERENCES)}")


if __name__ == "__main__":
    main()
