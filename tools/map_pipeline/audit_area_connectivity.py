#!/usr/bin/env python3
"""Audit EU4 area connectivity by bitmap borders and explicit adjacencies."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/audits/area_connectivity_audit.md"
HAN_REGIONS = ("south_china_region", "xinan_region", "north_china_region")


def blocks(text: str, suffix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    pattern = re.compile(rf"(?m)^\s*([A-Za-z0-9_]+{re.escape(suffix)})\s*=\s*\{{")
    for match in pattern.finditer(text):
        depth = 1
        index = match.end()
        while index < len(text) and depth:
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            index += 1
        result[match.group(1)] = text[match.end():index - 1]
    return result


def clean(text: str) -> str:
    return re.sub(r"#.*", "", text)


def area_ids(body: str) -> list[int]:
    value = clean(body)
    value = re.sub(r"(?ms)\bcolor\s*=\s*\{.*?\}", "", value)
    return [int(number) for number in re.findall(r"\b\d+\b", value)]


def definitions() -> tuple[dict[int, int], dict[int, int]]:
    by_id: dict[int, int] = {}
    by_color: dict[int, int] = {}
    with (MAP / "definition.csv").open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                province_id = int(row[0])
                packed = (int(row[1]) << 16) | (int(row[2]) << 8) | int(row[3])
                by_id[province_id] = packed
                by_color[packed] = province_id
    return by_id, by_color


def bitmap_edges(by_color: dict[int, int]) -> set[tuple[int, int]]:
    image = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    packed = (
        (image[:, :, 0].astype(np.uint32) << 16)
        | (image[:, :, 1].astype(np.uint32) << 8)
        | image[:, :, 2].astype(np.uint32)
    )
    result: set[tuple[int, int]] = set()
    for left, right in ((packed[:, :-1], packed[:, 1:]), (packed[:-1], packed[1:])):
        changed = left != right
        pairs = np.stack((left[changed], right[changed]), axis=1)
        pairs.sort(axis=1)
        for first, second in np.unique(pairs, axis=0):
            a, b = by_color.get(int(first)), by_color.get(int(second))
            if a is not None and b is not None and a != b:
                result.add((min(a, b), max(a, b)))
    return result


def bitmap_presence(by_color: dict[int, int]) -> set[int]:
    image = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    packed = (
        (image[:, :, 0].astype(np.uint32) << 16)
        | (image[:, :, 1].astype(np.uint32) << 8)
        | image[:, :, 2].astype(np.uint32)
    )
    return {by_color[int(value)] for value in np.unique(packed) if int(value) in by_color}


def explicit_edges() -> set[tuple[int, int]]:
    result: set[tuple[int, int]] = set()
    with (MAP / "adjacencies.csv").open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if len(row) < 3 or not row[0].isdigit() or not row[1].isdigit():
                continue
            a, b = int(row[0]), int(row[1])
            if a >= 0 and b >= 0 and row[2].strip().lower() != "impassable":
                result.add((min(a, b), max(a, b)))
    return result


def components(ids: list[int], edges: set[tuple[int, int]]) -> list[list[int]]:
    members = set(ids)
    adjacency = {province_id: set() for province_id in members}
    for a, b in edges:
        if a in members and b in members:
            adjacency[a].add(b)
            adjacency[b].add(a)
    result: list[list[int]] = []
    unseen = set(members)
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        stack = [start]
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        result.append(sorted(component))
    return sorted(result, key=lambda value: (-len(value), value))


def localisation() -> tuple[dict[int, str], dict[str, str]]:
    province_names: dict[int, str] = {}
    area_names: dict[str, str] = {}
    for path in (MOD / "localisation_source").glob("*.txt"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for province_id, name in re.findall(r'^\s*PROV(\d+):\d*\s+"([^"]+)"', text, re.M):
            province_names[int(province_id)] = name
        for key, name in re.findall(r'^\s*([A-Za-z0-9_]+_area):\d*\s+"([^"]+)"', text, re.M):
            area_names[key] = name
    return province_names, area_names


def format_components(values: list[list[int]], names: dict[int, str]) -> str:
    groups = []
    for component in values:
        groups.append("、".join(f"{names.get(pid, str(pid))}({pid})" for pid in component))
    return " ｜ ".join(groups)


def main() -> None:
    area_blocks = blocks((MAP / "area.txt").read_text(encoding="cp1252", errors="replace"), "_area")
    region_blocks = blocks((MAP / "region.txt").read_text(encoding="cp1252", errors="replace"), "_region")
    areas = {key: area_ids(body) for key, body in area_blocks.items()}
    han_areas = {
        area
        for region in HAN_REGIONS
        for area in re.findall(r"\b[A-Za-z0-9_]+_area\b", clean(region_blocks.get(region, "")))
    }
    _by_id, by_color = definitions()
    pixel = bitmap_edges(by_color)
    present = bitmap_presence(by_color)
    gameplay = pixel | explicit_edges()
    province_names, area_names = localisation()

    strict_bad = {}
    gameplay_bad = {}
    empty_references = {}
    for area, ids in areas.items():
        missing = [province_id for province_id in ids if province_id not in present]
        if missing:
            empty_references[area] = missing
        active_ids = [province_id for province_id in ids if province_id in present]
        if len(active_ids) < 2:
            continue
        strict = components(active_ids, pixel)
        played = components(active_ids, gameplay)
        if len(strict) > 1:
            strict_bad[area] = strict
        if len(played) > 1:
            gameplay_bad[area] = played

    lines = [
        "# Area connectivity audit",
        "",
        f"- Total areas: {len(areas)}",
        f"- Strict bitmap-disconnected: {len(strict_bad)}",
        f"- Still disconnected after explicit adjacencies: {len(gameplay_bad)}",
        f"- Areas containing empty province references: {len(empty_references)}",
        f"- Han-region areas checked: {len(han_areas)}",
        "",
        "## Han areas requiring reassignment",
        "",
        "| Area | Localised | Strict components | Gameplay components | Components |",
        "|---|---|---:|---:|---|",
    ]
    han_real = sorted(area for area in gameplay_bad if area in han_areas)
    for area in han_real:
        strict = strict_bad.get(area, [areas[area]])
        played = gameplay_bad[area]
        lines.append(
            f"| `{area}` | {area_names.get(area, area)} | {len(strict)} | {len(played)} | "
            f"{format_components(played, province_names)} |"
        )
    if not han_real:
        lines.append("| — | — | 0 | 0 | No issues |")

    lines += [
        "",
        "## Han areas separated only by a navigable river or defined crossing",
        "",
        "| Area | Localised | Bitmap components | Components before crossing |",
        "|---|---|---:|---|",
    ]
    river_only = sorted(area for area in strict_bad if area in han_areas and area not in gameplay_bad)
    for area in river_only:
        lines.append(
            f"| `{area}` | {area_names.get(area, area)} | {len(strict_bad[area])} | "
            f"{format_components(strict_bad[area], province_names)} |"
        )
    if not river_only:
        lines.append("| — | — | 0 | None |")

    lines += [
        "",
        "## Han areas containing province IDs with no bitmap pixels",
        "",
        "| Area | Localised | Empty references |",
        "|---|---|---|",
    ]
    han_empty = sorted(area for area in empty_references if area in han_areas)
    for area in han_empty:
        values = "、".join(
            f"{province_names.get(pid, str(pid))}({pid})" for pid in empty_references[area]
        )
        lines.append(f"| `{area}` | {area_names.get(area, area)} | {values} |")
    if not han_empty:
        lines.append("| — | — | None |")

    lines += [
        "",
        "## Full-map gameplay-disconnected areas",
        "",
        "These include intentional archipelagos and vanilla layouts; review before changing.",
        "",
        "| Area | Localised | Components | Provinces |",
        "|---|---|---:|---|",
    ]
    for area in sorted(gameplay_bad):
        played = gameplay_bad[area]
        lines.append(
            f"| `{area}` | {area_names.get(area, area)} | {len(played)} | "
            f"{format_components(played, province_names)} |"
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"AREAS:{len(areas)} STRICT_BAD:{len(strict_bad)} GAMEPLAY_BAD:{len(gameplay_bad)} EMPTY_REF_AREAS:{len(empty_references)}")
    print(f"HAN_AREAS:{len(han_areas)} HAN_REAL:{len(han_real)} HAN_RIVER_ONLY:{len(river_only)} HAN_EMPTY:{len(han_empty)}")
    print("HAN_REAL_KEYS:" + ",".join(han_real))
    print("HAN_RIVER_ONLY_KEYS:" + ",".join(river_only))
    print("HAN_EMPTY_KEYS:" + ",".join(han_empty))
    print(OUT)


if __name__ == "__main__":
    main()
