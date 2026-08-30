#!/usr/bin/env python3
"""Apply and validate the reviewed 1444 religion geography transaction."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
MANIFEST = ROOT / "planning/religious_geography_1444/religious_geography_manifest.json"
COUNTRIES = MOD / "history/countries"
PROVINCES = MOD / "history/provinces"


def load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def first_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^\s#]+)", text)
    if not match:
        raise ValueError(f"missing initial {key}")
    return match.group(1)


def replace_first_value(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^(\s*{re.escape(key)}\s*=\s*)[^\s#]+")
    changed, count = pattern.subn(rf"\g<1>{value}", text, count=1)
    if count != 1:
        raise ValueError(f"expected one initial {key}, replaced {count}")
    return changed


def province_path(province_id: int) -> Path:
    matches = sorted(PROVINCES.glob(f"{province_id} - *.txt"))
    if len(matches) != 1:
        raise ValueError(f"province {province_id} has {len(matches)} local histories")
    return matches[0]


def apply() -> None:
    manifest = load_manifest()
    for _tag, config in manifest["country_targets"].items():
        if "harmonized" in config:
            raise ValueError(
                "religious geography may not reintroduce retired Harmony state"
            )
        path = COUNTRIES / config["history"]
        text = path.read_text(encoding="latin-1")
        text = replace_first_value(text, "religion", config["religion"])
        path.write_text(text, encoding="latin-1")

    for religion, province_ids in manifest["province_targets"].items():
        for province_id in province_ids:
            path = province_path(province_id)
            text = path.read_text(encoding="latin-1")
            path.write_text(
                replace_first_value(text, "religion", religion),
                encoding="latin-1",
            )

    for filename in manifest["retired_history_files"]:
        (PROVINCES / filename).unlink(missing_ok=True)


def validate() -> dict[str, int]:
    manifest = load_manifest()
    seen_provinces: dict[int, str] = {}
    for religion, province_ids in manifest["province_targets"].items():
        for province_id in province_ids:
            if province_id in seen_provinces:
                raise ValueError(
                    f"province {province_id} is assigned to both "
                    f"{seen_provinces[province_id]} and {religion}"
                )
            seen_provinces[province_id] = religion
            actual = first_value(
                province_path(province_id).read_text(encoding="latin-1"),
                "religion",
            )
            if actual != religion:
                raise ValueError(
                    f"province {province_id}: religion {actual}, expected {religion}"
                )

    for tag, config in manifest["country_targets"].items():
        if "harmonized" in config:
            raise ValueError(f"{tag}: retired manifest field 'harmonized' returned")
        path = COUNTRIES / config["history"]
        text = path.read_text(encoding="latin-1")
        actual = first_value(text, "religion")
        if actual != config["religion"]:
            raise ValueError(f"{tag}: religion {actual}, expected {config['religion']}")

    for path in sorted(COUNTRIES.glob("*.txt")):
        text = path.read_text(encoding="latin-1")
        if re.search(r"(?m)^\s*add_harmonized_religion\s*=", text):
            raise ValueError(f"{path.name}: retired Harmony history effect returned")

    for filename in manifest["retired_history_files"]:
        if (PROVINCES / filename).exists():
            raise ValueError(f"retired orphan history returned: {filename}")

    return {
        "countries": len(manifest["country_targets"]),
        "provinces": len(seen_provinces),
        "retired_histories": len(manifest["retired_history_files"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        apply()
    result = validate()
    print(
        "ZHX_RELIGIOUS_GEOGRAPHY_VALID; "
        f"countries={result['countries']}; provinces={result['provinces']}; "
        f"retired_histories={result['retired_histories']}"
    )


if __name__ == "__main__":
    main()
