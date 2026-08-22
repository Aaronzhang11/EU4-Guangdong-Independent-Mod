#!/usr/bin/env python3
"""Static contract checks for the Ritual Teaching Ru/Fa/Mo prototype."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

SCRIPT_PATHS = (
    MOD / "common/scripted_triggers/zhx_doctrine_triggers.txt",
    MOD / "common/scripted_effects/zhx_doctrine_effects.txt",
    MOD / "common/event_modifiers/zhx_doctrine_modifiers.txt",
    MOD / "decisions/zhx_doctrine_decisions.txt",
    MOD / "events/zhx_doctrine_events.txt",
)
ON_ACTION_PATH = MOD / "common/on_actions/zhx_system_on_actions.txt"
LOCALISATION_PATH = (
    MOD / "localisation_source/zhx_doctrine_readable_utf8.txt"
)

EXPECTED_EVENT_IDS = {"1", "10", "11", "12", "20", "90"}
EXPECTED_FLAGS = {
    "ru": "zhx_doctrine_ru",
    "fa": "zhx_doctrine_fa",
    "mo": "zhx_doctrine_mo",
}
EXPECTED_MODIFIERS = {
    "zhx_doctrine_practice_hollow",
    "zhx_doctrine_ru_established",
    "zhx_doctrine_ru_flourishing",
    "zhx_doctrine_ru_exemplary",
    "zhx_doctrine_fa_established",
    "zhx_doctrine_fa_flourishing",
    "zhx_doctrine_fa_exemplary",
    "zhx_doctrine_mo_established",
    "zhx_doctrine_mo_flourishing",
    "zhx_doctrine_mo_exemplary",
    "zhx_doctrine_change_cooldown",
}
EXPECTED_LOCALISATION = {
    "zhx_convene_hundred_schools_debate_title",
    "zhx_convene_hundred_schools_debate_desc",
    "zhx_review_current_doctrine_title",
    "zhx_review_current_doctrine_desc",
    "zhx_doctrine.1.t",
    "zhx_doctrine.1.e",
    "zhx_doctrine.1.a",
    "zhx_doctrine.1.b",
    "zhx_doctrine.1.c",
    "zhx_doctrine.1.d",
    "zhx_doctrine.10.t",
    "zhx_doctrine.10.d",
    "zhx_doctrine.11.t",
    "zhx_doctrine.11.d",
    "zhx_doctrine.12.t",
    "zhx_doctrine.12.d",
    "zhx_doctrine.choose_ru",
    "zhx_doctrine.choose_fa",
    "zhx_doctrine.choose_mo",
    "zhx_doctrine.no_verdict",
    "zhx_doctrine_postpone_tt",
    "zhx_doctrine_inconclusive_tt",
    "zhx_adopt_ru_doctrine_tt",
    "zhx_adopt_fa_doctrine_tt",
    "zhx_adopt_mo_doctrine_tt",
    "zhx_doctrine.20.t",
    "zhx_doctrine.20.d.ru",
    "zhx_doctrine.20.d.fa",
    "zhx_doctrine.20.d.mo",
    "zhx_doctrine.20.a",
    "zhx_doctrine.90.t",
    "zhx_doctrine.90.d",
}
FORBIDDEN_TOKENS = {
    "add_treasury": "the doctrine must not be purchased with money",
    "add_adm_power": "the doctrine must not be purchased with ADM",
    "add_dip_power": "the doctrine must not be purchased with DIP",
    "add_mil_power": "the doctrine must not be purchased with MIL",
    "change_religion": "country religion must not be changed by doctrine",
    "change_province_religion": "province religion must remain stable",
    "every_country": "the prototype must not run a scripted full-country scan",
    "every_province": "the prototype must not run a scripted full-province scan",
    "on_monthly_pulse": "practice is intentionally annual, not monthly",
    "on_daily_pulse": "practice is intentionally annual, not daily",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8-sig")


def validate_braces(path: Path, text: str) -> None:
    """Balance Clausewitz braces while ignoring comments and quoted strings."""
    depth = 0
    in_string = False
    escaped = False
    in_comment = False
    for index, char in enumerate(text):
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
            require(
                depth >= 0,
                f"{path.relative_to(ROOT)}:{index}: closing brace without opener",
            )
    require(not in_string, f"{path.relative_to(ROOT)}: unterminated string")
    require(depth == 0, f"{path.relative_to(ROOT)}: unbalanced braces ({depth})")


def top_level_effect_body(text: str, effect: str) -> str:
    match = re.search(rf"(?m)^{re.escape(effect)}\s*=\s*\{{", text)
    require(match is not None, f"missing scripted effect {effect}")
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
                return text[opening + 1:index]
    raise ValueError(f"scripted effect {effect} has no closing brace")


def main() -> None:
    texts = {path: read(path) for path in SCRIPT_PATHS}
    on_action = read(ON_ACTION_PATH)
    localisation = read(LOCALISATION_PATH)

    for path, text in (*texts.items(), (ON_ACTION_PATH, on_action)):
        validate_braces(path, text)

    event_text = texts[MOD / "events/zhx_doctrine_events.txt"]
    event_ids = re.findall(r"(?m)^\s*id\s*=\s*zhx_doctrine\.(\d+)\s*$", event_text)
    require(len(event_ids) == len(set(event_ids)), "duplicate zhx_doctrine event ID")
    require(
        set(event_ids) == EXPECTED_EVENT_IDS,
        f"event ID contract changed: {sorted(event_ids)}",
    )
    require(
        len(re.findall(r"(?m)^\s*zhx_doctrine\.90\s*$", on_action)) == 1,
        "on_yearly_pulse must contain zhx_doctrine.90 exactly once",
    )

    modifier_text = texts[MOD / "common/event_modifiers/zhx_doctrine_modifiers.txt"]
    modifier_definitions = set(
        re.findall(r"(?m)^(zhx_doctrine_[a-z0-9_]+)\s*=\s*\{", modifier_text)
    )
    require(
        modifier_definitions == EXPECTED_MODIFIERS,
        "modifier definition contract changed: "
        f"missing={sorted(EXPECTED_MODIFIERS - modifier_definitions)}, "
        f"extra={sorted(modifier_definitions - EXPECTED_MODIFIERS)}",
    )

    all_scripts = "\n".join(texts.values())
    referenced_modifiers = set(
        re.findall(
            r"(?:name|has_country_modifier|remove_country_modifier)\s*=\s*"
            r"(zhx_doctrine_[a-z0-9_]+)",
            all_scripts,
        )
    )
    require(
        referenced_modifiers <= modifier_definitions,
        f"undefined doctrine modifiers: {sorted(referenced_modifiers - modifier_definitions)}",
    )

    effect_text = texts[MOD / "common/scripted_effects/zhx_doctrine_effects.txt"]
    for school, flag in EXPECTED_FLAGS.items():
        setters = re.findall(rf"set_country_flag\s*=\s*{re.escape(flag)}\b", effect_text)
        require(len(setters) == 1, f"{flag} must be set exactly once")
        body = top_level_effect_body(effect_text, f"zhx_adopt_{school}_doctrine")
        require(
            re.search(rf"set_country_flag\s*=\s*{re.escape(flag)}\b", body) is not None,
            f"{flag} may only be set by its adoption effect",
        )

    for token, reason in FORBIDDEN_TOKENS.items():
        require(
            re.search(rf"\b{re.escape(token)}\b", all_scripts) is None,
            f"forbidden token {token}: {reason}",
        )

    require(
        "religion = confucianism" in texts[MOD / "common/scripted_triggers/zhx_doctrine_triggers.txt"],
        "the Ritual Teaching eligibility trigger must use confucianism",
    )
    require(
        "duration = 3650" in effect_text,
        "successful doctrine adoption must retain the ten-year cooldown",
    )
    require(event_text.count("duration = 1825") == 3, "each no-verdict path needs five years")
    require(event_text.count("duration = 730") == 1, "postponement needs two years")

    localisation_keys = re.findall(r"(?m)^\s*([^\s:#]+):\d+\s+\"", localisation)
    require(
        len(localisation_keys) == len(set(localisation_keys)),
        "duplicate keys in doctrine readable localisation",
    )
    actual_localisation = set(localisation_keys)
    expected_with_modifiers = EXPECTED_LOCALISATION | EXPECTED_MODIFIERS | {
        f"{modifier}_desc" for modifier in EXPECTED_MODIFIERS
    }
    require(
        expected_with_modifiers <= actual_localisation,
        f"missing doctrine localisation: {sorted(expected_with_modifiers - actual_localisation)}",
    )

    print("Ritual Teaching doctrine prototype static contract: PASS")
    print(f"  Clausewitz files: {len(SCRIPT_PATHS) + 1}")
    print(f"  Events: {len(event_ids)}")
    print(f"  Doctrine modifiers: {len(modifier_definitions)}")
    print(f"  Readable localisation keys: {len(localisation_keys)}")


if __name__ == "__main__":
    main()
