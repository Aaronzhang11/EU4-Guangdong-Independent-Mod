"""Build companion assets for the hand-drawn B01 Guangdong map.

``map/provinces.bmp`` is the canonical, user-authored geometry.  This script
audits that bitmap and writes the coupled Clausewitz text assets, but it never
generates, copies, or overwrites province pixels.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MOD_ROOT = REPO_ROOT / "guangdong_independent_practice"
DEFAULT_REGISTRY = REPO_ROOT / "docs/map/china_province_split_registry.csv"
DEFAULT_CONFIG = Path(__file__).with_name("b01_guangdong_manual.json")
DEFAULT_REPORT = REPO_ROOT / "docs/map/previews/B01_mod_build_report.json"

IMPLEMENTED_IDS = tuple(range(4942, 4950))
PREPARED_DESIGN_KEYS = (
    "S-04",
    "S-05",
    "S-11",
    "S-12",
    "S-17",
    "S-18",
    "S-23",
    "S-24",
    "S-25",
    "S-26",
    "S-27",
    "S-28",
)
PREPARED_IDS = tuple(range(4950, 4962))
ACTIVE_IDS = IMPLEMENTED_IDS + PREPARED_IDS
GAME_MAX_PROVINCES = 4962
NEW_DEFINITION_NAMES = {
    4942: "Foshan",
    4943: "Dongguan",
    4944: "Meizhou",
    4945: "Gaozhou",
    4946: "Hong Kong",
    4947: "Luoding",
    4948: "Nanxiong",
    4949: "Lufeng",
    4950: "Huzhou",
    4951: "Taizhou",
    4952: "Putian",
    4953: "Zhangzhou",
    4954: "Xunzhou",
    4955: "Zhuluo",
    4956: "Quzhou",
    4957: "Shaowu",
    4958: "Xiamen",
    4959: "Qingyuan",
    4960: "Taiping",
    4961: "Kavalan",
}

# Positions use Clausewitz coordinates, whose vertical axis is the inverse of
# provinces.bmp.  Each tuple contains city, unit, text, port, two auxiliary
# points, and the unused seventh point.
POSITION_DATA = {
    664: {
        "comment": "Lingyun - positioned from painted Guangxi geometry",
        "positions": (
            4472, 1032, 4475, 1038, 4468, 1046, 4472, 1032,
            4471, 1036, 4476, 1033, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    738: {
        "comment": "Sakam - adjusted after Zhuluo split",
        "positions": (
            4690, 1013, 4691, 1013, 4691, 1010, 4687, 1013,
            4690, 1011, 4692, 1012, 0, 0,
        ),
        "rotation": (0, 0, 0, 1.745, 0, 0, 0),
    },
    2155: {
        "comment": "Middag - port adjusted after Taiwan split",
        "positions": (
            4696, 1034, 4693, 1034, 4696, 1034, 4684, 1042,
            4696, 1034, 4694, 1034, 4696, 1034,
        ),
        "rotation": (0, 0, 0, 2.356, 0, 0, 0),
    },
    1840: {
        "comment": "Guilin - positioned from painted Guangxi geometry",
        "positions": (
            4531, 1053, 4538, 1049, 4543, 1048, 4531, 1053,
            4537, 1053, 4534, 1049, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2162: {
        "comment": "Ngchow - positioned from painted Guangxi geometry",
        "positions": (
            4536, 1025, 4534, 1023, 4538, 1029, 4536, 1025,
            4530, 1020, 4542, 1024, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2163: {
        "comment": "Liuzhou - positioned from painted Guangxi geometry",
        "positions": (
            4512, 1044, 4515, 1051, 4519, 1058, 4512, 1044,
            4514, 1040, 4515, 1055, 0, 0,
        ),
        "rotation": (3.142, 0, 0, 0, 0, 0, 0),
    },
    2164: {
        "comment": "Namning - positioned from painted Guangxi geometry",
        "positions": (
            4493, 1023, 4496, 1031, 4503, 1027, 4493, 1023,
            4492, 1027, 4495, 1035, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    665: {
        "comment": "Shiuhing",
        "positions": (
            4556, 1012, 4559, 1019, 4554, 1011, 4555.5, 1001.5,
            4558, 1013, 4552, 1010, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    667: {
        "comment": "Canton",
        "positions": (
            4575, 1022, 4575, 1026, 4581, 1034, 4578, 1021,
            4584, 1035, 4579, 1029, 0, 0,
        ),
        "rotation": (0, 0, 0, -0.262, 0, 0, 0),
    },
    2157: {
        "comment": "Waichow",
        "positions": (
            4602, 1041, 4606, 1039, 4601, 1045, 4597, 1019,
            4604, 1035, 4598, 1039, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2158: {
        "comment": "Shiukwan",
        "positions": (
            4578.5, 1051, 4572, 1050, 4576, 1052, 4565, 1051,
            4576, 1052, 4581, 1048, 4576, 1052,
        ),
        "rotation": (1.571, 0, 0, 0, 0, 0, 0),
    },
    2159: {
        "comment": "Leichow",
        "positions": (
            4522, 988, 4524, 993, 4523, 985, 4529.5, 978,
            4522, 991, 4526, 981, 4532, 998,
        ),
        "rotation": (0, 0, 0, -0.785, 0, 0, 0),
    },
    4942: {
        "comment": "Foshan",
        "positions": (
            4571, 1027, 4570, 1024, 4571, 1024, 4571, 1009,
            4572, 1021, 4572, 1024, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4943: {
        "comment": "Dongguan",
        "positions": (
            4585, 1019, 4587, 1018, 4586, 1021, 4594, 1018,
            4583, 1018, 4589, 1017, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4944: {
        "comment": "Meizhou",
        "positions": (
            4618, 1051, 4615, 1054, 4619, 1048, 4618, 1051,
            4620, 1045, 4615, 1050, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4945: {
        "comment": "Gaozhou",
        "positions": (
            4540, 1011, 4541, 1004, 4539, 1008, 4541, 997,
            4539, 1014, 4544, 1003, 0, 0,
        ),
        "rotation": (0, 0, 0, -0.785, 0, 0, 0),
    },
    4946: {
        "comment": "Hong Kong",
        "positions": (
            4587, 1013, 4585, 1012, 4589, 1012, 4589, 1014,
            4586, 1015, 4588, 1010, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4947: {
        "comment": "Luoding",
        "positions": (
            4552, 1026, 4551, 1028, 4554, 1025, 4552, 1023,
            4552, 1030, 4550, 1022, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4948: {
        "comment": "Nanxiong",
        "positions": (
            4586, 1058, 4587, 1056, 4585, 1060, 4583, 1058,
            4591, 1060, 4586, 1054, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4949: {
        "comment": "Lufeng",
        "positions": (
            4610, 1025, 4608, 1024, 4613, 1024, 4611, 1021,
            4611, 1027, 4607, 1022, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4950: {
        "comment": "Huzhou - provisional anchor until hand drawing",
        "positions": (
            4669, 1157, 4670, 1157, 4668, 1158, 4669, 1157,
            4668, 1156, 4670, 1158, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4951: {
        "comment": "Taizhou - provisional anchor until hand drawing",
        "positions": (
            4693, 1125, 4692, 1125, 4694, 1126, 4702, 1129,
            4693, 1124, 4694, 1125, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4952: {
        "comment": "Putian - provisional anchor until hand drawing",
        "positions": (
            4659, 1062, 4658, 1062, 4660, 1063, 4662, 1062,
            4659, 1061, 4660, 1062, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4953: {
        "comment": "Zhangzhou - provisional anchor until hand drawing",
        "positions": (
            4638, 1038, 4637, 1038, 4639, 1039, 4638, 1037,
            4638, 1039, 4639, 1038, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4954: {
        "comment": "Xunzhou - positioned from painted province geometry",
        "positions": (
            4527, 1034, 4525, 1029, 4521, 1025, 4527, 1034,
            4530, 1031, 4523, 1034, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4955: {
        "comment": "Zhuluo - positioned from painted province geometry",
        "positions": (
            4688, 1020, 4687, 1021, 4686, 1022, 4681, 1020,
            4686, 1023, 4685, 1022, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4956: {
        "comment": "Quzhou - provisional anchor until hand drawing",
        "positions": (
            4658, 1120, 4657, 1120, 4659, 1121, 4658, 1120,
            4658, 1119, 4659, 1120, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4957: {
        "comment": "Shaowu - provisional anchor until hand drawing",
        "positions": (
            4638, 1095, 4637, 1095, 4639, 1096, 4638, 1095,
            4638, 1094, 4639, 1095, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4958: {
        "comment": "Xiamen - positioned from painted province geometry",
        "positions": (
            4647, 1051, 4646, 1051, 4647, 1050, 4649, 1051,
            4646, 1052, 4648, 1051, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4959: {
        "comment": "Qingyuan - positioned from painted province geometry",
        "positions": (
            4495, 1053, 4491, 1052, 4484, 1052, 4495, 1053,
            4487, 1055, 4499, 1052, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4960: {
        "comment": "Taiping - positioned from painted province geometry",
        "positions": (
            4480, 1015, 4479, 1013, 4483, 1021, 4480, 1015,
            4481, 1017, 4475, 1014, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4961: {
        "comment": "Kavalan - positioned from painted province geometry",
        "positions": (
            4707, 1055, 4706, 1055, 4707, 1054, 4708, 1055,
            4706, 1054, 4707, 1055, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one exact match, found {count}")
    return text.replace(old, new, 1)


def find_named_block(text: str, name: str, start: int = 0) -> tuple[int, int]:
    pattern = re.compile(rf"(?m)^[ \t]*{re.escape(name)}[ \t]*=[ \t]*\{{")
    match = pattern.search(text, start)
    if not match:
        raise ValueError(f"Could not find block {name!r}")
    opening = text.find("{", match.start(), match.end())
    depth = 0
    in_string = False
    in_comment = False
    escaped = False
    index = opening
    while index < len(text):
        character = text[index]
        if in_comment:
            if character == "\n":
                in_comment = False
            index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == "#":
            in_comment = True
        elif character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return match.start(), index + 1
        index += 1
    raise ValueError(f"Unclosed block {name!r}")


def replace_named_block(text: str, name: str, replacement: str) -> str:
    start, end = find_named_block(text, name)
    return text[:start] + replacement + text[end:]


def append_to_named_block(text: str, name: str, line: str) -> str:
    start, end = find_named_block(text, name)
    block = text[start:end]
    closing = block.rfind("}")
    if closing < 0:
        raise ValueError(f"{name}: missing closing brace")
    block = block[:closing].rstrip() + "\n" + line.rstrip() + "\n" + block[closing:]
    return text[:start] + block + text[end:]


def modify_nested_block(
    text: str,
    outer_name: str,
    modifier: Callable[[str], str],
) -> str:
    start, end = find_named_block(text, outer_name)
    block = text[start:end]
    modified = modifier(block)
    if modified == block:
        raise ValueError(f"{outer_name}: nested modifier made no change")
    return text[:start] + modified + text[end:]


def read_text(path: Path) -> str:
    return path.read_text(encoding="cp1252")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [line.expandtabs(4).rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    path.write_text("\n".join(lines) + "\n", encoding="cp1252", newline="\n")


def load_active_registry(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [
            row for row in csv.DictReader(handle)
            if row["draw_batch"] == "B01"
            or row["design_key"] in PREPARED_DESIGN_KEYS
        ]
    rows.sort(key=lambda row: int(row["game_id"]))
    ids = tuple(int(row["game_id"]) for row in rows)
    if ids != ACTIVE_IDS:
        raise ValueError(f"Active registry IDs must be {ACTIVE_IDS}, found {ids}")
    return rows


def load_definition_colors(
    path: Path,
) -> tuple[dict[tuple[int, int, int], int], set[int]]:
    colors: dict[tuple[int, int, int], int] = {}
    ids: set[int] = set()
    with path.open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if not row or not row[0].isdigit():
                continue
            province_id = int(row[0])
            color = (int(row[1]), int(row[2]), int(row[3]))
            colors[color] = province_id
            ids.add(province_id)
    return colors, ids


def validate_classic_bmp_header(path: Path) -> None:
    header = path.read_bytes()[:54]
    if len(header) < 54 or header[:2] != b"BM":
        raise ValueError("provinces.bmp is not a Windows BMP")
    pixel_offset = struct.unpack_from("<I", header, 10)[0]
    dib_size = struct.unpack_from("<I", header, 14)[0]
    planes = struct.unpack_from("<H", header, 26)[0]
    bits_per_pixel = struct.unpack_from("<H", header, 28)[0]
    compression = struct.unpack_from("<I", header, 30)[0]
    actual_size = path.stat().st_size
    declared_size = struct.unpack_from("<I", header, 2)[0]
    if (
        pixel_offset != 54
        or dib_size != 40
        or planes != 1
        or bits_per_pixel != 24
        or compression != 0
        or declared_size != actual_size
    ):
        raise ValueError(
            "provinces.bmp must use the classic 40-byte, 24-bit, "
            "uncompressed BI_RGB header"
        )


def audit_manual_geometry(
    vanilla_root: Path,
    provinces_path: Path,
    registry_rows: list[dict[str, str]],
    config: dict[str, object],
) -> dict[str, object]:
    if config.get("source_policy") != "hand_drawn_canonical_bmp":
        raise ValueError("Manual map config has an unexpected source policy")
    configured = (REPO_ROOT / str(config["canonical_bmp"])).resolve()
    if provinces_path.resolve() != configured:
        raise ValueError(
            f"Canonical hand-drawn bitmap must be {configured}, found {provinces_path}"
        )

    baseline_verified: dict[str, bool] = {}
    for filename, expected_hash in config["baseline_file_sha256"].items():
        path = vanilla_root / "map" / filename
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise ValueError(
                f"EU4 baseline {filename} hash {actual_hash} does not match "
                f"the locked {config['baseline_version']} baseline"
            )
        baseline_verified[filename] = True

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

    changed_mask = np.any(province_map != baseline_map, axis=2)
    changed_pixels = int(changed_mask.sum())
    expected_changed = int(config["expected_changed_pixels"])
    if changed_pixels != expected_changed:
        raise ValueError(
            f"Hand-drawn map has {changed_pixels} pixels changed from vanilla; "
            f"the reviewed geometry expects {expected_changed}"
        )

    vanilla_colors, _vanilla_ids = load_definition_colors(
        vanilla_root / "map/definition.csv"
    )
    allowed_sources = {int(value) for value in config["allowed_vanilla_source_ids"]}
    actual_sources = {
        vanilla_colors[tuple(int(channel) for channel in color)]
        for color in np.unique(baseline_map[changed_mask].reshape(-1, 3), axis=0)
    }
    if not actual_sources <= allowed_sources:
        raise ValueError(
            "Hand-drawn changes escaped the reviewed Guangdong source provinces: "
            f"{sorted(actual_sources - allowed_sources)}"
        )

    defined_colors = set(vanilla_colors)
    for row in registry_rows:
        defined_colors.add(
            (int(row["rgb_r"]), int(row["rgb_g"]), int(row["rgb_b"]))
        )
    unknown_colors = [
        tuple(int(channel) for channel in color)
        for color in np.unique(province_map.reshape(-1, 3), axis=0)
        if tuple(int(channel) for channel in color) not in defined_colors
    ]
    if unknown_colors:
        raise ValueError(
            f"provinces.bmp contains colors absent from definition data: "
            f"{unknown_colors[:10]}"
        )

    pixel_counts: dict[str, int] = {}
    for province in config["provinces"]:
        color = np.array(province["rgb"], dtype=np.uint8)
        count = int(np.all(province_map == color, axis=2).sum())
        expected = int(province["expected_pixels"])
        if count != expected:
            raise ValueError(
                f"{province['game_id']} has {count} pixels; expected {expected}"
            )
        pixel_counts[str(province["game_id"])] = count

    return {
        "baseline_version": config["baseline_version"],
        "baseline_verified_by_sha256": baseline_verified,
        "source_policy": config["source_policy"],
        "changed_pixels": changed_pixels,
        "province_pixels": pixel_counts,
        "provinces_sha256": sha256_file(provinces_path),
    }


def build_definition(
    vanilla_root: Path,
    output: Path,
    registry_rows: list[dict[str, str]],
) -> None:
    source = read_text(vanilla_root / "map/definition.csv").rstrip("\r\n")
    _colors, existing_ids = load_definition_colors(
        vanilla_root / "map/definition.csv"
    )
    if existing_ids & set(ACTIVE_IDS):
        raise ValueError("Vanilla definition unexpectedly contains an active mod ID")
    additions = [
        f"{row['game_id']};{row['rgb_r']};{row['rgb_g']};{row['rgb_b']};"
        f"{NEW_DEFINITION_NAMES[int(row['game_id'])]};x"
        for row in registry_rows
    ]
    write_text(output, source + "\n" + "\n".join(additions) + "\n")


def build_default_map(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/default.map")
    text, count = re.subn(
        r"(?m)^max_provinces\s*=\s*\d+\s*$",
        f"max_provinces = {GAME_MAX_PROVINCES}",
        text,
    )
    if count != 1:
        raise ValueError(f"default.map: expected one max_provinces, found {count}")
    write_text(output, text)


def build_area(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/area.txt")
    pearl_and_east = """pearl_river_delta_area = { #5
\t667 668 4942 4943 4946
}

guangdong_area = { #6
\t2156 2157 2158 4944 4948 4949
}"""
    text = replace_named_block(text, "guangdong_area", pearl_and_east)
    text = replace_named_block(
        text,
        "west_guangdong_area",
        """west_guangdong_area = { #7
\t665 666 2159 2160 2161 4945 4947
}""",
    )
    text = replace_named_block(
        text,
        "zhejiang_area",
        """zhejiang_area = { #8
\t684 1824 2148 2149 2150 4950 4951 4956
}""",
    )
    text = replace_named_block(
        text,
        "fujian_area",
        """fujian_area = { #5 (East Fujian)
\t669 1829 4952 4953 4958
}

west_fujian_area = { #3
\t2152 2153 4957
}""",
    )
    text = replace_named_block(
        text,
        "taiwan_area",
        """taiwan_area = { #5
\t738 2154 2155 4955 4961
}""",
    )
    text = replace_named_block(
        text,
        "guangxi_area",
        """guangxi_area = { #4 (Zuojiang)
\t2162 2164 4954 4960
}

youjiang_area = { #4
\t664 1840 2163 4959
}""",
    )
    write_text(output, text)


def build_region(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/region.txt")

    def add_area(block: str) -> str:
        block = replace_once(
            block,
            "\t\tguangdong_area\n",
            "\t\tpearl_river_delta_area\n\t\tguangdong_area\n",
            "south_china_region areas",
        )
        block = replace_once(
            block,
            "\t\tfujian_area\n",
            "\t\tfujian_area\n\t\twest_fujian_area\n",
            "south_china_region Fujian areas",
        )
        return replace_once(
            block,
            "\t\tguangxi_area\n",
            "\t\tguangxi_area\n\t\tyoujiang_area\n",
            "south_china_region Guangxi areas",
        )

    write_text(
        output,
        modify_nested_block(text, "south_china_region", add_area),
    )


def build_continent(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/continent.txt")
    text = append_to_named_block(
        text,
        "asia",
        "\t4942 4943 4944 4945 4946 4947 4948 4949 # B01 Guangdong",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t4950 4951 4952 4953 4954 4955 4956 4957 4958 4959 4960 4961"
        " # P02 Southeast prepared",
    )
    write_text(output, text)


def build_climate(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/climate.txt")
    text = append_to_named_block(
        text,
        "tropical",
        "\t4945 # B01 Gaozhou inherits the Leichow tropical climate",
    )
    text = append_to_named_block(
        text,
        "tropical",
        "\t4954 4955 4960 4961 # P02 southern subtropical frontier",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4942 4943 4944 4945 4946 4947 4948 4949 # B01 Guangdong",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4950 4951 4952 4953 4955 4956 4957 4958 4960 4961"
        " # P02 monsoon provinces",
    )
    write_text(output, text)


def build_terrain(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/terrain.txt")
    text = replace_once(
        text,
        "\t\t\t665 667 2156 2157 2159 2163 700",
        "\t\t\t665 667 2156 2157 2159 2163 700 4942 4943 4950 4954",
        "farmlands terrain override",
    )
    text = replace_once(
        text,
        "\t\t\t2146 2147 2152 2153 2158 2171 2173 2174 ",
        "\t\t\t2146 2147 2152 2153 2158 2171 2173 2174 "
        "4944 4945 4946 4947 4948 4949 4951 4952 4953 "
        "4956 4957 4958 4960 4961 ",
        "hills terrain override",
    )
    text = modify_nested_block(
        text,
        "grasslands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t4955 # P02 Zhuluo western plain",
        ),
    )
    text = modify_nested_block(
        text,
        "highlands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t4959 # P02 Qingyuan karst frontier",
        ),
    )
    write_text(output, text)


def format_position_block(province_id: int, *, include_comment: bool = True) -> str:
    data = POSITION_DATA[province_id]
    positions = " ".join(f"{float(value):.3f}" for value in data["positions"])
    rotations = " ".join(f"{float(value):.3f}" for value in data["rotation"])
    heights = "0.000 0.000 1.000 0.000 0.000 0.000 0.000"
    comment = f"#{data['comment']}\n" if include_comment else ""
    return f"""{comment}{province_id}={{
\tposition={{
\t\t{positions}
\t}}
\trotation={{
\t\t{rotations}
\t}}
\theight={{
\t\t{heights}
\t}}
}}"""


def build_positions(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/positions.txt")
    for province_id in (
        664, 665, 667, 738, 1840, 2155, 2157, 2158, 2159,
        2162, 2163, 2164,
    ):
        text = replace_named_block(
            text,
            str(province_id),
            format_position_block(province_id, include_comment=False),
        )
    text = text.rstrip() + "\n\n"
    text += "\n\n".join(
        format_position_block(province_id) for province_id in ACTIVE_IDS
    )
    write_text(output, text + "\n")


def append_members_to_outer_block(
    text: str,
    outer_name: str,
    member_ids: tuple[int, ...],
    comment: str,
) -> str:
    def modify_outer(block: str) -> str:
        member_start, member_end = find_named_block(block, "members")
        members = block[member_start:member_end]
        closing = members.rfind("}")
        insertion = (
            "\n\t\t"
            + " ".join(str(value) for value in member_ids)
            + f" # {comment}\n\t"
        )
        members = members[:closing].rstrip() + insertion + members[closing:]
        return block[:member_start] + members + block[member_end:]

    return modify_nested_block(text, outer_name, modify_outer)


def build_trade_nodes(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "common/tradenodes/00_tradenodes.txt")
    text = append_members_to_outer_block(
        text,
        "hangzhou",
        (4950, 4951, 4952, 4953, 4956, 4957, 4958),
        "P02 Zhejiang and Fujian",
    )
    text = append_members_to_outer_block(
        text,
        "canton",
        IMPLEMENTED_IDS + (4954, 4955, 4959, 4960, 4961),
        "B01 Guangdong and P02 Guangxi/Taiwan",
    )
    write_text(
        output,
        text,
    )


def build_trade_companies(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "common/trade_companies/00_trade_companies.txt")

    def add_company_provinces(
        block: str,
        province_ids: tuple[int, ...],
        comment: str,
    ) -> str:
        start, end = find_named_block(block, "provinces")
        provinces = block[start:end]
        closing = provinces.rfind("}")
        insertion = (
            "\n\t\t"
            + " ".join(str(value) for value in province_ids)
            + f" # {comment}\n\t"
        )
        provinces = provinces[:closing].rstrip() + insertion + provinces[closing:]
        return block[:start] + provinces + block[end:]

    text = modify_nested_block(
        text,
        "trade_company_south_china",
        lambda block: add_company_provinces(
            block,
            IMPLEMENTED_IDS + (4954, 4955, 4959, 4960, 4961),
            "B01 Guangdong and P02 Guangxi/Taiwan",
        ),
    )
    text = modify_nested_block(
        text,
        "trade_company_east_china",
        lambda block: add_company_provinces(
            block,
            (4950, 4951, 4952, 4953, 4956, 4957, 4958),
            "P02 Zhejiang and Fujian",
        ),
    )
    write_text(output, text)


def write_report(
    report_path: Path,
    mod_root: Path,
    geometry_report: dict[str, object],
    outputs: list[Path],
) -> None:
    report = {
        "status": "B01_FORMAL_AND_P02_ASSETS_PREPARED",
        "scope": "B01 Guangdong formal geometry plus P02 pre-drawing assets",
        "baseline_version": geometry_report["baseline_version"],
        "baseline_verified_by_sha256": geometry_report[
            "baseline_verified_by_sha256"
        ],
        "baseline_source": "EU4_INSTALL_ROOT",
        "geometry_source": geometry_report["source_policy"],
        "canonical_geometry_preserved": True,
        "mod_root": mod_root.name,
        "implemented_ids": list(IMPLEMENTED_IDS),
        "prepared_ids": list(PREPARED_IDS),
        "max_provinces": GAME_MAX_PROVINCES,
        "changed_pixels": geometry_report["changed_pixels"],
        "province_pixels": geometry_report["province_pixels"],
        "outputs": {
            str(path.relative_to(mod_root)): {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in outputs
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, required=True)
    parser.add_argument("--mod-root", type=Path, default=DEFAULT_MOD_ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    vanilla_root = args.vanilla_root.expanduser().resolve()
    mod_root = args.mod_root.expanduser().resolve()
    if not (mod_root / "descriptor.mod").is_file():
        raise ValueError(f"Not an EU4 mod root: {mod_root}")

    registry_rows = load_active_registry(args.registry)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    provinces_output = mod_root / "map/provinces.bmp"
    geometry_report = audit_manual_geometry(
        vanilla_root,
        provinces_output,
        registry_rows,
        config,
    )

    builders = [
        (build_definition, mod_root / "map/definition.csv"),
        (build_default_map, mod_root / "map/default.map"),
        (build_area, mod_root / "map/area.txt"),
        (build_region, mod_root / "map/region.txt"),
        (build_continent, mod_root / "map/continent.txt"),
        (build_climate, mod_root / "map/climate.txt"),
        (build_terrain, mod_root / "map/terrain.txt"),
        (build_positions, mod_root / "map/positions.txt"),
        (
            build_trade_nodes,
            mod_root / "common/tradenodes/00_tradenodes.txt",
        ),
        (
            build_trade_companies,
            mod_root / "common/trade_companies/00_trade_companies.txt",
        ),
    ]
    outputs = [provinces_output]
    for builder, output in builders:
        if builder is build_definition:
            builder(vanilla_root, output, registry_rows)
        else:
            builder(vanilla_root, output)
        outputs.append(output)

    write_report(
        report_path=args.report,
        mod_root=mod_root,
        geometry_report=geometry_report,
        outputs=outputs,
    )
    print(f"{provinces_output}: canonical hand-drawn geometry preserved")
    print(f"{mod_root}: active assets written for IDs 4942-4961")
    print(f"{args.report}: B01_FORMAL_AND_P02_ASSETS_PREPARED")


if __name__ == "__main__":
    main()
