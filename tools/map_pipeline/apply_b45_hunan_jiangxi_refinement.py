#!/usr/bin/env python3
"""Apply the reviewed B45 balanced Hunan-Jiangxi refinement.

The geometry is clipped to eleven current parent provinces and follows the
reviewed Jiazi reference only for internal borders.  The script is a terminal,
idempotent transaction: it never restores the whole bitmap from its backup and
never changes pixels outside the frozen parent mask.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, deque
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
HISTORY = MOD / "history/provinces"
COUNTRY_HISTORY = MOD / "history/countries"
COUNTRIES = MOD / "common/countries"
FLAGS = MOD / "gfx/flags"
PLAN = ROOT / "planning/hunan_jiangxi_refinement_b45"
BACKUP = PLAN / "pre_b45_provinces.bmp"
PREVIEW_COUNTRIES = PLAN / "b45_country_preview.png"
PREVIEW_AREAS = PLAN / "b45_area_preview.png"
MANIFEST = PLAN / "batch_manifest.json"
MARKER = "GDD_B45_HUNAN_JIANGXI_REFINEMENT"
B46_MANIFEST = ROOT / "planning/chuandongbei_chongqing_b46/batch_manifest.json"
B47_MANIFEST = ROOT / "planning/jingxiang_yunan_b47/batch_manifest.json"
DEFAULT_REFERENCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/3400977776"
)
FONT = Path("/System/Library/Fonts/STHeiti Medium.ttc")
BITMAP_HEIGHT = 2048


@dataclass(frozen=True)
class Province:
    province_id: int
    chinese: str
    english: str
    parent_id: int
    colour: tuple[int, int, int] | None
    reference_ids: tuple[int, ...]
    area: str
    owner: str
    culture: str
    religion: str
    capital: str
    goods: str
    development: tuple[int, int, int]
    cores: tuple[str, ...]
    cot: int = 0
    fort: bool = False
    kilns: bool = False


P = (
    # Hunan: eleven new provinces, while Changsha is deliberately capped at
    # Changsha-Xiangtan-Liuyang rather than receiving the whole province set.
    Province(2173, "辰州", "Chenzhou West", 2173, None, (2173, 5283, 5284, 5261), "wuling_hunan_area", "CZM", "miao", "animism", "Yuanling", "tea", (1, 1, 1), ("CZM",)),
    Province(5312, "永顺", "Yongshun", 2173, (233, 147, 191), (5289, 5288, 5248), "wuling_hunan_area", "WLM", "miao", "animism", "Yongshun", "tea", (1, 1, 1), ("WLM",)),
    Province(5313, "保靖", "Baojing", 2173, (50, 42, 134), (5277, 5278), "wuling_hunan_area", "WLM", "miao", "animism", "Baojing", "livestock", (0, 1, 2), ("WLM",)),
    Province(5314, "沅州", "Yuanzhou Hunan", 2173, (123, 193, 77), (5279, 5282, 5285, 5268), "wuling_hunan_area", "CZM", "miao", "animism", "Yuanzhou", "tea", (1, 1, 2), ("CZM",)),
    Province(4999, "靖州", "Jingzhou Hunan", 4999, None, (5281, 5279, 5280), "southwest_hunan_area", "CZM", "miao", "animism", "Jingzhou", "livestock", (2, 2, 3), ("CZM",)),
    Province(5315, "绥宁", "Suining Hunan", 4999, (196, 88, 20), (5282, 673), "southwest_hunan_area", "CZM", "miao", "animism", "Suining", "naval_supplies", (1, 1, 2), ("CZM",)),
    Province(4996, "澧州", "Lizhou", 4996, None, (5286, 5287), "lishui_area", "WLM", "miao", "confucianism", "Lizhou", "grain", (1, 2, 1), ("WLM",)),
    Province(5316, "慈利", "Cili", 4996, (13, 239, 219), (5290, 5288), "lishui_area", "WLM", "gdd_chu", "confucianism", "Cili", "grain", (1, 1, 1), ("WLM",)),
    Province(5317, "桑植", "Sangzhi", 4996, (86, 134, 162), (5291, 5289), "lishui_area", "WLM", "miao", "animism", "Sangzhi", "livestock", (0, 1, 2), ("WLM",)),
    Province(2174, "衡州", "Hengzhou", 2174, None, (2174, 5270, 5268, 5269), "hengchen_area", "HNG", "gdd_chu", "confucianism", "Hengyang", "gold", (2, 2, 2), ("HNG",), cot=1),
    Province(5318, "耒阳", "Leiyang", 2174, (159, 29, 105), (5266, 5274, 5275, 5276), "hengchen_area", "HNG", "gdd_chu", "confucianism", "Leiyang", "copper", (1, 1, 2), ("HNG",)),
    Province(5319, "茶陵", "Chaling", 2174, (232, 180, 48), (5267, 5264, 5263, 5304), "hengchen_area", "HNG", "gdd_chu", "confucianism", "Chaling", "tea", (1, 1, 1), ("HNG",)),
    Province(671, "长沙", "Changsha", 671, None, (671, 5259, 5257), "hunan_area", "CSA", "gdd_chu", "confucianism", "Changsha", "grain", (4, 4, 2), ("CSA",)),
    Province(5320, "平江", "Pingjiang", 671, (49, 75, 247), (5260,), "hunan_area", "CHC", "gdd_chu", "confucianism", "Pingjiang", "tea", (3, 2, 1), ("CHC",)),
    Province(5321, "浏阳", "Liuyang", 671, (122, 226, 190), (5265, 5261, 5263, 5264, 5296, 5295), "hunan_area", "CSA", "gdd_chu", "confucianism", "Liuyang", "chinaware", (1, 3, 1), ("CSA",)),
    Province(4997, "益阳", "Yiyang", 4997, None, (5261, 5263, 671), "dongting_area", "WLM", "gdd_chu", "confucianism", "Yiyang", "naval_supplies", (2, 2, 2), ("WLM",)),
    Province(5322, "安化", "Anhua", 4997, (195, 121, 133), (5262, 5284, 5283, 2174), "dongting_area", "WLM", "gdd_chu", "confucianism", "Anhua", "tea", (2, 2, 2), ("WLM",)),
    # Jiangxi: six new provinces, preserving every parent group's development.
    Province(683, "南昌", "Nanchang", 683, None, (683, 5292, 5297), "jiangxi_area", "NCH", "gdd_gan", "confucianism", "Nanchang", "paper", (4, 4, 2), ("NNG", "NCH")),
    Province(5323, "丰城", "Fengcheng", 683, (12, 16, 76), (5299, 5296, 1833), "xunyang_area", "NCH", "gdd_gan", "confucianism", "Fengcheng", "grain", (3, 3, 2), ("NNG", "NCH")),
    Province(5324, "奉新", "Fengxin", 683, (85, 167, 19), (5300, 5302, 5295), "xunyang_area", "NCH", "gdd_gan", "confucianism", "Fengxin", "paper", (2, 3, 2), ("NNG", "NCH")),
    Province(2151, "饶州", "Raozhou", 2151, None, (2151, 5294, 5292, 5405), "jiangxi_area", "NCH", "gdd_gan", "confucianism", "Poyang", "chinaware", (4, 4, 2), ("NNG", "NCH")),
    Province(5325, "昌南", "Changnan", 2151, (158, 62, 218), (5293, 5305), "jiangxi_area", "NCH", "gdd_gan", "confucianism", "Changnan", "chinaware", (3, 5, 2), ("NNG", "NCH"), kilns=True),
    Province(4993, "广信", "Guangxin", 4993, None, (5349, 5305, 5211, 5405, 5332), "jiangxi_area", "TSF", "gdd_gan", "confucianism", "Shangrao", "copper", (3, 3, 2), ("NNG", "TSF")),
    Province(5326, "德兴", "Dexing", 4993, (231, 213, 161), (5306, 5293, 5351), "jiangxi_area", "TSF", "gdd_gan", "confucianism", "Dexing", "copper", (2, 3, 1), ("NNG", "TSF")),
    Province(670, "赣州", "Ganzhou", 670, None, (670, 5310, 5303, 5309, 5347, 5405), "gannan_area", "HAK", "gdd_hakka", "confucianism", "Ganzhou", "grain", (4, 4, 2), ("NNG", "HAK"), cot=1),
    Province(5327, "宁都", "Ningdu", 670, (48, 108, 104), (5308, 5301, 5353, 1833), "gannan_area", "HAK", "gdd_hakka", "confucianism", "Ningdu", "grain", (2, 3, 3), ("NNG", "HAK")),
    Province(4994, "袁州", "Yuanzhou Jiangxi", 4994, None, (1833, 5298, 5296, 5297), "south_jiangxi_area", "CHC", "gdd_gan", "confucianism", "Yuanzhou", "grain", (2, 2, 2), ("NNG", "CHC")),
    Province(5328, "安福", "Anfu", 4994, (121, 3, 47), (5304, 5303), "south_jiangxi_area", "LCH", "gdd_gan", "confucianism", "Anfu", "grain", (1, 2, 1), ("NNG", "LCH")),
)


# Unsplit Hunan provinces whose political balance changes in the same batch.
UNSPLIT_UPDATES = {
    672: dict(owner="WLM", culture="gdd_chu", religion="confucianism", cores=("WLM",), capital="Changde", goods="cotton", development=(5, 6, 4), cot=0, fort=False),
    4982: dict(owner="CHC", culture="gdd_chu", religion="confucianism", cores=("CHC",), capital="Yuezhou", goods="tea", development=(7, 8, 4), cot=1, fort=False),
    4983: dict(owner="HNG", culture="gdd_chu", religion="confucianism", cores=("HNG",), capital="Baoqing", goods="livestock", development=(3, 3, 4), cot=0, fort=False),
    4998: dict(owner="CSA", culture="gdd_chu", religion="confucianism", cores=("CSA",), capital="Xiangtan", goods="chinaware", development=(4, 5, 3), cot=0, fort=False),
    5000: dict(owner="HNG", culture="gdd_chu", religion="confucianism", cores=("HNG",), capital="Yongzhou", goods="iron", development=(3, 3, 4), cot=0, fort=False),
    5001: dict(owner="HNG", culture="gdd_gui", religion="confucianism", cores=("HNG",), capital="Chenzhou", goods="copper", development=(4, 6, 4), cot=0, fort=True),
    5216: dict(owner="HNG", culture="gdd_hakka", religion="confucianism", cores=("HNG",), capital="Lianzhou", goods="livestock", development=(2, 2, 1), cot=0, fort=False),
}


AREA_MEMBERS = {
    "wuling_hunan_area": (2173, 5312, 5313, 5314),
    "lishui_area": (4996, 5316, 5317),
    "dongting_area": (672, 4997, 5322),
    "hunan_area": (4982, 671, 5320, 5321, 4998),
    "hengchen_area": (2174, 5318, 5319, 5001),
    "southwest_hunan_area": (4999, 5315, 4983, 5000),
    "xunyang_area": (4979, 5324, 4992, 5323),
    "jiangxi_area": (683, 2151, 5325, 4993, 5326),
    "south_jiangxi_area": (1833, 4980, 4994, 5328),
    "gannan_area": (670, 5327, 4995),
    "jingyi_shinan_area": (2172, 5015, 5010, 5013, 5014),
}

AREA_CHINESE = {
    "wuling_hunan_area": "黔中", "lishui_area": "澧水", "dongting_area": "云梦",
    "hunan_area": "长沙", "hengchen_area": "衡湘", "southwest_hunan_area": "湘沅",
    "xunyang_area": "艾邑", "jiangxi_area": "豫章", "south_jiangxi_area": "庐陵",
    "gannan_area": "南野",
}

NEW_IDS = tuple(province.province_id for province in P if province.colour is not None)
HUNAN_NEW_IDS = tuple(pid for pid in NEW_IDS if pid <= 5322)
JIANGXI_NEW_IDS = tuple(pid for pid in NEW_IDS if pid >= 5323)
PARENT_IDS = tuple(dict.fromkeys(province.parent_id for province in P))
FINAL_PROVINCE_BY_ID = {province.province_id: province for province in P}
SPLIT_BY_PARENT = {
    parent: tuple(province for province in P if province.parent_id == parent)
    for parent in PARENT_IDS
}

SCOPE_NAMES = {
    **{province.province_id: province.chinese for province in P},
    672: "常德", 4982: "岳州", 4998: "湘潭", 4983: "宝庆", 5000: "永州", 5001: "郴州",
    4979: "九江", 4992: "瑞州", 1833: "吉安", 4980: "临川", 4995: "南安",
}

OWNER_COLOURS = {
    "CSA": (113, 149, 141), "HNG": (93, 117, 160), "CHC": (231, 176, 194),
    "WLM": (159, 129, 111), "CZM": (128, 149, 109), "NCH": (82, 136, 174),
    "LCH": (193, 166, 82), "TSF": (171, 136, 146), "HAK": (181, 151, 101),
}

UNSPLIT_OWNERS = {
    672: "WLM", 4982: "CHC", 4998: "CSA", 4983: "HNG", 5000: "HNG", 5001: "HNG",
    4979: "CHC", 4992: "CHC", 1833: "LCH", 4980: "LCH", 4995: "HAK",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def definition_rows(path: Path = MAP / "definition.csv") -> dict[int, tuple[tuple[int, int, int], str]]:
    rows: dict[int, tuple[tuple[int, int, int], str]] = {}
    for raw in path.read_text(encoding="cp1252").splitlines():
        parts = raw.split(";")
        if len(parts) < 5:
            continue
        try:
            province_id = int(parts[0])
            colour = tuple(map(int, parts[1:4]))
        except ValueError:
            continue
        rows[province_id] = (colour, parts[4])
    return rows


def decode_ids(bitmap: Path, definition: Path) -> np.ndarray:
    lut = np.full(1 << 24, -1, dtype=np.int32)
    for province_id, (colour, _name) in definition_rows(definition).items():
        red, green, blue = colour
        lut[(red << 16) | (green << 8) | blue] = province_id
    rgb = np.asarray(Image.open(bitmap).convert("RGB"), dtype=np.uint32)
    packed = (rgb[:, :, 0] << 16) | (rgb[:, :, 1] << 8) | rgb[:, :, 2]
    return lut[packed]


def components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    seen = np.zeros(mask.shape, dtype=bool)
    result: list[list[tuple[int, int]]] = []
    height, width = mask.shape
    for y, x in zip(*np.where(mask & ~seen)):
        if seen[y, x]:
            continue
        queue = [(int(y), int(x))]
        seen[y, x] = True
        component: list[tuple[int, int]] = []
        for cy, cx in queue:
            component.append((cy, cx))
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        result.append(component)
    return sorted(result, key=len, reverse=True)


def fill_unassigned(parent_mask: np.ndarray, labels: np.ndarray) -> None:
    height, width = labels.shape
    queue: deque[tuple[int, int]] = deque(
        (int(y), int(x)) for y, x in zip(*np.where(parent_mask & (labels >= 0)))
    )
    if not queue:
        raise ValueError("Split parent has no reference seeds")
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width and parent_mask[ny, nx] and labels[ny, nx] < 0:
                labels[ny, nx] = labels[y, x]
                queue.append((ny, nx))


def clean_labels(parent_mask: np.ndarray, labels: np.ndarray, group_count: int) -> None:
    height, width = labels.shape
    for _ in range(16):
        changed = False
        for group in range(group_count):
            for component in components(parent_mask & (labels == group))[1:]:
                votes: Counter[int] = Counter()
                for y, x in component:
                    for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                        if 0 <= ny < height and 0 <= nx < width and parent_mask[ny, nx]:
                            other = int(labels[ny, nx])
                            if other >= 0 and other != group:
                                votes[other] += 1
                if not votes:
                    raise ValueError("Disconnected fragment has no replacement neighbour")
                replacement = votes.most_common(1)[0][0]
                for y, x in component:
                    labels[y, x] = replacement
                changed = True
        if not changed:
            return
    raise ValueError("Split cleanup did not converge")


def expected_geometry(reference_root: Path) -> tuple[np.ndarray, np.ndarray, dict[int, int]]:
    if not BACKUP.exists():
        raise FileNotFoundError(f"Missing B45 bitmap backup: {BACKUP}")
    base = np.array(Image.open(BACKUP).convert("RGB"), dtype=np.uint8)
    current_rows = definition_rows()
    base_ids = decode_ids(BACKUP, MAP / "definition.csv")
    reference_ids = decode_ids(reference_root / "map/provinces.bmp", reference_root / "map/definition.csv")
    expected = base.copy()
    editable = np.isin(base_ids, PARENT_IDS)
    pixel_counts: dict[int, int] = {}
    for parent_id, provinces in SPLIT_BY_PARENT.items():
        parent_mask = base_ids == parent_id
        labels = np.full(base_ids.shape, -1, dtype=np.int16)
        for index, province in enumerate(provinces):
            labels[parent_mask & np.isin(reference_ids, province.reference_ids)] = index
        seed_counts = [int(np.sum(parent_mask & (labels == index))) for index in range(len(provinces))]
        if any(count == 0 for count in seed_counts):
            raise ValueError(f"Parent {parent_id} has empty Jiazi seed groups: {seed_counts}")
        fill_unassigned(parent_mask, labels)
        clean_labels(parent_mask, labels, len(provinces))
        # A pre-B45 parent can contain an old detached crumb that no land path
        # can reach from any reviewed reference seed.  Retire only that crumb
        # inside the frozen editable mask by folding it into its real neighbour.
        for orphan in components(parent_mask & (labels < 0)):
            votes: Counter[tuple[int, int, int]] = Counter()
            for y, x in orphan:
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < base.shape[0] and 0 <= nx < base.shape[1] and not parent_mask[ny, nx]:
                        votes[tuple(int(value) for value in base[ny, nx])] += 1
            if not votes:
                raise ValueError(f"Parent {parent_id} has an isolated crumb without a neighbour")
            replacement = votes.most_common(1)[0][0]
            for y, x in orphan:
                expected[y, x] = replacement
        for index, province in enumerate(provinces):
            province_mask = parent_mask & (labels == index)
            if len(components(province_mask)) != 1:
                raise ValueError(f"Province {province.province_id} is not four-way connected")
            if province.colour is None:
                colour = current_rows[parent_id][0]
            else:
                colour = province.colour
            expected[province_mask] = colour
            pixel_counts[province.province_id] = int(province_mask.sum())
    return expected, editable, pixel_counts


def apply_geometry(reference_root: Path) -> tuple[int, int, dict[int, int]]:
    PLAN.mkdir(parents=True, exist_ok=True)
    canonical_path = MAP / "provinces.bmp"
    if not BACKUP.exists():
        shutil.copy2(canonical_path, BACKUP)
    current = np.array(Image.open(canonical_path).convert("RGB"), dtype=np.uint8)
    expected, editable, pixel_counts = expected_geometry(reference_root)
    before = current.copy()
    current[editable] = expected[editable]
    changed = np.any(current != before, axis=2)
    exterior = int(np.count_nonzero(changed & ~editable))
    if exterior:
        raise ValueError(f"B45 attempted {exterior} exterior pixel changes")
    Image.fromarray(current, mode="RGB").save(canonical_path, format="BMP")
    return int(np.count_nonzero(changed)), exterior, pixel_counts


def update_definition() -> None:
    path = MAP / "definition.csv"
    lines = path.read_text(encoding="cp1252").splitlines()
    existing = definition_rows(path)
    used_colours = {colour: province_id for province_id, (colour, _name) in existing.items()}
    new_by_id = {province.province_id: province for province in P if province.colour is not None}
    for province in new_by_id.values():
        collision = used_colours.get(province.colour)
        if collision is not None and collision != province.province_id:
            raise ValueError(f"RGB {province.colour} collides with province {collision}")
    output: list[str] = []
    found: set[int] = set()
    for line in lines:
        head = line.split(";", 1)[0]
        if head.isdigit() and int(head) in new_by_id:
            province = new_by_id[int(head)]
            red, green, blue = province.colour
            output.append(f"{province.province_id};{red};{green};{blue};{province.english};x")
            found.add(province.province_id)
        else:
            output.append(line)
    for province in sorted(new_by_id.values(), key=lambda value: value.province_id):
        if province.province_id not in found:
            red, green, blue = province.colour
            output.append(f"{province.province_id};{red};{green};{blue};{province.english};x")
    path.write_text("\n".join(output) + "\n", encoding="cp1252")

    default_path = MAP / "default.map"
    default_text = default_path.read_text(encoding="cp1252")
    ceiling = 5351 if B47_MANIFEST.exists() else (5341 if B46_MANIFEST.exists() else 5329)
    default_text, count = re.subn(r"(?m)^max_provinces\s*=\s*\d+", f"max_provinces = {ceiling}", default_text)
    if count != 1:
        raise ValueError("default.map must contain exactly one max_provinces")
    default_path.write_text(default_text, encoding="cp1252")


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


def replace_block(text: str, key: str, body: str) -> str:
    start, end = block_bounds(text, key)
    return text[:start] + body + text[end:]


def remove_all_blocks(text: str, key: str) -> str:
    while re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text):
        start, end = block_bounds(text, key)
        text = text[:start] + text[end:]
    return text


def update_areas_and_region() -> None:
    path = MAP / "area.txt"
    text = path.read_text(encoding="cp1252")
    for key, members in AREA_MEMBERS.items():
        body = f"{key} = {{ # {MARKER}\n    {' '.join(map(str, members))}\n}}"
        if re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text):
            text = replace_block(text, key, body)
        else:
            text = text.rstrip() + "\n\n" + body + "\n"
    path.write_text(text, encoding="cp1252")

    path = MAP / "region.txt"
    text = path.read_text(encoding="cp1252")
    start, end = block_bounds(text, "south_china_region")
    block = text[start:end]
    for area in ("wuling_hunan_area", "lishui_area", "hengchen_area", "xunyang_area", "gannan_area"):
        block = re.sub(rf"(?m)^\s*{re.escape(area)}\s*$\n?", "", block)
    insert = "".join(
        f"        {area}\n"
        for area in ("wuling_hunan_area", "lishui_area", "hengchen_area", "xunyang_area", "gannan_area")
    )
    anchor = "        southwest_hunan_area\n"
    if anchor not in block:
        raise ValueError("south_china_region lacks southwest_hunan_area anchor")
    block = block.replace(anchor, anchor + insert, 1)
    path.write_text(text[:start] + block + text[end:], encoding="cp1252")


def append_marker_line_to_block(path: Path, key: str, line: str, nested: str | None = None) -> None:
    text = path.read_text(encoding="cp1252")
    start, end = block_bounds(text, key)
    block = text[start:end]
    block = re.sub(rf"(?m)^.*# {re.escape(MARKER)}\s*$\n?", "", block)
    if nested is not None:
        nested_start, nested_end = block_bounds(block, nested)
        nested_block = block[nested_start:nested_end]
        close = nested_block.rfind("}")
        nested_block = nested_block[:close].rstrip() + f"\n        {line} # {MARKER}\n" + nested_block[close:]
        block = block[:nested_start] + nested_block + block[nested_end:]
    else:
        close = block.rfind("}")
        block = block[:close].rstrip() + f"\n    {line} # {MARKER}\n" + block[close:]
    path.write_text(text[:start] + block + text[end:], encoding="cp1252")


def update_memberships() -> None:
    all_new = " ".join(map(str, NEW_IDS))
    append_marker_line_to_block(MAP / "continent.txt", "asia", all_new)
    append_marker_line_to_block(MAP / "climate.txt", "mild_monsoon", all_new)
    append_marker_line_to_block(MAP / "terrain.txt", "farmlands", "5320 5321 5323 5324 5325", "terrain_override")
    append_marker_line_to_block(MAP / "terrain.txt", "hills", "5316 5317 5318 5319 5322 5326 5327 5328", "terrain_override")
    append_marker_line_to_block(MAP / "terrain.txt", "highlands", "5312 5313 5314 5315", "terrain_override")
    trade_nodes = MOD / "common/tradenodes/00_tradenodes.txt"
    append_marker_line_to_block(trade_nodes, "canton", " ".join(map(str, HUNAN_NEW_IDS)), "members")
    append_marker_line_to_block(trade_nodes, "hangzhou", " ".join(map(str, JIANGXI_NEW_IDS)), "members")
    trade_companies = MOD / "common/trade_companies/00_trade_companies.txt"
    append_marker_line_to_block(trade_companies, "trade_company_south_china", " ".join(map(str, HUNAN_NEW_IDS)), "provinces")
    append_marker_line_to_block(trade_companies, "trade_company_east_china", " ".join(map(str, JIANGXI_NEW_IDS)), "provinces")


def initial_suffix(text: str) -> str:
    match = re.search(r"(?m)^discovered_by\s*=", text)
    if not match:
        raise ValueError("Province history lacks discovered_by suffix")
    return text[match.start():].lstrip()


def split_suffix(text: str, parent_id: int) -> str:
    suffix = initial_suffix(text)
    if parent_id == 2151:
        suffix = re.sub(
            r"(?ms)\n*add_permanent_province_modifier\s*=\s*\{\s*"
            r"name\s*=\s*jingdezhen_kilns\s*duration\s*=\s*-1\s*\}\s*",
            "\n\n",
            suffix,
        )
    return suffix.lstrip()


def history_path(province_id: int) -> Path:
    matches = sorted(HISTORY.glob(f"{province_id} - *.txt"))
    if len(matches) != 1:
        raise ValueError(f"Province {province_id} has {len(matches)} local history files")
    return matches[0]


def history_text(
    province_id: int,
    english: str,
    owner: str,
    culture: str,
    religion: str,
    cores: Iterable[str],
    capital: str,
    goods: str,
    development: tuple[int, int, int],
    suffix: str,
    cot: int = 0,
    fort: bool = False,
    kilns: bool = False,
) -> str:
    lines = [
        f"# {province_id} - {english}", "", f"owner = {owner}", f"controller = {owner}",
        *(f"add_core = {core}" for core in dict.fromkeys(cores)),
        f"culture = {culture}", f"religion = {religion}", f'capital = "{capital}"',
        f"trade_goods = {goods}", "hre = no", f"base_tax = {development[0]}",
        f"base_production = {development[1]}", f"base_manpower = {development[2]}", "is_city = yes",
    ]
    if cot:
        lines.append(f"center_of_trade = {cot}")
    if fort:
        lines.append("fort_15th = yes")
    if kilns:
        lines += ["", "add_permanent_province_modifier = {", "    name = jingdezhen_kilns", "    duration = -1", "}"]
    return "\n".join(lines) + "\n\n" + suffix.rstrip() + "\n"


def update_histories() -> None:
    parent_text = {parent_id: history_path(parent_id).read_text(encoding="cp1252") for parent_id in PARENT_IDS}
    for province in P:
        suffix = split_suffix(parent_text[province.parent_id], province.parent_id)
        if province.province_id in PARENT_IDS:
            desired = history_path(province.province_id)
        else:
            desired = HISTORY / f"{province.province_id} - {province.english}.txt"
            for obsolete in HISTORY.glob(f"{province.province_id} - *.txt"):
                if obsolete != desired:
                    obsolete.unlink()
        desired.write_text(
            history_text(
                province.province_id, province.english, province.owner, province.culture,
                province.religion, province.cores, province.capital, province.goods,
                province.development, suffix, province.cot, province.fort, province.kilns,
            ),
            encoding="cp1252",
        )
    for province_id, policy in UNSPLIT_UPDATES.items():
        path = history_path(province_id)
        suffix = initial_suffix(path.read_text(encoding="cp1252"))
        path.write_text(
            history_text(
                province_id, path.stem.split(" - ", 1)[1], policy["owner"], policy["culture"],
                policy["religion"], policy["cores"], policy["capital"], policy["goods"],
                policy["development"], suffix, policy["cot"], policy["fort"], False,
            ),
            encoding="cp1252",
        )


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


def position_block(province_id: int, english: str, x: int, y: int) -> str:
    points = " ".join([f"{x:.3f} {y:.3f}"] * 6 + ["0.000 0.000"])
    return f"""# {english} - {MARKER}
{province_id}={{
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
    ids = decode_ids(MAP / "provinces.bmp", MAP / "definition.csv")
    path = MAP / "positions.txt"
    text = path.read_text(encoding="cp1252")
    text = re.sub(rf"(?m)^# .* - {re.escape(MARKER)}\n", "", text)
    for province in P:
        x, bitmap_y = deep_interior_point(ids == province.province_id)
        y = BITMAP_HEIGHT - bitmap_y
        replacement = position_block(province.province_id, province.english, x, y)
        pattern = re.compile(rf"(?m)^{province.province_id}=\s*\{{")
        if pattern.search(text):
            start, end = block_bounds(text, str(province.province_id))
            text = text[:start] + replacement + text[end:]
        else:
            text = text.rstrip() + "\n\n" + replacement + "\n"
    path.write_text(text, encoding="cp1252")


def update_country() -> None:
    tags = MOD / "common/country_tags/gdd_country_tags.txt"
    text = tags.read_text(encoding="cp1252")
    text = re.sub(r"(?m)^HNG\s*=.*$\n?", "", text).rstrip()
    text += '\nHNG = "countries/B45_Heng.txt"\n'
    tags.write_text(text, encoding="cp1252")

    (COUNTRIES / "B45_Heng.txt").write_text(
        "# B45 balanced Hunan polity.\n"
        "graphical_culture = asiangfx\n\n"
        "color = { 93 117 160 }\n"
        "revolutionary_colors = { 3 5 8 }\n",
        encoding="cp1252",
    )
    (COUNTRY_HISTORY / "HNG - Heng.txt").write_text(
        "# B45 balanced Hunan polity history.\n"
        "government = monarchy\n"
        "add_government_reform = gdd_local_fiefdom_reform\n"
        "government_rank = 1\n"
        "technology_group = chinese\n"
        "religion = confucianism\n"
        "primary_culture = gdd_chu\n"
        "add_accepted_culture = gdd_gui\n"
        "add_accepted_culture = gdd_hakka\n"
        "capital = 2174\n"
        "fixed_capital = 2174\n",
        encoding="cp1252",
    )
    wuling = COUNTRY_HISTORY / "WLM - Wuling.txt"
    text = wuling.read_text(encoding="cp1252")
    if "add_accepted_culture = gdd_chu" not in text:
        text = text.replace("primary_culture = miao\n", "primary_culture = miao\nadd_accepted_culture = gdd_chu\n", 1)
    wuling.write_text(text, encoding="cp1252")

    # A restrained blue field and white Heng glyph; deterministic and valid
    # 128x128 TGA like the other custom polity flags.
    flag = Image.new("RGB", (128, 128), (93, 117, 160))
    draw = ImageDraw.Draw(flag)
    draw.ellipse((15, 15, 113, 113), fill=(223, 202, 151), outline=(52, 61, 85), width=4)
    font = ImageFont.truetype(str(FONT), 62)
    bbox = draw.textbbox((0, 0), "衡", font=font)
    draw.text(((128 - (bbox[2] - bbox[0])) / 2, (128 - (bbox[3] - bbox[1])) / 2 - 5), "衡", font=font, fill=(48, 54, 70))
    flag.save(FLAGS / "HNG.tga")


def source_text() -> str:
    lines = ["﻿l_english:"]
    for province in P:
        if province.colour is not None:
            lines += [f' PROV{province.province_id}:0 "{province.chinese}"', f' PROV_ADJ{province.province_id}:0 "{province.chinese}"']
    lines += ["", ' HNG:0 "衡"', ' HNG_ADJ:0 "衡"']
    for key, chinese in AREA_CHINESE.items():
        if key in {"dongting_area", "hunan_area", "southwest_hunan_area", "jiangxi_area", "south_jiangxi_area"}:
            continue
        lines += ["", f' {key}:0 "{chinese}"', f' {key}_name:0 "{chinese}"', f' {key}_adj:0 "{chinese}"']
    return "\n".join(lines) + "\n"


def update_localisation() -> None:
    source = MOD / "localisation_source/gdd_b45_hunan_jiangxi_refinement_readable_utf8.txt"
    source.write_text(source_text(), encoding="utf-8")

    override = MOD / "localisation_source/gdd_zzz_chunqiu_area_overrides_readable_utf8.txt"
    text = override.read_text(encoding="utf-8-sig")
    for area in ("dongting_area", "hunan_area", "southwest_hunan_area", "jiangxi_area", "south_jiangxi_area"):
        for key in (area, f"{area}_name", f"{area}_adj"):
            text, count = re.subn(
                rf'(?m)^(\s*{re.escape(key)}:\d+\s+")[^"]*("\s*)$',
                rf'\g<1>{AREA_CHINESE[area]}\g<2>',
                text,
            )
            if count != 1:
                raise ValueError(f"Expected one override provider for {key}, found {count}")
    override.write_text("﻿" + text, encoding="utf-8")

    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file

    encode_file(source, MOD / "localisation/gdd_b45_hunan_jiangxi_refinement_l_english.yml")
    encode_file(override, MOD / "localisation/replace/zzz_gdd_chunqiu_area_overrides_l_english.yml")


def update_culture_policy() -> None:
    path = ROOT / "planning/culture_overhaul/approved_province_culture_assignments.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    rows = [row for row in rows if int(row["province_id"]) not in NEW_IDS]
    group_name = {
        "miao": ("百越文化组", "苗瑶文化"), "gdd_chu": ("汉文化组", "楚文化"),
        "gdd_gan": ("汉文化组", "江右文化"), "gdd_hakka": ("汉文化组", "客家文化"),
    }
    for province in P:
        if province.colour is None:
            continue
        document_group, document_culture = group_name[province.culture]
        rows.append({
            "province_id": str(province.province_id), "province_name": province.chinese,
            "document_group": document_group, "document_culture": document_culture,
            "document_entry": "B45赣湘细化", "target_culture": province.culture,
            "source_rule": "user_delegated", "decision_note": "用户授权按国家与区域平衡裁决；B45新增省份",
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
    rows = [row for row in rows if row["draw_batch"] != "B45"]
    parent_lookup = {province_id: (colour, name) for province_id, (colour, name) in definition_rows().items()}
    sequence = 1
    for province in P:
        if province.colour is None:
            continue
        red, green, blue = province.colour
        parent_colour, parent_name = parent_lookup[province.parent_id]
        del parent_colour
        retained = SPLIT_BY_PARENT[province.parent_id][0]
        row = {field: "" for field in fields}
        row.update({
            "design_key": f"B45-{sequence:02d}", "game_id": str(province.province_id),
            "rgb_r": str(red), "rgb_g": str(green), "rgb_b": str(blue),
            "macro_region": "south_china", "draw_batch": "B45", "new_name_zh": province.chinese,
            "new_name_en": province.english, "internal_key_hint": f"gdd_b45_{province.english.lower().replace(' ', '_')}",
            "parent_id": str(province.parent_id), "parent_definition_name": parent_name,
            "parent_history_name": history_path(province.parent_id).stem.split(" - ", 1)[1],
            "parent_area": province.area, "parent_tax": str(sum(p.development[0] for p in SPLIT_BY_PARENT[province.parent_id])),
            "parent_production": str(sum(p.development[1] for p in SPLIT_BY_PARENT[province.parent_id])),
            "parent_manpower": str(sum(p.development[2] for p in SPLIT_BY_PARENT[province.parent_id])),
            "retained_name_zh": retained.chinese, "retained_tax": str(retained.development[0]),
            "retained_production": str(retained.development[1]), "retained_manpower": str(retained.development[2]),
            "new_tax": str(province.development[0]), "new_production": str(province.development[1]),
            "new_manpower": str(province.development[2]), "split_group": f"b45-p{province.parent_id}",
            "group_dev_delta": "0", "proposed_owner": province.owner,
            "claims_or_uncertainty": "用户授权国家与文化平衡裁决", "status": "implemented",
            "rationale": "湖南—江西统一适度细化；几何采用审定效果图并保持母省发展度守恒。",
        })
        rows.append(row)
        sequence += 1
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def edge_map(values: np.ndarray) -> np.ndarray:
    edge = np.zeros(values.shape, dtype=bool)
    horizontal = values[:, 1:] != values[:, :-1]
    vertical = values[1:, :] != values[:-1, :]
    edge[:, 1:] |= horizontal
    edge[:, :-1] |= horizontal
    edge[1:, :] |= vertical
    edge[:-1, :] |= vertical
    return edge


def render_preview() -> None:
    ids = decode_ids(MAP / "provinces.bmp", MAP / "definition.csv")
    scope_ids = set(SCOPE_NAMES)
    scope = np.isin(ids, list(scope_ids))
    ys, xs = np.where(scope)
    x0, x1 = max(0, int(xs.min()) - 16), min(ids.shape[1], int(xs.max()) + 17)
    y0, y1 = max(0, int(ys.min()) - 12), min(ids.shape[0], int(ys.max()) + 13)
    crop = ids[y0:y1, x0:x1]
    crop_scope = np.isin(crop, list(scope_ids))
    height, width = crop.shape
    font = ImageFont.truetype(str(FONT), 12)
    for mode, path in (("country", PREVIEW_COUNTRIES), ("area", PREVIEW_AREAS)):
        pixels = np.full((height, width, 3), (214, 214, 205), dtype=np.uint8)
        pixels[crop <= 0] = (192, 213, 221)
        if mode == "country":
            for province_id in scope_ids:
                owner = FINAL_PROVINCE_BY_ID.get(province_id).owner if province_id in FINAL_PROVINCE_BY_ID else UNSPLIT_OWNERS[province_id]
                pixels[crop == province_id] = OWNER_COLOURS[owner]
        else:
            palette = [(200,170,221),(176,196,222),(148,205,210),(144,204,164),(187,213,143),(226,207,139),(241,191,145),(235,166,152),(225,163,188),(191,174,215)]
            for index, (_area, members) in enumerate((item for item in AREA_MEMBERS.items() if item[0] != "jingyi_shinan_area")):
                pixels[np.isin(crop, members)] = palette[index]
        pixels[edge_map(crop)] = (43, 46, 42)
        scale = 6
        image = Image.fromarray(pixels).resize((width * scale, height * scale), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(image)
        for province_id, name in SCOPE_NAMES.items():
            mask = crop == province_id
            if not mask.any():
                continue
            x, y = deep_interior_point(mask)
            px, py = x * scale + scale // 2, y * scale + scale // 2
            bbox = draw.textbbox((0, 0), name, font=font, stroke_width=1)
            draw.text((px - (bbox[2] - bbox[0]) / 2, py - (bbox[3] - bbox[1]) / 2), name, font=font,
                      fill=(33, 36, 33), stroke_width=2, stroke_fill=(247, 244, 232))
        image.save(path)


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
    new_colours = {
        province.province_id: rows[province.province_id][0]
        for province in P if province.colour is not None
    }
    if len(set(new_colours.values())) != len(new_colours):
        raise ValueError("B45 definition rows contain duplicate RGB values")
    for province_id, colour in new_colours.items():
        collisions = [other_id for other_id, (other_colour, _name) in rows.items() if other_colour == colour and other_id != province_id]
        if collisions:
            raise ValueError(f"B45 province {province_id} RGB collides with {collisions}")
    expected_highest = 5350 if B47_MANIFEST.exists() else (5340 if B46_MANIFEST.exists() else 5328)
    expected_ceiling = 5351 if B47_MANIFEST.exists() else (5341 if B46_MANIFEST.exists() else 5329)
    if max(rows) != expected_highest:
        raise ValueError(f"Expected highest province ID {expected_highest}, found {max(rows)}")
    if f"max_provinces = {expected_ceiling}" not in (MAP / "default.map").read_text(encoding="cp1252"):
        raise ValueError(f"max_provinces is not the required exclusive upper bound {expected_ceiling}")
    ids = decode_ids(MAP / "provinces.bmp", MAP / "definition.csv")
    for province in P:
        mask = ids == province.province_id
        count = int(mask.sum())
        if count != pixel_counts[province.province_id] or len(components(mask)) != 1:
            raise ValueError(f"Province {province.province_id} geometry mismatch")
    memberships = parse_area_memberships()
    for area, members in AREA_MEMBERS.items():
        if area == "jingyi_shinan_area" and B47_MANIFEST.exists():
            # B47 intentionally replaces this transitional B36 area with the
            # reviewed 荆郢/云梦/夷陵 partition.
            continue
        for province_id in members:
            if memberships.get(province_id) != {area}:
                raise ValueError(f"Province {province_id} area mismatch: {memberships.get(province_id)}")
        mask = np.isin(ids, members)
        land_components = len(components(mask))
        if area == "jingyi_shinan_area":
            adjacency_text = (MAP / "adjacencies.csv").read_text(encoding="cp1252")
            if land_components != 2 or not re.search(r"(?m)^2172;5013;sea;5037;", adjacency_text):
                raise ValueError("jingyi_shinan_area must be two land components joined by the reviewed Yichang crossing")
        elif land_components != 1:
            raise ValueError(f"Area {area} is not four-way land-connected")
    for province_id in NEW_IDS:
        if len(list(HISTORY.glob(f"{province_id} - *.txt"))) != 1:
            raise ValueError(f"Province {province_id} does not have exactly one local history")
    country_dev: Counter[str] = Counter()
    for province in P:
        country_dev[province.owner] += sum(province.development)
    for province_id, policy in UNSPLIT_UPDATES.items():
        country_dev[policy["owner"]] += sum(policy["development"])
    # The explicit user constraint: Changsha owns only three provinces and 27 development.
    changsha_ids = sorted(
        [province.province_id for province in P if province.owner == "CSA"]
        + [pid for pid, policy in UNSPLIT_UPDATES.items() if policy["owner"] == "CSA"]
    )
    actual_changsha_ids: list[int] = []
    for path in HISTORY.glob("*.txt"):
        text = path.read_text(encoding="cp1252", errors="ignore")
        if re.search(r"(?m)^owner\s*=\s*CSA\s*$", text):
            actual_changsha_ids.append(int(path.name.split()[0]))
    if sorted(actual_changsha_ids) != changsha_ids:
        raise ValueError(f"Changsha has unmanaged starting provinces: {sorted(actual_changsha_ids)}")
    if changsha_ids != [671, 4998, 5321] or country_dev["CSA"] != 27:
        raise ValueError(f"Changsha cap failed: provinces={changsha_ids}, dev={country_dev['CSA']}")
    return {
        "province_components": "all one component",
        "area_components": (
            "10 B45 areas land-connected; B47 owns the successor Jingxiang areas"
            if B47_MANIFEST.exists()
            else "10 B45 areas land-connected; jingyi_shinan_area crossing-connected via 2172-5013 through 5037"
        ),
        "country_development_in_scope": dict(sorted(country_dev.items())),
        "changsha_constraint": {"province_ids": changsha_ids, "development": country_dev["CSA"]},
    }


def write_manifest(changed_pixels: int, exterior_pixels: int, pixel_counts: dict[int, int], validation: dict[str, object], reference_root: Path) -> None:
    canonical = np.array(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    baseline = np.array(Image.open(BACKUP).convert("RGB"), dtype=np.uint8)
    total_changed = np.any(canonical != baseline, axis=2)
    baseline_ids = decode_ids(BACKUP, MAP / "definition.csv")
    editable = np.isin(baseline_ids, PARENT_IDS)
    payload = {
        "batch": "B45_hunan_jiangxi_balanced_refinement",
        "marker": MARKER,
        "purpose": "Implement the reviewed unified Hunan-Jiangxi refinement while preventing Changsha from becoming overpowered.",
        "reference_root": str(reference_root),
        "parent_ids": list(PARENT_IDS),
        "new_provinces": [asdict(province) for province in P if province.colour is not None],
        "editable_mask": {"source": str(BACKUP), "parent_ids": list(PARENT_IDS)},
        "backup": str(BACKUP),
        "previews": [str(PREVIEW_COUNTRIES), str(PREVIEW_AREAS)],
        "changed_pixels_this_run": changed_pixels,
        "changed_pixels_vs_pre_b45_backup": int(np.count_nonzero(total_changed)),
        "changed_pixels_vs_backup_outside_editable_mask": int(np.count_nonzero(total_changed & ~editable)),
        "changed_pixels_outside_editable_mask": exterior_pixels,
        "pixel_counts": pixel_counts,
        "areas": {key: list(value) for key, value in AREA_MEMBERS.items()},
        "region": "south_china_region",
        "trade_policy": {"hunan": "canton/trade_company_south_china", "jiangxi": "hangzhou/trade_company_east_china"},
        "localisation_source": "localisation_source/gdd_b45_hunan_jiangxi_refinement_readable_utf8.txt",
        "localisation_target": "localisation/gdd_b45_hunan_jiangxi_refinement_l_english.yml",
        "validation": validation,
        "canonical_bitmap_sha256": sha256(MAP / "provinces.bmp"),
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply(reference_root: Path) -> None:
    PLAN.mkdir(parents=True, exist_ok=True)
    changed_pixels, exterior_pixels, pixel_counts = apply_geometry(reference_root)
    update_definition()
    update_areas_and_region()
    update_memberships()
    update_histories()
    update_positions()
    update_country()
    update_localisation()
    update_culture_policy()
    update_registry()
    render_preview()
    validation = validate(pixel_counts)
    write_manifest(changed_pixels, exterior_pixels, pixel_counts, validation, reference_root)
    print(
        f"{MARKER}; NEW_PROVINCES:{len(NEW_IDS)}; CHANGED_PIXELS:{changed_pixels}; "
        f"EXTERIOR_PIXELS:{exterior_pixels}; CHANGSHA_DEV:27"
    )


def check(reference_root: Path) -> None:
    expected, editable, pixel_counts = expected_geometry(reference_root)
    current = np.array(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    check_mask = editable.copy()
    for later_manifest in (B46_MANIFEST, B47_MANIFEST):
        if later_manifest.exists():
            payload = json.loads(later_manifest.read_text(encoding="utf-8"))
            later_backup = Path(payload["backup"])
            later_editable = np.isin(
                decode_ids(later_backup, MAP / "definition.csv"),
                tuple(payload["parent_ids"]),
            )
            check_mask &= ~later_editable
    mismatch = np.any(current[check_mask] != expected[check_mask], axis=1)
    if int(np.count_nonzero(mismatch)):
        raise ValueError(f"Canonical bitmap differs from expected B45 geometry at {int(np.count_nonzero(mismatch))} editable pixels")
    validation = validate(pixel_counts)
    print(f"{MARKER}_CHECK; PASS; NEW_PROVINCES:{len(NEW_IDS)}; CHANGSHA:{validation['changsha_constraint']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-root", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check(args.reference_root)
    else:
        apply(args.reference_root)
        if B46_MANIFEST.exists():
            subprocess.run(
                [sys.executable, str(ROOT / "tools/map_pipeline/apply_b46_chuandongbei_chongqing_refinement.py")],
                check=True,
            )
        if B47_MANIFEST.exists():
            subprocess.run(
                [sys.executable, str(ROOT / "tools/map_pipeline/apply_b47_jingxiang_yunan_refinement.py")],
                check=True,
            )


if __name__ == "__main__":
    main()
