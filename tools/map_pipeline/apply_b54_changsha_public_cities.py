#!/usr/bin/env python3
"""Apply the B54 Changsha transfer and three independent public cities.

This batch changes only opening ownership, cores and country data. Province
geometry, development, areas, trade nodes and trade centres remain unchanged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
PROVINCE_HISTORY = MOD / "history/provinces"
COUNTRY_HISTORY = MOD / "history/countries"
COUNTRIES = MOD / "common/countries"
FLAGS = MOD / "gfx/flags"
CLIMATE = MOD / "map/climate.txt"
TAG_FILE = MOD / "common/country_tags/gdd_country_tags.txt"
SOURCE = MOD / "localisation_source/007_gdd_b54_changsha_public_cities_readable_utf8.txt"
TARGET = MOD / "localisation/replace/007_gdd_b54_changsha_public_cities_l_english.yml"
PLAN = ROOT / "planning/changsha_public_cities_b54"
REPORT = PLAN / "ownership_report.json"
MANIFEST = PLAN / "batch_manifest.json"
DEFAULT_VANILLA_ROOT = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)
DEFAULT_DEPENDENCY_ROOTS = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/workshop/content/236850/2976470733",
    Path.home()
    / "Library/Application Support/Steam/steamapps/workshop/content/236850/1999055990",
)

sys.path.insert(0, str(ROOT / "tools/map_pipeline"))
from country_name_pool_support import country_definition_bytes  # noqa: E402
from apply_b43_chunqiu_polities import (  # noqa: E402
    EXACT_CORE_TAGS,
    POLITIES,
    TAG_PROVINCES,
    apply_owner,
    country_definition,
    country_history,
    ensure_core_override_files,
    flag_bytes,
    initial_cores,
    initial_value,
    province_id_from_path,
    read_text,
    remove_initial_core,
    should_remove_core,
    validate as validate_b43,
)


PUBLIC_CITIES = ("CDE", "JJG", "HYA")
AFFECTED_TAGS = ("CSA", "WLM", "CHC", *PUBLIC_CITIES)
EXPECTED_DEVELOPMENT = {
    "CSA": 39,
    "WLM": 16,
    "CHC": 105,
    "CDE": 15,
    "JJG": 20,
    "HYA": 9,
}
LOCALISATION = {"CDE": "常", "JJG": "九", "HYA": "汉"}
TAG_MARKER_BEGIN = "# GDD_B54_CHANGSHA_PUBLIC_CITIES_BEGIN"
TAG_MARKER_END = "# GDD_B54_CHANGSHA_PUBLIC_CITIES_END"
CLIMATE_MARKER = "GDD_B54_CHANGSHA_PUBLIC_CITIES"


def history_paths(province_id: int) -> list[Path]:
    paths = sorted(PROVINCE_HISTORY.glob(f"{province_id} - *.txt"))
    if not paths:
        raise ValueError(f"Province {province_id}: missing local history")
    return paths


def ensure_climate_membership() -> None:
    text = CLIMATE.read_text(encoding="cp1252")
    match = re.search(r"(?m)^mild_monsoon\s*=\s*\{", text)
    if not match:
        raise ValueError("climate.txt: missing mild_monsoon block")
    depth = 1
    index = match.end()
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    if depth:
        raise ValueError("climate.txt: unbalanced mild_monsoon block")
    start, end = match.start(), index
    block = text[start:end]
    cleaned: list[str] = []
    for line in block.splitlines():
        if CLIMATE_MARKER in line:
            continue
        code, separator, comment = line.partition("#")
        tokens = code.split()
        if "672" in tokens:
            tokens = [token for token in tokens if token != "672"]
            indent = code[: len(code) - len(code.lstrip())]
            code = indent + " ".join(tokens)
            if separator and code.strip():
                code += " "
        cleaned.append(code + (separator + comment if separator else ""))
    block = "\n".join(cleaned)
    close = block.rfind("}")
    block = (
        block[:close].rstrip()
        + f"\n    672 # {CLIMATE_MARKER}\n"
        + block[close:]
    )
    CLIMATE.write_text(text[:start] + block + text[end:], encoding="cp1252")


def update_tag_file() -> None:
    text = read_text(TAG_FILE)
    text = re.sub(
        rf"(?ms)^\s*{re.escape(TAG_MARKER_BEGIN)}.*?{re.escape(TAG_MARKER_END)}\s*\n?",
        "",
        text,
    )
    for tag in PUBLIC_CITIES:
        text = re.sub(rf'(?m)^\s*{tag}\s*=\s*"[^"]+"\s*\n?', "", text)
    lines = [TAG_MARKER_BEGIN]
    for tag in PUBLIC_CITIES:
        lines.append(f'{tag} = "countries/{POLITIES[tag]["file"]}"')
    lines.append(TAG_MARKER_END)
    TAG_FILE.write_text(
        text.rstrip() + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_localisation() -> None:
    lines = ["l_english:"]
    for tag, name in LOCALISATION.items():
        lines.extend((f' {tag}:0 "{name}"', f' {tag}_ADJ:0 "{name}"'))
    SOURCE.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file, verify_file

    encode_file(SOURCE, TARGET)
    verify_file(SOURCE, TARGET)


def apply_province_policy(vanilla_root: Path) -> None:
    for tag in AFFECTED_TAGS:
        for province_id in TAG_PROVINCES[tag]:
            for path in history_paths(province_id):
                old = read_text(path)
                new = apply_owner(old, tag)
                if new != old:
                    path.write_text(new, encoding="utf-8")

    ensure_core_override_files(vanilla_root, write=True)
    for path in PROVINCE_HISTORY.glob("*.txt"):
        province_id = province_id_from_path(path)
        if province_id is None:
            continue
        old = read_text(path)
        new = old
        for tag in initial_cores(old):
            if should_remove_core(tag, province_id):
                new = remove_initial_core(new, tag)
        if new != old:
            path.write_text(new, encoding="utf-8")


def write_countries() -> None:
    COUNTRIES.mkdir(parents=True, exist_ok=True)
    COUNTRY_HISTORY.mkdir(parents=True, exist_ok=True)
    FLAGS.mkdir(parents=True, exist_ok=True)
    for tag in PUBLIC_CITIES:
        config = POLITIES[tag]
        capital = read_text(history_paths(int(config["capital"]))[0])
        culture = initial_value(capital, "culture")
        religion = initial_value(capital, "religion")
        (COUNTRIES / str(config["file"])).write_bytes(
            country_definition_bytes(country_definition(config["color"]), culture)
        )
        (COUNTRY_HISTORY / str(config["history"])).write_text(
            country_history(
                int(config["capital"]),
                int(config["rank"]),
                culture,
                religion,
                government="republic",
                reform="oligarchy_reform",
            ),
            encoding="utf-8",
        )
        (FLAGS / f"{tag}.tga").write_bytes(flag_bytes(config["color"]))

    sys.path.insert(0, str(ROOT / "tools"))
    from generate_zhuxia_seal_flags import run as generate_zhuxia_seal_flags

    generate_zhuxia_seal_flags(check=False)


def province_development(province_id: int) -> int:
    text = read_text(history_paths(province_id)[0])
    return sum(
        int(initial_value(text, key))
        for key in ("base_tax", "base_production", "base_manpower")
    )


def scan_tag_collisions(roots: tuple[Path, ...]) -> None:
    for tag in PUBLIC_CITIES:
        matches: list[str] = []
        for root in roots:
            directory = root / "common/country_tags"
            if not directory.exists():
                continue
            for path in directory.glob("*.txt"):
                if re.search(rf"(?m)^\s*{tag}\s*=", read_text(path)):
                    matches.append(str(path))
        if matches:
            raise ValueError(f"{tag}: conflicts with dependency tag(s): {matches}")


def validate_manifest() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("batch") != "B54_changsha_public_cities":
        raise ValueError("B54 manifest batch marker is missing")
    opening = manifest.get("opening_territory", {})
    for tag in AFFECTED_TAGS:
        if opening.get(tag) != list(TAG_PROVINCES[tag]):
            raise ValueError(f"{tag}: B54 manifest territory drifted")
    return manifest


def validate(vanilla_root: Path, dependency_roots: tuple[Path, ...]) -> dict[str, object]:
    scan_tag_collisions((vanilla_root, *dependency_roots))
    manifest = validate_manifest()
    climate = CLIMATE.read_text(encoding="cp1252")
    if len(re.findall(r"(?<!\d)672(?!\d)", climate)) != 1:
        raise ValueError("Changde (672) must have exactly one climate membership")
    if not re.search(rf"(?m)^\s*672\s+#\s*{CLIMATE_MARKER}\s*$", climate):
        raise ValueError("Changde (672) must be in the B54 mild_monsoon membership")
    b43 = validate_b43(vanilla_root, check_colors=True)
    stats: dict[str, dict[str, int]] = {}
    for tag in AFFECTED_TAGS:
        provinces = tuple(TAG_PROVINCES[tag])
        development = sum(province_development(value) for value in provinces)
        if development != EXPECTED_DEVELOPMENT[tag]:
            raise ValueError(
                f"{tag}: development {development} != {EXPECTED_DEVELOPMENT[tag]}"
            )
        if set(EXACT_CORE_TAGS[tag]) != set(provinces):
            raise ValueError(f"{tag}: exact-core policy drifted")
        stats[tag] = {"provinces": len(provinces), "development": development}

    for tag in PUBLIC_CITIES:
        history = read_text(COUNTRY_HISTORY / str(POLITIES[tag]["history"]))
        if initial_value(history, "government") != "republic":
            raise ValueError(f"{tag}: public city must be a republic")
        if initial_value(history, "add_government_reform") != "oligarchy_reform":
            raise ValueError(f"{tag}: public city must use oligarchy_reform")
        province = read_text(history_paths(int(POLITIES[tag]["capital"]))[0])
        if initial_cores(province) != {tag}:
            raise ValueError(f"{tag}: public-city capital must have only its own core")
        for path in (MOD / "history/diplomacy").glob("*.txt"):
            if re.search(rf"(?<![A-Z0-9]){tag}(?![A-Z0-9])", read_text(path)):
                raise ValueError(f"{tag}: public city must start independent")

    source_text = SOURCE.read_text(encoding="utf-8-sig")
    for tag, name in LOCALISATION.items():
        for key in (tag, f"{tag}_ADJ"):
            expected = rf'(?m)^\s*{key}:0\s+"{re.escape(name)}"\s*$'
            if len(re.findall(expected, source_text)) != 1:
                raise ValueError(f"{key}: missing one-character B54 localisation")

    return {
        "batch": "B54_changsha_public_cities",
        "countries": stats,
        "public_cities": {tag: LOCALISATION[tag] for tag in PUBLIC_CITIES},
        "independence": "no starting subject relation",
        "geometry": "unchanged",
        "areas": "unchanged",
        "trade_nodes": "unchanged",
        "trade_centres": "unchanged",
        "province_development": "unchanged",
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "manifest_invariants": manifest["invariants"],
        "b43_validation": b43,
    }


def apply(vanilla_root: Path, dependency_roots: tuple[Path, ...]) -> dict[str, object]:
    ensure_climate_membership()
    apply_province_policy(vanilla_root)
    update_tag_file()
    write_localisation()
    write_countries()
    report = validate(vanilla_root, dependency_roots)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA_ROOT)
    parser.add_argument("--dependency-root", action="append", type=Path)
    args = parser.parse_args()
    dependencies = tuple(args.dependency_root or DEFAULT_DEPENDENCY_ROOTS)
    result = (
        validate(args.vanilla_root, dependencies)
        if args.check
        else apply(args.vanilla_root, dependencies)
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
