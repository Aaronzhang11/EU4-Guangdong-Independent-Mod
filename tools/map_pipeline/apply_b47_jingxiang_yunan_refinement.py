#!/usr/bin/env python3
"""Apply the reviewed B47 Jingxiang–southern Henan balanced refinement.

The frozen v3 bitmap is the geometry authority.  The union of thirteen
pre-B47 provinces is the only editable mask; internal borders may cross the
former parent borders inside each modern province domain, while the modern
Hubei-Henan boundary and every pixel outside the union remain locked.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
HISTORY = MOD / "history/provinces"
PLAN = ROOT / "planning/jingxiang_yunan_b47"
REVIEWED = PLAN / "b47_geojson_v3_reviewed_provinces.bmp"
BACKUP = PLAN / "pre_b47_provinces.bmp"
CORRECTION_BACKUP = PLAN / "pre_b47_modern_border_correction_provinces.bmp"
FORMAL_REVIEW = PLAN / "b47_formal_review.png"
MANIFEST = PLAN / "batch_manifest.json"
MARKER = "GDD_B47_JINGXIANG_YUNAN_BALANCED"
BITMAP_HEIGHT = 2048


@dataclass(frozen=True)
class Province:
    province_id: int
    chinese: str
    english: str
    parent_id: int
    colour: tuple[int, int, int] | None
    area: str
    owner: str
    culture: str
    religion: str
    capital: str
    goods: str
    development: tuple[int, int, int]
    cot: int = 0
    fort: bool = False


P = (
    Province(5008, "郧", "Yun", 5008, None, "hanshang_area", "SHE", "gdd_chu", "confucianism", "Yun", "iron", (1, 2, 1)),
    Province(5341, "房州", "Fangzhou (Hubei)", 5008, (210, 87, 145), "hanshang_area", "SHE", "gdd_chu", "confucianism", "Fangzhou", "livestock", (1, 1, 2)),
    Province(2171, "襄阳", "Xiangyang", 2171, None, "hanshang_area", "LUO", "gdd_zhongyuan", "confucianism", "Xiangyang", "grain", (4, 4, 3), fort=True),
    Province(5342, "宜城", "Yicheng", 2171, (77, 172, 204), "hanshang_area", "LUO", "gdd_zhongyuan", "confucianism", "Yicheng", "grain", (2, 2, 2)),
    Province(5010, "安陆", "Anlu", 5010, None, "yunmeng_jingmen_area", "QVN", "gdd_chu", "confucianism", "Anlu", "paper", (2, 1, 1)),
    Province(5343, "荆门", "Jingmen", 5010, (188, 151, 62), "yunmeng_jingmen_area", "QVN", "gdd_chu", "confucianism", "Jingmen", "grain", (1, 2, 1)),
    Province(5015, "沔阳", "Mianyang", 5015, None, "yunmeng_jingmen_area", "ZHU", "gdd_chu", "confucianism", "Mianyang", "tea", (1, 1, 1)),
    Province(5344, "监利", "Jianli", 5015, (92, 189, 108), "yunmeng_jingmen_area", "ZHU", "gdd_chu", "confucianism", "Jianli", "grain", (1, 1, 1)),
    Province(2172, "荆州", "Jingzhou", 2172, None, "jingyi_area", "CHC", "gdd_chu", "confucianism", "Jiangling", "grain", (3, 3, 3), cot=1, fort=True),
    Province(5345, "枝江", "Zhijiang", 2172, (133, 83, 198), "jingyi_area", "CHC", "gdd_chu", "confucianism", "Zhijiang", "grain", (2, 2, 1)),
    Province(5014, "公安", "Gongan", 5014, None, "jingyi_area", "CHC", "gdd_chu", "confucianism", "Gongan", "grain", (2, 4, 3)),
    Province(681, "夷陵", "Yiling", 681, None, "yigui_area", "SHE", "gdd_chu", "confucianism", "Yiling", "tea", (3, 2, 2)),
    Province(5346, "归州", "Guizhou (Hubei)", 681, (218, 111, 67), "yigui_area", "SHE", "gdd_chu", "confucianism", "Guizhou", "tea", (1, 2, 1)),
    Province(5013, "施州", "Shizhou", 5013, None, "jingyi_area", "BD2", "gdd_diqiang", "animism", "Shizhou", "livestock", (2, 2, 2)),
    Province(687, "南阳", "Nanyang", 687, None, "wandeng_area", "GON", "gdd_zhongyuan", "confucianism", "Nanyang", "cloth", (4, 4, 2)),
    Province(5347, "方城", "Fangcheng", 687, (68, 123, 190), "wandeng_area", "GON", "gdd_zhongyuan", "confucianism", "Fangcheng", "livestock", (2, 2, 1)),
    Province(5055, "邓州", "Dengzhou", 5055, None, "wandeng_area", "GON", "gdd_zhongyuan", "confucianism", "Dengzhou", "livestock", (2, 2, 2)),
    Province(5348, "内乡", "Neixiang", 5055, (172, 76, 102), "wandeng_area", "GON", "gdd_zhongyuan", "confucianism", "Neixiang", "iron", (1, 2, 1)),
    Province(5053, "汝州", "Ruzhou", 5053, None, "rucai_area", "CZH", "gdd_zhongyuan", "confucianism", "Ruzhou", "iron", (3, 3, 2)),
    Province(5054, "汝宁", "Runing", 5054, None, "rucai_area", "CAI", "gdd_zhongyuan", "confucianism", "Runing", "grain", (3, 3, 2)),
    Province(5349, "息州", "Xizhou", 5054, (112, 169, 73), "rucai_area", "CAI", "gdd_zhongyuan", "confucianism", "Xizhou", "grain", (2, 1, 1)),
    Province(2175, "信阳", "Xinyang", 2175, None, "dean_qihuang_area", "SUI", "gdd_chu", "confucianism", "Xinyang", "tea", (2, 2, 1)),
    Province(5350, "光州", "Guangzhou (Henan)", 2175, (201, 124, 183), "dean_qihuang_area", "SUI", "gdd_chu", "confucianism", "Guangzhou", "tea", (1, 2, 1)),
)

PARENT_IDS = (5008, 2171, 681, 2172, 5015, 5010, 5013, 5014, 687, 5053, 5054, 5055, 2175)
NEW_IDS = tuple(province.province_id for province in P if province.colour is not None)
ALL_IDS = tuple(province.province_id for province in P)
CLIMATE_IDS = NEW_IDS + (681, 687, 2171, 2175)
BY_ID = {province.province_id: province for province in P}
HISTORY_FILENAMES = {
    5008: "5008 - Yunyang.txt", 2171: "2171 - Xiangyang.txt", 681: "681 - Yichang.txt",
    2172: "2172 - Jingzhou.txt", 5015: "5015 - Mianyang.txt", 5010: "5010 - Chengtian.txt",
    5013: "5013 - Shizhou.txt", 5014: "5014 - Gongan.txt", 687: "687 - Nanyang.txt",
    5053: "5053 - Ruzhou.txt", 5054: "5054 - Runing.txt", 5055: "5055 - Dengzhou.txt",
    2175: "2175 - Runing.txt",
}
AREA_MEMBERS = {
    "hanshang_area": (5008, 5341, 2171, 5342),
    "yunmeng_jingmen_area": (5010, 5343, 5015, 5344),
    "jingyi_area": (2172, 5345, 5014, 5013),
    "yigui_area": (681, 5346),
    "wandeng_area": (687, 5347, 5055, 5348),
    "rucai_area": (5053, 5054, 5349),
    "dean_qihuang_area": (5009, 4197, 5012, 2175, 5350),
}
AREA_CHINESE = {
    "hanshang_area": "鄢庸", "yunmeng_jingmen_area": "江汉", "jingyi_area": "荆郢",
    "yigui_area": "夷陵", "wandeng_area": "申邓", "rucai_area": "汝蔡",
    "dean_qihuang_area": "随黄",
}
OBSOLETE_AREAS = ("hanjiang_xiangyun_area", "jingyi_shinan_area", "runing_nanyang_area")
TERRAIN_IDS = {
    "farmlands": (5342, 5344, 5349),
    "grasslands": (5343, 5345),
    "hills": (5346, 5347, 5348, 5350),
    "highlands": (5341,),
}
POLITY_SCOPE = {
    "SHE": (5008, 5341, 681, 5346), "LUO": (2171, 5342),
    "CHC": (2172, 5345, 5014), "QVN": (5010, 5343),
    "ZHU": (5015, 5344), "BD2": (5013,),
    "GON": (687, 5347, 5055, 5348), "CZH": (5053,),
    "CAI": (5054, 5349), "SUI": (2175, 5350),
}
POLITY_DEVELOPMENT = {"SHE": 19, "LUO": 17, "CHC": 23, "QVN": 8, "ZHU": 6, "BD2": 6, "GON": 25, "CZH": 8, "CAI": 12, "SUI": 9}
ORIGINAL_PARENT_DEV = {
    5008: (2, 3, 3), 2171: (6, 6, 5), 681: (4, 4, 3), 2172: (5, 5, 4),
    5015: (2, 2, 2), 5010: (3, 3, 2), 5013: (2, 2, 2), 5014: (2, 4, 3),
    687: (6, 6, 3), 5053: (3, 3, 2), 5054: (5, 5, 2), 5055: (4, 4, 2),
    2175: (3, 4, 2),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def definition_rows(path: Path = MAP / "definition.csv") -> dict[int, tuple[tuple[int, int, int], str]]:
    rows: dict[int, tuple[tuple[int, int, int], str]] = {}
    for line in path.read_text(encoding="cp1252").splitlines():
        parts = line.split(";")
        if len(parts) >= 5 and parts[0].isdigit():
            rows[int(parts[0])] = (tuple(map(int, parts[1:4])), parts[4])
    return rows


def decode_ids(bitmap: Path, rows: dict[int, tuple[tuple[int, int, int], str]] | None = None) -> np.ndarray:
    lut = np.full(1 << 24, -1, dtype=np.int32)
    for province_id, (colour, _name) in (rows or definition_rows()).items():
        red, green, blue = colour
        lut[(red << 16) | (green << 8) | blue] = province_id
    rgb = np.asarray(Image.open(bitmap).convert("RGB"), dtype=np.uint32)
    packed = (rgb[:, :, 0] << 16) | (rgb[:, :, 1] << 8) | rgb[:, :, 2]
    return lut[packed]


def components(mask: np.ndarray) -> int:
    seen = np.zeros(mask.shape, dtype=bool)
    count = 0
    height, width = mask.shape
    for source_y, source_x in zip(*np.where(mask), strict=True):
        if seen[source_y, source_x]:
            continue
        count += 1
        stack = [(int(source_y), int(source_x))]
        seen[source_y, source_x] = True
        while stack:
            y, x = stack.pop()
            for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= next_y < height and 0 <= next_x < width and mask[next_y, next_x] and not seen[next_y, next_x]:
                    seen[next_y, next_x] = True
                    stack.append((next_y, next_x))
    return count


def block_bounds(text: str, key: str, start_at: int = 0) -> tuple[int, int]:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text[start_at:])
    if not match:
        raise ValueError(f"Missing block {key}")
    start = start_at + match.start()
    cursor = start_at + match.end()
    depth = 1
    while cursor < len(text) and depth:
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
        cursor += 1
    if depth:
        raise ValueError(f"Unclosed block {key}")
    return start, cursor


def replace_block(text: str, key: str, replacement: str) -> str:
    try:
        start, end = block_bounds(text, key)
    except ValueError:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[:start] + replacement.rstrip() + text[end:]


def remove_block(text: str, key: str) -> str:
    try:
        start, end = block_bounds(text, key)
    except ValueError:
        return text
    while end < len(text) and text[end] in " \t\r\n":
        end += 1
    return text[:start] + text[end:]


def add_marker_ids(text: str, key: str, ids: tuple[int, ...]) -> str:
    start, end = block_bounds(text, key)
    block = text[start:end]
    block = re.sub(rf"(?m)^\s*[0-9 ]+\s+# {re.escape(MARKER)}\s*$\n?", "", block)
    block = block[:-1].rstrip() + "\n        " + " ".join(map(str, ids)) + f" # {MARKER}\n}}"
    return text[:start] + block + text[end:]


def add_marker_ids_to_nested(text: str, outer_key: str, nested_key: str, ids: tuple[int, ...]) -> str:
    outer_start, outer_end = block_bounds(text, outer_key)
    outer = text[outer_start:outer_end]
    outer = re.sub(rf"(?m)^\s*[0-9 ]+\s+# {re.escape(MARKER)}\s*$\n?", "", outer)
    nested_start, nested_end = block_bounds(outer, nested_key)
    nested = add_marker_ids(outer[nested_start:nested_end], nested_key, ids)
    outer = outer[:nested_start] + nested + outer[nested_end:]
    return text[:outer_start] + outer + text[outer_end:]


def expected_geometry() -> tuple[np.ndarray, np.ndarray, dict[int, int]]:
    if not BACKUP.exists() or not REVIEWED.exists():
        raise FileNotFoundError("B47 needs pre_b47_provinces.bmp and the frozen v3 reviewed bitmap")
    base = np.asarray(Image.open(BACKUP).convert("RGB"), dtype=np.uint8)
    reviewed = np.asarray(Image.open(REVIEWED).convert("RGB"), dtype=np.uint8)
    if base.shape != reviewed.shape:
        raise ValueError("B47 bitmap dimensions differ")
    editable = np.isin(decode_ids(BACKUP), PARENT_IDS)
    outside = int(np.count_nonzero(np.any(base != reviewed, axis=2) & ~editable))
    if outside:
        raise ValueError(f"Reviewed B47 bitmap changed {outside} pixels outside the frozen union")
    expected = base.copy()
    expected[editable] = reviewed[editable]
    rows = definition_rows()
    counts: dict[int, int] = {}
    for province in P:
        colour = province.colour or rows[province.province_id][0]
        mask = np.all(expected == np.asarray(colour, dtype=np.uint8), axis=2) & editable
        if not mask.any() or components(mask) != 1:
            raise ValueError(f"Reviewed province {province.province_id} is empty or disconnected")
        counts[province.province_id] = int(mask.sum())
    return expected, editable, counts


def apply_geometry() -> tuple[int, int, dict[int, int]]:
    PLAN.mkdir(parents=True, exist_ok=True)
    canonical = MAP / "provinces.bmp"
    if not BACKUP.exists():
        shutil.copy2(canonical, BACKUP)
    if not CORRECTION_BACKUP.exists():
        shutil.copy2(canonical, CORRECTION_BACKUP)
    expected, editable, counts = expected_geometry()
    current = np.asarray(Image.open(canonical).convert("RGB"), dtype=np.uint8).copy()
    before = current.copy()
    current[editable] = expected[editable]
    changed = np.any(current != before, axis=2)
    exterior = int(np.count_nonzero(changed & ~editable))
    if exterior:
        raise ValueError(f"B47 attempted {exterior} exterior pixel changes")
    Image.fromarray(current, mode="RGB").save(canonical, format="BMP")
    return int(np.count_nonzero(changed)), exterior, counts


def update_definition_and_ceiling() -> None:
    path = MAP / "definition.csv"
    lines = path.read_text(encoding="cp1252").splitlines()
    current = definition_rows(path)
    desired: dict[int, tuple[tuple[int, int, int], str]] = {}
    for province in P:
        desired[province.province_id] = (province.colour or current[province.province_id][0], province.english)
    used = {colour: province_id for province_id, (colour, _name) in current.items() if province_id not in desired}
    for province_id, (colour, _name) in desired.items():
        if colour in used:
            raise ValueError(f"Province RGB {colour} collides with {used[colour]}")
    output: list[str] = []
    found: set[int] = set()
    for line in lines:
        head = line.split(";", 1)[0]
        if head.isdigit() and int(head) in desired:
            province_id = int(head)
            (red, green, blue), name = desired[province_id]
            output.append(f"{province_id};{red};{green};{blue};{name};x")
            found.add(province_id)
        else:
            output.append(line)
    for province_id in sorted(set(desired) - found):
        (red, green, blue), name = desired[province_id]
        output.append(f"{province_id};{red};{green};{blue};{name};x")
    path.write_text("\n".join(output) + "\n", encoding="cp1252")
    default = MAP / "default.map"
    current_text = default.read_text(encoding="cp1252")
    current_ceiling = int(re.search(r"(?m)^max_provinces\s*=\s*(\d+)", current_text).group(1))
    text, count = re.subn(r"(?m)^max_provinces\s*=\s*\d+", f"max_provinces = {max(current_ceiling, 5351)}", current_text)
    if count != 1:
        raise ValueError("default.map needs exactly one max_provinces")
    default.write_text(text, encoding="cp1252")


def set_region_areas(text: str, region: str, remove: tuple[str, ...], add: tuple[str, ...]) -> str:
    region_start, region_end = block_bounds(text, region)
    region_block = text[region_start:region_end]
    areas_start, areas_end = block_bounds(region_block, "areas")
    areas = region_block[areas_start:areas_end]
    for key in remove + add:
        areas = re.sub(rf"(?m)^\s*{re.escape(key)}\s*$\n?", "", areas)
    insertion = "".join(f"        {key}\n" for key in add)
    areas = areas[:-1].rstrip() + "\n" + insertion + "    }"
    region_block = region_block[:areas_start] + areas + region_block[areas_end:]
    return text[:region_start] + region_block + text[region_end:]


def update_areas_and_regions() -> None:
    area_path = MAP / "area.txt"
    text = area_path.read_text(encoding="cp1252")
    for key in OBSOLETE_AREAS:
        text = remove_block(text, key)
    for key, members in AREA_MEMBERS.items():
        text = replace_block(text, key, f"{key} = {{ # {MARKER}\n    {' '.join(map(str, members))}\n}}")
    area_path.write_text(text, encoding="cp1252")

    region_path = MAP / "region.txt"
    text = region_path.read_text(encoding="cp1252")
    text = set_region_areas(
        text, "south_china_region",
        ("hanjiang_xiangyun_area", "jingyi_shinan_area"),
        ("hanshang_area", "yunmeng_jingmen_area", "jingyi_area", "yigui_area"),
    )
    text = set_region_areas(text, "north_china_region", ("runing_nanyang_area",), ("wandeng_area", "rucai_area"))
    region_path.write_text(text, encoding="cp1252")


def initial_and_dated(text: str) -> tuple[str, str]:
    match = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", text)
    return (text[:match.start()], text[match.start():]) if match else (text, "")


def history_path(province_id: int) -> Path:
    matches = list(HISTORY.glob(f"{province_id} - *.txt"))
    if len(matches) != 1:
        raise ValueError(f"Province {province_id} has {len(matches)} local history files")
    return matches[0]


def history_text(province: Province, dated: str) -> str:
    lines = [
        f"# {province.province_id} - {province.english}", "", f"owner = {province.owner}",
        f"controller = {province.owner}", f"add_core = {province.owner}", f"culture = {province.culture}",
        f"religion = {province.religion}", f'capital = "{province.capital}"', f"trade_goods = {province.goods}",
        f"base_tax = {province.development[0]}", f"base_production = {province.development[1]}",
        f"base_manpower = {province.development[2]}", "is_city = yes",
    ]
    if province.cot:
        lines.append(f"center_of_trade = {province.cot}")
    if province.fort:
        lines.append("fort_15th = yes")
    lines.extend(("discovered_by = chinese", "discovered_by = nomad_group"))
    if province.religion == "animism":
        lines.append("discovered_by = indian")
    body = "\n".join(lines) + "\n"
    return body + ("\n" + dated.lstrip() if dated.strip() else "")


def update_histories() -> None:
    dated = {parent: initial_and_dated(history_path(parent).read_text(encoding="cp1252"))[1] for parent in PARENT_IDS}
    for province in P:
        filename = HISTORY_FILENAMES.get(province.province_id, f"{province.province_id} - {province.english}.txt")
        desired = HISTORY / filename
        for old in HISTORY.glob(f"{province.province_id} - *.txt"):
            if old != desired:
                old.unlink()
        desired.write_text(history_text(province, dated[province.parent_id]), encoding="cp1252")


def deep_interior_point(mask: np.ndarray) -> tuple[int, int]:
    current = mask.copy()
    last = current.copy()
    while current.any():
        last = current
        padded = np.pad(current, 1)
        current = padded[1:-1, 1:-1] & padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
    y, x = np.where(last)
    return int(np.median(x)), int(np.median(y))


def position_block(province: Province, x: int, y: int) -> str:
    points = " ".join([f"{x:.3f} {y:.3f}"] * 6 + ["0.000 0.000"])
    return f"""# {province.english} - {MARKER}
{province.province_id}={{
    position={{
        {points}
    }}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 1.000 0.000 0.000 0.000 0.000
    }}
}}"""


def update_positions() -> None:
    ids = decode_ids(MAP / "provinces.bmp")
    path = MAP / "positions.txt"
    text = path.read_text(encoding="cp1252")
    text = re.sub(rf"(?m)^# .* - {re.escape(MARKER)}\n", "", text)
    for province in P:
        x, bitmap_y = deep_interior_point(ids == province.province_id)
        replacement = position_block(province, x, BITMAP_HEIGHT - bitmap_y)
        try:
            start, end = block_bounds(text, str(province.province_id))
            text = text[:start] + replacement + text[end:]
        except ValueError:
            text = text.rstrip() + "\n\n" + replacement + "\n"
    path.write_text(text, encoding="cp1252")


def update_memberships() -> None:
    continent = MAP / "continent.txt"
    continent.write_text(add_marker_ids(continent.read_text(encoding="cp1252"), "asia", NEW_IDS), encoding="cp1252")
    climate = MAP / "climate.txt"
    climate.write_text(add_marker_ids(climate.read_text(encoding="cp1252"), "normal_monsoon", CLIMATE_IDS), encoding="cp1252")
    terrain = MAP / "terrain.txt"
    text = terrain.read_text(encoding="cp1252")
    for key, ids in TERRAIN_IDS.items():
        text = add_marker_ids_to_nested(text, key, "terrain_override", ids)
    terrain.write_text(text, encoding="cp1252")
    node = MOD / "common/tradenodes/00_tradenodes.txt"
    text = node.read_text(encoding="cp1252")
    for node_name, ids in (("huguang", (5341, 5342, 5343, 5344, 5345, 5346)),
                           ("zhongyuan", (5347, 5348, 5349, 5350))):
        start, end = block_bounds(text, node_name)
        block = add_marker_ids(text[start:end], "members", ids)
        text = text[:start] + block + text[end:]
    node.write_text(text, encoding="cp1252")
    company = MOD / "common/trade_companies/00_trade_companies.txt"
    text = company.read_text(encoding="cp1252")
    start, end = block_bounds(text, "trade_company_xian")
    block = add_marker_ids(text[start:end], "provinces", NEW_IDS)
    company.write_text(text[:start] + block + text[end:], encoding="cp1252")


def upsert_localisation(text: str, key: str, value: str) -> str:
    line = f' {key}:0 "{value}"'
    pattern = rf"(?m)^\s*{re.escape(key)}:\d+\s+\"[^\"]*\"\s*$"
    if re.search(pattern, text):
        return re.sub(pattern, line, text)
    return text.rstrip() + "\n" + line + "\n"


def update_localisation() -> None:
    lines = ["﻿l_english:"]
    for province in P:
        # 5008/5010 already have authoritative replace-layer names from B44.
        # Mirror the same values in this paired source so non-recursive static
        # localisation auditors can also see the complete B47 target set.
        if province.colour is not None or province.province_id in {5008, 5010}:
            lines.extend((f' PROV{province.province_id}:0 "{province.chinese}"', f' PROV_ADJ{province.province_id}:0 "{province.chinese}"'))
    source = MOD / "localisation_source/gdd_b47_jingxiang_yunan_refinement_readable_utf8.txt"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    override = MOD / "localisation_source/gdd_zzz_chunqiu_area_overrides_readable_utf8.txt"
    text = override.read_text(encoding="utf-8-sig")
    for area, chinese in AREA_CHINESE.items():
        for key in (area, f"{area}_name", f"{area}_adj"):
            text = upsert_localisation(text, key, chinese)
    override.write_text("﻿" + text.lstrip("﻿"), encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(source, MOD / "localisation/gdd_b47_jingxiang_yunan_refinement_l_english.yml")
    encode_file(override, MOD / "localisation/replace/zzz_gdd_chunqiu_area_overrides_l_english.yml")


def update_culture_csv() -> None:
    path = ROOT / "planning/culture_overhaul/approved_province_culture_assignments.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    rows = [row for row in rows if int(row["province_id"]) not in NEW_IDS]
    labels = {"gdd_chu": ("汉文化组", "楚文化"), "gdd_zhongyuan": ("汉文化组", "中原文化")}
    for province in P:
        if province.colour is None:
            continue
        group, culture = labels[province.culture]
        rows.append({
            "province_id": str(province.province_id), "province_name": province.chinese,
            "document_group": group, "document_culture": culture, "document_entry": "B47荆襄豫南二次细化",
            "target_culture": province.culture, "source_rule": "user_delegated",
            "decision_note": "用户授权国家与文化归属；跨旧省界均衡版新增省份",
        })
    rows.sort(key=lambda row: int(row["province_id"]))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def update_registry() -> None:
    path = ROOT / "docs/map/china_province_split_registry.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    rows = [row for row in rows if row["draw_batch"] != "B47"]
    definitions = definition_rows()
    for sequence, province in enumerate((value for value in P if value.colour is not None), 1):
        red, green, blue = province.colour
        siblings = tuple(value for value in P if value.parent_id == province.parent_id)
        retained = next(value for value in siblings if value.province_id == province.parent_id)
        original = ORIGINAL_PARENT_DEV[province.parent_id]
        row = {field: "" for field in fields}
        row.update({
            "design_key": f"B47-{sequence:02d}", "game_id": str(province.province_id),
            "rgb_r": str(red), "rgb_g": str(green), "rgb_b": str(blue),
            "macro_region": "south_china" if province.owner in {"SHE", "LUO", "CHC", "QVN", "ZHU", "BD2", "SUI"} else "north_china",
            "draw_batch": "B47", "new_name_zh": province.chinese, "new_name_en": province.english,
            "internal_key_hint": f"gdd_b47_{province.province_id}", "parent_id": str(province.parent_id),
            "parent_definition_name": definitions[province.parent_id][1],
            "parent_history_name": HISTORY_FILENAMES[province.parent_id].split(" - ", 1)[1][:-4],
            "parent_area": province.area, "parent_tax": str(original[0]),
            "parent_production": str(original[1]), "parent_manpower": str(original[2]),
            "retained_name_zh": retained.chinese, "retained_tax": str(retained.development[0]),
            "retained_production": str(retained.development[1]), "retained_manpower": str(retained.development[2]),
            "new_tax": str(province.development[0]), "new_production": str(province.development[1]),
            "new_manpower": str(province.development[2]), "split_group": f"b47-p{province.parent_id}",
            "group_dev_delta": "0", "proposed_owner": province.owner,
            "claims_or_uncertainty": "用户批准跨旧省界均衡；县级GeoJSON只作方位与边界语言",
            "status": "implemented", "rationale": "荆襄—豫南二次细化；外缘锁定、内部重排、发展度守恒。",
        })
        rows.append(row)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def read_history_value(path: Path, key: str) -> str:
    initial, _dated = initial_and_dated(path.read_text(encoding="cp1252"))
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^\s#]+)", initial)
    if not match:
        raise ValueError(f"{path.name}: missing {key}")
    return match.group(1).strip('"')


def parse_area_memberships() -> dict[int, set[str]]:
    text = (MAP / "area.txt").read_text(encoding="cp1252")
    memberships: dict[int, set[str]] = {}
    for match in re.finditer(r"(?m)^\s*([A-Za-z0-9_]+_area)\s*=\s*\{", text):
        key = match.group(1)
        start, end = block_bounds(text, key, match.start())
        body = re.sub(r"#.*", "", text[start:end])
        for token in re.findall(r"\b\d+\b", body):
            memberships.setdefault(int(token), set()).add(key)
    return memberships


def render_formal_review() -> None:
    renderer_path = PLAN / "render_b47_geojson_proposal.py"
    spec = importlib.util.spec_from_file_location("b47_formal_renderer", renderer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load B47 review renderer")
    renderer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = renderer
    spec.loader.exec_module(renderer)
    ids = decode_ids(MAP / "provinces.bmp")
    masks = {province_id: ids == province_id for province_id in ALL_IDS}
    union = np.isin(ids, ALL_IDS)
    ys, xs = np.where(union)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    country = renderer.render_map(masks, box, "polity")
    area = renderer.render_map(masks, box, "area")
    renderer.compose_review(
        country, area, title="B47 荆襄—豫南二次细化 · 鄂豫省界修订正式图",
        subtitle="现代鄂豫省界硬约束｜域内可跨旧省界均衡｜23省全部连通｜总发展度133守恒",
        output=FORMAL_REVIEW,
    )


def validate_modern_province_boundary(ids: np.ndarray) -> dict[str, int]:
    renderer_path = PLAN / "render_b47_geojson_v3_province_border.py"
    spec = importlib.util.spec_from_file_location("b47_modern_boundary_validator", renderer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load B47 modern-province boundary validator")
    renderer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = renderer
    spec.loader.exec_module(renderer)
    _base, _masks, _editable, _box, domains, _metadata = renderer.build_v3()
    violations = {
        "hubei_cells_in_henan": int(sum(np.count_nonzero((ids == province_id) & (domains == 2)) for province_id in renderer.HUBEI_IDS)),
        "henan_cells_in_hubei": int(sum(np.count_nonzero((ids == province_id) & (domains == 1)) for province_id in renderer.HENAN_IDS)),
    }
    if any(violations.values()):
        raise ValueError(f"B47 modern Hubei-Henan boundary violations: {violations}")
    return violations


def validate(pixel_counts: dict[int, int]) -> dict[str, object]:
    rows = definition_rows()
    ceiling = int(re.search(r"(?m)^max_provinces\s*=\s*(\d+)", (MAP / "default.map").read_text(encoding="cp1252")).group(1))
    if max(rows) < 5350 or ceiling <= max(rows):
        raise ValueError("B47 province ceiling is not a valid exclusive upper bound")
    colour_owners: dict[tuple[int, int, int], list[tuple[int, str]]] = {}
    for province_id, (colour, name) in rows.items():
        colour_owners.setdefault(colour, []).append((province_id, name))
    harmful_duplicates = {
        colour: owners
        for colour, owners in colour_owners.items()
        if len(owners) > 1 and not all(name == "RNW" for _province_id, name in owners)
    }
    if harmful_duplicates:
        raise ValueError(f"definition.csv contains non-RNW duplicate RGB values: {harmful_duplicates}")
    ids = decode_ids(MAP / "provinces.bmp")
    modern_boundary_violations = validate_modern_province_boundary(ids)
    for province in P:
        mask = ids == province.province_id
        if int(mask.sum()) != pixel_counts[province.province_id] or components(mask) != 1:
            raise ValueError(f"Province {province.province_id} geometry mismatch")
        path = history_path(province.province_id)
        development = tuple(int(read_history_value(path, key)) for key in ("base_tax", "base_production", "base_manpower"))
        if read_history_value(path, "owner") != province.owner or read_history_value(path, "culture") != province.culture or development != province.development:
            raise ValueError(f"Province {province.province_id} history mismatch")
    memberships = parse_area_memberships()
    area_components: dict[str, int] = {}
    for area, members in AREA_MEMBERS.items():
        for province_id in members:
            if memberships.get(province_id) != {area}:
                raise ValueError(f"Province {province_id} area mismatch: {memberships.get(province_id)}")
        area_components[area] = components(np.isin(ids, members))
    if area_components["jingyi_area"] != 2:
        raise ValueError(f"jingyi_area should have two land components around the Yangtze, got {area_components['jingyi_area']}")
    if any(count != 1 for area, count in area_components.items() if area != "jingyi_area"):
        raise ValueError(f"Unexpected fragmented B47 area: {area_components}")
    adjacency = (MAP / "adjacencies.csv").read_text(encoding="cp1252")
    if not re.search(r"(?m)^(2172;5013|5013;2172);sea;5037;", adjacency):
        raise ValueError("jingyi_area lacks its real Jingzhou-Shizhou Yangtze crossing")
    actual_polity_dev = {
        tag: sum(sum(BY_ID[province_id].development) for province_id in members)
        for tag, members in POLITY_SCOPE.items()
    }
    if actual_polity_dev != POLITY_DEVELOPMENT:
        raise ValueError(f"B47 polity development drift: {actual_polity_dev}")
    if sum(sum(province.development) for province in P) != 133:
        raise ValueError("B47 development total drifted from 133")
    terrain = (MAP / "terrain.txt").read_text(encoding="cp1252")
    for category, expected_ids in TERRAIN_IDS.items():
        start, end = block_bounds(terrain, category)
        category_block = terrain[start:end]
        nested_start, nested_end = block_bounds(category_block, "terrain_override")
        nested = category_block[nested_start:nested_end]
        if MARKER in category_block[:nested_start] + category_block[nested_end:]:
            raise ValueError(f"{category}: B47 terrain IDs escaped terrain_override")
        for province_id in expected_ids:
            if len(re.findall(rf"(?<!\d){province_id}(?!\d)", nested)) != 1:
                raise ValueError(f"{category}: province {province_id} terrain membership mismatch")
    culture_path = ROOT / "planning/culture_overhaul/approved_province_culture_assignments.csv"
    with culture_path.open(encoding="utf-8-sig", newline="") as handle:
        culture_rows = {int(row["province_id"]): row["target_culture"] for row in csv.DictReader(handle)}
    for province_id in NEW_IDS:
        if culture_rows.get(province_id) != BY_ID[province_id].culture:
            raise ValueError(f"Province {province_id} approved culture mismatch")
    b43_path = ROOT / "tools/map_pipeline/apply_b43_chunqiu_polities.py"
    spec = importlib.util.spec_from_file_location("b47_b43_policy", b43_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load B43 polity policy")
    b43 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = b43
    spec.loader.exec_module(b43)
    for tag, members in POLITY_SCOPE.items():
        if not set(members).issubset(set(b43.TAG_PROVINCES[tag])):
            raise ValueError(f"B43 replay policy is missing B47 {tag} provinces")
    all_policy_ids = [province_id for members in b43.TAG_PROVINCES.values() for province_id in members]
    if len(all_policy_ids) != 309 or len(set(all_policy_ids)) != 309:
        raise ValueError("B43 replay policy does not contain 309 unique post-B56 provinces")
    return {
        "province_components": "23/23 one component",
        "area_land_components": area_components,
        "jingyi_gameplay_connectivity": "crossing-connected via 2172-5013 through navigable river 5037",
        "development_total": 133,
        "polity_development_in_scope": actual_polity_dev,
        "minimum_province_pixels": min(pixel_counts.values()),
        "modern_hubei_henan_boundary": "hard constraint from reviewed county GeoJSON",
        "modern_boundary_violations": modern_boundary_violations,
    }


def write_manifest(changed: int, exterior: int, pixel_counts: dict[int, int], validation: dict[str, object]) -> None:
    canonical = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    baseline = np.asarray(Image.open(BACKUP).convert("RGB"), dtype=np.uint8)
    editable = np.isin(decode_ids(BACKUP), PARENT_IDS)
    delta = np.any(canonical != baseline, axis=2)
    payload = {
        "batch": "B47_jingxiang_yunan_balanced_refinement", "marker": MARKER,
        "purpose": "Apply the approved balanced Jingxiang and southern Henan refinement while locking the modern Hubei-Henan boundary and regional development.",
        "geometry_policy": "lock the modern Hubei-Henan boundary; allow cross-parent rebalancing only inside each modern province domain",
        "parent_ids": list(PARENT_IDS), "target_ids": list(ALL_IDS),
        "new_provinces": [asdict(province) for province in P if province.colour is not None],
        "reviewed_bitmap": str(REVIEWED), "reviewed_bitmap_sha256": sha256(REVIEWED),
        "backup": str(BACKUP), "backup_sha256": sha256(BACKUP),
        "correction_backup": str(CORRECTION_BACKUP), "correction_backup_sha256": sha256(CORRECTION_BACKUP),
        "formal_review": str(FORMAL_REVIEW), "changed_pixels_this_run": changed,
        "changed_pixels_vs_backup": int(np.count_nonzero(delta)),
        "changed_pixels_vs_backup_outside_editable_mask": int(np.count_nonzero(delta & ~editable)),
        "changed_pixels_outside_editable_mask": exterior, "pixel_counts": pixel_counts,
        "areas": {key: list(value) for key, value in AREA_MEMBERS.items()},
        "regions": {"south_china_region": ["hanshang_area", "yunmeng_jingmen_area", "jingyi_area", "yigui_area", "dean_qihuang_area"], "north_china_region": ["wandeng_area", "rucai_area"]},
        "trade_node": {"hubei": "huguang", "henan": "zhongyuan"},
        "trade_company": "trade_company_xian",
        "countries": {key: list(value) for key, value in POLITY_SCOPE.items()},
        "validation": validation, "canonical_bitmap_sha256": sha256(MAP / "provinces.bmp"),
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply() -> None:
    changed, exterior, pixel_counts = apply_geometry()
    update_definition_and_ceiling()
    update_areas_and_regions()
    update_histories()
    update_positions()
    update_memberships()
    update_localisation()
    update_culture_csv()
    update_registry()
    render_formal_review()
    validation = validate(pixel_counts)
    write_manifest(changed, exterior, pixel_counts, validation)
    print(f"{MARKER}; NEW_PROVINCES:{len(NEW_IDS)}; CHANGED_PIXELS:{changed}; EXTERIOR_PIXELS:{exterior}; DEV:133")


def check() -> None:
    expected, editable, pixel_counts = expected_geometry()
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    mismatch = int(np.count_nonzero(np.any(current != expected, axis=2) & editable))
    if mismatch:
        raise ValueError(f"Canonical bitmap differs from frozen B47 geometry at {mismatch} editable pixels")
    validation = validate(pixel_counts)
    print(f"{MARKER}_CHECK; PASS; DEV:{validation['development_total']}; NEW_PROVINCES:{len(NEW_IDS)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    check() if args.check else apply()


if __name__ == "__main__":
    main()
