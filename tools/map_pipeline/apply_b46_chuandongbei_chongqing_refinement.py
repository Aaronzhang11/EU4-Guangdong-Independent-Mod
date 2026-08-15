#!/usr/bin/env python3
"""Apply the reviewed GeoJSON-guided B46 northeast Sichuan/Chongqing split.

The reviewed bitmap is the geometry authority.  Only pixels belonging to the
ten frozen parent provinces may change; the script never restores the whole
bitmap from its backup and does not need network access.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
HISTORY = MOD / "history/provinces"
COUNTRY_HISTORY = MOD / "history/countries"
COUNTRIES = MOD / "common/countries"
FLAGS = MOD / "gfx/flags"
PLAN = ROOT / "planning/chuandongbei_chongqing_b46"
REVIEWED = PLAN / "b46_reviewed_provinces.bmp"
BACKUP = PLAN / "pre_b46_provinces.bmp"
MANIFEST = PLAN / "batch_manifest.json"
B47_MANIFEST = ROOT / "planning/jingxiang_yunan_b47/batch_manifest.json"
MARKER = "GDD_B46_CHUANDONGBEI_CHONGQING_GEOJSON"
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
    Province(5080, "绵州", "Mianzhou", 5080, None, "chuanbei_area", "SHU", "gdd_shu", "confucianism", "Mianzhou", "cloth", (5, 5, 2)),
    Province(5081, "剑州", "Jianzhou (Sichuan)", 5081, None, "chuanbei_area", "JUU", "gdd_shu", "confucianism", "Jianzhou", "iron", (1, 2, 1), fort=True),
    Province(5329, "昭化", "Zhaohua", 5081, (184, 165, 77), "chuanbei_area", "JUU", "gdd_shu", "confucianism", "Zhaohua", "grain", (1, 1, 2)),
    Province(2169, "阆中", "Langzhong", 2169, None, "chuanbei_area", "BAA", "gdd_shu", "confucianism", "Langzhong", "grain", (3, 2, 2)),
    Province(5330, "蓬州", "Pengzhou", 2169, (155, 76, 224), "baqu_area", "BAA", "gdd_shu", "confucianism", "Pengzhou", "grain", (1, 2, 1)),
    Province(5331, "遂州", "Suizhou", 5082, (48, 184, 80), "chuanbei_area", "SHU", "gdd_shu", "confucianism", "Suizhou", "cloth", (1, 2, 1)),
    Province(5332, "巴州", "Bazhou", 4211, (224, 94, 101), "baqu_area", "DQU", "gdd_shu", "confucianism", "Bazhou", "grain", (1, 1, 1)),
    Province(5082, "顺庆", "Shunqing", 5082, None, "baqu_area", "BAA", "gdd_shu", "confucianism", "Shunqing", "grain", (2, 2, 1)),
    Province(4211, "达州", "Dazhou", 4211, None, "baqu_area", "DQU", "gdd_shu", "confucianism", "Dazhou", "livestock", (1, 1, 1)),
    Province(5333, "渠州", "Quzhou", 4211, (62, 104, 184), "baqu_area", "DQU", "gdd_shu", "confucianism", "Quzhou", "iron", (1, 1, 1)),
    Province(5026, "合州", "Hezhou (Chongqing)", 5026, None, "chongqing_area", "BAA", "gdd_shu", "confucianism", "Hezhou", "grain", (2, 2, 1)),
    Province(5334, "昌州", "Changzhou Sichuan", 5026, (164, 224, 58), "chongqing_area", "BAA", "gdd_shu", "confucianism", "Changzhou", "grain", (1, 2, 1)),
    Province(680, "重庆", "Chongqing", 680, None, "chongqing_area", "BAA", "gdd_shu", "confucianism", "Chongqing", "cloth", (4, 5, 2), cot=2),
    Province(5335, "江津", "Jiangjin", 680, (184, 77, 176), "chongqing_area", "BAA", "gdd_shu", "confucianism", "Jiangjin", "wine", (2, 3, 1)),
    Province(5027, "涪州", "Fuzhou (Chongqing)", 5027, None, "fuling_area", "ZHI", "miao", "animism", "Fuzhou", "paper", (1, 2, 1)),
    Province(5336, "南川", "Nanchuan", 5027, (76, 224, 192), "fuling_area", "ZHI", "miao", "animism", "Nanchuan", "iron", (1, 1, 1)),
    Province(5337, "彭水", "Pengshui", 5027, (184, 114, 48), "fuling_area", "ZHI", "miao", "animism", "Pengshui", "livestock", (1, 1, 1)),
    Province(4987, "万州", "Wanzhou", 4987, None, "xiajiang_area", "DQU", "gdd_shu", "confucianism", "Wanzhou", "tea", (2, 2, 1)),
    Province(5338, "忠州", "Zhongzhou", 4987, (120, 94, 224), "fuling_area", "ZHI", "gdd_shu", "confucianism", "Zhongzhou", "tea", (1, 2, 1)),
    Province(5339, "开州", "Kaizhou", 4987, (74, 184, 62), "xiajiang_area", "DQU", "gdd_shu", "confucianism", "Kaizhou", "tea", (1, 1, 1)),
    Province(5028, "夔州", "Kuizhou", 5028, None, "xiajiang_area", "BD2", "gdd_diqiang", "confucianism", "Kuizhou", "naval_supplies", (2, 2, 2), fort=True),
    Province(5340, "石砫", "Shizhu", 5028, (224, 58, 123), "fuling_area", "ZHI", "miao", "animism", "Shizhu", "livestock", (1, 1, 1)),
)

PARENT_IDS = (5080, 5081, 2169, 5082, 4211, 5026, 680, 5027, 4987, 5028)
NEW_IDS = tuple(p.province_id for p in P if p.colour is not None)
ALL_IDS = tuple(p.province_id for p in P)
BY_ID = {p.province_id: p for p in P}
HISTORY_FILENAMES = {
    5080: "5080 - Mianzhou.txt", 5081: "5081 - Jianzhou (Sichuan).txt",
    2169: "2169 - Langzhong.txt", 5082: "5082 - Shunqing.txt",
    4211: "4211 - Dazhou.txt", 5026: "5026 - Hezhou (Chongqing).txt",
    680: "680 - Chongqing.txt", 5027: "5027 - Fuzhou (Chongqing).txt",
    4987: "4987 - Wanzhou.txt", 5028: "5028 - Kuizhou.txt",
}
AREA_MEMBERS = {
    "chuanbei_area": (5080, 5081, 5329, 2169, 5331),
    "baqu_area": (5330, 5332, 5082, 4211, 5333),
    "chongqing_area": (5026, 5334, 680, 5335),
    "fuling_area": (5027, 5336, 5337, 5338, 5340),
    "xiajiang_area": (4987, 5339, 5028),
}
AREA_CHINESE = {
    "chuanbei_area": "苴阆", "baqu_area": "巴渠", "chongqing_area": "巴渝",
    "fuling_area": "枳涪", "xiajiang_area": "巫峡",
}
TERRAIN_IDS = {
    "grasslands": (5330, 5331, 5334, 5335),
    "hills": (5329, 5332, 5333, 5338, 5339),
    "highlands": (5336, 5337, 5340),
}
POLITY_SCOPE = {
    "SHU": (5080, 5331), "JUU": (5081, 5329),
    "BAA": (2169, 5330, 5082, 5026, 5334, 680, 5335),
    "DQU": (5332, 4211, 5333, 4987, 5339),
    "ZHI": (5027, 5336, 5337, 5338, 5340), "BD2": (5028,),
}
ORIGINAL_PARENT_DEV = {
    5081: (3, 3, 2), 2169: (4, 4, 2), 5082: (4, 5, 2),
    4211: (3, 3, 2), 5026: (4, 4, 2), 680: (8, 9, 3),
    5027: (4, 4, 2), 4987: (3, 4, 2), 5028: (3, 3, 2),
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
        if len(parts) < 5 or not parts[0].isdigit():
            continue
        rows[int(parts[0])] = (tuple(map(int, parts[1:4])), parts[4])
    return rows


def decode_ids(bitmap: Path) -> np.ndarray:
    lut = np.full(1 << 24, -1, dtype=np.int32)
    for province_id, (colour, _name) in definition_rows().items():
        red, green, blue = colour
        lut[(red << 16) | (green << 8) | blue] = province_id
    rgb = np.asarray(Image.open(bitmap).convert("RGB"), dtype=np.uint32)
    packed = (rgb[:, :, 0] << 16) | (rgb[:, :, 1] << 8) | rgb[:, :, 2]
    return lut[packed]


def components(mask: np.ndarray) -> int:
    seen = np.zeros(mask.shape, dtype=bool)
    count = 0
    height, width = mask.shape
    for y, x in zip(*np.where(mask & ~seen)):
        if seen[y, x]:
            continue
        count += 1
        stack = [(int(y), int(x))]
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
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


def add_marker_ids(text: str, key: str, ids: tuple[int, ...]) -> str:
    start, end = block_bounds(text, key)
    block = text[start:end]
    block = re.sub(rf"(?m)^\s*[0-9 ]+\s+# {re.escape(MARKER)}\s*$\n?", "", block)
    insertion = "\n        " + " ".join(map(str, ids)) + f" # {MARKER}\n"
    block = block[:-1].rstrip() + insertion + "}"
    return text[:start] + block + text[end:]


def add_marker_ids_to_nested_block(
    text: str,
    outer_key: str,
    nested_key: str,
    ids: tuple[int, ...],
) -> str:
    """Insert marker IDs into a nested membership block, not its parent category."""
    outer_start, outer_end = block_bounds(text, outer_key)
    outer = text[outer_start:outer_end]
    # Remove both the valid nested form and the former invalid category-level form.
    outer = re.sub(rf"(?m)^\s*[0-9 ]+\s+# {re.escape(MARKER)}\s*$\n?", "", outer)
    nested_start, nested_end = block_bounds(outer, nested_key)
    nested = add_marker_ids(outer[nested_start:nested_end], nested_key, ids)
    outer = outer[:nested_start] + nested + outer[nested_end:]
    return text[:outer_start] + outer + text[outer_end:]


def expected_geometry() -> tuple[np.ndarray, np.ndarray, dict[int, int]]:
    if not BACKUP.exists() or not REVIEWED.exists():
        raise FileNotFoundError("B46 needs pre_b46_provinces.bmp and b46_reviewed_provinces.bmp")
    base = np.asarray(Image.open(BACKUP).convert("RGB"), dtype=np.uint8)
    reviewed = np.asarray(Image.open(REVIEWED).convert("RGB"), dtype=np.uint8)
    if base.shape != reviewed.shape:
        raise ValueError("B46 bitmap dimensions differ")
    editable = np.isin(decode_ids(BACKUP), PARENT_IDS)
    outside_drift = int(np.count_nonzero(np.any(base != reviewed, axis=2) & ~editable))
    if outside_drift:
        raise ValueError(f"Reviewed B46 bitmap changed {outside_drift} pixels outside the frozen mask")
    expected = base.copy()
    expected[editable] = reviewed[editable]
    colours = definition_rows()
    pixel_counts: dict[int, int] = {}
    for province in P:
        colour = province.colour or colours[province.province_id][0]
        mask = np.all(expected == np.asarray(colour, dtype=np.uint8), axis=2) & editable
        if not mask.any() or components(mask) != 1:
            raise ValueError(f"Reviewed province {province.province_id} is empty or disconnected")
        pixel_counts[province.province_id] = int(mask.sum())
    return expected, editable, pixel_counts


def apply_geometry() -> tuple[int, int, dict[int, int]]:
    PLAN.mkdir(parents=True, exist_ok=True)
    canonical = MAP / "provinces.bmp"
    if not BACKUP.exists():
        shutil.copy2(canonical, BACKUP)
    expected, editable, pixel_counts = expected_geometry()
    current = np.asarray(Image.open(canonical).convert("RGB"), dtype=np.uint8).copy()
    before = current.copy()
    current[editable] = expected[editable]
    changed = np.any(current != before, axis=2)
    exterior = int(np.count_nonzero(changed & ~editable))
    if exterior:
        raise ValueError(f"B46 attempted {exterior} exterior pixel changes")
    Image.fromarray(current, mode="RGB").save(canonical, format="BMP")
    return int(np.count_nonzero(changed)), exterior, pixel_counts


def update_definition() -> None:
    path = MAP / "definition.csv"
    lines = path.read_text(encoding="cp1252").splitlines()
    new = {p.province_id: p for p in P if p.colour is not None}
    existing = definition_rows(path)
    used = {colour: province_id for province_id, (colour, _name) in existing.items()}
    for province in new.values():
        collision = used.get(province.colour)
        if collision is not None and collision != province.province_id:
            raise ValueError(f"Province RGB {province.colour} collides with {collision}")
    output: list[str] = []
    found: set[int] = set()
    for line in lines:
        head = line.split(";", 1)[0]
        if head.isdigit() and int(head) in new:
            province = new[int(head)]
            red, green, blue = province.colour
            output.append(f"{province.province_id};{red};{green};{blue};{province.english};x")
            found.add(province.province_id)
        else:
            output.append(line)
    for province in sorted(new.values(), key=lambda value: value.province_id):
        if province.province_id not in found:
            red, green, blue = province.colour
            output.append(f"{province.province_id};{red};{green};{blue};{province.english};x")
    path.write_text("\n".join(output) + "\n", encoding="cp1252")
    default = MAP / "default.map"
    ceiling = 5351 if B47_MANIFEST.exists() else 5341
    text, count = re.subn(r"(?m)^max_provinces\s*=\s*\d+", f"max_provinces = {ceiling}", default.read_text(encoding="cp1252"))
    if count != 1:
        raise ValueError("default.map needs exactly one max_provinces")
    default.write_text(text, encoding="cp1252")


def update_areas_and_region() -> None:
    path = MAP / "area.txt"
    text = path.read_text(encoding="cp1252")
    for area, members in AREA_MEMBERS.items():
        replacement = f"{area} = {{ # {MARKER}\n    {' '.join(map(str, members))}\n}}"
        text = replace_block(text, area, replacement)
    path.write_text(text, encoding="cp1252")

    path = MAP / "region.txt"
    text = path.read_text(encoding="cp1252")
    start, end = block_bounds(text, "xinan_region")
    block = text[start:end]
    for area in ("baqu_area", "fuling_area", "xiajiang_area"):
        block = re.sub(rf"(?m)^\s*{re.escape(area)}\s*$\n?", "", block)
    anchor = "        chongqing_area\n"
    if anchor not in block:
        raise ValueError("xinan_region lacks chongqing_area anchor")
    block = block.replace(anchor, anchor + "        baqu_area\n        fuling_area\n        xiajiang_area\n", 1)
    path.write_text(text[:start] + block + text[end:], encoding="cp1252")


def initial_and_dated(text: str) -> tuple[str, str]:
    match = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", text)
    return (text[:match.start()], text[match.start():]) if match else (text, "")


def history_path(province_id: int) -> Path:
    matches = list(HISTORY.glob(f"{province_id} - *.txt"))
    if len(matches) != 1:
        raise ValueError(f"Province {province_id} has {len(matches)} history files")
    return matches[0]


def history_text(province: Province, dated: str) -> str:
    lines = [
        f"# {province.province_id} - {province.english}", "",
        f"owner = {province.owner}", f"controller = {province.owner}",
        f"add_core = {province.owner}", f"culture = {province.culture}",
        f"religion = {province.religion}", f'capital = "{province.capital}"',
        f"trade_goods = {province.goods}", f"base_tax = {province.development[0]}",
        f"base_production = {province.development[1]}", f"base_manpower = {province.development[2]}",
        "is_city = yes",
    ]
    if province.cot:
        lines.append(f"center_of_trade = {province.cot}")
    if province.fort:
        lines.append("fort_15th = yes")
    lines += ["discovered_by = chinese", "discovered_by = nomad_group"]
    if province.religion == "animism":
        lines.append("discovered_by = indian")
    return "\n".join(lines) + "\n\n" + dated.lstrip()


def update_histories() -> None:
    dated_by_parent = {
        parent: initial_and_dated(history_path(parent).read_text(encoding="cp1252"))[1]
        for parent in PARENT_IDS
    }
    for province in P:
        filename = HISTORY_FILENAMES.get(province.province_id, f"{province.province_id} - {province.english}.txt")
        desired = HISTORY / filename
        for old in HISTORY.glob(f"{province.province_id} - *.txt"):
            if old != desired:
                old.unlink()
        desired.write_text(history_text(province, dated_by_parent[province.parent_id]), encoding="cp1252")


def deep_interior_point(mask: np.ndarray) -> tuple[int, int]:
    current = mask.copy()
    last = current.copy()
    while current.any():
        last = current
        padded = np.pad(current, 1)
        current = (
            padded[1:-1, 1:-1] & padded[:-2, 1:-1] & padded[2:, 1:-1]
            & padded[1:-1, :-2] & padded[1:-1, 2:]
        )
    ys, xs = np.where(last)
    return int(np.median(xs)), int(np.median(ys))


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
    for filename, block in (("continent.txt", "asia"), ("climate.txt", "normal_monsoon")):
        path = MAP / filename
        path.write_text(add_marker_ids(path.read_text(encoding="cp1252"), block, NEW_IDS), encoding="cp1252")
    terrain = MAP / "terrain.txt"
    text = terrain.read_text(encoding="cp1252")
    for block, ids in TERRAIN_IDS.items():
        text = add_marker_ids_to_nested_block(text, block, "terrain_override", ids)
    terrain.write_text(text, encoding="cp1252")
    node = MOD / "common/tradenodes/00_tradenodes.txt"
    text = node.read_text(encoding="cp1252")
    start, end = block_bounds(text, "chengdu")
    chengdu = add_marker_ids(text[start:end], "members", NEW_IDS)
    node.write_text(text[:start] + chengdu + text[end:], encoding="cp1252")
    company = MOD / "common/trade_companies/00_trade_companies.txt"
    text = company.read_text(encoding="cp1252")
    start, end = block_bounds(text, "trade_company_chengdu")
    chengdu = add_marker_ids(text[start:end], "provinces", NEW_IDS)
    company.write_text(text[:start] + chengdu + text[end:], encoding="cp1252")


def write_flag(tag: str, background: tuple[int, int, int]) -> None:
    """Write the deterministic uncompressed 128x128 TGA used by B43."""
    red, green, blue = background
    light = tuple(min(255, channel + 52) for channel in background)
    dark = tuple(max(0, channel - 52) for channel in background)
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, 128, 128, 24, 0x20)
    pixels = bytearray()
    for y in range(128):
        for x in range(128):
            if abs(x - y) < 11:
                pixel = light
            elif abs((127 - x) - y) < 9:
                pixel = dark
            else:
                pixel = (red, green, blue)
            pixels.extend((pixel[2], pixel[1], pixel[0]))
    (FLAGS / f"{tag}.tga").write_bytes(header + bytes(pixels))


def update_countries() -> None:
    tags = MOD / "common/country_tags/gdd_country_tags.txt"
    text = tags.read_text(encoding="cp1252")
    for tag in ("DQU", "ZHI"):
        text = re.sub(rf"(?m)^{tag}\s*=.*$\n?", "", text)
    text = text.rstrip() + '\nDQU = "countries/B46_Dangqu.txt"\nZHI = "countries/B46_Zhi.txt"\n'
    tags.write_text(text, encoding="cp1252")
    (COUNTRIES / "B46_Dangqu.txt").write_text(
        "# B46 GeoJSON-guided northeast Sichuan polity.\ngraphical_culture = asiangfx\n\n"
        "color = { 74 150 105 }\nrevolutionary_colors = { 3 6 4 }\n", encoding="cp1252"
    )
    (COUNTRIES / "B46_Zhi.txt").write_text(
        "# B46 GeoJSON-guided Chongqing polity.\ngraphical_culture = asiangfx\n\n"
        "color = { 161 86 151 }\nrevolutionary_colors = { 6 3 6 }\n", encoding="cp1252"
    )
    (COUNTRY_HISTORY / "DQU - Dangqu.txt").write_text(
        "# B46 Dangqu polity.\ngovernment = monarchy\nadd_government_reform = gdd_local_fiefdom_reform\n"
        "government_rank = 1\ntechnology_group = chinese\nreligion = confucianism\n"
        "primary_culture = gdd_shu\nadd_accepted_culture = gdd_diqiang\ncapital = 5333\nfixed_capital = 5333\n",
        encoding="cp1252",
    )
    (COUNTRY_HISTORY / "ZHI - Zhi.txt").write_text(
        "# B46 Zhi polity.\ngovernment = monarchy\nadd_government_reform = gdd_local_fiefdom_reform\n"
        "government_rank = 1\ntechnology_group = chinese\nreligion = animism\n"
        "primary_culture = miao\nadd_accepted_culture = gdd_shu\ncapital = 5027\nfixed_capital = 5027\n",
        encoding="cp1252",
    )
    write_flag("DQU", (74, 150, 105))
    write_flag("ZHI", (161, 86, 151))


def update_localisation() -> None:
    lines = ["﻿l_english:"]
    for province in P:
        if province.colour is not None:
            lines += [f' PROV{province.province_id}:0 "{province.chinese}"', f' PROV_ADJ{province.province_id}:0 "{province.chinese}"']
    lines += ["", ' DQU:0 "宕渠"', ' DQU_ADJ:0 "宕渠"', ' ZHI:0 "枳"', ' ZHI_ADJ:0 "枳"']
    for area in ("baqu_area", "fuling_area", "xiajiang_area"):
        chinese = AREA_CHINESE[area]
        lines += ["", f' {area}:0 "{chinese}"', f' {area}_name:0 "{chinese}"', f' {area}_adj:0 "{chinese}"']
    source = MOD / "localisation_source/gdd_b46_chuandongbei_chongqing_refinement_readable_utf8.txt"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    override = MOD / "localisation_source/gdd_zzz_chunqiu_area_overrides_readable_utf8.txt"
    text = override.read_text(encoding="utf-8-sig")
    for area in ("chuanbei_area", "chongqing_area"):
        for key in (area, f"{area}_name", f"{area}_adj"):
            text, count = re.subn(rf'(?m)^(\s*{re.escape(key)}:\d+\s+")[^"]*("\s*)$', rf'\g<1>{AREA_CHINESE[area]}\g<2>', text)
            if count != 1:
                raise ValueError(f"Expected one area override for {key}, found {count}")
    override.write_text("﻿" + text, encoding="utf-8")
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(source, MOD / "localisation/gdd_b46_chuandongbei_chongqing_refinement_l_english.yml")
    encode_file(override, MOD / "localisation/replace/zzz_gdd_chunqiu_area_overrides_l_english.yml")


def update_culture_csv() -> None:
    path = ROOT / "planning/culture_overhaul/approved_province_culture_assignments.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    rows = [row for row in rows if int(row["province_id"]) not in NEW_IDS]
    group = {"gdd_shu": ("汉文化组", "巴蜀文化"), "miao": ("百越文化组", "苗瑶文化")}
    for province in P:
        if province.colour is None:
            continue
        document_group, document_culture = group[province.culture]
        rows.append({
            "province_id": str(province.province_id), "province_name": province.chinese,
            "document_group": document_group, "document_culture": document_culture,
            "document_entry": "B46川东北重庆二次细化", "target_culture": province.culture,
            "source_rule": "user_delegated", "decision_note": "用户授权按国家、地形与区域连通性裁决；B46新增省份",
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
    rows = [row for row in rows if row["draw_batch"] != "B46"]
    definitions = definition_rows()
    for sequence, province in enumerate((value for value in P if value.colour is not None), 1):
        red, green, blue = province.colour
        parent_group = tuple(value for value in P if value.parent_id == province.parent_id)
        retained = next(value for value in parent_group if value.province_id == province.parent_id)
        original = ORIGINAL_PARENT_DEV[province.parent_id]
        final_total = sum(sum(value.development) for value in parent_group)
        row = {field: "" for field in fields}
        row.update({
            "design_key": f"B46-{sequence:02d}", "game_id": str(province.province_id),
            "rgb_r": str(red), "rgb_g": str(green), "rgb_b": str(blue),
            "macro_region": "south_china", "draw_batch": "B46", "new_name_zh": province.chinese,
            "new_name_en": province.english, "internal_key_hint": f"gdd_b46_{province.english.lower().replace(' ', '_')}",
            "parent_id": str(province.parent_id), "parent_definition_name": definitions[province.parent_id][1],
            "parent_history_name": history_path(province.parent_id).stem.split(" - ", 1)[1],
            "parent_area": province.area,
            "parent_tax": str(original[0]), "parent_production": str(original[1]),
            "parent_manpower": str(original[2]),
            "retained_name_zh": retained.chinese, "retained_tax": str(retained.development[0]),
            "retained_production": str(retained.development[1]), "retained_manpower": str(retained.development[2]),
            "new_tax": str(province.development[0]), "new_production": str(province.development[1]),
            "new_manpower": str(province.development[2]), "split_group": f"b46-p{province.parent_id}",
            "group_dev_delta": str(final_total - sum(original)), "proposed_owner": province.owner,
            "claims_or_uncertainty": "用户授权国家与文化归属；县级GeoJSON用于边界语言",
            "status": "implemented", "rationale": "川东北—重庆二次细化；只拆母省、总发展度守恒。",
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


def validate(pixel_counts: dict[int, int]) -> dict[str, object]:
    rows = definition_rows()
    expected_highest = 5350 if B47_MANIFEST.exists() else 5340
    expected_ceiling = 5351 if B47_MANIFEST.exists() else 5341
    if max(rows) != expected_highest or f"max_provinces = {expected_ceiling}" not in (MAP / "default.map").read_text(encoding="cp1252"):
        raise ValueError(f"B46 province ceiling is not {expected_highest}/{expected_ceiling}")
    new_colours = {province.province_id: rows[province.province_id][0] for province in P if province.colour is not None}
    for province_id, colour in new_colours.items():
        collisions = [other for other, (other_colour, _name) in rows.items() if other != province_id and other_colour == colour]
        if collisions:
            raise ValueError(f"Province {province_id} colour collides with {collisions}")
    ids = decode_ids(MAP / "provinces.bmp")
    for province in P:
        mask = ids == province.province_id
        if int(mask.sum()) != pixel_counts[province.province_id] or components(mask) != 1:
            raise ValueError(f"Province {province.province_id} geometry mismatch")
        path = history_path(province.province_id)
        actual_dev = tuple(int(read_history_value(path, key)) for key in ("base_tax", "base_production", "base_manpower"))
        if read_history_value(path, "owner") != province.owner or read_history_value(path, "culture") != province.culture or actual_dev != province.development:
            raise ValueError(f"Province {province.province_id} history mismatch")
    memberships = parse_area_memberships()
    for area, members in AREA_MEMBERS.items():
        for province_id in members:
            if memberships.get(province_id) != {area}:
                raise ValueError(f"Province {province_id} area mismatch: {memberships.get(province_id)}")
        if components(np.isin(ids, members)) != 1:
            raise ValueError(f"Area {area} is not land-connected")
    for tag, members in POLITY_SCOPE.items():
        if components(np.isin(ids, members)) != 1:
            raise ValueError(f"Polity {tag} B46 scope is not land-connected")
    actual_scope: dict[str, list[int]] = {}
    for province in P:
        actual_scope.setdefault(read_history_value(history_path(province.province_id), "owner"), []).append(province.province_id)
    if {tag: sorted(ids_) for tag, ids_ in actual_scope.items()} != {tag: sorted(ids_) for tag, ids_ in POLITY_SCOPE.items()}:
        raise ValueError(f"B46 polity scope mismatch: {actual_scope}")
    total = sum(sum(province.development) for province in P)
    if total != 106:
        raise ValueError(f"B46 development drifted to {total}")
    for tag in ("DQU", "ZHI"):
        if len(list(COUNTRY_HISTORY.glob(f"{tag} - *.txt"))) != 1 or not (FLAGS / f"{tag}.tga").exists():
            raise ValueError(f"Country {tag} artifacts are incomplete")
    terrain_text = (MAP / "terrain.txt").read_text(encoding="cp1252")
    for category, expected_ids in TERRAIN_IDS.items():
        category_start, category_end = block_bounds(terrain_text, category)
        category_block = terrain_text[category_start:category_end]
        override_start, override_end = block_bounds(category_block, "terrain_override")
        override_block = category_block[override_start:override_end]
        outside_override = category_block[:override_start] + category_block[override_end:]
        if MARKER in outside_override:
            raise ValueError(f"{category}: B46 terrain IDs escaped terrain_override")
        for province_id in expected_ids:
            occurrences = len(re.findall(rf"(?<!\d){province_id}(?!\d)", override_block))
            if occurrences != 1:
                raise ValueError(
                    f"{category}: province {province_id} must occur exactly once in terrain_override, found {occurrences}"
                )
    return {
        "province_components": "22/22 one component",
        "area_components": "5/5 one component",
        "polity_components": "6/6 one component in B46 scope",
        "development_total": total,
        "polity_development_in_scope": {
            tag: sum(sum(BY_ID[province_id].development) for province_id in members)
            for tag, members in POLITY_SCOPE.items()
        },
    }


def write_manifest(changed: int, exterior: int, pixel_counts: dict[int, int], validation: dict[str, object]) -> None:
    canonical = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    baseline = np.asarray(Image.open(BACKUP).convert("RGB"), dtype=np.uint8)
    editable = np.isin(decode_ids(BACKUP), PARENT_IDS)
    delta = np.any(canonical != baseline, axis=2)
    payload = {
        "batch": "B46_chuandongbei_chongqing_geojson_refinement", "marker": MARKER,
        "purpose": "Implement the reviewed GeoJSON-guided second refinement without increasing regional development.",
        "parent_ids": list(PARENT_IDS), "new_provinces": [asdict(province) for province in P if province.colour is not None],
        "reviewed_bitmap": str(REVIEWED), "reviewed_bitmap_sha256": sha256(REVIEWED),
        "backup": str(BACKUP), "changed_pixels_this_run": changed,
        "changed_pixels_vs_backup": int(np.count_nonzero(delta)),
        "changed_pixels_vs_backup_outside_editable_mask": int(np.count_nonzero(delta & ~editable)),
        "changed_pixels_outside_editable_mask": exterior, "pixel_counts": pixel_counts,
        "areas": {key: list(value) for key, value in AREA_MEMBERS.items()},
        "region": "xinan_region", "trade_node": "chengdu", "trade_company": "trade_company_chengdu",
        "countries": {key: list(value) for key, value in POLITY_SCOPE.items()},
        "validation": validation, "canonical_bitmap_sha256": sha256(MAP / "provinces.bmp"),
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply() -> None:
    changed, exterior, pixel_counts = apply_geometry()
    update_definition()
    update_areas_and_region()
    update_histories()
    update_positions()
    update_memberships()
    update_countries()
    update_localisation()
    update_culture_csv()
    update_registry()
    validation = validate(pixel_counts)
    write_manifest(changed, exterior, pixel_counts, validation)
    print(f"{MARKER}; NEW_PROVINCES:{len(NEW_IDS)}; CHANGED_PIXELS:{changed}; EXTERIOR_PIXELS:{exterior}; DEV:106")


def check() -> None:
    expected, editable, pixel_counts = expected_geometry()
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    mismatches = int(np.count_nonzero(np.any(current != expected, axis=2) & editable))
    if mismatches:
        raise ValueError(f"Canonical bitmap differs from frozen B46 geometry at {mismatches} pixels")
    validation = validate(pixel_counts)
    print(f"{MARKER}_CHECK; PASS; DEV:{validation['development_total']}; NEW_PROVINCES:{len(NEW_IDS)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    check() if args.check else apply()


if __name__ == "__main__":
    main()
