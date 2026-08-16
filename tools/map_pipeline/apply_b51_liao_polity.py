#!/usr/bin/env python3
"""Invest a Khitan Liao state in the six-province Liaodong area."""

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
SOURCE = MOD / "localisation_source/005_gdd_b51_liao_polity_readable_utf8.txt"
TARGET = MOD / "localisation/replace/005_gdd_b51_liao_polity_l_english.yml"
REPORT = ROOT / "planning/liao_polity_b51/ownership_report.json"
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
    should_remove_core,
    validate as validate_b43,
)


LIAODONG_IDS = (726, 5204, 5205, 2112, 4652, 2113)
EXPECTED_DEVELOPMENT = {"YAN": 123, "LIO": 58}
TAG_MARKER_BEGIN = "# GDD_B51_LIAO_POLITY_BEGIN"
TAG_MARKER_END = "# GDD_B51_LIAO_POLITY_END"


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
    text = re.sub(r'(?m)^\s*LIO\s*=\s*"[^"]+"\s*\n?', "", text)
    block = "\n".join(
        (
            TAG_MARKER_BEGIN,
            'LIO = "countries/B51_Liao.txt"',
            TAG_MARKER_END,
        )
    )
    TAG_FILE.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8")


def write_localisation() -> None:
    SOURCE.write_text(
        'l_english:\n LIO:0 "辽"\n LIO_ADJ:0 "辽"\n', encoding="utf-8-sig"
    )
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file, verify_file

    encode_file(SOURCE, TARGET)
    verify_file(SOURCE, TARGET)


def apply_province_policy(vanilla_root: Path) -> None:
    for tag in ("YAN", "LIO"):
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


def write_country() -> None:
    config = POLITIES["LIO"]
    capital_text = read_text(history_paths(int(config["capital"]))[0])
    capital_religion = initial_value(capital_text, "religion")
    (COUNTRIES / str(config["file"])).write_text(
        country_definition(config["color"]), encoding="utf-8"
    )
    (COUNTRY_HISTORY / str(config["history"])).write_text(
        country_history(
            int(config["capital"]),
            int(config["rank"]),
            str(config["culture"]),
            capital_religion,
            tuple(config["accepted"]),
        ),
        encoding="utf-8",
    )
    (FLAGS / "LIO.tga").write_bytes(flag_bytes(config["color"]))


def province_development(province_id: int) -> int:
    text = read_text(history_paths(province_id)[0])
    return sum(
        int(initial_value(text, key))
        for key in ("base_tax", "base_production", "base_manpower")
    )


def scan_tag_collisions(roots: tuple[Path, ...]) -> None:
    matches: list[str] = []
    for root in roots:
        directory = root / "common/country_tags"
        if not directory.exists():
            continue
        for path in directory.glob("*.txt"):
            if re.search(r"(?m)^\s*LIO\s*=", read_text(path)):
                matches.append(str(path))
    if matches:
        raise ValueError(f"LIO conflicts with dependency tag(s): {matches}")


def validate(vanilla_root: Path, dependency_roots: tuple[Path, ...]) -> dict[str, object]:
    scan_tag_collisions((vanilla_root, *dependency_roots))
    if tuple(TAG_PROVINCES["LIO"]) != LIAODONG_IDS:
        raise ValueError("LIO must own exactly the canonical liaoning_area province list")
    b43 = validate_b43(vanilla_root, check_colors=True)

    stats: dict[str, dict[str, int]] = {}
    for tag in ("YAN", "LIO"):
        provinces = tuple(TAG_PROVINCES[tag])
        development = sum(province_development(province_id) for province_id in provinces)
        if development != EXPECTED_DEVELOPMENT[tag]:
            raise ValueError(
                f"{tag}: development {development} != {EXPECTED_DEVELOPMENT[tag]}"
            )
        if set(EXACT_CORE_TAGS[tag]) != set(provinces):
            raise ValueError(f"{tag}: exact-core policy drifted")
        stats[tag] = {"provinces": len(provinces), "development": development}

    history = read_text(COUNTRY_HISTORY / "LIO - Liao.txt")
    if initial_value(history, "capital") != "5204":
        raise ValueError("LIO capital must be Liaoyang (5204)")
    if initial_value(history, "primary_culture") != "mongol":
        raise ValueError("LIO must use mongol as the temporary Khitan gameplay proxy")
    accepted = set(re.findall(r"(?m)^\s*add_accepted_culture\s*=\s*(\S+)", history))
    if accepted != {"manchu", "gdd_qi"}:
        raise ValueError(f"LIO accepted-culture policy drifted: {sorted(accepted)}")

    source_text = SOURCE.read_text(encoding="utf-8-sig")
    for key in ("LIO", "LIO_ADJ"):
        if len(re.findall(rf'(?m)^\s*{key}:0\s+"辽"\s*$', source_text)) != 1:
            raise ValueError(f"{key}: missing readable localisation")

    return {
        "batch": "B51_liao_polity",
        "setting": "Khitan ruling house invested by the Zhou court as a member polity",
        "capital": {"province_id": 5204, "name": "Liaoyang"},
        "geometry": "unchanged",
        "areas": "unchanged",
        "trade_nodes": "unchanged",
        "trade_centres": "unchanged",
        "countries": stats,
        "b43_validation": b43,
    }


def apply(vanilla_root: Path, dependency_roots: tuple[Path, ...]) -> dict[str, object]:
    apply_province_policy(vanilla_root)
    update_tag_file()
    write_country()
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
