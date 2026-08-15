#!/usr/bin/env python3
"""Restore E, Quan and Zhou as small starting vassals of Chu."""

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
DIPLOMACY = MOD / "history/diplomacy/gdd_b52_chu_vassals.txt"
SOURCE = MOD / "localisation_source/006_gdd_b52_chu_vassals_readable_utf8.txt"
TARGET = MOD / "localisation/replace/006_gdd_b52_chu_vassals_l_english.yml"
REPORT = ROOT / "planning/chu_vassals_b52/ownership_report.json"
MANIFEST = ROOT / "planning/chu_vassals_b52/batch_manifest.json"
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


VASSAL_TAGS = ("EGU", "QVN", "ZHU")
AFFECTED_TAGS = ("CHC", *VASSAL_TAGS)
EXPECTED_DEVELOPMENT = {"CHC": 134, "EGU": 27, "QVN": 8, "ZHU": 6}
LOCALISATION = {"EGU": "鄂", "QVN": "权", "ZHU": "州"}
CHU_CAPITAL = 2172
TAG_MARKER_BEGIN = "# GDD_B52_CHU_VASSALS_BEGIN"
TAG_MARKER_END = "# GDD_B52_CHU_VASSALS_END"


def history_paths(province_id: int) -> list[Path]:
    paths = sorted(PROVINCE_HISTORY.glob(f"{province_id} - *.txt"))
    if not paths:
        raise ValueError(f"Province {province_id}: missing local history")
    return paths


def diplomacy_text() -> str:
    blocks = ["# B52: restored Chu-affiliated small states."]
    for tag in VASSAL_TAGS:
        blocks.extend(
            (
                "vassal = {",
                "\tfirst = CHC",
                f"\tsecond = {tag}",
                "\tstart_date = 1444.1.1",
                "\tend_date = 1821.1.1",
                "}",
            )
        )
    return "\n".join(blocks) + "\n"


def update_tag_file() -> None:
    text = read_text(TAG_FILE)
    text = re.sub(
        rf"(?ms)^\s*{re.escape(TAG_MARKER_BEGIN)}.*?{re.escape(TAG_MARKER_END)}\s*\n?",
        "",
        text,
    )
    for tag in VASSAL_TAGS:
        text = re.sub(rf'(?m)^\s*{tag}\s*=\s*"[^"]+"\s*\n?', "", text)
    lines = [TAG_MARKER_BEGIN]
    for tag in VASSAL_TAGS:
        lines.append(f'{tag} = "countries/{POLITIES[tag]["file"]}"')
    lines.append(TAG_MARKER_END)
    TAG_FILE.write_text(text.rstrip() + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


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
    for tag in VASSAL_TAGS:
        config = POLITIES[tag]
        capital_text = read_text(history_paths(int(config["capital"]))[0])
        culture = initial_value(capital_text, "culture")
        religion = initial_value(capital_text, "religion")
        (COUNTRIES / str(config["file"])).write_text(
            country_definition(config["color"]), encoding="utf-8"
        )
        (COUNTRY_HISTORY / str(config["history"])).write_text(
            country_history(
                int(config["capital"]), int(config["rank"]), culture, religion
            ),
            encoding="utf-8",
        )
        (FLAGS / f"{tag}.tga").write_bytes(flag_bytes(config["color"]))

    set_existing_country_capital(
        COUNTRY_HISTORY / "CHC - Chu.txt", CHU_CAPITAL, write=True
    )
    DIPLOMACY.parent.mkdir(parents=True, exist_ok=True)
    DIPLOMACY.write_text(diplomacy_text(), encoding="utf-8")


def province_development(province_id: int) -> int:
    text = read_text(history_paths(province_id)[0])
    return sum(
        int(initial_value(text, key))
        for key in ("base_tax", "base_production", "base_manpower")
    )


def scan_tag_collisions(roots: tuple[Path, ...]) -> None:
    for tag in VASSAL_TAGS:
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
    if manifest.get("batch") != "B52_chu_vassals":
        raise ValueError("B52 manifest batch marker is missing")
    targets = manifest.get("opening_territory", {})
    for tag in AFFECTED_TAGS:
        if targets.get(tag) != list(TAG_PROVINCES[tag]):
            raise ValueError(f"{tag}: B52 manifest territory drifted")
    return manifest


def validate(vanilla_root: Path, dependency_roots: tuple[Path, ...]) -> dict[str, object]:
    scan_tag_collisions((vanilla_root, *dependency_roots))
    manifest = validate_manifest()
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

    chu = read_text(COUNTRY_HISTORY / "CHC - Chu.txt")
    if initial_value(chu, "capital") != str(CHU_CAPITAL):
        raise ValueError("Chu capital must be Jiangling/Jingzhou (2172)")
    if initial_value(chu, "fixed_capital") != str(CHU_CAPITAL):
        raise ValueError("Chu fixed capital must be Jiangling/Jingzhou (2172)")

    for tag in VASSAL_TAGS:
        history = read_text(COUNTRY_HISTORY / str(POLITIES[tag]["history"]))
        if initial_value(history, "add_government_reform") != "gdd_local_fiefdom_reform":
            raise ValueError(f"{tag}: must use the existing local-fiefdom reform")
    if read_text(DIPLOMACY) != diplomacy_text():
        raise ValueError("B52 starting-vassal diplomacy drifted")

    source_text = SOURCE.read_text(encoding="utf-8-sig")
    for tag, name in LOCALISATION.items():
        for key in (tag, f"{tag}_ADJ"):
            expected = rf'(?m)^\s*{key}:0\s+"{re.escape(name)}"\s*$'
            if len(re.findall(expected, source_text)) != 1:
                raise ValueError(f"{key}: missing B52 localisation")

    return {
        "batch": "B52_chu_vassals",
        "design": "Chu direct realm plus three restored starting vassals",
        "chu_capital": {"province_id": CHU_CAPITAL, "name": "Jiangling"},
        "countries": stats,
        "vassals": {tag: "CHC" for tag in VASSAL_TAGS},
        "geometry": "unchanged",
        "areas": "unchanged",
        "trade_nodes": "unchanged",
        "trade_centres": "unchanged",
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "manifest_invariants": manifest["invariants"],
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
