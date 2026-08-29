#!/usr/bin/env python3
"""Validate the dormant LGU country tag and its small-seal stamp flag."""

from __future__ import annotations

import importlib.util
import hashlib
import re
import struct
import sys
from pathlib import Path

from apply_culture_country_name_pools import apply as check_country_name_pools
from generate_liang_small_seal_mask import run as check_liang_mask
from generate_zhuxia_seal_flags import run as check_zhuxia_flags


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
VANILLA = Path.home() / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
DEPENDENCIES = (
    Path.home() / "Library/Application Support/Steam/steamapps/workshop/content/236850/2976470733",
    Path.home() / "Library/Application Support/Steam/steamapps/workshop/content/236850/1999055990",
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def tag_declarations(root: Path) -> list[Path]:
    directory = root / "common/country_tags"
    if not directory.exists():
        return []
    result: list[Path] = []
    pattern = re.compile(r"(?m)^\s*LGU\s*=")
    for path in directory.glob("*.txt"):
        if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
            result.append(path)
    return result


def load_encoder():
    path = ROOT / "tools/encode_eu4_chinese_localisation.py"
    spec = importlib.util.spec_from_file_location("gdd_localisation_encoder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load localisation encoder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    errors: list[str] = []
    external = tag_declarations(VANILLA)
    for dependency in DEPENDENCIES:
        external.extend(tag_declarations(dependency))
    local = tag_declarations(MOD)
    require(not external, f"LGU collides outside the mod: {external}", errors)
    require(len(local) == 1, f"LGU must have one local declaration, found {local}", errors)

    country = MOD / "common/countries/B76_Liang.txt"
    history = MOD / "history/countries/LGU - Liang.txt"
    flag = MOD / "gfx/flags/LGU.tga"
    reference = ROOT / "tools/assets/liang_flag/liang_small_seal_reference.png"
    for path in (country, history, flag):
        require(path.exists(), f"missing asset: {path}", errors)
    require(reference.exists(), f"missing approved glyph reference: {reference}", errors)
    if reference.exists():
        require(
            hashlib.sha256(reference.read_bytes()).hexdigest()
            == "813697811e0964bdb0b59722ec427f67e28d820fb8bd61f00b5d3e298d9de437",
            "approved LGU glyph reference hash drifted",
            errors,
        )

    if country.exists():
        data = country.read_bytes()
        require(b"color = { 48 91 112 }" in data, "LGU country colour drifted", errors)
        require(b"graphical_culture = asiangfx" in data, "LGU graphical culture missing", errors)
        require(data.count(b"monarch_names = {") == 1, "LGU monarch name pool missing or duplicated", errors)
        require(data.count(b"leader_names = {") == 1, "LGU leader name pool missing or duplicated", errors)
    if history.exists():
        text = history.read_text(encoding="utf-8")
        expected = (
            "government = monarchy",
            "add_government_reform = feudalism_reform",
            "technology_group = chinese",
            "religion = confucianism",
            "primary_culture = gdd_long",
            "capital = 708",
        )
        for token in expected:
            require(token in text, f"LGU history missing: {token}", errors)
        require("fixed_capital" not in text, "dormant LGU must not force an unowned capital", errors)

    culture_policy = (ROOT / "tools/map_pipeline/apply_culture_overhaul.py").read_text(encoding="utf-8")
    require(
        culture_policy.count('"LGU": ("gdd_long", ()),') == 1,
        "LGU culture-overhaul replay policy missing or duplicated",
        errors,
    )

    province_refs: list[str] = []
    reference = re.compile(r"(?m)^\s*(?:owner|controller|add_core)\s*=\s*LGU\s*$")
    for path in (MOD / "history/provinces").glob("*.txt"):
        if reference.search(path.read_text(encoding="utf-8", errors="ignore")):
            province_refs.append(path.name)
    require(not province_refs, f"LGU must start without ownership or cores: {province_refs}", errors)

    source = MOD / "localisation_source/gdd_liang_restoration_readable_utf8.txt"
    target = MOD / "localisation/gdd_liang_restoration_l_english.yml"
    if source.exists() and target.exists():
        source_text = source.read_text(encoding="utf-8-sig")
        require(len(re.findall(r"(?m)^\s*LGU:0\s+\"凉\"\s*$", source_text)) == 1, "LGU name localisation missing or duplicated", errors)
        require(len(re.findall(r"(?m)^\s*LGU_ADJ:0\s+\"凉\"\s*$", source_text)) == 1, "LGU adjective localisation missing or duplicated", errors)
        try:
            load_encoder().verify_file(source, target)
        except Exception as exc:
            errors.append(f"LGU localisation round trip failed: {exc}")
    else:
        errors.append("LGU readable/generated localisation pair missing")

    if flag.exists():
        data = flag.read_bytes()
        require(len(data) == 18 + 128 * 128 * 3, f"unexpected LGU TGA size: {len(data)}", errors)
        if len(data) >= 18:
            _, _, image_type, _, _, _, _, _, width, height, bpp, descriptor = struct.unpack("<BBBHHBHHHHBB", data[:18])
            require(image_type == 2, "LGU flag must be uncompressed true-colour TGA", errors)
            require((width, height, bpp) == (128, 128, 24), f"LGU flag header drifted: {(width, height, bpp)}", errors)
            require(descriptor & 0x20 != 0, "LGU flag must use top-left origin", errors)

    try:
        check_liang_mask(check=True)
    except Exception as exc:
        errors.append(f"LGU small-seal mask check failed: {exc}")
    try:
        check_zhuxia_flags(check=True)
    except Exception as exc:
        errors.append(f"Zhuxia flag policy check failed: {exc}")
    try:
        check_country_name_pools(VANILLA, check=True)
    except Exception as exc:
        errors.append(f"LGU country name-pool check failed: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Liang restoration tag validation passed: LGU is unique, dormant, localised, and has a current small-seal stamp flag.")


if __name__ == "__main__":
    main()
