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
GAME_MAX_PROVINCES = 4950
NEW_DEFINITION_NAMES = {
    4942: "Foshan",
    4943: "Dongguan",
    4944: "Meizhou",
    4945: "Gaozhou",
    4946: "Hong Kong",
    4947: "Luoding",
    4948: "Nanxiong",
    4949: "Lufeng",
}

# Positions use Clausewitz coordinates, whose vertical axis is the inverse of
# provinces.bmp.  Each tuple contains city, unit, text, port, two auxiliary
# points, and the unused seventh point.
POSITION_DATA = {
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


def load_b01_registry(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [
            row for row in csv.DictReader(handle)
            if row["draw_batch"] == "B01"
        ]
    rows.sort(key=lambda row: int(row["game_id"]))
    ids = tuple(int(row["game_id"]) for row in rows)
    if ids != IMPLEMENTED_IDS:
        raise ValueError(f"B01 registry IDs must be {IMPLEMENTED_IDS}, found {ids}")
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
    if existing_ids & set(IMPLEMENTED_IDS):
        raise ValueError("Vanilla definition unexpectedly contains a B01 ID")
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
    write_text(output, text)


def build_region(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/region.txt")

    def add_area(block: str) -> str:
        return replace_once(
            block,
            "\t\tguangdong_area\n",
            "\t\tpearl_river_delta_area\n\t\tguangdong_area\n",
            "south_china_region areas",
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
        "normal_monsoon",
        "\t4942 4943 4944 4945 4946 4947 4948 4949 # B01 Guangdong",
    )
    write_text(output, text)


def build_terrain(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/terrain.txt")
    text = replace_once(
        text,
        "\t\t\t665 667 2156 2157 2159 2163 700",
        "\t\t\t665 667 2156 2157 2159 2163 700 4942 4943",
        "farmlands terrain override",
    )
    text = replace_once(
        text,
        "\t\t\t2146 2147 2152 2153 2158 2171 2173 2174 ",
        "\t\t\t2146 2147 2152 2153 2158 2171 2173 2174 "
        "4944 4945 4946 4947 4948 4949 ",
        "hills terrain override",
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
    for province_id in (665, 667, 2157, 2158, 2159):
        text = replace_named_block(
            text,
            str(province_id),
            format_position_block(province_id, include_comment=False),
        )
    text = text.rstrip() + "\n\n"
    text += "\n\n".join(
        format_position_block(province_id) for province_id in IMPLEMENTED_IDS
    )
    write_text(output, text + "\n")


def append_members_to_outer_block(
    text: str,
    outer_name: str,
    member_ids: tuple[int, ...],
) -> str:
    def modify_outer(block: str) -> str:
        member_start, member_end = find_named_block(block, "members")
        members = block[member_start:member_end]
        closing = members.rfind("}")
        insertion = (
            "\n\t\t"
            + " ".join(str(value) for value in member_ids)
            + " # B01 Guangdong\n\t"
        )
        members = members[:closing].rstrip() + insertion + members[closing:]
        return block[:member_start] + members + block[member_end:]

    return modify_nested_block(text, outer_name, modify_outer)


def build_trade_nodes(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "common/tradenodes/00_tradenodes.txt")
    write_text(
        output,
        append_members_to_outer_block(text, "canton", IMPLEMENTED_IDS),
    )


def build_trade_companies(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "common/trade_companies/00_trade_companies.txt")

    def modify_company(block: str) -> str:
        start, end = find_named_block(block, "provinces")
        provinces = block[start:end]
        closing = provinces.rfind("}")
        insertion = (
            "\n\t\t"
            + " ".join(str(value) for value in IMPLEMENTED_IDS)
            + " # B01 Guangdong\n\t"
        )
        provinces = provinces[:closing].rstrip() + insertion + provinces[closing:]
        return block[:start] + provinces + block[end:]

    write_text(
        output,
        modify_nested_block(
            text,
            "trade_company_south_china",
            modify_company,
        ),
    )


def write_report(
    report_path: Path,
    mod_root: Path,
    geometry_report: dict[str, object],
    outputs: list[Path],
) -> None:
    report = {
        "status": "FORMAL_B01_MANUAL_ASSETS_WRITTEN",
        "scope": "B01 Guangdong hand-drawn playable map slice",
        "baseline_version": geometry_report["baseline_version"],
        "baseline_verified_by_sha256": geometry_report[
            "baseline_verified_by_sha256"
        ],
        "baseline_source": "EU4_INSTALL_ROOT",
        "geometry_source": geometry_report["source_policy"],
        "canonical_geometry_preserved": True,
        "mod_root": mod_root.name,
        "implemented_ids": list(IMPLEMENTED_IDS),
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

    registry_rows = load_b01_registry(args.registry)
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
    print(f"{mod_root}: B01 companion assets written for IDs 4942-4949")
    print(f"{args.report}: FORMAL_B01_MANUAL_ASSETS_WRITTEN")


if __name__ == "__main__":
    main()
