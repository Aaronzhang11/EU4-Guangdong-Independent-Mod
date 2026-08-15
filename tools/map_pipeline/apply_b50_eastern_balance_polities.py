#!/usr/bin/env python3
"""Apply B50 eastern political fragmentation without changing map geometry.

The transaction weakens WUU, YUE and XU2 by creating Huai and Ou, plus the
one-character commercial cities Yang, Wu and Zhou.  It intentionally leaves
trade nodes, centres of trade, areas and province development untouched.
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
TAG_FILE = MOD / "common/country_tags/gdd_country_tags.txt"
SOURCE = MOD / "localisation_source/004_gdd_b50_eastern_polities_readable_utf8.txt"
TARGET = MOD / "localisation/replace/004_gdd_b50_eastern_polities_l_english.yml"
REPORT = ROOT / "planning/eastern_balance_b50/ownership_report.json"
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
    set_existing_country_capital,
    should_remove_core,
    validate as validate_b43,
)


B50_TAGS = ("HUA", "OUE", "HYM", "WHU", "ZHO")
PUBLIC_CITIES = ("HYM", "WHU", "ZHO")
AFFECTED_TAGS = ("WUU", "YUE", "MIN", "XU2", *B50_TAGS)
CUSTOM_TAGS = ("OUE", "HYM", "WHU", "ZHO")
CORE_EXCEPTIONS = {"XU2": {2144}}
EXPECTED_DEVELOPMENT = {
    "WUU": 112,
    "YUE": 119,
    "MIN": 121,
    "XU2": 59,
    "HUA": 51,
    "OUE": 27,
    "HYM": 35,
    "WHU": 12,
    "ZHO": 6,
}
LOCALISATION = {
    "HUA": "淮",
    "OUE": "瓯",
    "HYM": "扬",
    "WHU": "芜",
    "ZHO": "舟",
}
TAG_MARKER_BEGIN = "# GDD_B50_EASTERN_BALANCE_BEGIN"
TAG_MARKER_END = "# GDD_B50_EASTERN_BALANCE_END"


def history_paths(province_id: int) -> list[Path]:
    paths = sorted(PROVINCE_HISTORY.glob(f"{province_id} - *.txt"))
    if not paths:
        raise ValueError(f"Province {province_id}: missing local history")
    return paths


def update_tag_file() -> None:
    text = read_text(TAG_FILE)
    text = re.sub(
        rf"(?ms)^\s*{re.escape(TAG_MARKER_BEGIN)}.*?{re.escape(TAG_MARKER_END)}\s*\n?",
        "",
        text,
    )
    for tag in B50_TAGS:
        text = re.sub(rf'(?m)^\s*{tag}\s*=\s*"[^"]+"\s*\n?', "", text)
    lines = [TAG_MARKER_BEGIN]
    for tag in B50_TAGS:
        lines.append(f'{tag} = "countries/{POLITIES[tag]["file"]}"')
    lines.append(TAG_MARKER_END)
    TAG_FILE.write_text(text.rstrip() + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


def write_localisation() -> None:
    lines = ["l_english:"]
    for tag, name in LOCALISATION.items():
        lines.append(f' {tag}:0 "{name}"')
        lines.append(f' {tag}_ADJ:0 "{name}"')
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

    for tag, province_ids in CORE_EXCEPTIONS.items():
        for province_id in province_ids:
            for path in history_paths(province_id):
                old = read_text(path)
                if tag in initial_cores(old):
                    continue
                initial, dated = old, ""
                match = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", old)
                if match:
                    initial, dated = old[:match.start()], old[match.start():]
                owner_line = re.search(r"(?m)^\s*add_core\s*=.*$", initial)
                if owner_line is None:
                    raise ValueError(f"{path.name}: no core insertion point")
                initial = (
                    initial[:owner_line.end()]
                    + f"\nadd_core = {tag}"
                    + initial[owner_line.end():]
                )
                path.write_text(initial + dated, encoding="utf-8")


def write_countries() -> None:
    COUNTRIES.mkdir(parents=True, exist_ok=True)
    COUNTRY_HISTORY.mkdir(parents=True, exist_ok=True)
    FLAGS.mkdir(parents=True, exist_ok=True)
    for tag in B50_TAGS:
        config = POLITIES[tag]
        capital_history = read_text(history_paths(int(config["capital"]))[0])
        culture = initial_value(capital_history, "culture")
        religion = initial_value(capital_history, "religion")
        (COUNTRIES / str(config["file"])).write_text(
            country_definition(config["color"]), encoding="utf-8"
        )
        (COUNTRY_HISTORY / str(config["history"])).write_text(
            country_history(
                int(config["capital"]),
                int(config["rank"]),
                culture,
                religion,
                tuple(config.get("accepted", ())),
                str(config.get("government", "monarchy")),
                str(config.get("reform", "gdd_local_fiefdom_reform")),
            ),
            encoding="utf-8",
        )
        (FLAGS / f"{tag}.tga").write_bytes(flag_bytes(config["color"]))
    set_existing_country_capital(COUNTRY_HISTORY / "XU2 - Xu2.txt", 2141, write=True)


def province_development(province_id: int) -> int:
    text = read_text(history_paths(province_id)[0])
    return sum(
        int(initial_value(text, key))
        for key in ("base_tax", "base_production", "base_manpower")
    )


def scan_tag_collisions(dependency_roots: tuple[Path, ...]) -> None:
    for tag in CUSTOM_TAGS:
        matches: list[str] = []
        for root in dependency_roots:
            tag_dir = root / "common/country_tags"
            if not tag_dir.exists():
                continue
            for path in tag_dir.glob("*.txt"):
                if re.search(rf"(?m)^\s*{tag}\s*=", read_text(path)):
                    matches.append(str(path))
        if matches:
            raise ValueError(f"{tag}: conflicts with dependency tag(s): {matches}")


def validate(vanilla_root: Path, dependency_roots: tuple[Path, ...]) -> dict[str, object]:
    scan_tag_collisions((vanilla_root, *dependency_roots))
    b43 = validate_b43(vanilla_root, check_colors=True)
    stats: dict[str, dict[str, int]] = {}
    for tag in AFFECTED_TAGS:
        provinces = tuple(TAG_PROVINCES[tag])
        development = sum(province_development(province_id) for province_id in provinces)
        if development != EXPECTED_DEVELOPMENT[tag]:
            raise ValueError(
                f"{tag}: development {development} != {EXPECTED_DEVELOPMENT[tag]}"
            )
        stats[tag] = {"provinces": len(provinces), "development": development}
        expected_cores = set(provinces) | CORE_EXCEPTIONS.get(tag, set())
        if set(EXACT_CORE_TAGS[tag]) != expected_cores:
            raise ValueError(f"{tag}: B43 exact-core policy drifted")

    for tag in PUBLIC_CITIES:
        history = read_text(COUNTRY_HISTORY / str(POLITIES[tag]["history"]))
        if initial_value(history, "government") != "republic":
            raise ValueError(f"{tag}: commercial city must use a basic republic")
        if initial_value(history, "add_government_reform") != "oligarchy_reform":
            raise ValueError(f"{tag}: commercial city must use the vanilla oligarchy baseline")

    if set(TAG_PROVINCES["ZHO"]) != {5004} or 2149 not in TAG_PROVINCES["YUE"]:
        raise ValueError("Zhou must occupy Zhoushan (5004), while Ningbo (2149) remains YUE")

    source_text = SOURCE.read_text(encoding="utf-8-sig")
    for tag, name in LOCALISATION.items():
        for key in (tag, f"{tag}_ADJ"):
            expected = rf'(?m)^\s*{key}:0\s+"{re.escape(name)}"\s*$'
            if len(re.findall(expected, source_text)) != 1:
                raise ValueError(f"{key}: missing one-character B50 localisation")

    return {
        "batch": "B50_eastern_balance_polities",
        "geometry": "unchanged",
        "areas": "unchanged",
        "trade_nodes": "unchanged",
        "trade_centres": "unchanged",
        "countries": stats,
        "public_cities": {tag: LOCALISATION[tag] for tag in PUBLIC_CITIES},
        "b43_validation": b43,
    }


def apply(vanilla_root: Path, dependency_roots: tuple[Path, ...]) -> dict[str, object]:
    apply_province_policy(vanilla_root)
    update_tag_file()
    write_countries()
    write_localisation()
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
