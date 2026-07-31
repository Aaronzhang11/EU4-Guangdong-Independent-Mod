"""Static validation for the hand-drawn B01 Guangdong map slice."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

from build_b01_mod import (
    ACTIVE_IDS,
    DEFAULT_CONFIG,
    DEFAULT_MOD_ROOT,
    DEFAULT_REPORT,
    GAME_MAX_PROVINCES,
    IMPLEMENTED_IDS,
    HUNAN_IDS,
    JIANGXI_IDS,
    ZHEJIANG_IDS,
    HUBEI_NEW_IDS,
    HUBEI_ALL_IDS,
    JIANGSU_ALL_IDS,
    JIANGSU_NEW_IDS,
    CHONGQING_ALL_IDS,
    CHONGQING_NEW_IDS,
    WANGJI_ALL_IDS,
    WANGJI_NEW_IDS,
    TAIWAN_MOUNTAIN_ID,
    TAIWAN_REVIEW_IDS,
    YANGTZE_SEA_IDS,
    HUAI_SEA_IDS,
    POSITION_DATA,
    PREPARED_IDS,
    find_named_block,
    validate_classic_bmp_header,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VALIDATION_REPORT = (
    REPO_ROOT / "docs/map/previews/B01_mod_validation_report.json"
)
EXPECTED_AREAS = {
    664: "youjiang_area",
    669: "fujian_area",
    1829: "fujian_area",
    1840: "youjiang_area",
    2152: "west_fujian_area",
    2153: "west_fujian_area",
    2162: "guangxi_area",
    2163: "youjiang_area",
    2164: "guangxi_area",
    4942: "pearl_river_delta_area",
    4943: "pearl_river_delta_area",
    4944: "guangdong_area",
    4945: "west_guangdong_area",
    4946: "pearl_river_delta_area",
    4947: "west_guangdong_area",
    4948: "guangdong_area",
    4949: "guangdong_area",
    4950: "zhejiang_area",
    4951: "east_zhejiang_area",
    4952: "fujian_area",
    4953: "fujian_area",
    4954: "guangxi_area",
    4955: "taiwan_area",
    4956: "jinqu_chuzhou_area",
    4957: "west_fujian_area",
    4958: "fujian_area",
    4959: "youjiang_area",
    4960: "guangxi_area",
    4961: "taiwan_area",
    670: "south_jiangxi_area",
    683: "jiangxi_area",
    1833: "south_jiangxi_area",
    2151: "jiangxi_area",
    4979: "jiangxi_area",
    4980: "south_jiangxi_area",
    4992: "jiangxi_area",
    4993: "jiangxi_area",
    4994: "south_jiangxi_area",
    4995: "south_jiangxi_area",
    671: "hunan_area",
    672: "dongting_area",
    2173: "southwest_hunan_area",
    2174: "hunan_area",
    4982: "dongting_area",
    4983: "hunan_area",
    4996: "dongting_area",
    4997: "dongting_area",
    4998: "hunan_area",
    4999: "southwest_hunan_area",
    5000: "southwest_hunan_area",
    5001: "southwest_hunan_area",
    684: "zhejiang_area",
    1824: "east_zhejiang_area",
    2148: "zhejiang_area",
    2149: "east_zhejiang_area",
    2150: "jinqu_chuzhou_area",
    5002: "zhejiang_area",
    5003: "zhejiang_area",
    5004: "east_zhejiang_area",
    5005: "east_zhejiang_area",
    5006: "jinqu_chuzhou_area",
    5007: "jinqu_chuzhou_area",
    5008: "hanjiang_xiangyun_area",
    2171: "hanjiang_xiangyun_area",
    5010: "hanjiang_xiangyun_area",
    681: "jingyi_shinan_area",
    2172: "jingyi_shinan_area",
    5013: "jingyi_shinan_area",
    5014: "jingyi_shinan_area",
    5015: "jingyi_shinan_area",
    5009: "dean_qihuang_area",
    4197: "dean_qihuang_area",
    5012: "dean_qihuang_area",
    4981: "wuhan_enan_area",
    682: "wuhan_enan_area",
    5011: "wuhan_enan_area",
    5016: "wuhan_enan_area",
    2141: "xuhuai_haizhou_area",
    5018: "xuhuai_haizhou_area",
    2142: "xuhuai_haizhou_area",
    5020: "xuhuai_haizhou_area",
    4196: "xuhuai_haizhou_area",
    685: "huaiyang_tongtai_area",
    5021: "huaiyang_tongtai_area",
    4977: "huaiyang_tongtai_area",
    5022: "huaiyang_tongtai_area",
    5023: "huaiyang_tongtai_area",
    1821: "jinling_wuhui_area",
    2145: "jinling_wuhui_area",
    5024: "jinling_wuhui_area",
    5025: "jinling_wuhui_area",
    1822: "jinling_wuhui_area",
    4976: "jinling_wuhui_area",
    680: "chongqing_area",
    4987: "chongqing_area",
    5026: "chongqing_area",
    5027: "chongqing_area",
    5028: "chongqing_area",
    688: "wangji_area",
    4966: "wangji_area",
    5030: "wangji_area",
    5031: "wangji_area",
    692: "north_henan_area",
    1836: "north_henan_area",
}
EXPECTED_TERRAIN = {
    4942: "farmlands",
    4943: "farmlands",
    4944: "hills",
    4945: "hills",
    4946: "hills",
    4947: "hills",
    4948: "hills",
    4949: "hills",
    4950: "farmlands",
    4951: "hills",
    4952: "hills",
    4953: "hills",
    4954: "farmlands",
    4955: "grasslands",
    4956: "hills",
    4957: "hills",
    4958: "hills",
    4959: "highlands",
    4960: "hills",
    4961: "hills",
    4979: "farmlands",
    4980: "hills",
    4992: "hills",
    4993: "hills",
    4994: "hills",
    4995: "highlands",
    671: "farmlands",
    672: "farmlands",
    2173: "highlands",
    2174: "hills",
    4982: "farmlands",
    4983: "hills",
    4996: "hills",
    4997: "hills",
    4998: "hills",
    4999: "highlands",
    5000: "hills",
    5001: "highlands",
    684: "farmlands",
    1824: "hills",
    2148: "farmlands",
    2149: "farmlands",
    2150: "hills",
    5002: "farmlands",
    5003: "hills",
    5004: "hills",
    5005: "hills",
    5006: "hills",
    5007: "highlands",
    5008: "highlands",
    2171: "farmlands",
    5009: "grasslands",
    5010: "grasslands",
    681: "hills",
    2172: "farmlands",
    4981: "farmlands",
    5011: "farmlands",
    4197: "grasslands",
    5012: "hills",
    5013: "highlands",
    5014: "grasslands",
    682: "farmlands",
    5015: "hills",
    5016: "hills",
    680: "hills",
    4987: "hills",
    5026: "hills",
    5027: "hills",
    5028: "highlands",
    688: "farmlands",
    4966: "hills",
    5030: "farmlands",
    5031: "farmlands",
    **{province_id: "farmlands" for province_id in JIANGSU_ALL_IDS},
}
PREPARED_HISTORY = {
    669: ("MNG", (5, 5, 2), "tea", "chimin"),
    1829: ("MNG", (4, 4, 1), "tea", "chimin"),
    2163: ("MNG", (1, 1, 1), "salt", "zhuang"),
    2152: ("MNG", (1, 1, 1), "tea", "chimin"),
    1840: ("MNG", (1, 1, 1), "silk", "zhuang"),
    2162: ("MNG", (1, 1, 1), "copper", "cantonese"),
    738: (None, (3, 3, 1), "unknown", "polynesian"),
    2155: (None, (1, 1, 2), "unknown", "polynesian"),
    4952: ("MNG", (3, 3, 1), "fish", "chimin"),
    4953: ("MNG", (3, 3, 1), "sugar", "chimin"),
    4954: ("MNG", (1, 1, 1), "grain", "zhuang"),
    4955: (None, (1, 1, 1), "livestock", "polynesian"),
    4957: ("MNG", (1, 1, 1), "paper", "chimin"),
    4958: ("MNG", (2, 3, 1), "fish", "chimin"),
    4959: ("MNG", (1, 1, 1), "livestock", "zhuang"),
    4960: ("MNG", (1, 1, 1), "grain", "zhuang"),
    4961: (None, (1, 1, 1), "fish", "polynesian"),
}
PREPARED_DEV_PARTITIONS = {
    669: ((4952,), (8, 8, 3)),
    1829: ((4953, 4958), (9, 10, 3)),
    2163: ((4954, 4960), (3, 3, 3)),
    2155: ((4955,), (2, 2, 3)),
    2152: ((4957,), (2, 2, 2)),
    1840: ((4959,), (2, 2, 2)),
    738: ((4961,), (4, 4, 2)),
}
EXPECTED_HISTORY = {
    665: ("GDD", (3, 3, 2), "chinaware", "cantonese"),
    667: ("GDD", (8, 8, 2), "incense", "cantonese"),
    2156: ("MNG", (4, 4, 1), "chinaware", "chimin"),
    2157: ("GDD", (2, 2, 1), "grain", "hakka"),
    2158: ("GDD", (2, 3, 1), "iron", "hakka"),
    2159: ("GDD", (2, 2, 1), "sugar", "chimin"),
    4942: ("GDD", (4, 4, 1), "chinaware", "cantonese"),
    4943: ("GDD", (3, 3, 1), "incense", "cantonese"),
    4944: ("GDD", (2, 2, 1), "tea", "hakka"),
    4945: ("GDD", (1, 1, 1), "grain", "cantonese"),
    4946: ("GDD", (1, 1, 1), "fish", "cantonese"),
    4947: ("GDD", (1, 1, 1), "grain", "cantonese"),
    4948: ("GDD", (2, 1, 1), "grain", "hakka"),
    4949: ("GDD", (1, 1, 1), "salt", "chimin"),
    680: ("MNG", (4, 4, 1), "spices", "sichuanese"),
    4987: ("MNG", (1, 1, 1), "tea", "sichuanese"),
    5026: ("MNG", (1, 1, 1), "grain", "sichuanese"),
    5027: ("MNG", (1, 1, 1), "paper", "sichuanese"),
    5028: ("MNG", (1, 1, 1), "naval_supplies", "sichuanese"),
    688: ("MNG", (4, 4, 1), "chinaware", "zhongyuan"),
    4966: ("MNG", (1, 1, 1), "grain", "zhongyuan"),
    5030: ("MNG", (2, 2, 1), "cloth", "zhongyuan"),
    5031: ("MNG", (1, 1, 1), "grain", "zhongyuan"),
}
EXPECTED_DEV_PARTITIONS = {
    665: {"children": (4947,), "original": (4, 4, 3), "delta": (0, 0, 0)},
    667: {"children": (4942,), "original": (12, 12, 3), "delta": (0, 0, 0)},
    2156: {"children": (4944,), "original": (6, 6, 2), "delta": (0, 0, 0)},
    2157: {
        "children": (4943, 4946, 4949),
        "original": (7, 7, 3),
        "delta": (0, 0, 1),
    },
    2158: {"children": (4948,), "original": (4, 4, 2), "delta": (0, 0, 0)},
    2159: {"children": (4945,), "original": (3, 3, 2), "delta": (0, 0, 0)},
    680: {
        "children": (4987, 5026, 5027, 5028),
        "original": (8, 8, 4),
        "delta": (0, 0, 1),
    },
    688: {
        "children": (4966, 5030, 5031),
        "original": (8, 8, 4),
        "delta": (0, 0, 0),
    },
}
JIANGXI_HISTORY = {
    670: ("MNG", (4, 4, 3), "grain", "hakka"),
    683: ("MNG", (6, 6, 4), "paper", "gan"),
    1833: ("MNG", (4, 4, 3), "cloth", "gan"),
    2151: ("MNG", (4, 5, 2), "chinaware", "gan"),
    4979: ("MNG", (4, 5, 3), "tea", "gan"),
    4980: ("MNG", (3, 4, 2), "paper", "gan"),
    4992: ("MNG", (3, 3, 2), "grain", "gan"),
    4993: ("MNG", (3, 3, 2), "copper", "gan"),
    4994: ("MNG", (3, 3, 2), "grain", "gan"),
    4995: ("MNG", (2, 2, 2), "iron", "hakka"),
}
HUNAN_HISTORY = {
    671: ("MNG", (5, 6, 3), "grain", "xiang", "confucianism"),
    672: ("MNG", (4, 4, 2), "cotton", "xiang", "confucianism"),
    2173: ("MNG", (2, 3, 4), "tea", "miao", "animism"),
    2174: ("MNG", (3, 3, 3), "gold", "xiang", "confucianism"),
    4982: ("MNG", (4, 5, 2), "tea", "xiang", "confucianism"),
    4983: ("MNG", (2, 2, 2), "livestock", "xiang", "confucianism"),
    4996: ("MNG", (2, 3, 2), "grain", "xiang", "confucianism"),
    4997: ("MNG", (3, 3, 2), "naval_supplies", "xiang", "confucianism"),
    4998: ("MNG", (2, 3, 2), "chinaware", "xiang", "confucianism"),
    4999: ("MNG", (2, 2, 3), "livestock", "miao", "animism"),
    5000: ("MNG", (3, 3, 3), "iron", "xiang", "confucianism"),
    5001: ("MNG", (3, 5, 3), "copper", "xiang", "confucianism"),
}
ZHEJIANG_HISTORY = {
    684: ("MNG", (7, 9, 3), "silk", "wu", "confucianism"),
    1824: ("MNG", (4, 5, 2), "chinaware", "wu", "confucianism"),
    2148: ("MNG", (5, 6, 3), "paper", "wu", "confucianism"),
    2149: ("MNG", (5, 7, 3), "naval_supplies", "wu", "confucianism"),
    2150: ("MNG", (3, 4, 2), "grain", "wu", "confucianism"),
    4950: ("MNG", (4, 5, 2), "silk", "wu", "confucianism"),
    4951: ("MNG", (3, 4, 2), "fish", "wu", "confucianism"),
    4956: ("MNG", (3, 3, 2), "tea", "wu", "confucianism"),
    5002: ("MNG", (4, 5, 2), "cloth", "wu", "confucianism"),
    5003: ("MNG", (3, 3, 2), "paper", "wu", "confucianism"),
    5004: ("MNG", (2, 3, 1), "fish", "wu", "confucianism"),
    5005: ("MNG", (2, 2, 1), "salt", "wu", "confucianism"),
    5006: ("MNG", (3, 3, 2), "livestock", "wu", "confucianism"),
    5007: ("MNG", (2, 3, 2), "chinaware", "wu", "confucianism"),
}
HUBEI_HISTORY = {
    681: ("MNG", (3, 3, 2), "tea", "hubei", "confucianism"),
    682: ("MNG", (5, 6, 3), "salt", "hubei", "confucianism"),
    2171: ("MNG", (5, 5, 3), "grain", "hubei", "confucianism"),
    2172: ("MNG", (4, 4, 3), "grain", "hubei", "confucianism"),
    4197: ("MNG", (3, 3, 2), "grain", "hubei", "confucianism"),
    4981: ("MNG", (3, 3, 2), "naval_supplies", "hubei", "confucianism"),
    5008: ("MNG", (2, 3, 2), "iron", "hubei", "confucianism"),
    5009: ("MNG", (3, 2, 2), "cotton", "hubei", "confucianism"),
    5010: ("MNG", (3, 3, 2), "paper", "hubei", "confucianism"),
    5011: ("MNG", (5, 8, 2), "cloth", "hubei", "confucianism"),
    5012: ("MNG", (3, 3, 2), "tea", "hubei", "confucianism"),
    5013: ("MNG", (2, 2, 2), "livestock", "miao", "animism"),
    5014: ("MNG", (2, 3, 2), "grain", "hubei", "confucianism"),
    5015: ("MNG", (2, 2, 2), "tea", "hubei", "confucianism"),
    5016: ("MNG", (3, 3, 2), "copper", "hubei", "confucianism"),
}
JIANGSU_HISTORY = {
    2141: ("MNG", (7, 8, 4), "iron", "zhongyuan", "confucianism"),
    5018: ("MNG", (3, 2, 2), "livestock", "jianghuai", "confucianism"),
    2142: ("MNG", (6, 8, 4), "grain", "jianghuai", "confucianism"),
    5020: ("MNG", (2, 4, 2), "salt", "jianghuai", "confucianism"),
    4196: ("MNG", (2, 3, 2), "fish", "jianghuai", "confucianism"),
    685: ("MNG", (6, 8, 3), "salt", "jianghuai", "confucianism"),
    5021: ("MNG", (3, 3, 2), "grain", "jianghuai", "confucianism"),
    4977: ("MNG", (3, 5, 2), "salt", "jianghuai", "confucianism"),
    5022: ("MNG", (3, 4, 2), "cloth", "jianghuai", "confucianism"),
    5023: ("MNG", (3, 3, 2), "grain", "jianghuai", "confucianism"),
    1821: ("MNG", (7, 8, 4), "silk", "jianghuai", "confucianism"),
    2145: ("MNG", (4, 4, 2), "naval_supplies", "jianghuai", "confucianism"),
    5024: ("MNG", (4, 5, 2), "cloth", "wu", "confucianism"),
    5025: ("MNG", (3, 4, 2), "silk", "wu", "confucianism"),
    1822: ("MNG", (5, 6, 2), "silk", "wu", "confucianism"),
    4976: ("MNG", (4, 5, 2), "cloth", "wu", "confucianism"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_definitions(
    path: Path,
) -> tuple[
    dict[int, tuple[tuple[int, int, int], str]],
    dict[tuple[int, int, int], int],
]:
    definitions: dict[int, tuple[tuple[int, int, int], str]] = {}
    colors: dict[tuple[int, int, int], int] = {}
    with path.open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if not row or not row[0].isdigit():
                continue
            province_id = int(row[0])
            color = (int(row[1]), int(row[2]), int(row[3]))
            if province_id in definitions:
                raise ValueError(f"definition.csv: duplicate ID {province_id}")
            if color in colors and (
                province_id in ACTIVE_IDS or colors[color] in ACTIVE_IDS
            ):
                raise ValueError(
                    f"definition.csv: RGB {color} reused by "
                    f"{colors[color]} and {province_id}"
                )
            definitions[province_id] = (color, row[4])
            colors.setdefault(color, province_id)
    return definitions, colors


def block_text(text: str, name: str) -> str:
    start, end = find_named_block(text, name)
    return text[start:end]


def numeric_tokens(text: str) -> list[int]:
    without_comments = re.sub(r"#.*$", "", text, flags=re.MULTILINE)
    return [
        int(value)
        for value in re.findall(r"(?<![\w.])\d+(?![\w.])", without_comments)
    ]


def assert_token_once(text: str, value: int, label: str) -> None:
    stripped = re.sub(r"#.*$", "", text, flags=re.MULTILINE)
    matches = re.findall(rf"(?<![\w.]){value}(?![\w.])", stripped)
    if len(matches) != 1:
        raise ValueError(f"{label}: expected ID {value} once, found {len(matches)}")


def read_sea_ids(default_map: str) -> set[int]:
    return set(numeric_tokens(block_text(default_map, "sea_starts")))


def component_sizes(mask: np.ndarray) -> list[int]:
    remaining = mask.copy()
    sizes: list[int] = []
    height, width = remaining.shape
    while remaining.any():
        seed_y, seed_x = np.argwhere(remaining)[0]
        queue: deque[tuple[int, int]] = deque([(int(seed_x), int(seed_y))])
        remaining[seed_y, seed_x] = False
        size = 0
        while queue:
            x, y = queue.popleft()
            size += 1
            for next_x, next_y in (
                (x + 1, y),
                (x - 1, y),
                (x, y + 1),
                (x, y - 1),
            ):
                if not (0 <= next_x < width and 0 <= next_y < height):
                    continue
                if not remaining[next_y, next_x]:
                    continue
                remaining[next_y, next_x] = False
                queue.append((next_x, next_y))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def neighboring_ids(
    province_map: np.ndarray,
    mask: np.ndarray,
    color_to_id: dict[tuple[int, int, int], int],
) -> set[int]:
    neighbors: set[int] = set()
    for delta_y, delta_x in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        shifted = np.roll(mask, shift=(delta_y, delta_x), axis=(0, 1))
        edge = shifted & ~mask
        if delta_y == 1:
            edge[0, :] = False
        elif delta_y == -1:
            edge[-1, :] = False
        elif delta_x == 1:
            edge[:, 0] = False
        else:
            edge[:, -1] = False
        for color in np.unique(province_map[edge].reshape(-1, 3), axis=0):
            province_id = color_to_id.get(tuple(int(channel) for channel in color))
            if province_id is not None:
                neighbors.add(province_id)
    return neighbors


def parse_positions(text: str, province_id: int) -> list[float]:
    block = block_text(text, str(province_id))
    position = block_text(block, "position")
    values = [
        float(value)
        for value in re.findall(
            r"-?\d+(?:\.\d+)?",
            position[position.find("{") + 1 : position.rfind("}")],
        )
    ]
    if len(values) != 14:
        raise ValueError(
            f"positions.txt: {province_id} needs 14 position values, "
            f"found {len(values)}"
        )
    for section in ("rotation", "height"):
        section_text = block_text(block, section)
        section_values = re.findall(
            r"-?\d+(?:\.\d+)?",
            section_text[
                section_text.find("{") + 1 : section_text.rfind("}")
            ],
        )
        if len(section_values) != 7:
            raise ValueError(
                f"positions.txt: {province_id} {section} needs 7 values, "
                f"found {len(section_values)}"
            )
    return values


def point_id(
    province_map: np.ndarray,
    color_to_id: dict[tuple[int, int, int], int],
    x_value: float,
    y_value: float,
) -> tuple[int | None, int, int]:
    x = int(round(x_value))
    y = province_map.shape[0] - int(round(y_value))
    if not (0 <= x < province_map.shape[1] and 0 <= y < province_map.shape[0]):
        raise ValueError(f"Position {(x_value, y_value)} is outside provinces.bmp")
    color = tuple(int(channel) for channel in province_map[y, x])
    return color_to_id.get(color), x, y


def history_path(mod_root: Path, province_id: int) -> Path:
    matches = list((mod_root / "history/provinces").glob(f"{province_id} - *.txt"))
    if len(matches) != 1:
        raise ValueError(
            f"history/provinces: ID {province_id} has {len(matches)} files"
        )
    return matches[0]


def initial_history_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*([^\s#]+)", text)
    if not match:
        raise ValueError(f"Province history missing {key}")
    return match.group(1).strip('"')


def validate_braces(path: Path) -> None:
    text = path.read_text(encoding="cp1252")
    depth = 0
    in_string = False
    in_comment = False
    escaped = False
    for character in text:
        if in_comment:
            if character == "\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == "#":
            in_comment = True
        elif character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                raise ValueError(f"{path}: closing brace without opener")
    if depth or in_string:
        raise ValueError(f"{path}: unbalanced Clausewitz syntax")


def validate_map(
    vanilla_root: Path,
    mod_root: Path,
    config: dict[str, object],
) -> dict[str, object]:
    map_dir = mod_root / "map"
    definitions, color_to_id = parse_definitions(map_dir / "definition.csv")
    configured_ids = tuple(
        int(province["game_id"]) for province in config["provinces"]
    )
    audited_ids = (
        IMPLEMENTED_IDS + JIANGXI_IDS + HUNAN_IDS
        + ZHEJIANG_IDS + HUBEI_NEW_IDS + HUBEI_ALL_IDS[:5] + JIANGSU_NEW_IDS
        + CHONGQING_NEW_IDS + TAIWAN_REVIEW_IDS + WANGJI_NEW_IDS
        + YANGTZE_SEA_IDS + HUAI_SEA_IDS
    )
    if configured_ids != audited_ids:
        raise ValueError(
            f"Manual config IDs must be {audited_ids}, found {configured_ids}"
        )
    for province in config["provinces"]:
        province_id = int(province["game_id"])
        expected = (
            tuple(int(value) for value in province["rgb"]),
            str(province["name_en"]),
        )
        if definitions.get(province_id) != expected:
            raise ValueError(
                f"definition.csv: {province_id} is {definitions.get(province_id)}, "
                f"expected {expected}"
            )
    exposed_new_ids = tuple(
        sorted(province_id for province_id in definitions if province_id >= 4942)
    )
    expected_exposed_ids = tuple(
        sorted(ACTIVE_IDS + YANGTZE_SEA_IDS + HUAI_SEA_IDS)
    )
    if exposed_new_ids != expected_exposed_ids:
        raise ValueError(
            f"definition.csv exposes {exposed_new_ids}; expected {expected_exposed_ids}"
        )

    default_map = (map_dir / "default.map").read_text(encoding="cp1252")
    max_match = re.search(r"(?m)^max_provinces\s*=\s*(\d+)", default_map)
    if not max_match or int(max_match.group(1)) != GAME_MAX_PROVINCES:
        raise ValueError(f"default.map: max_provinces must be {GAME_MAX_PROVINCES}")
    sea_ids = read_sea_ids(default_map)
    if not set(
        YANGTZE_SEA_IDS + HUAI_SEA_IDS + (1655, 1897, 1896)
    ) <= sea_ids:
        raise ValueError("default.map: navigable Yangtze or Huai sea IDs are missing")
    lakes = set(numeric_tokens(block_text(default_map, "lakes")))
    if lakes & {1655, 1897, 1896}:
        raise ValueError(
            "default.map: Dongting, Poyang or Hongze remains classified as a lake"
        )

    provinces_path = map_dir / "provinces.bmp"
    validate_classic_bmp_header(provinces_path)
    with Image.open(provinces_path) as image:
        expected_size = tuple(int(value) for value in config["expected_size"])
        if image.size != expected_size or image.mode != config["expected_mode"]:
            raise ValueError(
                f"provinces.bmp must be {expected_size} {config['expected_mode']}, "
                f"found {image.size} {image.mode}"
            )
        province_map = np.asarray(image, dtype=np.uint8)
    with Image.open(vanilla_root / "map/provinces.bmp") as image:
        baseline_map = np.asarray(image, dtype=np.uint8)
    changed_pixels = int(np.any(province_map != baseline_map, axis=2).sum())
    if changed_pixels != int(config["expected_changed_pixels"]):
        raise ValueError(
            f"provinces.bmp: expected {config['expected_changed_pixels']} "
            f"changed pixels, found {changed_pixels}"
        )

    province_stats: dict[int, dict[str, object]] = {}
    for province in config["provinces"]:
        province_id = int(province["game_id"])
        color = np.array(province["rgb"], dtype=np.uint8)
        mask = np.all(province_map == color, axis=2)
        pixels = int(mask.sum())
        if pixels != int(province["expected_pixels"]):
            raise ValueError(
                f"provinces.bmp: {province_id} has {pixels} pixels, "
                f"expected {province['expected_pixels']}"
            )
        components = component_sizes(mask)
        expected_components = [
            int(value) for value in province["expected_component_sizes"]
        ]
        if components != expected_components:
            raise ValueError(
                f"provinces.bmp: {province_id} components {components}, "
                f"expected {expected_components}"
            )
        neighbors = neighboring_ids(province_map, mask, color_to_id)
        expected_neighbors = {
            int(value) for value in province["expected_neighbor_ids"]
        }
        if neighbors != expected_neighbors:
            raise ValueError(
                f"provinces.bmp: {province_id} neighbors {sorted(neighbors)}, "
                f"expected {sorted(expected_neighbors)}"
            )
        coastal = bool(neighbors & sea_ids)
        if coastal is not bool(province["expected_coastal"]):
            raise ValueError(
                f"provinces.bmp: {province_id} coastal={coastal}, "
                f"expected {province['expected_coastal']}"
            )
        province_stats[province_id] = {
            "pixels": pixels,
            "component_sizes": components,
            "neighbors": sorted(neighbors),
            "coastal": coastal,
        }

    terrain_path = map_dir / "terrain.bmp"
    with Image.open(terrain_path) as image:
        if image.size != province_map.shape[1::-1] or image.mode != "P":
            raise ValueError(
                f"terrain.bmp must be {province_map.shape[1::-1]} paletted, "
                f"found {image.size} {image.mode}"
            )
        terrain_map = np.asarray(image, dtype=np.uint8)
        terrain_palette = image.getpalette()
    with Image.open(vanilla_root / "map/terrain.bmp") as image:
        baseline_terrain = np.asarray(image, dtype=np.uint8)
        baseline_palette = image.getpalette()
    if terrain_palette != baseline_palette:
        raise ValueError("terrain.bmp: palette differs from the vanilla terrain palette")
    mountain_color = np.array((115, 75, 50), dtype=np.uint8)
    mountain_mask = np.all(province_map == mountain_color, axis=2)
    if not np.array_equal(terrain_map[~mountain_mask], baseline_terrain[~mountain_mask]):
        raise ValueError(
            "terrain.bmp: pixels outside the Taiwan Mountains differ from vanilla"
        )
    mountain_terrain = terrain_map[mountain_mask]
    terrain_counts = {
        int(index): int((mountain_terrain == index).sum())
        for index in np.unique(mountain_terrain)
    }
    expected_terrain_counts = {0: 23, 1: 54, 3: 1, 6: 75, 16: 21}
    if terrain_counts != expected_terrain_counts:
        raise ValueError(
            f"terrain.bmp: Taiwan ridge palette {terrain_counts}, "
            f"expected {expected_terrain_counts}"
        )
    if tuple(terrain_palette[6 * 3:6 * 3 + 3]) != (65, 42, 17):
        raise ValueError("terrain.bmp: palette index 6 is not the brown ridge color")
    if tuple(terrain_palette[16 * 3:16 * 3 + 3]) != (255, 255, 255):
        raise ValueError("terrain.bmp: palette index 16 is not the white summit color")
    if np.any(mountain_terrain == 128):
        raise ValueError("terrain.bmp: Taiwan ridge still contains the gray placeholder")

    heightmap_path = map_dir / "heightmap.bmp"
    with Image.open(heightmap_path) as image:
        if image.size != province_map.shape[1::-1] or image.mode != "L":
            raise ValueError("heightmap.bmp must remain a full-size grayscale bitmap")
        heightmap = np.asarray(image)
    with Image.open(vanilla_root / "map/heightmap.bmp") as image:
        baseline_heightmap = np.asarray(image)
    if int((heightmap != baseline_heightmap).sum()) != 1699:
        raise ValueError("heightmap.bmp: Yangtze/Huai transplant pixel count changed")

    rivers_path = map_dir / "rivers.bmp"
    with Image.open(rivers_path) as image:
        if image.size != province_map.shape[1::-1] or image.mode != "P":
            raise ValueError("rivers.bmp must remain a full-size paletted bitmap")
        river_map = np.asarray(image)
        river_palette = image.getpalette()
    with Image.open(vanilla_root / "map/rivers.bmp") as image:
        baseline_rivers = np.asarray(image)
        baseline_river_palette = image.getpalette()
    if river_palette != baseline_river_palette:
        raise ValueError("rivers.bmp: palette differs from vanilla")
    if int((river_map != baseline_rivers).sum()) != 530:
        raise ValueError("rivers.bmp: Yangtze/Huai transplant pixel count changed")

    prepared_pixels: dict[int, int] = {}
    for province_id in PREPARED_IDS:
        color = np.array(definitions[province_id][0], dtype=np.uint8)
        pixels = int(np.all(province_map == color, axis=2).sum())
        if pixels != 0:
            raise ValueError(
                f"provinces.bmp: prepared province {province_id} unexpectedly "
                f"has {pixels} pixels; this batch must not modify the BMP"
            )
        prepared_pixels[province_id] = pixels

    positions = (map_dir / "positions.txt").read_text(encoding="cp1252")
    port_seas = {
        int(province_id): int(sea_id)
        for province_id, sea_id in config["port_seas"].items()
    }
    for province_id in (int(value) for value in config["position_province_ids"]):
        position_block_count = len(
            re.findall(
                rf"(?m)^[ \t]*{province_id}[ \t]*=[ \t]*\{{",
                positions,
            )
        )
        if position_block_count != 1:
            raise ValueError(
                f"positions.txt: {province_id} has "
                f"{position_block_count} position blocks"
            )
        values = parse_positions(positions, province_id)
        pairs = list(zip(values[0::2], values[1::2], strict=True))
        for index in (0, 1, 2, 4, 5):
            sampled_id, _x, _y = point_id(
                province_map,
                color_to_id,
                pairs[index][0],
                pairs[index][1],
            )
            if sampled_id != province_id:
                raise ValueError(
                    f"positions.txt: {province_id} slot {index + 1} "
                    f"lands in {sampled_id}"
                )
        port_id, port_x, port_y = point_id(
            province_map,
            color_to_id,
            pairs[3][0],
            pairs[3][1],
        )
        if province_id in port_seas:
            expected_sea = port_seas[province_id]
            if port_id != expected_sea:
                raise ValueError(
                    f"positions.txt: {province_id} port is in {port_id}, "
                    f"expected sea {expected_sea}"
                )
            adjacent_ids = {
                color_to_id.get(
                    tuple(int(channel) for channel in province_map[next_y, next_x])
                )
                for next_x, next_y in (
                    (port_x + 1, port_y),
                    (port_x - 1, port_y),
                    (port_x, port_y + 1),
                    (port_x, port_y - 1),
                )
                if 0 <= next_x < province_map.shape[1]
                and 0 <= next_y < province_map.shape[0]
            }
            if province_id not in adjacent_ids:
                raise ValueError(
                    f"positions.txt: {province_id} port does not touch the province"
                )
        elif port_id != province_id:
            raise ValueError(
                f"positions.txt: inland {province_id} port slot is in {port_id}"
            )

    navigable_water_positions: dict[int, list[int]] = {}
    for province_id in (1655, 1897, 1896) + YANGTZE_SEA_IDS + HUAI_SEA_IDS:
        position_block_count = len(
            re.findall(
                rf"(?m)^[ \t]*{province_id}[ \t]*=[ \t]*\{{",
                positions,
            )
        )
        if position_block_count != 1:
            raise ValueError(
                f"positions.txt: navigable water {province_id} has "
                f"{position_block_count} position blocks"
            )
        values = parse_positions(positions, province_id)
        pairs = list(zip(values[0::2], values[1::2], strict=True))
        expected_anchor = tuple(
            float(value)
            for value in POSITION_DATA[province_id]["positions"][:2]
        )
        for index in range(6):
            sampled_id, _x, _y = point_id(
                province_map,
                color_to_id,
                pairs[index][0],
                pairs[index][1],
            )
            if sampled_id != province_id:
                raise ValueError(
                    f"positions.txt: navigable water {province_id} "
                    f"slot {index + 1} lands in {sampled_id}"
                )
            if pairs[index] != expected_anchor:
                raise ValueError(
                    f"positions.txt: navigable water {province_id} "
                    f"slot {index + 1} is {pairs[index]}, "
                    f"expected {expected_anchor}"
                )
        navigable_water_positions[province_id] = [
            int(expected_anchor[0]),
            int(expected_anchor[1]),
        ]

    lower_yangtze_x, lower_yangtze_clausewitz_y = (
        navigable_water_positions[5033]
    )
    lower_yangtze_y = province_map.shape[0] - lower_yangtze_clausewitz_y
    lower_yangtze_color = np.array(definitions[5033][0], dtype=np.uint8)
    lower_yangtze_berth = province_map[
        lower_yangtze_y - 2:lower_yangtze_y + 3,
        lower_yangtze_x - 2:lower_yangtze_x + 3,
    ]
    if (
        lower_yangtze_berth.shape != (5, 5, 3)
        or not np.all(lower_yangtze_berth == lower_yangtze_color)
    ):
        raise ValueError(
            "positions.txt: Lower Yangtze fleet anchor lacks "
            "a 5x5 water-pixel berth"
        )
    if int(heightmap[lower_yangtze_y, lower_yangtze_x]) > 93:
        raise ValueError(
            "heightmap.bmp: Lower Yangtze fleet anchor is above water level"
        )

    huai_route = (5039, 5040, 5041, 5042, 1896, 5043, 5044)
    for left_id, right_id in zip(huai_route[:-1], huai_route[1:], strict=True):
        if right_id not in province_stats.get(left_id, {}).get("neighbors", []):
            # Hongze is an existing province and therefore is not part of the
            # manual config stats; test that contact directly below instead.
            if left_id != 1896 and right_id != 1896:
                raise ValueError(
                    f"provinces.bmp: Huai route breaks between {left_id} and {right_id}"
                )
    for province_id in (1896,) + HUAI_SEA_IDS:
        anchor_x, anchor_clausewitz_y = navigable_water_positions[province_id]
        anchor_y = province_map.shape[0] - anchor_clausewitz_y
        if int(heightmap[anchor_y, anchor_x]) > 93:
            raise ValueError(
                f"heightmap.bmp: Huai fleet anchor {province_id} is above water level"
            )
        if int(river_map[anchor_y, anchor_x]) != 254:
            raise ValueError(
                f"rivers.bmp: Huai fleet anchor {province_id} is not water background"
            )
    huai_color_masks = {
        province_id: np.all(
            province_map == np.array(definitions[province_id][0], dtype=np.uint8),
            axis=2,
        )
        for province_id in HUAI_SEA_IDS
    }
    hongze_mask = np.all(
        province_map == np.array(definitions[1896][0], dtype=np.uint8), axis=2
    )
    route_masks = [huai_color_masks[value] for value in HUAI_SEA_IDS[:4]]
    route_masks += [hongze_mask]
    route_masks += [huai_color_masks[value] for value in HUAI_SEA_IDS[4:]]
    for left_id, right_id, left_mask, right_mask in zip(
        huai_route[:-1], huai_route[1:],
        route_masks[:-1], route_masks[1:], strict=True
    ):
        adjacent = (
            np.any(left_mask[1:] & right_mask[:-1])
            or np.any(left_mask[:-1] & right_mask[1:])
            or np.any(left_mask[:, 1:] & right_mask[:, :-1])
            or np.any(left_mask[:, :-1] & right_mask[:, 1:])
        )
        if not adjacent:
            raise ValueError(
                f"provinces.bmp: Huai route lacks orthogonal contact "
                f"between {left_id} and {right_id}"
            )

    for province_id in PREPARED_IDS:
        position_block_count = len(
            re.findall(
                rf"(?m)^[ \t]*{province_id}[ \t]*=[ \t]*\{{",
                positions,
            )
        )
        if position_block_count != 1:
            raise ValueError(
                f"positions.txt: prepared province {province_id} has "
                f"{position_block_count} position blocks"
            )
        values = parse_positions(positions, province_id)
        expected_city = tuple(
            float(value) for value in POSITION_DATA[province_id]["positions"][:2]
        )
        if tuple(values[:2]) != expected_city:
            raise ValueError(
                f"positions.txt: prepared province {province_id} city anchor "
                f"{tuple(values[:2])} differs from {expected_city}"
            )

    def bitmap_seat(province_id: int) -> tuple[int, int]:
        x, clausewitz_y = POSITION_DATA[province_id]["positions"][:2]
        return int(x), int(province_map.shape[0] - clausewitz_y)

    def province_at(x: int, y: int) -> int:
        color = tuple(int(value) for value in province_map[y, x])
        return color_to_id[color]

    # Wuhan's three urban provinces are deliberately separated by the actual
    # Han and Yangtze pixels rather than by an approximate geometric core.
    han_bank_samples = (
        (4582, 894, 4582, 893, 4582, 895),
        (4580, 896, 4580, 895, 4580, 897),
    )
    for river_x, river_y, north_x, north_y, south_x, south_y in han_bank_samples:
        if int(river_map[river_y, river_x]) != 3:
            raise ValueError(f"rivers.bmp: missing Han River at {(river_x, river_y)}")
        if province_at(north_x, north_y) != 5011:
            raise ValueError("Hankou must remain on the north bank of the Han River")
        if province_at(south_x, south_y) != 4981:
            raise ValueError("Hanyang must remain south of the Han River")

    yangtze_bank_samples = (
        (4588, 894, 4586, 894, 4590, 895),
        (4590, 892, 4588, 891, 4591, 894),
    )
    for river_x, river_y, north_x, north_y, south_x, south_y in yangtze_bank_samples:
        if province_at(river_x, river_y) != 5035:
            raise ValueError("provinces.bmp: Wuhan Reach is missing from the Yangtze")
        if province_at(north_x, north_y) != 5011:
            raise ValueError("Hankou must remain on the north/west bank of the Yangtze")
        if province_at(south_x, south_y) != 682:
            raise ValueError("Wuchang must remain on the south/east bank of the Yangtze")

    hanyang_seat = bitmap_seat(4981)
    hankou_seat = bitmap_seat(5011)
    wuchang_seat = bitmap_seat(682)
    if not (
        hankou_seat[0] > hanyang_seat[0]
        and hankou_seat[1] < hanyang_seat[1]
        and wuchang_seat[0] > hanyang_seat[0]
        and wuchang_seat[1] > hankou_seat[1]
    ):
        raise ValueError(
            "Wuhan seats must place Hankou north of Hanyang and "
            "Wuchang southeast of the Han-Yangtze confluence"
        )
    for seat in (hanyang_seat, hankou_seat, wuchang_seat):
        if (seat[0] - 4584) ** 2 + (seat[1] - 898) ** 2 > 12 ** 2:
            raise ValueError(f"Wuhan seat {seat} is too far from the river confluence")
    balanced_hubei_ids = set(HUBEI_ALL_IDS) - {4981, 5011, 682}
    balanced_sizes = [province_stats[value]["pixels"] for value in balanced_hubei_ids]
    if max(balanced_sizes) / min(balanced_sizes) > 3.5:
        raise ValueError(
            f"Non-Wuhan Hubei provinces are not size-balanced: {balanced_sizes}"
        )

    return {
        "changed_pixels": changed_pixels,
        "province_stats": province_stats,
        "wuhan_seats_bitmap": {
            "Hanyang": list(hanyang_seat),
            "Hankou": list(hankou_seat),
            "Wuchang": list(wuchang_seat),
        },
        "navigable_water_positions": navigable_water_positions,
        "taiwan_terrain_palette_counts": terrain_counts,
        "prepared_pixels": prepared_pixels,
        "provinces_sha256": sha256_file(provinces_path),
    }


def validate_memberships(vanilla_root: Path, mod_root: Path) -> None:
    area_text = (mod_root / "map/area.txt").read_text(encoding="cp1252")
    for province_id, area_name in EXPECTED_AREAS.items():
        assert_token_once(area_text, province_id, "area.txt")
        if province_id not in numeric_tokens(block_text(area_text, area_name)):
            raise ValueError(f"area.txt: {province_id} is not in {area_name}")
    yangtze_area = set(numeric_tokens(block_text(area_text, "yangtze_river_area")))
    if yangtze_area != set(YANGTZE_SEA_IDS + (1655, 1897)):
        raise ValueError(f"area.txt: unexpected Yangtze sea membership {yangtze_area}")
    huai_area = set(numeric_tokens(block_text(area_text, "huai_river_area")))
    if huai_area != set(HUAI_SEA_IDS + (1896,)):
        raise ValueError(f"area.txt: unexpected Huai sea membership {huai_area}")

    region_text = (mod_root / "map/region.txt").read_text(encoding="cp1252")
    south_china = block_text(region_text, "south_china_region")
    for area_name in {
        "pearl_river_delta_area",
        "guangdong_area",
        "west_guangdong_area",
        "fujian_area",
        "west_fujian_area",
        "guangxi_area",
        "youjiang_area",
        "jiangxi_area",
        "south_jiangxi_area",
        "dongting_area",
        "hunan_area",
        "southwest_hunan_area",
        "east_zhejiang_area",
        "jinqu_chuzhou_area",
        "hanjiang_xiangyun_area",
        "jingyi_shinan_area",
        "dean_qihuang_area",
        "wuhan_enan_area",
    }:
        if not re.search(rf"\b{re.escape(area_name)}\b", south_china):
            raise ValueError(f"region.txt: south_china_region lacks {area_name}")

    xinan = block_text(region_text, "xinan_region")
    if not re.search(r"\bchongqing_area\b", xinan):
        raise ValueError("region.txt: xinan_region lacks chongqing_area")

    north_china = block_text(region_text, "north_china_region")
    if not re.search(r"\bwangji_area\b", north_china):
        raise ValueError("region.txt: north_china_region lacks wangji_area")
    east_china_sea = block_text(region_text, "east_china_sea_region")
    if not re.search(r"\byangtze_river_area\b", east_china_sea):
        raise ValueError("region.txt: east_china_sea_region lacks yangtze_river_area")
    if not re.search(r"\bhuai_river_area\b", east_china_sea):
        raise ValueError("region.txt: east_china_sea_region lacks huai_river_area")

    superregion_text = (vanilla_root / "map/superregion.txt").read_text(
        encoding="cp1252"
    )
    china = block_text(superregion_text, "china_superregion")
    if not re.search(r"\bsouth_china_region\b", china):
        raise ValueError("superregion.txt: China lacks south_china_region")

    continent_text = (mod_root / "map/continent.txt").read_text(encoding="cp1252")
    asia = block_text(continent_text, "asia")
    for province_id in ACTIVE_IDS:
        assert_token_once(continent_text, province_id, "continent.txt")
        if province_id not in numeric_tokens(asia):
            raise ValueError(f"continent.txt: {province_id} is not in Asia")

    climate_text = (mod_root / "map/climate.txt").read_text(encoding="cp1252")
    normal_monsoon = set(numeric_tokens(block_text(climate_text, "normal_monsoon")))
    tropical = set(numeric_tokens(block_text(climate_text, "tropical")))
    impassable = set(numeric_tokens(block_text(climate_text, "impassable")))
    for province_id in IMPLEMENTED_IDS + (
        4950, 4951, 4952, 4953, 4955,
        4956, 4957, 4958, 4960, 4961,
        4979, 4980, 4992, 4993, 4994, 4995,
        4982, 4983, 4996, 4997, 4998, 4999, 5000, 5001,
        684, 1824, 2148, 2149, 2150,
        5002, 5003, 5004, 5005, 5006, 5007,
        4981, 5008, 5009, 5010, 5011, 5012, 5013, 5014, 5015, 5016,
        4987, 5026, 5027, 5028,
        4966, 5030, 5031,
    ):
        if province_id not in normal_monsoon:
            raise ValueError(f"climate.txt: {province_id} lacks normal_monsoon")
    expected_tropical = {4945, 4954, 4955, 4960, 4961}
    if not expected_tropical <= tropical:
        raise ValueError("climate.txt: a prepared tropical province is missing")
    if tropical & (set(ACTIVE_IDS) - expected_tropical):
        raise ValueError("climate.txt: an unintended active province is tropical")
    if TAIWAN_MOUNTAIN_ID not in impassable:
        raise ValueError("climate.txt: Taiwan Mountains is not impassable")

    terrain_text = (mod_root / "map/terrain.txt").read_text(encoding="cp1252")
    for province_id, terrain_name in EXPECTED_TERRAIN.items():
        assert_token_once(terrain_text, province_id, "terrain.txt")
        if province_id not in numeric_tokens(block_text(terrain_text, terrain_name)):
            raise ValueError(
                f"terrain.txt: {province_id} is not overridden to {terrain_name}"
            )
    ocean_ids = set(numeric_tokens(block_text(terrain_text, "inland_ocean")))
    if not set(
        YANGTZE_SEA_IDS + HUAI_SEA_IDS + (1655, 1897, 1896)
    ) <= ocean_ids:
        raise ValueError("terrain.txt: navigable Yangtze or Huai is not ocean terrain")

    trade_nodes = (
        mod_root / "common/tradenodes/00_tradenodes.txt"
    ).read_text(encoding="cp1252")
    canton = block_text(trade_nodes, "canton")
    canton_members = set(numeric_tokens(block_text(canton, "members")))
    for province_id in (
        IMPLEMENTED_IDS
        + (4954, 4955, 4959, 4960, 4961)
        + HUNAN_IDS
    ):
        assert_token_once(trade_nodes, province_id, "00_tradenodes.txt")
        if province_id not in canton_members:
            raise ValueError(f"Canton trade node lacks {province_id}")
    hangzhou = block_text(trade_nodes, "hangzhou")
    hangzhou_members = set(numeric_tokens(block_text(hangzhou, "members")))
    for province_id in (
        4950, 4951, 4952, 4953, 4956, 4957, 4958,
        4979, 4980, 4992, 4993, 4994, 4995,
        5002, 5003, 5004, 5005, 5006, 5007,
    ):
        assert_token_once(trade_nodes, province_id, "00_tradenodes.txt")
        if province_id not in hangzhou_members:
            raise ValueError(f"Hangzhou trade node lacks {province_id}")
    xian = block_text(trade_nodes, "xian")
    xian_members = set(numeric_tokens(block_text(xian, "members")))
    for province_id in HUBEI_NEW_IDS + WANGJI_NEW_IDS:
        assert_token_once(trade_nodes, province_id, "00_tradenodes.txt")
        if province_id not in xian_members:
            raise ValueError(f"Xi'an trade node lacks {province_id}")
    chengdu = block_text(trade_nodes, "chengdu")
    chengdu_members = set(numeric_tokens(block_text(chengdu, "members")))
    for province_id in CHONGQING_NEW_IDS:
        assert_token_once(trade_nodes, province_id, "00_tradenodes.txt")
        if province_id not in chengdu_members:
            raise ValueError(f"Chengdu trade node lacks {province_id}")

    companies = (
        mod_root / "common/trade_companies/00_trade_companies.txt"
    ).read_text(encoding="cp1252")
    south_china = block_text(companies, "trade_company_south_china")
    company_provinces = set(numeric_tokens(block_text(south_china, "provinces")))
    for province_id in (
        IMPLEMENTED_IDS
        + (4954, 4955, 4959, 4960, 4961)
        + HUNAN_IDS
    ):
        assert_token_once(companies, province_id, "00_trade_companies.txt")
        if province_id not in company_provinces:
            raise ValueError(f"South China trade company lacks {province_id}")
    east_china = block_text(companies, "trade_company_east_china")
    east_company_provinces = set(
        numeric_tokens(block_text(east_china, "provinces"))
    )
    for province_id in (
        4950, 4951, 4952, 4953, 4956, 4957, 4958,
        4979, 4980, 4992, 4993, 4994, 4995,
        5002, 5003, 5004, 5005, 5006, 5007,
    ):
        assert_token_once(companies, province_id, "00_trade_companies.txt")
        if province_id not in east_company_provinces:
            raise ValueError(f"East China trade company lacks {province_id}")
    xian_company = block_text(companies, "trade_company_xian")
    xian_company_provinces = set(
        numeric_tokens(block_text(xian_company, "provinces"))
    )
    for province_id in HUBEI_NEW_IDS + WANGJI_NEW_IDS:
        assert_token_once(companies, province_id, "00_trade_companies.txt")
        if province_id not in xian_company_provinces:
            raise ValueError(f"Xi'an trade company lacks {province_id}")
    chengdu_company = block_text(companies, "trade_company_chengdu")
    chengdu_company_provinces = set(
        numeric_tokens(block_text(chengdu_company, "provinces"))
    )
    for province_id in CHONGQING_NEW_IDS:
        assert_token_once(companies, province_id, "00_trade_companies.txt")
        if province_id not in chengdu_company_provinces:
            raise ValueError(f"Chengdu trade company lacks {province_id}")


def validate_histories(mod_root: Path) -> dict[int, tuple[int, int, int]]:
    development: dict[int, tuple[int, int, int]] = {}
    for province_id, (owner, expected_dev, goods, culture) in EXPECTED_HISTORY.items():
        path = history_path(mod_root, province_id)
        validate_braces(path)
        text = path.read_text(encoding="cp1252")
        actual_owner = initial_history_value(text, "owner")
        actual_goods = initial_history_value(text, "trade_goods")
        actual_culture = initial_history_value(text, "culture")
        actual_dev = tuple(
            int(initial_history_value(text, key))
            for key in ("base_tax", "base_production", "base_manpower")
        )
        actual = (actual_owner, actual_dev, actual_goods, actual_culture)
        expected = (owner, expected_dev, goods, culture)
        if actual != expected:
            raise ValueError(f"{path.name}: history {actual}, expected {expected}")
        if province_id in IMPLEMENTED_IDS:
            if "add_core = GDD" not in text:
                raise ValueError(f"{path.name}: missing GDD core")
            if initial_history_value(text, "religion") != "confucianism":
                raise ValueError(f"{path.name}: religion must be confucianism")
            if initial_history_value(text, "is_city") != "yes":
                raise ValueError(f"{path.name}: must be a city")
        development[province_id] = actual_dev

    for parent_id, partition in EXPECTED_DEV_PARTITIONS.items():
        child_ids = partition["children"]
        recombined = tuple(
            development[parent_id][index]
            + sum(development[child_id][index] for child_id in child_ids)
            for index in range(3)
        )
        expected = tuple(
            partition["original"][index] + partition["delta"][index]
            for index in range(3)
        )
        if recombined != expected:
            raise ValueError(
                f"Development partition {parent_id} recombines to {recombined}, "
                f"expected {expected}"
            )

    nanxiong = history_path(mod_root, 4948).read_text(encoding="cp1252")
    if initial_history_value(nanxiong, "center_of_trade") != "1":
        raise ValueError("4948 Nanxiong must have a level-1 center of trade")
    lufeng = history_path(mod_root, 4949).read_text(encoding="cp1252")
    if initial_history_value(lufeng, "fort_15th") != "yes":
        raise ValueError("4949 Lufeng must have a 15th-century fort")
    return development


def validate_taiwan_mountain_history(mod_root: Path) -> None:
    path = history_path(mod_root, TAIWAN_MOUNTAIN_ID)
    validate_braces(path)
    text = path.read_text(encoding="cp1252")
    for forbidden in (
        "owner", "controller", "base_tax", "base_production",
        "base_manpower", "trade_goods", "culture", "religion", "is_city",
    ):
        if re.search(rf"(?m)^\s*{forbidden}\s*=", text):
            raise ValueError(
                f"{path.name}: impassable mountain must not define {forbidden}"
            )
    if not re.search(r"(?m)^\s*discovered_by\s*=", text):
        raise ValueError(f"{path.name}: missing discovery groups")


def validate_prepared_histories(
    vanilla_root: Path,
    mod_root: Path,
) -> dict[int, tuple[int, int, int]]:
    development: dict[int, tuple[int, int, int]] = {}
    for province_id, (owner, expected_dev, goods, culture) in PREPARED_HISTORY.items():
        path = history_path(mod_root, province_id)
        validate_braces(path)
        text = path.read_text(encoding="cp1252")
        owner_match = re.search(r"(?m)^owner\s*=\s*([^\s#]+)", text)
        actual_owner = owner_match.group(1).strip('"') if owner_match else None
        actual_goods = initial_history_value(text, "trade_goods")
        actual_culture = initial_history_value(text, "culture")
        actual_dev = tuple(
            int(initial_history_value(text, key))
            for key in ("base_tax", "base_production", "base_manpower")
        )
        actual = (actual_owner, actual_dev, actual_goods, actual_culture)
        expected = (owner, expected_dev, goods, culture)
        if actual != expected:
            raise ValueError(f"{path.name}: history {actual}, expected {expected}")
        if province_id in PREPARED_IDS:
            if initial_history_value(text, "religion") not in {
                "confucianism",
                "animism",
            }:
                raise ValueError(f"{path.name}: unexpected religion")
            if owner is not None and initial_history_value(text, "is_city") != "yes":
                raise ValueError(f"{path.name}: owned province must be a city")
        development[province_id] = actual_dev

    for parent_id, (child_ids, expected_total) in PREPARED_DEV_PARTITIONS.items():
        recombined = tuple(
            development[parent_id][index]
            + sum(development[child_id][index] for child_id in child_ids)
            for index in range(3)
        )
        if recombined != expected_total:
            raise ValueError(
                f"Prepared development partition {parent_id}+{child_ids} "
                f"recombines to {recombined}, expected {expected_total}"
            )

    guangxi_ids = (664, 1840, 2162, 2163, 2164, 4954, 4959, 4960)
    guangxi_total = [0, 0, 0]
    for province_id in guangxi_ids:
        if province_id not in development:
            matches = list(
                (vanilla_root / "history/provinces").glob(f"{province_id} - *.txt")
            )
            if len(matches) != 1:
                raise ValueError(
                    f"Vanilla history for Guangxi province {province_id} is ambiguous"
                )
            text = matches[0].read_text(encoding="cp1252")
            development[province_id] = tuple(
                int(initial_history_value(text, key))
                for key in ("base_tax", "base_production", "base_manpower")
            )
        for index, value in enumerate(development[province_id]):
            guangxi_total[index] += value
    if tuple(guangxi_total) != (8, 8, 9):
        raise ValueError(
            f"Guangxi area recombines to {tuple(guangxi_total)}, expected (8, 8, 9)"
        )
    return development


def validate_jiangxi_histories(mod_root: Path) -> dict[int, tuple[int, int, int]]:
    development: dict[int, tuple[int, int, int]] = {}
    center_of_trade_ids: set[int] = set()
    for province_id, (owner, expected_dev, goods, culture) in JIANGXI_HISTORY.items():
        path = history_path(mod_root, province_id)
        validate_braces(path)
        text = path.read_text(encoding="cp1252")
        actual = (
            initial_history_value(text, "owner"),
            tuple(
                int(initial_history_value(text, key))
                for key in ("base_tax", "base_production", "base_manpower")
            ),
            initial_history_value(text, "trade_goods"),
            initial_history_value(text, "culture"),
        )
        expected = (owner, expected_dev, goods, culture)
        if actual != expected:
            raise ValueError(f"{path.name}: history {actual}, expected {expected}")
        if initial_history_value(text, "religion") != "confucianism":
            raise ValueError(f"{path.name}: religion must be confucianism")
        if initial_history_value(text, "is_city") != "yes":
            raise ValueError(f"{path.name}: must be a city")
        cot = re.search(r"(?m)^center_of_trade\s*=\s*(\d+)", text)
        if cot:
            if int(cot.group(1)) != 1:
                raise ValueError(f"{path.name}: opening center of trade must be level 1")
            center_of_trade_ids.add(province_id)
        development[province_id] = actual[1]

    totals = tuple(
        sum(values[index] for values in development.values())
        for index in range(3)
    )
    if totals != (36, 39, 25):
        raise ValueError(f"Jiangxi development is {totals}, expected (36, 39, 25)")
    if sum(sum(values) for values in development.values()) != 100:
        raise ValueError("Jiangxi total development must be exactly 100")
    if center_of_trade_ids != {670, 4979}:
        raise ValueError(
            f"Jiangxi centers of trade are {sorted(center_of_trade_ids)}, "
            "expected Ganzhou and Jiujiang"
        )

    raozhou = history_path(mod_root, 2151).read_text(encoding="cp1252")
    if "name = jingdezhen_kilns" not in raozhou:
        raise ValueError("2151 Raozhou lost the Jingdezhen kilns modifier")
    nanan = history_path(mod_root, 4995).read_text(encoding="cp1252")
    if initial_history_value(nanan, "fort_15th") != "yes":
        raise ValueError("4995 Nan'an must have a 15th-century fort")
    return development


def validate_hunan_histories(mod_root: Path) -> dict[int, tuple[int, int, int]]:
    development: dict[int, tuple[int, int, int]] = {}
    center_of_trade_ids: set[int] = set()
    for province_id, expected in HUNAN_HISTORY.items():
        path = history_path(mod_root, province_id)
        validate_braces(path)
        text = path.read_text(encoding="cp1252")
        actual_dev = tuple(
            int(initial_history_value(text, key))
            for key in ("base_tax", "base_production", "base_manpower")
        )
        actual = (
            initial_history_value(text, "owner"),
            actual_dev,
            initial_history_value(text, "trade_goods"),
            initial_history_value(text, "culture"),
            initial_history_value(text, "religion"),
        )
        if actual != expected:
            raise ValueError(f"{path.name}: history {actual}, expected {expected}")
        if initial_history_value(text, "is_city") != "yes":
            raise ValueError(f"{path.name}: must be a city")
        cot = re.search(r"(?m)^center_of_trade\s*=\s*(\d+)", text)
        if cot:
            if int(cot.group(1)) != 1:
                raise ValueError(f"{path.name}: opening center of trade must be level 1")
            center_of_trade_ids.add(province_id)
        development[province_id] = actual_dev

    totals = tuple(
        sum(values[index] for values in development.values())
        for index in range(3)
    )
    if totals != (35, 42, 31):
        raise ValueError(f"Hunan development is {totals}, expected (35, 42, 31)")
    if sum(sum(values) for values in development.values()) != 108:
        raise ValueError("Hunan total development must be exactly 108")
    if center_of_trade_ids != {2174, 4982}:
        raise ValueError(
            f"Hunan centers of trade are {sorted(center_of_trade_ids)}, "
            "expected Hengzhou and Yuezhou"
        )
    chenzhou = history_path(mod_root, 5001).read_text(encoding="cp1252")
    if initial_history_value(chenzhou, "fort_15th") != "yes":
        raise ValueError("5001 Chenzhou must have a 15th-century fort")
    return development


def validate_zhejiang_histories(mod_root: Path) -> dict[int, tuple[int, int, int]]:
    development: dict[int, tuple[int, int, int]] = {}
    center_of_trade: dict[int, int] = {}
    for province_id, expected in ZHEJIANG_HISTORY.items():
        path = history_path(mod_root, province_id)
        validate_braces(path)
        text = path.read_text(encoding="cp1252")
        actual_dev = tuple(
            int(initial_history_value(text, key))
            for key in ("base_tax", "base_production", "base_manpower")
        )
        actual = (
            initial_history_value(text, "owner"),
            actual_dev,
            initial_history_value(text, "trade_goods"),
            initial_history_value(text, "culture"),
            initial_history_value(text, "religion"),
        )
        if actual != expected:
            raise ValueError(f"{path.name}: history {actual}, expected {expected}")
        if initial_history_value(text, "is_city") != "yes":
            raise ValueError(f"{path.name}: must be a city")
        cot = re.search(r"(?m)^center_of_trade\s*=\s*(\d+)", text)
        if cot:
            center_of_trade[province_id] = int(cot.group(1))
        development[province_id] = actual_dev

    totals = tuple(
        sum(values[index] for values in development.values())
        for index in range(3)
    )
    if totals != (50, 62, 29):
        raise ValueError(f"Zhejiang development is {totals}, expected (50, 62, 29)")
    if sum(sum(values) for values in development.values()) != 141:
        raise ValueError("Zhejiang total development must be exactly 141")
    if center_of_trade != {684: 2, 2149: 1}:
        raise ValueError(
            f"Zhejiang centers of trade are {center_of_trade}, "
            "expected Hangzhou level 2 and Ningbo level 1"
        )
    for province_id in (4950, 4956):
        text = history_path(mod_root, province_id).read_text(encoding="cp1252")
        if initial_history_value(text, "fort_15th") != "yes":
            raise ValueError(f"{province_id} must have a 15th-century fort")
    return development


def validate_hubei_histories(mod_root: Path) -> dict[int, tuple[int, int, int]]:
    development: dict[int, tuple[int, int, int]] = {}
    centers: dict[int, int] = {}
    for province_id, expected in HUBEI_HISTORY.items():
        path = history_path(mod_root, province_id)
        validate_braces(path)
        text = path.read_text(encoding="cp1252")
        actual_dev = tuple(
            int(initial_history_value(text, key))
            for key in ("base_tax", "base_production", "base_manpower")
        )
        actual = (
            initial_history_value(text, "owner"),
            actual_dev,
            initial_history_value(text, "trade_goods"),
            initial_history_value(text, "culture"),
            initial_history_value(text, "religion"),
        )
        if actual != expected:
            raise ValueError(f"{path.name}: history {actual}, expected {expected}")
        if initial_history_value(text, "is_city") != "yes":
            raise ValueError(f"{path.name}: must be a city")
        cot = re.search(r"(?m)^center_of_trade\s*=\s*(\d+)", text)
        if cot:
            centers[province_id] = int(cot.group(1))
        development[province_id] = actual_dev
    totals = tuple(
        sum(values[index] for values in development.values())
        for index in range(3)
    )
    if totals != (48, 53, 33):
        raise ValueError(f"Hubei development is {totals}, expected (48, 53, 33)")
    if centers != {2172: 1, 5011: 2}:
        raise ValueError(
            f"Hubei centers of trade are {centers}, expected Jingzhou 1/Hankou 2"
        )
    for province_id in (682, 2171, 2172):
        text = history_path(mod_root, province_id).read_text(encoding="cp1252")
        if initial_history_value(text, "fort_15th") != "yes":
            raise ValueError(f"{province_id} must have a 15th-century fort")
    hankou = history_path(mod_root, 5011).read_text(encoding="cp1252")
    if "add_core = CHC" in hankou:
        raise ValueError("Hankou free city must not begin with a Chu core")
    return development


def validate_jiangsu_histories(mod_root: Path) -> dict[int, tuple[int, int, int]]:
    development: dict[int, tuple[int, int, int]] = {}
    centers: dict[int, int] = {}
    for province_id, expected in JIANGSU_HISTORY.items():
        path = history_path(mod_root, province_id)
        validate_braces(path)
        text = path.read_text(encoding="cp1252")
        actual_dev = tuple(
            int(initial_history_value(text, key))
            for key in ("base_tax", "base_production", "base_manpower")
        )
        actual = (
            initial_history_value(text, "owner"),
            actual_dev,
            initial_history_value(text, "trade_goods"),
            initial_history_value(text, "culture"),
            initial_history_value(text, "religion"),
        )
        if actual != expected:
            raise ValueError(f"{path.name}: history {actual}, expected {expected}")
        if initial_history_value(text, "is_city") != "yes":
            raise ValueError(f"{path.name}: must be a city")
        cot = re.search(r"(?m)^center_of_trade\s*=\s*(\d+)", text)
        if cot:
            centers[province_id] = int(cot.group(1))
        development[province_id] = actual_dev
    totals = tuple(
        sum(values[index] for values in development.values())
        for index in range(3)
    )
    if totals != (65, 80, 39):
        raise ValueError(f"Jiangsu development is {totals}, expected (65, 80, 39)")
    if centers != {2142: 1, 685: 2, 1822: 2}:
        raise ValueError(
            f"Jiangsu centers of trade are {centers}, "
            "expected Huai'an 1/Yangzhou 2/Suzhou 2"
        )
    for province_id in (2141, 1821):
        text = history_path(mod_root, province_id).read_text(encoding="cp1252")
        if initial_history_value(text, "fort_15th") != "yes":
            raise ValueError(f"{province_id} must have a 15th-century fort")
    return development


def validate_locked_guangzhou_assets(vanilla_root: Path, mod_root: Path) -> None:
    canton_history = history_path(mod_root, 667).read_text(encoding="cp1252")
    required_history_snippets = (
        "fort_15th = yes",
        "extra_cost = 34",
        "center_of_trade = 3",
        "name = pearl_estuary_modifier",
    )
    for snippet in required_history_snippets:
        if snippet not in canton_history:
            raise ValueError(f"667 Canton history lost locked asset: {snippet}")

    great_project = (
        mod_root / "common/great_projects/gdd_great_projects.txt"
    ).read_text(encoding="utf-8", errors="replace")
    if not re.search(r"(?m)^\s*start\s*=\s*667\b", great_project):
        raise ValueError("Nanhai Temple is no longer anchored to province 667")

    trade_modifier = (
        mod_root
        / "common/triggered_modifiers/gdd_guangzhou_trade_modifiers.txt"
    ).read_text(encoding="utf-8", errors="replace")
    if len(re.findall(r"(?m)^\s*owns\s*=\s*667\b", trade_modifier)) < 2:
        raise ValueError("Guangzhou trade modifier no longer checks province 667")

    adjacency_path = mod_root / "map/adjacencies.csv"
    with adjacency_path.open(encoding="cp1252", errors="replace", newline="") as handle:
        special_rows = [
            row
            for row in csv.reader(handle, delimiter=";")
            if len(row) >= 4
            and row[0].lstrip("-").isdigit()
            and row[1].lstrip("-").isdigit()
            and int(row[0]) >= 0
            and int(row[1]) >= 0
        ]
    special_pairs = {
        tuple(sorted((int(row[0]), int(row[1])))) for row in special_rows
    }
    if (666, 2159) not in special_pairs:
        raise ValueError("Vanilla Leichow-Kiungchow special adjacency is missing")
    changguo_rows = [
        row
        for row in special_rows
        if tuple(sorted((int(row[0]), int(row[1])))) == (2149, 5004)
    ]
    if len(changguo_rows) != 1:
        raise ValueError("Ningbo-Changguo must have exactly one strait adjacency")
    if changguo_rows[0][2:4] != ["sea", "1373"]:
        raise ValueError("Ningbo-Changguo strait must pass through sea province 1373")


def validate_localisation(mod_root: Path) -> None:
    source = (
        mod_root / "localisation_source/gdd_b01_map_readable_utf8.txt"
    ).read_text(encoding="utf-8-sig")
    for province_id in IMPLEMENTED_IDS:
        for key in (f"PROV{province_id}", f"PROV_ADJ{province_id}"):
            if not re.search(rf"(?m)^\s*{key}:0\s+\"", source):
                raise ValueError(f"Localisation source lacks {key}")
    for key in (
        "pearl_river_delta_area",
        "pearl_river_delta_area_name",
        "pearl_river_delta_area_adj",
    ):
        if not re.search(rf"(?m)^\s*{key}:0\s+\"", source):
            raise ValueError(f"Localisation source lacks {key}")
    encoded = mod_root / "localisation/gdd_b01_map_l_english.yml"
    if not encoded.is_file() or not encoded.read_bytes().startswith(b"\xef\xbb\xbf"):
        raise ValueError("Encoded B01 localisation is missing or lacks a BOM")
    prepared_source = (
        mod_root
        / "localisation_source/gdd_p02_southeast_map_readable_utf8.txt"
    ).read_text(encoding="utf-8-sig")
    for province_id in PREPARED_IDS:
        for key in (f"PROV{province_id}", f"PROV_ADJ{province_id}"):
            if not re.search(rf"(?m)^\s*{key}:0\s+\"", prepared_source):
                raise ValueError(f"Prepared localisation source lacks {key}")
    for key in (f"PROV{TAIWAN_MOUNTAIN_ID}", f"PROV_ADJ{TAIWAN_MOUNTAIN_ID}"):
        if not re.search(rf"(?m)^\s*{key}:0\s+\"", prepared_source):
            raise ValueError(f"Taiwan localisation source lacks {key}")
    for key in (
        "fujian_area",
        "fujian_area_name",
        "fujian_area_adj",
        "west_fujian_area",
        "west_fujian_area_name",
        "west_fujian_area_adj",
        "guangxi_area",
        "guangxi_area_name",
        "guangxi_area_adj",
        "youjiang_area",
        "youjiang_area_name",
        "youjiang_area_adj",
    ):
        if not re.search(rf"(?m)^\s*{key}:0\s+\"", prepared_source):
            raise ValueError(f"Prepared localisation source lacks {key}")
    prepared_encoded = (
        mod_root / "localisation/gdd_p02_southeast_map_l_english.yml"
    )
    if (
        not prepared_encoded.is_file()
        or not prepared_encoded.read_bytes().startswith(b"\xef\xbb\xbf")
    ):
        raise ValueError("Encoded P02 localisation is missing or lacks a BOM")
    jiangxi_source = (
        mod_root / "localisation_source/gdd_b07_jiangxi_map_readable_utf8.txt"
    ).read_text(encoding="utf-8-sig")
    for province_id in (2151,) + JIANGXI_IDS:
        for key in (f"PROV{province_id}", f"PROV_ADJ{province_id}"):
            if not re.search(rf"(?m)^\s*{key}:0\s+\"", jiangxi_source):
                raise ValueError(f"Jiangxi localisation source lacks {key}")
    for key in (
        "jiangxi_area",
        "jiangxi_area_name",
        "jiangxi_area_adj",
        "south_jiangxi_area",
        "south_jiangxi_area_name",
        "south_jiangxi_area_adj",
    ):
        if not re.search(rf"(?m)^\s*{key}:0\s+\"", jiangxi_source):
            raise ValueError(f"Jiangxi localisation source lacks {key}")
    jiangxi_encoded = (
        mod_root / "localisation/gdd_b07_jiangxi_map_l_english.yml"
    )
    if (
        not jiangxi_encoded.is_file()
        or not jiangxi_encoded.read_bytes().startswith(b"\xef\xbb\xbf")
    ):
        raise ValueError("Encoded Jiangxi localisation is missing or lacks a BOM")
    hunan_source = (
        mod_root / "localisation_source/gdd_b07_hunan_map_readable_utf8.txt"
    ).read_text(encoding="utf-8-sig")
    for province_id in (672, 2173, 2174) + HUNAN_IDS:
        for key in (f"PROV{province_id}", f"PROV_ADJ{province_id}"):
            if not re.search(rf"(?m)^\s*{key}:0\s+\"", hunan_source):
                raise ValueError(f"Hunan localisation source lacks {key}")
    for key in (
        "dongting_area",
        "dongting_area_name",
        "dongting_area_adj",
        "hunan_area",
        "hunan_area_name",
        "hunan_area_adj",
        "southwest_hunan_area",
        "southwest_hunan_area_name",
        "southwest_hunan_area_adj",
    ):
        if not re.search(rf"(?m)^\s*{key}:0\s+\"", hunan_source):
            raise ValueError(f"Hunan localisation source lacks {key}")
    hunan_encoded = mod_root / "localisation/gdd_b07_hunan_map_l_english.yml"
    if (
        not hunan_encoded.is_file()
        or not hunan_encoded.read_bytes().startswith(b"\xef\xbb\xbf")
    ):
        raise ValueError("Encoded Hunan localisation is missing or lacks a BOM")
    zhejiang_source = (
        mod_root / "localisation_source/gdd_b06_zhejiang_map_readable_utf8.txt"
    ).read_text(encoding="utf-8-sig")
    for province_id in tuple(ZHEJIANG_HISTORY):
        for key in (f"PROV{province_id}", f"PROV_ADJ{province_id}"):
            if not re.search(rf"(?m)^\s*{key}:0\s+\"", zhejiang_source):
                raise ValueError(f"Zhejiang localisation source lacks {key}")
    for key in (
        "zhejiang_area",
        "zhejiang_area_name",
        "zhejiang_area_adj",
        "east_zhejiang_area",
        "east_zhejiang_area_name",
        "east_zhejiang_area_adj",
        "jinqu_chuzhou_area",
        "jinqu_chuzhou_area_name",
        "jinqu_chuzhou_area_adj",
    ):
        if not re.search(rf"(?m)^\s*{key}:0\s+\"", zhejiang_source):
            raise ValueError(f"Zhejiang localisation source lacks {key}")
    zhejiang_encoded = (
        mod_root / "localisation/gdd_b06_zhejiang_map_l_english.yml"
    )
    if (
        not zhejiang_encoded.is_file()
        or not zhejiang_encoded.read_bytes().startswith(b"\xef\xbb\xbf")
    ):
        raise ValueError("Encoded Zhejiang localisation is missing or lacks a BOM")
    hubei_source = (
        mod_root / "localisation_source/gdd_b10_hubei_map_readable_utf8.txt"
    ).read_text(encoding="utf-8-sig")
    for province_id in HUBEI_ALL_IDS:
        for key in (f"PROV{province_id}", f"PROV_ADJ{province_id}"):
            if not re.search(rf"(?m)^\s*{key}:0\s+\"", hubei_source):
                raise ValueError(f"Hubei localisation source lacks {key}")
    for key in (
        "hanjiang_xiangyun_area",
        "hanjiang_xiangyun_area_name",
        "hanjiang_xiangyun_area_adj",
        "jingyi_shinan_area",
        "jingyi_shinan_area_name",
        "jingyi_shinan_area_adj",
        "dean_qihuang_area",
        "dean_qihuang_area_name",
        "dean_qihuang_area_adj",
        "wuhan_enan_area",
        "wuhan_enan_area_name",
        "wuhan_enan_area_adj",
    ):
        if not re.search(rf"(?m)^\s*{key}:0\s+\"", hubei_source):
            raise ValueError(f"Hubei localisation source lacks {key}")
    hubei_encoded = mod_root / "localisation/gdd_b10_hubei_map_l_english.yml"
    if (
        not hubei_encoded.is_file()
        or not hubei_encoded.read_bytes().startswith(b"\xef\xbb\xbf")
    ):
        raise ValueError("Encoded Hubei localisation is missing or lacks a BOM")
    jiangsu_source = (
        mod_root / "localisation_source/gdd_b11_jiangsu_map_readable_utf8.txt"
    ).read_text(encoding="utf-8-sig")
    for province_id in JIANGSU_ALL_IDS:
        for key in (f"PROV{province_id}", f"PROV_ADJ{province_id}"):
            if not re.search(rf"(?m)^\s*{key}:0\s+\"", jiangsu_source):
                raise ValueError(f"Jiangsu localisation source lacks {key}")
    for key in (
        "xuhuai_haizhou_area", "xuhuai_haizhou_area_name",
        "xuhuai_haizhou_area_adj", "huaiyang_tongtai_area",
        "huaiyang_tongtai_area_name", "huaiyang_tongtai_area_adj",
        "jinling_wuhui_area", "jinling_wuhui_area_name",
        "jinling_wuhui_area_adj",
    ):
        if not re.search(rf"(?m)^\s*{key}:0\s+\"", jiangsu_source):
            raise ValueError(f"Jiangsu localisation source lacks {key}")
    jiangsu_encoded = mod_root / "localisation/gdd_b11_jiangsu_map_l_english.yml"
    if (
        not jiangsu_encoded.is_file()
        or not jiangsu_encoded.read_bytes().startswith(b"\xef\xbb\xbf")
    ):
        raise ValueError("Encoded Jiangsu localisation is missing or lacks a BOM")

    huai_source = (
        mod_root / "localisation_source/gdd_huai_navigation_readable_utf8.txt"
    ).read_text(encoding="utf-8-sig")
    for province_id in (1896,) + HUAI_SEA_IDS:
        for key in (f"PROV{province_id}", f"PROV_ADJ{province_id}"):
            if not re.search(rf"(?m)^\s*{key}:0\s+\"", huai_source):
                raise ValueError(f"Huai localisation source lacks {key}")
    for key in (
        "huai_river_area", "huai_river_area_name",
        "huai_river_area_adj", "huai_river_engagement",
    ):
        if not re.search(rf"(?m)^\s*{key}:0\s+\"", huai_source):
            raise ValueError(f"Huai localisation source lacks {key}")
    huai_encoded = mod_root / "localisation/gdd_huai_navigation_l_english.yml"
    if (
        not huai_encoded.is_file()
        or not huai_encoded.read_bytes().startswith(b"\xef\xbb\xbf")
    ):
        raise ValueError("Encoded Huai localisation is missing or lacks a BOM")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, required=True)
    parser.add_argument("--mod-root", type=Path, default=DEFAULT_MOD_ROOT)
    parser.add_argument("--build-report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=DEFAULT_VALIDATION_REPORT)
    args = parser.parse_args()

    vanilla_root = args.vanilla_root.expanduser().resolve()
    mod_root = args.mod_root.expanduser().resolve()
    config = json.loads(args.config.read_text(encoding="utf-8"))

    generated_text_files = [
        mod_root / "map/default.map",
        mod_root / "map/positions.txt",
        mod_root / "map/adjacencies.csv",
        mod_root / "map/trade_winds.txt",
        mod_root / "map/area.txt",
        mod_root / "map/terrain.txt",
        mod_root / "map/region.txt",
        mod_root / "map/continent.txt",
        mod_root / "map/climate.txt",
        mod_root / "common/tradenodes/00_tradenodes.txt",
        mod_root / "common/trade_companies/00_trade_companies.txt",
    ]
    for path in generated_text_files:
        validate_braces(path)

    map_report = validate_map(vanilla_root, mod_root, config)
    validate_memberships(vanilla_root, mod_root)
    development = validate_histories(mod_root)
    validate_taiwan_mountain_history(mod_root)
    prepared_development = validate_prepared_histories(vanilla_root, mod_root)
    jiangxi_development = validate_jiangxi_histories(mod_root)
    hunan_development = validate_hunan_histories(mod_root)
    zhejiang_development = validate_zhejiang_histories(mod_root)
    hubei_development = validate_hubei_histories(mod_root)
    jiangsu_development = validate_jiangsu_histories(mod_root)
    validate_locked_guangzhou_assets(vanilla_root, mod_root)
    validate_localisation(mod_root)

    for province_id in (1896,) + HUAI_SEA_IDS:
        water_history = history_path(mod_root, province_id).read_text(
            encoding="cp1252"
        )
        if "name = huai_river_engagement" not in water_history:
            raise ValueError(
                f"history/provinces: Huai water {province_id} lacks engagement modifier"
            )

    trade_winds = (mod_root / "map/trade_winds.txt").read_text(encoding="cp1252")
    for province_id in YANGTZE_SEA_IDS + HUAI_SEA_IDS:
        if len(re.findall(rf"(?m)^\s*{province_id}\s*=", trade_winds)) != 1:
            raise ValueError(f"trade_winds.txt: missing navigable water {province_id}")

    build_report = json.loads(args.build_report.read_text(encoding="utf-8"))
    if build_report.get("status") != (
        "B01_P02_B03_B06_B07_B09_B10_B11_YANGTZE_HUAI_ASSETS_PREPARED"
    ):
        raise ValueError("B01 through B11 and navigable-river build is not successful")
    if build_report.get("canonical_geometry_preserved") is not True:
        raise ValueError("Build report does not confirm preservation of manual geometry")
    for relative_path, metadata in build_report["outputs"].items():
        path = mod_root / relative_path
        if sha256_file(path) != metadata["sha256"]:
            raise ValueError(f"{relative_path}: hash differs from the build report")

    result = {
        "status": (
            "B01_P02_B03_B06_B07_B09_B10_B11_"
            "YANGTZE_HUAI_STATIC_VALIDATION_PASS"
        ),
        "implemented_ids": list(IMPLEMENTED_IDS),
        "prepared_ids": list(PREPARED_IDS),
        "geometry_status": {
            "B01": "hand_drawn_validated",
            "P02": "hand_drawn_validated",
            "B03_Wangji": "hand_drawn_validated",
            "B08_Taiwan": "central_mountain_and_coastal_ring_validated",
            "B06_Zhejiang": "hand_drawn_validated",
            "B07_Jiangxi": "hand_drawn_validated",
            "B07_Hunan": "hand_drawn_validated",
            "B09_Chongqing": "hand_drawn_validated",
            "B10_Hubei": "hand_drawn_validated",
            "B11_Jiangsu": "hand_drawn_validated",
            "B12_Yangtze": "navigable_waterway_validated",
            "B13_Huai": "workshop_geometry_navigable_waterway_validated",
        },
        "max_provinces": GAME_MAX_PROVINCES,
        "map": map_report,
        "development": {
            str(province_id): list(values)
            for province_id, values in {
                **development,
                **prepared_development,
                **jiangxi_development,
                **hunan_development,
                **zhejiang_development,
                **hubei_development,
                **jiangsu_development,
            }.items()
        },
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    print(
        f"{args.report}: "
        "B01_P02_B03_B06_B07_B09_B10_B11_"
        "YANGTZE_HUAI_STATIC_VALIDATION_PASS"
    )


if __name__ == "__main__":
    main()
