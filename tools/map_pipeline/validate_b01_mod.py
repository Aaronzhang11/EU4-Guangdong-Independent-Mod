"""Static validation for the loadable B01 Guangdong map slice."""

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
    DEFAULT_MOD_ROOT,
    DEFAULT_REPORT,
    GAME_MAX_PROVINCES,
    IMPLEMENTED_IDS,
    find_named_block,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("b01_guangdong.json")
DEFAULT_VALIDATION_REPORT = (
    REPO_ROOT / "docs/map/previews/B01_mod_validation_report.json"
)
DEFAULT_LOCALISATION_SOURCE = (
    DEFAULT_MOD_ROOT / "localisation_source/gdd_b01_map_readable_utf8.txt"
)
EXPECTED_DEFINITIONS = {
    4942: ((190, 91, 45), "Foshan"),
    4943: ((67, 219, 159), "Dongguan"),
    4944: ((187, 30, 204), "Meizhou"),
    4945: ((186, 212, 73), "Gaozhou"),
    4946: ((20, 200, 220), "Hong Kong"),
}
EXPECTED_AREAS = {
    4942: "pearl_river_delta_area",
    4943: "pearl_river_delta_area",
    4944: "guangdong_area",
    4945: "west_guangdong_area",
    4946: "pearl_river_delta_area",
}
EXPECTED_TERRAIN = {
    4942: "farmlands",
    4943: "farmlands",
    4944: "hills",
    4945: "hills",
    4946: "hills",
}
EXPECTED_PORT_SEAS = {
    667: 1371,
    2157: 1371,
    4943: 1371,
    4945: 1370,
    4946: 1371,
}
EXPECTED_HISTORY = {
    667: ("GDD", (8, 8, 2), "incense", "cantonese"),
    2156: ("MNG", (4, 4, 1), "chinaware", "chimin"),
    2157: ("GDD", (3, 3, 1), "grain", "hakka"),
    2159: ("GDD", (2, 2, 1), "sugar", "chimin"),
    4942: ("GDD", (4, 4, 1), "chinaware", "cantonese"),
    4943: ("GDD", (3, 3, 1), "incense", "cantonese"),
    4944: ("GDD", (2, 2, 1), "tea", "hakka"),
    4945: ("GDD", (1, 1, 1), "grain", "cantonese"),
    4946: ("GDD", (1, 1, 1), "fish", "cantonese"),
}
EXPECTED_DEV_PARTITIONS = {
    667: (4942,),
    2157: (4943, 4946),
    2156: (4944,),
    2159: (4945,),
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
    return [int(value) for value in re.findall(r"(?<![\w.])\d+(?![\w.])", without_comments)]


def assert_token_once(text: str, value: int, label: str) -> None:
    matches = re.findall(rf"(?<![\w.]){value}(?![\w.])", re.sub(r"#.*$", "", text, flags=re.MULTILINE))
    if len(matches) != 1:
        raise ValueError(f"{label}: expected ID {value} once, found {len(matches)}")


def read_sea_ids(default_map: str) -> set[int]:
    return set(numeric_tokens(block_text(default_map, "sea_starts")))


def component_count(mask: np.ndarray) -> int:
    remaining = mask.copy()
    count = 0
    height, width = remaining.shape
    while remaining.any():
        seed_y, seed_x = np.argwhere(remaining)[0]
        queue: deque[tuple[int, int]] = deque([(int(seed_x), int(seed_y))])
        remaining[seed_y, seed_x] = False
        while queue:
            x, y = queue.popleft()
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
        count += 1
    return count


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
    opening = position.find("{")
    closing = position.rfind("}")
    values = [
        float(value)
        for value in re.findall(r"-?\d+(?:\.\d+)?", position[opening + 1 : closing])
    ]
    if len(values) != 14:
        raise ValueError(
            f"positions.txt: {province_id} needs 14 position values, found {len(values)}"
        )
    for section in ("rotation", "height"):
        section_text = block_text(block, section)
        section_values = re.findall(
            r"-?\d+(?:\.\d+)?",
            section_text[section_text.find("{") + 1 : section_text.rfind("}")],
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
    for province_id, expected in EXPECTED_DEFINITIONS.items():
        if definitions.get(province_id) != expected:
            raise ValueError(
                f"definition.csv: {province_id} is {definitions.get(province_id)}, "
                f"expected {expected}"
            )

    default_map = (map_dir / "default.map").read_text(encoding="cp1252")
    max_match = re.search(r"(?m)^max_provinces\s*=\s*(\d+)", default_map)
    if not max_match or int(max_match.group(1)) != GAME_MAX_PROVINCES:
        raise ValueError(f"default.map: max_provinces must be {GAME_MAX_PROVINCES}")
    sea_ids = read_sea_ids(default_map)

    with Image.open(map_dir / "provinces.bmp") as image:
        if image.size != (5632, 2048) or image.mode != "RGB":
            raise ValueError(
                f"provinces.bmp must be 5632x2048 RGB, found {image.size} {image.mode}"
            )
        province_map = np.array(image, dtype=np.uint8)

    baseline_map = np.array(
        Image.open(vanilla_root / "map/provinces.bmp"),
        dtype=np.uint8,
    )
    changed_pixels = np.any(province_map != baseline_map, axis=2)
    if int(changed_pixels.sum()) != 710:
        raise ValueError(
            f"provinces.bmp: expected 710 changed pixels, "
            f"found {int(changed_pixels.sum())}"
        )

    expected_neighbors = {
        child["design_key"]: set(int(value) for value in child["expected_neighbor_ids"])
        for partition in config["partitions"]
        for child in partition["children"]
    }
    # Config uses design keys, while definitions use English names.  The fixed
    # B01 order makes the intended mapping explicit and resistant to labels.
    key_to_id = {
        "S-13": 4942,
        "S-14": 4943,
        "S-15": 4944,
        "S-16": 4945,
        "S-19": 4946,
    }
    province_stats: dict[int, dict[str, object]] = {}
    for design_key, province_id in key_to_id.items():
        color = definitions[province_id][0]
        mask = np.all(province_map == np.array(color, dtype=np.uint8), axis=2)
        if not mask.any():
            raise ValueError(f"provinces.bmp: {province_id} has no pixels")
        components = component_count(mask)
        if components != 1:
            raise ValueError(
                f"provinces.bmp: {province_id} has {components} components"
            )
        neighbors = neighboring_ids(province_map, mask, color_to_id)
        if neighbors != expected_neighbors[design_key]:
            raise ValueError(
                f"provinces.bmp: {province_id} neighbors {sorted(neighbors)}, "
                f"expected {sorted(expected_neighbors[design_key])}"
            )
        province_stats[province_id] = {
            "pixels": int(mask.sum()),
            "neighbors": sorted(neighbors),
            "coastal": bool(neighbors & sea_ids),
        }

    positions = (map_dir / "positions.txt").read_text(encoding="cp1252")
    for province_id in (667, 2157, *IMPLEMENTED_IDS):
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
        if province_id in EXPECTED_PORT_SEAS:
            expected_sea = EXPECTED_PORT_SEAS[province_id]
            if port_id != expected_sea:
                raise ValueError(
                    f"positions.txt: {province_id} port is in {port_id}, "
                    f"expected sea {expected_sea}"
                )
            adjacent_colors = [
                tuple(int(channel) for channel in province_map[next_y, next_x])
                for next_x, next_y in (
                    (port_x + 1, port_y),
                    (port_x - 1, port_y),
                    (port_x, port_y + 1),
                    (port_x, port_y - 1),
                )
                if 0 <= next_x < province_map.shape[1]
                and 0 <= next_y < province_map.shape[0]
            ]
            adjacent_ids = {color_to_id.get(color) for color in adjacent_colors}
            if province_id not in adjacent_ids:
                raise ValueError(
                    f"positions.txt: {province_id} port does not touch the province"
                )
        elif port_id != province_id:
            raise ValueError(
                f"positions.txt: inland {province_id} port slot is in {port_id}"
            )

    return {
        "changed_pixels": int(changed_pixels.sum()),
        "province_stats": province_stats,
        "provinces_sha256": sha256_file(map_dir / "provinces.bmp"),
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
    if tropical & {4942, 4943, 4944, 4946}:
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
        text = path.read_text(encoding="cp1252")
        actual_owner = initial_history_value(text, "owner")
        actual_goods = initial_history_value(text, "trade_goods")
        actual_culture = initial_history_value(text, "culture")
        actual_dev = tuple(
            int(initial_history_value(text, key))
            for key in ("base_tax", "base_production", "base_manpower")
        )
        if (actual_owner, actual_dev, actual_goods, actual_culture) != (
            owner,
            expected_dev,
            goods,
            culture,
        ):
            raise ValueError(
                f"{path.name}: history mismatch "
                f"{(actual_owner, actual_dev, actual_goods, actual_culture)}"
            )
        if province_id in IMPLEMENTED_IDS:
            if "add_core = GDD" not in text:
                raise ValueError(f"{path.name}: missing GDD core")
            if initial_history_value(text, "religion") != "confucianism":
                raise ValueError(f"{path.name}: religion must be confucianism")
            if initial_history_value(text, "is_city") != "yes":
                raise ValueError(f"{path.name}: must be a city")
        development[province_id] = actual_dev

    original_development = {
        667: (12, 12, 3),
        2157: (7, 7, 3),
        2156: (6, 6, 2),
        2159: (3, 3, 2),
    }
    for parent_id, child_ids in EXPECTED_DEV_PARTITIONS.items():
        recombined = tuple(
            development[parent_id][index]
            + sum(development[child_id][index] for child_id in child_ids)
            for index in range(3)
        )
        if recombined != original_development[parent_id]:
            raise ValueError(
                f"Development partition {parent_id} recombines to {recombined}, "
                f"expected {original_development[parent_id]}"
            )
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
    if build_report.get("status") != "FORMAL_B01_ASSETS_WRITTEN":
        raise ValueError("Formal B01 build report is not successful")
    for relative_path, metadata in build_report["outputs"].items():
        path = mod_root / relative_path
        if sha256_file(path) != metadata["sha256"]:
            raise ValueError(f"{relative_path}: hash differs from the build report")

    result = {
        "status": "FORMAL_B01_VALIDATION_PASS",
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
    print(f"{args.report}: FORMAL_B01_VALIDATION_PASS")


if __name__ == "__main__":
    main()
