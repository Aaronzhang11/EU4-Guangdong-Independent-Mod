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
    DEFAULT_CONFIG,
    DEFAULT_MOD_ROOT,
    DEFAULT_REPORT,
    GAME_MAX_PROVINCES,
    IMPLEMENTED_IDS,
    find_named_block,
    validate_classic_bmp_header,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VALIDATION_REPORT = (
    REPO_ROOT / "docs/map/previews/B01_mod_validation_report.json"
)
EXPECTED_AREAS = {
    4942: "pearl_river_delta_area",
    4943: "pearl_river_delta_area",
    4944: "guangdong_area",
    4945: "west_guangdong_area",
    4946: "pearl_river_delta_area",
    4947: "west_guangdong_area",
    4948: "guangdong_area",
    4949: "guangdong_area",
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
                province_id in IMPLEMENTED_IDS or colors[color] in IMPLEMENTED_IDS
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
    if configured_ids != IMPLEMENTED_IDS:
        raise ValueError(
            f"Manual config IDs must be {IMPLEMENTED_IDS}, found {configured_ids}"
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
    if exposed_new_ids != IMPLEMENTED_IDS:
        raise ValueError(
            f"definition.csv exposes {exposed_new_ids}; expected {IMPLEMENTED_IDS}"
        )

    default_map = (map_dir / "default.map").read_text(encoding="cp1252")
    max_match = re.search(r"(?m)^max_provinces\s*=\s*(\d+)", default_map)
    if not max_match or int(max_match.group(1)) != GAME_MAX_PROVINCES:
        raise ValueError(f"default.map: max_provinces must be {GAME_MAX_PROVINCES}")
    sea_ids = read_sea_ids(default_map)

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

    return {
        "changed_pixels": changed_pixels,
        "province_stats": province_stats,
        "provinces_sha256": sha256_file(provinces_path),
    }


def validate_memberships(vanilla_root: Path, mod_root: Path) -> None:
    area_text = (mod_root / "map/area.txt").read_text(encoding="cp1252")
    for province_id, area_name in EXPECTED_AREAS.items():
        assert_token_once(area_text, province_id, "area.txt")
        if province_id not in numeric_tokens(block_text(area_text, area_name)):
            raise ValueError(f"area.txt: {province_id} is not in {area_name}")

    region_text = (mod_root / "map/region.txt").read_text(encoding="cp1252")
    south_china = block_text(region_text, "south_china_region")
    for area_name in {
        "pearl_river_delta_area",
        "guangdong_area",
        "west_guangdong_area",
    }:
        if not re.search(rf"\b{re.escape(area_name)}\b", south_china):
            raise ValueError(f"region.txt: south_china_region lacks {area_name}")

    superregion_text = (vanilla_root / "map/superregion.txt").read_text(
        encoding="cp1252"
    )
    china = block_text(superregion_text, "china_superregion")
    if not re.search(r"\bsouth_china_region\b", china):
        raise ValueError("superregion.txt: China lacks south_china_region")

    continent_text = (mod_root / "map/continent.txt").read_text(encoding="cp1252")
    asia = block_text(continent_text, "asia")
    for province_id in IMPLEMENTED_IDS:
        assert_token_once(continent_text, province_id, "continent.txt")
        if province_id not in numeric_tokens(asia):
            raise ValueError(f"continent.txt: {province_id} is not in Asia")

    climate_text = (mod_root / "map/climate.txt").read_text(encoding="cp1252")
    normal_monsoon = set(numeric_tokens(block_text(climate_text, "normal_monsoon")))
    tropical = set(numeric_tokens(block_text(climate_text, "tropical")))
    for province_id in IMPLEMENTED_IDS:
        if province_id not in normal_monsoon:
            raise ValueError(f"climate.txt: {province_id} lacks normal_monsoon")
    if 4945 not in tropical:
        raise ValueError("climate.txt: Gaozhou must inherit tropical")
    if tropical & (set(IMPLEMENTED_IDS) - {4945}):
        raise ValueError("climate.txt: an unintended B01 province is tropical")

    terrain_text = (mod_root / "map/terrain.txt").read_text(encoding="cp1252")
    for province_id, terrain_name in EXPECTED_TERRAIN.items():
        assert_token_once(terrain_text, province_id, "terrain.txt")
        if province_id not in numeric_tokens(block_text(terrain_text, terrain_name)):
            raise ValueError(
                f"terrain.txt: {province_id} is not overridden to {terrain_name}"
            )

    trade_nodes = (
        mod_root / "common/tradenodes/00_tradenodes.txt"
    ).read_text(encoding="cp1252")
    canton = block_text(trade_nodes, "canton")
    canton_members = set(numeric_tokens(block_text(canton, "members")))
    for province_id in IMPLEMENTED_IDS:
        assert_token_once(trade_nodes, province_id, "00_tradenodes.txt")
        if province_id not in canton_members:
            raise ValueError(f"Canton trade node lacks {province_id}")

    companies = (
        mod_root / "common/trade_companies/00_trade_companies.txt"
    ).read_text(encoding="cp1252")
    south_china = block_text(companies, "trade_company_south_china")
    company_provinces = set(numeric_tokens(block_text(south_china, "provinces")))
    for province_id in IMPLEMENTED_IDS:
        assert_token_once(companies, province_id, "00_trade_companies.txt")
        if province_id not in company_provinces:
            raise ValueError(f"South China trade company lacks {province_id}")


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

    adjacency_path = vanilla_root / "map/adjacencies.csv"
    with adjacency_path.open(encoding="cp1252", errors="replace", newline="") as handle:
        special_pairs = {
            tuple(sorted((int(row[0]), int(row[1]))))
            for row in csv.reader(handle, delimiter=";")
            if len(row) >= 2
            and row[0].lstrip("-").isdigit()
            and row[1].lstrip("-").isdigit()
            and int(row[0]) >= 0
            and int(row[1]) >= 0
        }
    if (666, 2159) not in special_pairs:
        raise ValueError("Vanilla Leichow-Kiungchow special adjacency is missing")


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
    validate_locked_guangzhou_assets(vanilla_root, mod_root)
    validate_localisation(mod_root)

    build_report = json.loads(args.build_report.read_text(encoding="utf-8"))
    if build_report.get("status") != "FORMAL_B01_MANUAL_ASSETS_WRITTEN":
        raise ValueError("Formal hand-drawn B01 build report is not successful")
    if build_report.get("canonical_geometry_preserved") is not True:
        raise ValueError("Build report does not confirm preservation of manual geometry")
    for relative_path, metadata in build_report["outputs"].items():
        path = mod_root / relative_path
        if sha256_file(path) != metadata["sha256"]:
            raise ValueError(f"{relative_path}: hash differs from the build report")

    result = {
        "status": "FORMAL_B01_MANUAL_VALIDATION_PASS",
        "implemented_ids": list(IMPLEMENTED_IDS),
        "max_provinces": GAME_MAX_PROVINCES,
        "map": map_report,
        "development": {
            str(province_id): list(values)
            for province_id, values in development.items()
        },
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    print(f"{args.report}: FORMAL_B01_MANUAL_VALIDATION_PASS")


if __name__ == "__main__":
    main()
