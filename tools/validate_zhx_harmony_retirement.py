#!/usr/bin/env python3
"""Validate the fresh-campaign contract which retires vanilla Harmony.

The Ritual Teaching source of truth is doctrine practice plus named-academy
thought tension.  Native Harmony GUI identifiers may remain as a dormant
engine shell, but production gameplay scripts must never read or write the old
Harmony state machine again.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
DEFAULT_VANILLA = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)

GAMEPLAY_DIRS = (
    "common",
    "decisions",
    "events",
    "history",
    "missions",
)

LEGACY_PATTERNS = {
    "uses_harmony": r"(?m)^\s*uses_harmony\s*=",
    "harmony value": r"(?m)^\s*harmony\s*=",
    "add_harmony": r"(?m)^\s*add_harmony\s*=",
    "yearly_harmony": r"(?m)^\s*yearly_harmony\s*=",
    "harmonization_speed": r"(?m)^\s*harmonization_speed\s*=",
    "add_harmonized_religion": r"(?m)^\s*add_harmonized_religion\s*=",
    "has_harmonized_with": r"(?m)^\s*(?:NOT\s*=\s*\{\s*)?has_harmonized_with\s*=",
    "is_harmonizing_with": r"(?m)^\s*is_harmonizing_with\s*=",
    "harmonization_progress": r"(?m)^\s*harmonization_progress\s*=",
    "add_harmonization_progress": r"(?m)^\s*add_harmonization_progress\s*=",
    "num_of_harmonized": r"(?m)^\s*num_of_harmonized\s*=",
    "full_loyalty_on_harmonization": r"(?m)^\s*full_loyalty_on_harmonization\s*=",
    "has_owner_harmonized_religion": r"(?m)^\s*has_owner_harmonized_religion\s*=",
}

PINNED_OVERRIDES = (
    "missions/DOM_Chinese_Missions.txt",
    "missions/DOM_Japanese_Missions.txt",
    "missions/Japanese_Missions.txt",
    "missions/Korean_Missions.txt",
    "missions/Manchu_Missions.txt",
    "missions/zzz_WoC_Shared_Horde_Missions.txt",
    "missions/zzzz_WoC_EoC_Yuan_Missions.txt",
    "decisions/ManchuDecisions.txt",
    "events/Shinto.txt",
    "events/Confucianism.txt",
    "common/scripted_effects/01_scripted_effects_for_estates.txt",
    "decisions/ShintoConversion.txt",
    "common/scripted_effects/02_scripted_effects_preview_missions.txt",
    "common/rebel_types/confucianism.txt",
    "events/Religious.txt",
)

LIJIAO_CULTURES = {
    "gdd_zhongyuan",
    "gdd_jianghuai",
    "gdd_chu",
    "gdd_gan",
    "gdd_hakka",
    "gdd_gui",
    "gdd_shu",
    "gdd_dian",
    "gdd_jin",
    "gdd_qi",
    "gdd_yan",
    "gdd_long",
    "gdd_wu",
    "gdd_min",
    "gdd_guangfu",
    "gdd_diqiang",
    "gdd_songwei",
    "gdd_dongyi",
}

LIJIAO_EXCLUDED_TAGS = {
    "BD2",
    "BMY",
    "DCH",
    "DZH",
    "GYA",
    "GZH",
    "HZH",
}

LIJIAO_REJECTED_1444_TAGS = {
    "AMD",
    "BD2",
    "BMY",
    "CGS",
    "DAI",
    "DCH",
    "DZH",
    "GYA",
    "GZH",
    "HZH",
    "JRG",
    "KOR",
    "LIL",
    "LIO",
    "LSH",
    "MDL",
    "NUN",
    "NZA",
    "TZZ",
    "WLM",
    "YEL",
}


class ContractError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"missing required file: {path.relative_to(ROOT)}")
    # Full-file 1.37.5 overrides retain a few Latin-1 bytes in vanilla comments.
    return path.read_bytes().decode("latin-1")


def validate_braces(label: str, text: str) -> None:
    depth = 0
    in_string = False
    in_comment = False
    escaped = False
    for char in text:
        if in_comment:
            if char == "\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            require(depth >= 0, f"{label}: closing brace without opener")
    require(not in_string and depth == 0, f"{label}: unbalanced Clausewitz text")


def named_block(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    require(match is not None, f"missing block {key}")
    opening = text.find("{", match.start())
    depth = 0
    in_string = False
    in_comment = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if in_comment:
            if char == "\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index]
    raise ContractError(f"block {key} has no closing brace")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_generated_outputs(vanilla_root: Path) -> None:
    retirement = load_module(
        ROOT / "tools/build_zhx_harmony_retirement.py",
        "zhx_harmony_retirement_builder_validation",
    )
    outputs = retirement.build(vanilla_root)
    require(set(outputs) == set(PINNED_OVERRIDES), "pinned override set changed")
    for relative, expected in outputs.items():
        path = MOD / relative
        validate_braces(relative, expected)
        require(
            path.is_file() and path.read_bytes() == expected.encode("latin-1"),
            f"stale pinned Harmony-retirement override: {relative}",
        )

    religion_builder = load_module(
        ROOT / "tools/build_zhx_religions.py",
        "zhx_religion_builder_harmony_validation",
    )
    religion_path = MOD / "common/religions/00_religion.txt"
    expected_religion = religion_builder.render(vanilla_root)
    validate_braces("common/religions/00_religion.txt", expected_religion)
    require(
        religion_path.read_text(encoding="utf-8") == expected_religion,
        "stale generated religion override",
    )
    confucian = named_block(expected_religion, "confucianism")
    require("uses_harmony" not in confucian, "Confucianism still owns vanilla Harmony")


def check_no_gameplay_legacy_tokens() -> int:
    checked = 0
    failures: list[str] = []
    for directory in GAMEPLAY_DIRS:
        for path in sorted((MOD / directory).rglob("*.txt")):
            checked += 1
            text = read(path)
            validate_braces(str(path.relative_to(ROOT)), text)
            for label, pattern in LEGACY_PATTERNS.items():
                match = re.search(pattern, text)
                if match is not None:
                    line = text.count("\n", 0, match.start()) + 1
                    failures.append(f"{path.relative_to(ROOT)}:{line}: {label}")
    require(
        not failures,
        "live vanilla-Harmony API calls remain:\n  " + "\n  ".join(failures),
    )
    return checked


def check_cohesion_contract() -> None:
    path = MOD / "common/scripted_triggers/zhx_doctrine_triggers.txt"
    text = read(path)
    eligibility = named_block(text, "zhx_can_adopt_lijiao")
    cultures = set(re.findall(r"primary_culture\s*=\s*([a-z0-9_]+)", eligibility))
    require(cultures == LIJIAO_CULTURES, "Ritual Teaching culture eligibility drifted")
    require("tag = JIZ" in eligibility, "Jizi Joseon eligibility exception is missing")
    excluded = set(
        re.findall(
            r"tag\s*=\s*([A-Z0-9]{3})\s*#",
            eligibility,
        )
    )
    require(
        excluded == LIJIAO_EXCLUDED_TAGS,
        "non-Zhuxia tag exclusions drifted from the religious-geography contract",
    )

    def history_values(tag: str) -> tuple[str, str]:
        matches = sorted((MOD / "history/countries").glob(f"{tag} - *.txt"))
        require(len(matches) == 1, f"{tag}: expected one country history")
        history = read(matches[0])
        religion = re.search(r"(?m)^\s*religion\s*=\s*([^\s#]+)", history)
        culture = re.search(r"(?m)^\s*primary_culture\s*=\s*([^\s#]+)", history)
        require(religion is not None and culture is not None, f"{tag}: incomplete country history")
        return religion.group(1), culture.group(1)

    def eligible(tag: str, culture: str) -> bool:
        return tag not in LIJIAO_EXCLUDED_TAGS and (
            tag == "JIZ" or culture in LIJIAO_CULTURES
        )

    opening_manifest = json.loads(
        (ROOT / "planning/religion_opening_schools/opening_schools_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    opening_tags = {
        tag
        for school in opening_manifest["schools"].values()
        for tag in school["tags"]
    }
    require(len(opening_tags) == 65, "opening school manifest no longer has 65 unique tags")
    for tag in sorted(opening_tags):
        religion, culture = history_values(tag)
        require(religion == "confucianism", f"{tag}: opening school country is not Ritual Teaching")
        require(eligible(tag, culture), f"{tag}: opening school country fails the live eligibility gate")

    for tag in sorted(LIJIAO_REJECTED_1444_TAGS):
        religion, culture = history_values(tag)
        require(not eligible(tag, culture), f"{tag}: non-Zhuxia country passes the live eligibility gate")
        require(religion != "confucianism", f"{tag}: non-Zhuxia country starts as hollow Ritual Teaching")

    lijiao = named_block(text, "zhx_is_lijiao_country")
    require("religion = confucianism" in lijiao and "zhx_can_adopt_lijiao = yes" in lijiao,
            "Ritual Teaching identity does not enforce the Zhuxia eligibility gate")
    expected = {
        75: ("value = 50", ("zhx_academy_tension_heavy",)),
        80: (
            "value = 50",
            ("zhx_academy_tension_medium", "zhx_academy_tension_heavy"),
        ),
        90: (
            "value = 75",
            ("zhx_academy_tension_medium", "zhx_academy_tension_heavy"),
        ),
        100: (
            "value = 75",
            (
                "zhx_academy_tension_mild",
                "zhx_academy_tension_medium",
                "zhx_academy_tension_heavy",
            ),
        ),
    }
    for tier, (practice, forbidden_tensions) in expected.items():
        body = named_block(text, f"zhx_lijiao_cohesion_{tier}")
        require("zhx_is_lijiao_country = yes" in body, f"cohesion {tier} lacks Lijiao gate")
        require("zhx_has_doctrine = yes" in body, f"cohesion {tier} lacks doctrine gate")
        require(practice in body, f"cohesion {tier} has the wrong practice threshold")
        found = tuple(
            tension
            for tension in (
                "zhx_academy_tension_mild",
                "zhx_academy_tension_medium",
                "zhx_academy_tension_heavy",
            )
            if tension in body
        )
        require(found == forbidden_tensions, f"cohesion {tier} has the wrong tension gate")


def check_retired_events_and_conversion() -> None:
    confucian_events = read(MOD / "events/Confucianism.txt")
    ids = tuple(int(value) for value in re.findall(r"id\s*=\s*confucian_events\.(\d+)", confucian_events))
    require(ids == (*range(1, 11), 19, 20), "Confucian compatibility event IDs changed")
    require(confucian_events.count("trigger = { always = no }") == 12,
            "every Confucian compatibility event must be inert")
    require(confucian_events.count("title = \"confucian_events.") == 12
            and confucian_events.count("desc = \"confucian_events.") == 12
            and confucian_events.count("picture = ") == 12,
            "every Confucian compatibility event must satisfy the engine presentation schema")

    chinese_empire = read(MOD / "events/ChineseEmpire.txt")
    emperor_stub = named_block(chinese_empire, "country_event")
    require("id = celestial_empire_events.1" in emperor_stub,
            "unexpected first Chinese Empire event")
    require(
        re.search(
            r"id\s*=\s*celestial_empire_events\.2.*?title\s*=.*?desc\s*=.*?picture\s*=.*?"
            r"trigger\s*=\s*\{\s*always\s*=\s*no\s*\}",
            chinese_empire,
            flags=re.S,
        ) is not None,
        "automatic Emperor conversion event is not inert",
    )

    shinto = read(MOD / "events/Shinto.txt")
    require(
        "trigger = { always = no } # ZHX: non-Zhuxia states cannot adopt Ritual Teaching here"
        in shinto,
        "Shinto forced Ritual Teaching option is not blocked",
    )
    manchu = read(MOD / "decisions/ManchuDecisions.txt")
    require("change_religion = confucianism" not in manchu,
            "Manchu formation still forces Ritual Teaching")
    shinto_decision = read(MOD / "decisions/ShintoConversion.txt")
    require(
        "always = no # ZHX: Ritual Teaching is unavailable through the Shinto conversion decision"
        in shinto_decision,
        "Shinto Ritual Teaching conversion decision is still visible",
    )
    horde_effects = read(MOD / "common/scripted_effects/02_scripted_effects_preview_missions.txt")
    require("change_religion = confucianism" not in horde_effects,
            "Horde mission selection still forces Ritual Teaching")
    require("set_country_flag = hordes_tolerance_branch_flag" in horde_effects,
            "ineligible Horde Confucian branch lacks a safe fallback")
    horde_missions = read(MOD / "missions/zzz_WoC_Shared_Horde_Missions.txt")
    require("is_or_was_mongol_nation = yes" not in horde_missions,
            "non-Ritual-Teaching Mongol countries may still select the Confucian branch")
    japanese_missions = read(MOD / "missions/Japanese_Missions.txt")
    require(japanese_missions.count("tolerance_to_this = 3") == 4,
            "Ainu accommodation must test the tolerance of each actual province religion")
    korean_missions = read(MOD / "missions/Korean_Missions.txt")
    require(
        "has_global_modifier_value = { which = tolerance_heretic value = 3 }"
        in korean_missions,
        "Korean Shinto accommodation must use the same-group tolerance threshold",
    )
    rebels = read(MOD / "common/rebel_types/confucianism.txt")
    require(rebels.count("zhx_can_adopt_lijiao = yes") >= 3,
            "Confucian rebels do not enforce spawn, province, and country eligibility")
    religious = read(MOD / "events/Religious.txt")
    require(religious.count("zhx_can_adopt_lijiao = yes") >= 5,
            "generic country/province conversion events do not enforce eligibility")

    lifecycle = read(MOD / "events/zhx_doctrine_events.txt")
    require(
        re.search(
            r"id\s*=\s*zhx_doctrine\.92.*?country_event\s*=\s*\{\s*id\s*=\s*zhx_doctrine\.1\s+days\s*=\s*1\s*\}",
            lifecycle,
            flags=re.S,
        ) is not None,
        "generic conversion into Ritual Teaching does not schedule school foundation",
    )
    lifecycle_event = named_block(lifecycle[lifecycle.index("id = zhx_doctrine.92"):], "trigger")
    require(
        "religion_group = eastern" in lifecycle_event
        and lifecycle_event.count("religious_school = {") == 6,
        "religion changes do not clear a stale six-school mirror after a non-eastern round-trip",
    )
    require(
        "change_religion = capital" in lifecycle
        and "change_religion = animism" in lifecycle,
        "an ineligible country can retain a hollow Ritual Teaching after forced conversion",
    )
    on_actions = read(MOD / "common/on_actions/zhx_system_on_actions.txt")
    startup = named_block(on_actions, "on_startup")
    culture_change = named_block(on_actions, "on_primary_culture_changed")
    released = named_block(on_actions, "on_country_released")
    require(
        startup.count("zhx_doctrine.92") == 1
        and culture_change.count("zhx_doctrine.92") == 1
        and released.count("zhx_doctrine.92") == 1,
        "custom-nation startup, primary-culture changes or released countries do not "
        "re-evaluate Ritual Teaching eligibility",
    )


def check_fresh_campaign_sources() -> None:
    manifest = (ROOT / "planning/religious_geography_1444/religious_geography_manifest.json").read_text(
        encoding="utf-8"
    )
    require('"harmonized"' not in manifest, "religious geography still declares harmonized religions")
    changsheng = read(MOD / "history/countries/CGS - Changsheng.txt")
    require(
        "religion = animism" in changsheng and "religion = confucianism" not in changsheng,
        "the Zhuang Changsheng polity still starts as a hollow Ritual Teaching country",
    )

    applicator = (ROOT / "tools/apply_zhx_religious_geography.py").read_text(encoding="utf-8")
    require('if "harmonized" in config:' in applicator,
            "geography applicator does not reject retired manifest state")
    require("add_harmonized_religion" in applicator,
            "geography applicator does not reject retired country-history state")

    presentation = (
        MOD / "localisation_source/015_gdd_b74_lijiao_presentation_readable_utf8.txt"
    ).read_text(encoding="utf-8-sig")
    for key in (
        "string_start_religion_confucianism",
        "string_harmonization_info",
        "string_harmonization_info_no",
    ):
        require(key in presentation, f"missing retired-Harmony presentation key {key}")
    require("原版宗教调和" in presentation,
            "start presentation does not explain that vanilla harmonization is retired")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA)
    args = parser.parse_args()

    check_generated_outputs(args.vanilla_root.resolve())
    checked_files = check_no_gameplay_legacy_tokens()
    check_cohesion_contract()
    check_retired_events_and_conversion()
    check_fresh_campaign_sources()
    print(
        "ZHX_HARMONY_RETIREMENT_VALID; "
        f"gameplay_files={checked_files}; pinned_overrides={len(PINNED_OVERRIDES)}; "
        "cohesion_tiers=4; inert_confucian_event_stubs=12"
    )


if __name__ == "__main__":
    main()
