"""Generate the loadable B01 Guangdong map assets for the mod.

The script treats the installed EU4 1.37.5 map as an immutable baseline.  It
first asks ``build_b01_preview.py`` to rebuild and validate the province
geometry, then writes the complete replacement files that EU4 requires under
the mod root.  Only the five implemented B01 IDs (4942-4946) are exposed to
the game; IDs reserved for later drawing batches remain design data only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MOD_ROOT = REPO_ROOT / "guangdong_independent_practice"
DEFAULT_REGISTRY = REPO_ROOT / "docs/map/china_province_split_registry.csv"
DEFAULT_REPORT = REPO_ROOT / "docs/map/previews/B01_mod_build_report.json"
PREVIEW_BUILDER = Path(__file__).with_name("build_b01_preview.py")
PREVIEW_CONFIG = Path(__file__).with_name("b01_guangdong.json")
STAGING_PROVINCES = REPO_ROOT / "build/map/B01/provinces.bmp"
STAGING_REPORT = REPO_ROOT / "docs/map/previews/B01_guangdong_report.json"

IMPLEMENTED_IDS = tuple(range(4942, 4947))
GAME_MAX_PROVINCES = 4947
NEW_DEFINITION_NAMES = {
    4942: "Foshan",
    4943: "Dongguan",
    4944: "Meizhou",
    4945: "Gaozhou",
    4946: "Hong Kong",
}

# Positions use Clausewitz coordinates, whose vertical axis is the inverse of
# provinces.bmp.  Every entry contains city, unit, text, port and three
# auxiliary points, followed by seven rotations and seven heights.
POSITION_BLOCKS = {
    667: """667={
\tposition={
\t\t4575.000 1022.000 4575.000 1026.000 4581.000 1034.000 4570.000 1007.000 4584.000 1035.000 4579.000 1029.000 0.000 0.000
\t}
\trotation={
\t\t0.000 0.000 0.000 -0.262 0.000 0.000 0.000
\t}
\theight={
\t\t0.000 0.000 1.000 0.000 0.000 0.000 0.000
\t}
}""",
    2157: """2157={
\tposition={
\t\t4602.000 1041.000 4606.000 1039.000 4601.000 1045.000 4614.000 1019.000 4604.000 1035.000 4598.000 1039.000 0.000 0.000
\t}
\trotation={
\t\t0.000 0.000 0.000 0.000 0.000 0.000 0.000
\t}
\theight={
\t\t0.000 0.000 1.000 0.000 0.000 0.000 0.000
\t}
}""",
    4942: """#Foshan
4942={
\tposition={
\t\t4571.000 1027.000 4570.000 1024.000 4571.000 1024.000 4571.000 1027.000 4572.000 1021.000 4572.000 1024.000 0.000 0.000
\t}
\trotation={
\t\t0.000 0.000 0.000 0.000 0.000 0.000 0.000
\t}
\theight={
\t\t0.000 0.000 1.000 0.000 0.000 0.000 0.000
\t}
}""",
    4943: """#Dongguan
4943={
\tposition={
\t\t4591.000 1028.000 4588.000 1027.000 4592.000 1031.000 4594.000 1018.000 4594.000 1027.000 4591.000 1024.000 0.000 0.000
\t}
\trotation={
\t\t0.000 0.000 0.000 0.000 0.000 0.000 0.000
\t}
\theight={
\t\t0.000 0.000 1.000 0.000 0.000 0.000 0.000
\t}
}""",
    4944: """#Meizhou
4944={
\tposition={
\t\t4618.000 1051.000 4615.000 1054.000 4619.000 1048.000 4618.000 1051.000 4620.000 1045.000 4615.000 1050.000 0.000 0.000
\t}
\trotation={
\t\t0.000 0.000 0.000 0.000 0.000 0.000 0.000
\t}
\theight={
\t\t0.000 0.000 1.000 0.000 0.000 0.000 0.000
\t}
}""",
    4945: """#Gaozhou
4945={
\tposition={
\t\t4540.000 1011.000 4541.000 1004.000 4539.000 1008.000 4541.000 997.000 4539.000 1014.000 4544.000 1003.000 0.000 0.000
\t}
\trotation={
\t\t0.000 0.000 0.000 -0.785 0.000 0.000 0.000
\t}
\theight={
\t\t0.000 0.000 1.000 0.000 0.000 0.000 0.000
\t}
}""",
    4946: """#Hong Kong
4946={
\tposition={
\t\t4599.000 1021.000 4602.000 1022.000 4601.000 1022.000 4602.000 1019.000 4606.000 1022.000 4596.000 1023.000 0.000 0.000
\t}
\trotation={
\t\t0.000 0.000 0.000 0.000 0.000 0.000 0.000
\t}
\theight={
\t\t0.000 0.000 1.000 0.000 0.000 0.000 0.000
\t}
}""",
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
    pattern = re.compile(
        rf"(?m)^[ \t]*{re.escape(name)}[ \t]*=[ \t]*\{{",
    )
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
    normalized = "\n".join(lines) + "\n"
    path.write_text(normalized, encoding="cp1252", newline="\n")


def load_b01_registry(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["draw_batch"] == "B01"
        ]
    rows.sort(key=lambda row: int(row["game_id"]))
    ids = tuple(int(row["game_id"]) for row in rows)
    if ids != IMPLEMENTED_IDS:
        raise ValueError(f"B01 registry IDs must be {IMPLEMENTED_IDS}, found {ids}")
    return rows


def build_geometry(vanilla_root: Path) -> dict[str, object]:
    command = [
        sys.executable,
        str(PREVIEW_BUILDER),
        "--vanilla-root",
        str(vanilla_root),
        "--config",
        str(PREVIEW_CONFIG),
        "--candidate-bmp",
        str(STAGING_PROVINCES),
    ]
    subprocess.run(command, cwd=REPO_ROOT, check=True)
    report = json.loads(STAGING_REPORT.read_text(encoding="utf-8"))
    if report.get("status") != "PREVIEW_GEOMETRY_PASS":
        raise ValueError("B01 preview geometry did not pass")
    if report.get("changed_pixels") != 710:
        raise ValueError(
            f"Expected 710 B01 changed pixels, found {report.get('changed_pixels')}"
        )
    return report


def build_definition(
    vanilla_root: Path,
    output: Path,
    registry_rows: list[dict[str, str]],
) -> None:
    source = read_text(vanilla_root / "map/definition.csv").rstrip("\r\n")
    existing_ids = {
        int(line.split(";", 1)[0])
        for line in source.splitlines()
        if line.split(";", 1)[0].isdigit()
    }
    if existing_ids & set(IMPLEMENTED_IDS):
        raise ValueError("Vanilla definition unexpectedly contains a B01 ID")
    additions = []
    for row in registry_rows:
        province_id = int(row["game_id"])
        additions.append(
            f"{province_id};{row['rgb_r']};{row['rgb_g']};{row['rgb_b']};"
            f"{NEW_DEFINITION_NAMES[province_id]};x"
        )
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

guangdong_area = { #4
\t2156 2157 2158 4944
}"""
    text = replace_named_block(text, "guangdong_area", pearl_and_east)
    text = replace_named_block(
        text,
        "west_guangdong_area",
        """west_guangdong_area = { #6
\t665 666 2159 2160 2161 4945
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

    text = modify_nested_block(text, "south_china_region", add_area)
    write_text(output, text)


def build_continent(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/continent.txt")
    text = append_to_named_block(
        text,
        "asia",
        "\t4942 4943 4944 4945 4946 # B01 Guangdong",
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
        "\t4942 4943 4944 4945 4946 # B01 Guangdong",
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
        "\t\t\t2146 2147 2152 2153 2158 2171 2173 2174 4944 4945 4946 ",
        "hills terrain override",
    )
    write_text(output, text)


def build_positions(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/positions.txt")
    for province_id in (667, 2157):
        text = replace_named_block(text, str(province_id), POSITION_BLOCKS[province_id])
    text = text.rstrip() + "\n\n"
    text += "\n\n".join(POSITION_BLOCKS[province_id] for province_id in IMPLEMENTED_IDS)
    text += "\n"
    write_text(output, text)


def append_members_to_outer_block(
    text: str,
    outer_name: str,
    member_ids: tuple[int, ...],
) -> str:
    def modify_outer(block: str) -> str:
        member_start, member_end = find_named_block(block, "members")
        members = block[member_start:member_end]
        closing = members.rfind("}")
        insertion = "\n\t\t" + " ".join(str(value) for value in member_ids) + " # B01 Guangdong\n\t"
        members = members[:closing].rstrip() + insertion + members[closing:]
        return block[:member_start] + members + block[member_end:]

    return modify_nested_block(text, outer_name, modify_outer)


def build_trade_nodes(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "common/tradenodes/00_tradenodes.txt")
    text = append_members_to_outer_block(text, "canton", IMPLEMENTED_IDS)
    write_text(output, text)


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

    text = modify_nested_block(
        text,
        "trade_company_south_china",
        modify_company,
    )
    write_text(output, text)


def write_report(
    report_path: Path,
    mod_root: Path,
    geometry_report: dict[str, object],
    outputs: list[Path],
) -> None:
    report = {
        "status": "FORMAL_B01_ASSETS_WRITTEN",
        "scope": "B01 Guangdong playable map slice",
        "baseline_version": geometry_report["baseline_version"],
        "baseline_verified_by_sha256": geometry_report[
            "baseline_verified_by_sha256"
        ],
        "baseline_source": "EU4_INSTALL_ROOT",
        "mod_root": mod_root.name,
        "implemented_ids": list(IMPLEMENTED_IDS),
        "max_provinces": GAME_MAX_PROVINCES,
        "changed_pixels": geometry_report["changed_pixels"],
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
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    vanilla_root = args.vanilla_root.expanduser().resolve()
    mod_root = args.mod_root.expanduser().resolve()
    if not (mod_root / "descriptor.mod").is_file():
        raise ValueError(f"Not an EU4 mod root: {mod_root}")

    registry_rows = load_b01_registry(args.registry)
    geometry_report = build_geometry(vanilla_root)

    provinces_output = mod_root / "map/provinces.bmp"
    provinces_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(STAGING_PROVINCES, provinces_output)

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
    print(f"{mod_root}: B01 formal map assets written")
    print(f"{args.report}: FORMAL_B01_ASSETS_WRITTEN")


if __name__ == "__main__":
    main()
