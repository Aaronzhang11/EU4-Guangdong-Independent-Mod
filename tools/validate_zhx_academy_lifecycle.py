#!/usr/bin/env python3
"""Validate the playable lifecycle of the twelve named ZHX academies."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from encode_eu4_chinese_localisation import FILES, verify_file


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
MANIFEST = ROOT / "planning/religion_academies/academy_manifest.json"
BUILDER = ROOT / "tools/build_zhx_academy_lifecycle.py"

TRIGGERS = MOD / "common/scripted_triggers/zhx_academy_lifecycle_triggers.txt"
EFFECTS = MOD / "common/scripted_effects/zhx_academy_lifecycle_effects.txt"
MODIFIERS = MOD / "common/event_modifiers/zhx_academy_lifecycle_modifiers.txt"
OPINIONS = MOD / "common/opinion_modifiers/zhx_academy_opinions.txt"
DECISIONS = MOD / "decisions/zhx_academy_decisions.txt"
EVENTS = MOD / "events/zhx_academy_lifecycle_events.txt"
ON_ACTIONS = MOD / "common/on_actions/zhx_system_on_actions.txt"
LOCALISATION_SOURCE = (
    MOD / "localisation_source/zhx_academy_lifecycle_readable_utf8.txt"
)

SCHOOLS = {
    "ru": ("zhx_doctrine_ru", "zhx_ru_invited_scholar_modifier"),
    "fa": ("zhx_doctrine_fa", "zhx_fa_invited_scholar_modifier"),
    "mo": ("zhx_doctrine_mo", "zhx_mo_invited_scholar_modifier"),
    "dao": ("zhx_doctrine_dao", "zhx_dao_invited_scholar_modifier"),
    "bing": ("zhx_doctrine_bing", "zhx_bing_invited_scholar_modifier"),
    "zongheng": (
        "zhx_doctrine_zongheng",
        "zhx_zongheng_invited_scholar_modifier",
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def matching_close(text: str, opening: int) -> int:
    depth = 0
    in_string = False
    in_comment = False
    escaped = False
    for index in range(opening, len(text)):
        character = text[index]
        if in_comment:
            if character == "\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == "#":
            in_comment = True
        elif character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            require(depth >= 0, "closing brace without opener")
            if depth == 0:
                return index
    raise ValueError("block has no matching closing brace")


def block_body(text: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*\{{", text)
    require(match is not None, f"missing top-level block {key}")
    opening = text.find("{", match.start())
    closing = matching_close(text, opening)
    return text[opening + 1 : closing]


def nested_block_body(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    require(match is not None, f"missing block {key}")
    opening = text.find("{", match.start())
    closing = matching_close(text, opening)
    return text[opening + 1 : closing]


def initial_scalar(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^#\n]+)", text)
    require(match is not None, f"missing scalar {key}")
    return match.group(1).strip()


def validate_balanced_clausewitz(paths: tuple[Path, ...]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        depth = 0
        in_string = False
        in_comment = False
        escaped = False
        for character in text:
            if in_comment:
                if character == "\n":
                    in_comment = False
                continue
            if in_string:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    in_string = False
                continue
            if character == "#":
                in_comment = True
            elif character == '"':
                in_string = True
            elif character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                require(depth >= 0, f"{path.name}: closing brace without opener")
        require(not in_string, f"{path.name}: unterminated string")
        require(depth == 0, f"{path.name}: unbalanced braces ({depth})")


def top_level_keys(text: str) -> list[str]:
    return re.findall(r"(?m)^([A-Za-z0-9_.]+)\s*=\s*\{", text)


def numeric_scalars(body: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for key, raw in re.findall(
        r"(?m)^\s*([A-Za-z0-9_]+)\s*=\s*(-?(?:\d+(?:\.\d*)?|\.\d+))\s*$",
        body,
    ):
        require(key not in values, f"duplicate numeric scalar {key}")
        values[key] = float(raw)
    return values


def event_blocks(text: str) -> dict[str, str]:
    events: dict[str, str] = {}
    pattern = re.compile(r"(?m)^(?:country_event|province_event)\s*=\s*\{")
    cursor = 0
    while match := pattern.search(text, cursor):
        opening = text.find("{", match.start())
        closing = matching_close(text, opening)
        body = text[opening + 1 : closing]
        event_id = initial_scalar(body, "id")
        require(event_id not in events, f"duplicate lifecycle event id {event_id}")
        events[event_id] = body
        cursor = closing + 1
    return events


def validate_builder_projection() -> None:
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    detail = (result.stderr or result.stdout).strip()
    require(result.returncode == 0, f"academy lifecycle builder --check failed: {detail}")


def load_academies() -> list[dict[str, object]]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    academies = payload.get("academies")
    require(isinstance(academies, list), "academy manifest lacks an academies list")
    require(len(academies) == 12, f"expected 12 academies, found {len(academies)}")
    keys = [str(entry["key"]) for entry in academies]
    modifiers = [str(entry["modifier"]) for entry in academies]
    require(len(keys) == len(set(keys)), "academy manifest duplicates an identity key")
    require(
        len(modifiers) == len(set(modifiers)),
        "academy manifest duplicates an active modifier",
    )
    school_counts = Counter(str(entry["school"]) for entry in academies)
    require(
        school_counts == Counter({school: 2 for school in SCHOOLS}),
        f"academy school distribution drifted: {school_counts}",
    )
    for entry in academies:
        key = str(entry["key"])
        require(
            entry["modifier"] == f"zhx_academy_{key}",
            f"{key}: active modifier/key binding drifted",
        )
    return academies


def validate_unique_generated_blocks(academies: list[dict[str, object]]) -> None:
    expected_modifier_keys = {
        "zhx_academy_expulsion_campaign",
        "zhx_academy_under_expulsion",
        "zhx_academy_expulsion_cooldown",
        *(f"zhx_academy_ruins_{entry['key']}" for entry in academies),
    }
    modifier_keys = top_level_keys(MODIFIERS.read_text(encoding="utf-8"))
    require(
        not [key for key, count in Counter(modifier_keys).items() if count != 1],
        "lifecycle event modifier file contains duplicate top-level keys",
    )
    require(
        set(modifier_keys) == expected_modifier_keys,
        "lifecycle event modifier set differs from the manifest contract",
    )
    modifier_owners: dict[str, list[Path]] = {key: [] for key in expected_modifier_keys}
    for path in (MOD / "common/event_modifiers").glob("*.txt"):
        for key in top_level_keys(path.read_text(encoding="utf-8-sig")):
            if key in modifier_owners:
                modifier_owners[key].append(path)
    for key, owners in modifier_owners.items():
        require(
            owners == [MODIFIERS],
            f"{key}: lifecycle modifier must have one global provider, found {owners}",
        )

    opinion_keys = top_level_keys(OPINIONS.read_text(encoding="utf-8"))
    require(
        opinion_keys == ["zhx_opinion_expelled_our_school"],
        f"lifecycle opinion modifier set drifted: {opinion_keys}",
    )
    opinion_owners: list[Path] = []
    for path in (MOD / "common/opinion_modifiers").glob("*.txt"):
        if "zhx_opinion_expelled_our_school" in top_level_keys(
            path.read_text(encoding="utf-8-sig")
        ):
            opinion_owners.append(path)
    require(
        opinion_owners == [OPINIONS],
        "zhx_opinion_expelled_our_school must have one global provider",
    )

    for path in (TRIGGERS, EFFECTS):
        keys = top_level_keys(path.read_text(encoding="utf-8"))
        duplicates = sorted(key for key, count in Counter(keys).items() if count != 1)
        require(not duplicates, f"{path.name}: duplicate top-level blocks {duplicates}")


def validate_costs_and_diplomatic_backlash(
    academies: list[dict[str, object]], effects: str
) -> None:
    opinion = block_body(OPINIONS.read_text(encoding="utf-8"), "zhx_opinion_expelled_our_school")
    require(
        re.search(r"(?m)^\s*opinion\s*=\s*-50\s*$", opinion) is not None,
        "expulsion opinion penalty must be -50",
    )

    for school, (doctrine_flag, invited_modifier) in SCHOOLS.items():
        outrage = block_body(effects, f"zhx_academy_outrage_{school}")
        require(
            outrage.count(f"has_country_flag = {doctrine_flag}") == 1,
            f"{school}: outrage lacks main-school audience",
        )
        require(
            outrage.count(f"has_country_modifier = {invited_modifier}") == 1,
            f"{school}: outrage lacks invited-school audience",
        )
        require(
            outrage.count("modifier = zhx_opinion_expelled_our_school") == 1,
            f"{school}: -50 opinion application missing or duplicated",
        )
        ae = nested_block_body(outrage, "add_aggressive_expansion")
        for token in ("who = ROOT", "value = 10", "apply_calc = no"):
            require(token in ae, f"{school}: exact 10 AE contract lacks {token}")

    for entry in academies:
        key = str(entry["key"])
        start = block_body(effects, f"zhx_academy_begin_expulsion_{key}")
        for pattern, label in (
            (r"(?m)^\s*adm_power\s*=\s*30\s*$", "30 ADM gate"),
            (r"(?m)^\s*add_adm_power\s*=\s*-30\s*$", "30 ADM cost"),
            (r"(?m)^\s*add_stability\s*=\s*-1\s*$", "-1 stability cost"),
            (r"(?m)^\s*add_prestige\s*=\s*-5\s*$", "-5 prestige cost"),
        ):
            require(re.search(pattern, start) is not None, f"{key}: missing {label}")
        require(
            re.search(
                r"province_event\s*=\s*\{\s*id\s*=\s*zhx_academy\.200\s+days\s*=\s*1095\s*\}",
                start,
                re.S,
            )
            is not None,
            f"{key}: expulsion deadline must be exactly 1095 days",
        )


def validate_expulsion_pressure() -> None:
    modifiers = MODIFIERS.read_text(encoding="utf-8")
    require(
        numeric_scalars(block_body(modifiers, "zhx_academy_expulsion_campaign"))
        == {"global_unrest": 0.5, "stability_cost_modifier": 0.05},
        "country expulsion pressure drifted",
    )
    require(
        numeric_scalars(block_body(modifiers, "zhx_academy_under_expulsion"))
        == {
            "local_unrest": 3.0,
            "local_development_cost": 0.05,
            "local_institution_spread": -0.10,
            "local_tax_modifier": -0.05,
            "local_production_efficiency": -0.05,
            "local_manpower_modifier": -0.05,
        },
        "province expulsion pressure drifted",
    )


def validate_offer_priority(
    academies: list[dict[str, object]], effects: str
) -> None:
    for entry in academies:
        key = str(entry["key"])
        school = str(entry["school"])
        doctrine_flag, invited_modifier = SCHOOLS[school]

        refuge = block_body(effects, f"zhx_academy_offer_refuge_{key}")
        main_token = f"has_country_flag = {doctrine_flag}"
        invited_token = f"has_country_modifier = {invited_modifier}"
        friendly_pattern = re.compile(
            r"has_opinion\s*=\s*\{\s*who\s*=\s*event_target:zhx_academy_expeller\s+value\s*=\s*50\s*\}",
            re.S,
        )
        require(refuge.count(main_token) == 2, f"{key}: refuge main tier drifted")
        require(refuge.count(invited_token) == 2, f"{key}: refuge invited tier drifted")
        friendly = list(friendly_pattern.finditer(refuge))
        require(len(friendly) == 2, f"{key}: refuge friendly tier drifted")
        require(
            refuge.find(main_token) < refuge.find(invited_token) < friendly[0].start(),
            f"{key}: refuge priority must be main -> invited -> friendly Lijiao",
        )
        require(
            refuge.count("any_country = {") == 3
            and refuge.count("random_country = {") == 3,
            f"{key}: refugee offer must have exactly three candidate tiers",
        )
        require(
            refuge.count("zhx_is_lijiao_country = yes") == 6,
            f"{key}: every refugee candidate query must require a Lijiao country",
        )
        require(
            refuge.count("country_event = { id = zhx_academy.210 }") == 3
            and "id = zhx_academy.210 days" not in refuge,
            f"{key}: refugee offers must open immediately without entering the event queue",
        )

        revival = block_body(effects, f"zhx_academy_offer_revival_{key}")
        require(revival.count(main_token) == 2, f"{key}: revival main tier drifted")
        require(revival.count(invited_token) == 2, f"{key}: revival invited tier drifted")
        require(
            revival.find(main_token) < revival.find(invited_token),
            f"{key}: revival must prefer main school before invited school",
        )
        require(
            revival.count("country_event = { id = zhx_academy.210 }") == 3
            and "id = zhx_academy.210 days" not in revival,
            f"{key}: revival offers must open immediately without entering the event queue",
        )
        require(
            revival.count("any_country = {") == 3
            and revival.count("random_country = {") == 3
            and revival.count("zhx_is_lijiao_country = yes") == 6,
            f"{key}: revival fallback must remain a third all-Lijiao tier",
        )


def validate_per_academy_lifecycle(
    academies: list[dict[str, object]], effects: str, events: dict[str, str]
) -> None:
    page_text = events["zhx_academy.100"] + events["zhx_academy.101"]
    deadline = events["zhx_academy.200"]
    accept_dispatch = block_body(effects, "zhx_academy_accept_pending_offer")
    revivals = block_body(effects, "zhx_academy_attempt_dormant_revivals")

    for token in (
        "is_at_war = no",
        "stability = 1",
        "adm_power = 30",
        "NOT = { has_country_modifier = zhx_academy_expulsion_campaign }",
        "NOT = { has_country_modifier = zhx_academy_expulsion_cooldown }",
    ):
        require(
            page_text.count(token) == 12,
            f"all 12 disposal options must expose the authoritative gate {token}",
        )

    for entry in academies:
        key = str(entry["key"])
        active = str(entry["modifier"])
        ruins = f"zhx_academy_ruins_{key}"
        dormant = f"zhx_academy_dormant_{key}"

        require(
            page_text.count(f"name = zhx_academy_lifecycle.expel_{key}") == 1,
            f"{key}: disposal pages must list the academy exactly once",
        )
        require(
            page_text.count(f"zhx_academy_begin_expulsion_{key} = yes") == 1,
            f"{key}: disposal page must open exactly one expulsion effect",
        )

        start = block_body(effects, f"zhx_academy_begin_expulsion_{key}")
        require(
            start.count(f"set_country_flag = zhx_academy_expelling_{key}") == 1,
            f"{key}: expulsion process flag missing or duplicated",
        )
        require(
            start.count(f"has_province_modifier = {active}") == 1,
            f"{key}: expulsion must select its active academy once",
        )

        require(
            deadline.count(f"has_province_modifier = {active}") == 1,
            f"{key}: deadline resolver must identify the active academy once",
        )
        require(
            deadline.count(f"has_country_flag = zhx_academy_expelling_{key}") == 1,
            f"{key}: deadline resolver lacks its process flag",
        )
        require(
            deadline.count(f"zhx_academy_finish_expulsion_{key} = yes") == 1,
            f"{key}: deadline must call exactly one terminal removal effect",
        )

        finish = block_body(effects, f"zhx_academy_finish_expulsion_{key}")
        require(
            finish.count(f"remove_province_modifier = {active}") == 1,
            f"{key}: terminal removal must delete the active authority once",
        )
        require(
            finish.count(f"name = {ruins}") == 1,
            f"{key}: terminal removal must install one permanent ruin",
        )
        require(
            finish.count(f"set_global_flag = {dormant}") == 1,
            f"{key}: terminal removal must enter dormancy once",
        )
        require(
            finish.count(f"zhx_academy_offer_refuge_{key} = yes") == 1,
            f"{key}: terminal removal must offer immediate refuge once",
        )

        install = block_body(effects, f"zhx_academy_install_{key}")
        require(
            install.count(f"name = {active}") == 3,
            f"{key}: install effect must cover the 20/12/fallback host tiers",
        )
        require(
            install.count(f"clr_global_flag = {dormant}") == 1,
            f"{key}: successful installation must clear dormancy once",
        )
        require(
            accept_dispatch.count(f"zhx_academy_install_{key} = yes") == 1,
            f"{key}: pending-offer dispatcher must install the academy once",
        )

        require(
            revivals.count(f"has_global_flag = {dormant}") == 2,
            f"{key}: annual revival must test active repair and dormant attempt",
        )
        require(
            revivals.count(f"clr_global_flag = {dormant}") == 1,
            f"{key}: annual revival must repair one stale dormant flag",
        )
        require(
            revivals.count(f"zhx_academy_offer_revival_{key} = yes") == 1,
            f"{key}: annual revival must make one ten-percent offer attempt",
        )


def validate_player_result_presentation(
    academies: list[dict[str, object]], effects: str, events: dict[str, str]
) -> None:
    clear_results = block_body(effects, "zhx_academy_clear_result_flags")
    require(
        clear_results.count("clr_country_flag = zhx_academy_result_protected") == 1,
        "deadline result cleanup must clear the protected-result flag once",
    )

    departed = events["zhx_academy.220"]
    protected = events["zhx_academy.221"]
    for event_id, body in (("220", departed), ("221", protected)):
        require(
            body.count("is_triggered_only = yes") == 1,
            f".{event_id}: trigger-only declaration drifted",
        )
        require(
            body.count("ai = no") == 1,
            f".{event_id}: result presentation must be player-only",
        )
        require(
            body.count(f"name = zhx_academy_lifecycle.{event_id}.a") == 1,
            f".{event_id}: result acknowledgement option missing or duplicated",
        )
        require(
            body.count("zhx_academy_clear_result_flags = yes") == 1,
            f".{event_id}: acknowledgement must consume all disposable result flags",
        )

    require(
        departed.count("NOT = { has_country_flag = zhx_academy_result_protected }") == 1,
        ".220 must be reserved for a completed departure",
    )
    require(
        protected.count("has_country_flag = zhx_academy_result_protected") == 1,
        ".221 must be reserved for school-protected cancellation",
    )

    deadline = events["zhx_academy.200"]
    require(
        deadline.count("limit = { ai = no }") == 12,
        "all twelve protected-deadline branches must gate presentation state to players",
    )
    require(
        deadline.count("set_country_flag = zhx_academy_result_protected") == 12,
        "all twelve protected-deadline branches must mark the protected result",
    )
    require(
        deadline.count("country_event = { id = zhx_academy.221 }") == 12,
        "all twelve protected-deadline branches must fire one immediate visible result",
    )

    for entry in academies:
        key = str(entry["key"])
        result_flag = f"zhx_academy_result_{key}"
        finish = block_body(effects, f"zhx_academy_finish_expulsion_{key}")

        require(
            clear_results.count(f"clr_country_flag = {result_flag}") == 1,
            f"{key}: result cleanup must clear its disposable identity flag once",
        )
        require(
            finish.count("limit = { ai = no }") == 1
            and finish.count(f"set_country_flag = {result_flag}") == 1
            and finish.count("country_event = { id = zhx_academy.220 }") == 1,
            f"{key}: departure result must be set and fired once for a player owner",
        )
        protected_pattern = re.compile(
            rf"if\s*=\s*\{{\s*limit\s*=\s*\{{\s*ai\s*=\s*no\s*\}}"
            rf"\s*set_country_flag\s*=\s*{re.escape(result_flag)}"
            r"\s*set_country_flag\s*=\s*zhx_academy_result_protected"
            r"\s*country_event\s*=\s*\{\s*id\s*=\s*zhx_academy\.221\s*\}",
            re.S,
        )
        require(
            len(protected_pattern.findall(deadline)) == 1,
            f"{key}: protected result must be set and fired inside one player-only block",
        )

        for event_id, body in (("220", departed), ("221", protected)):
            require(
                body.count(f"has_country_flag = {result_flag}") == 2,
                f"{key}: .{event_id} must use its identity once for description and once for trigger",
            )
            require(
                body.count(f"desc = zhx_academy_lifecycle.{event_id}.d.{key}") == 1,
                f"{key}: .{event_id} lacks one academy-specific narrative",
            )


def validate_player_arrival_presentation(
    academies: list[dict[str, object]], effects: str, events: dict[str, str]
) -> None:
    offer = events["zhx_academy.210"]
    arrival = events["zhx_academy.211"]
    event_text = EVENTS.read_text(encoding="utf-8")

    refusal_pattern = re.compile(
        r"option\s*=\s*\{\s*"
        r"name\s*=\s*zhx_academy_lifecycle\.210\.b\s*"
        r"custom_tooltip\s*=\s*zhx_academy_refuse_refuge_tt\s*"
        r"hidden_effect\s*=\s*\{\s*"
        r"zhx_academy_clear_refuge_offer_flags\s*=\s*yes\s*\}\s*"
        r"ai_chance\s*=\s*\{\s*factor\s*=\s*1\s*\}\s*\}",
        re.S,
    )
    require(
        len(refusal_pattern.findall(offer)) == 1,
        ".210 refusal must add one result tooltip without changing cleanup or AI weight",
    )
    require(
        event_text.count("custom_tooltip = zhx_academy_refuse_refuge_tt") == 1,
        "refuge-refusal tooltip must have exactly one event consumer",
    )

    require(
        len(
            re.findall(
                r"(?m)^country_event\s*=\s*\{\s*id\s*=\s*zhx_academy\.211\b",
                event_text,
                re.S,
            )
        )
        == 1,
        ".211 must have exactly one country-event definition",
    )
    require(
        re.search(
            r"(?m)^province_event\s*=\s*\{\s*id\s*=\s*zhx_academy\.211\b",
            event_text,
            re.S,
        )
        is None,
        ".211 must not be defined as a province event",
    )

    require(
        offer.count("zhx_academy_accept_pending_offer = yes") == 1,
        ".210 acceptance must dispatch exactly one pending academy installation",
    )
    receipt_dispatch = re.compile(
        r"zhx_academy_accept_pending_offer\s*=\s*yes\s*"
        r"if\s*=\s*\{\s*limit\s*=\s*\{\s*ai\s*=\s*no\s*"
        r"has_saved_global_event_target\s*=\s*zhx_academy_arrival_province\s*\}\s*"
        r"country_event\s*=\s*\{\s*id\s*=\s*zhx_academy\.211\s*\}\s*\}",
        re.S,
    )
    require(
        len(receipt_dispatch.findall(offer)) == 1,
        ".210 must install first, then synchronously dispatch .211 from the current human country",
    )
    require(
        sum(
            body.count("zhx_academy_accept_pending_offer = yes")
            for event_id, body in events.items()
            if event_id != "zhx_academy.210"
        )
        == 0,
        "only .210 acceptance may dispatch a pending academy installation",
    )
    require(
        offer.count("country_event = { id = zhx_academy.211 }") == 1,
        ".210 must be the unique immediate .211 caller",
    )
    require(
        sum(
            body.count("country_event = { id = zhx_academy.211 }")
            for event_id, body in events.items()
            if event_id != "zhx_academy.210"
        )
        == 0,
        "only .210 acceptance may dispatch the arrival receipt",
    )
    require(
        arrival.count("is_triggered_only = yes") == 1,
        ".211 arrival receipt must remain trigger-only",
    )
    require(
        re.search(r"(?m)^\s*hidden\s*=", arrival) is None,
        ".211 arrival receipt must remain visible",
    )
    require(
        arrival.count("ai = no") == 1,
        ".211 arrival receipt trigger must be human-country only",
    )
    require(
        arrival.count("has_saved_global_event_target = zhx_academy_arrival_province")
        == 1,
        ".211 arrival receipt must require its saved global destination target",
    )
    require(
        arrival.count("owned_by = ROOT") == 1,
        ".211 saved destination must still be owned by the receiving country",
    )
    require(
        arrival.count("zhx_academy_is_active_province = yes") == 1,
        ".211 arrival receipt must require a successfully installed active academy",
    )
    require(
        arrival.count("name = zhx_academy_lifecycle.211.a") == 1,
        ".211 arrival acknowledgement option missing or duplicated",
    )
    require(
        arrival.count("goto = zhx_academy_arrival_province") == 1,
        ".211 must expose the native province locator for its saved destination",
    )
    require(
        arrival.count("clear_global_event_target = zhx_academy_arrival_province")
        == 1,
        ".211 acknowledgement must clear its disposable global destination target",
    )

    total_target_saves = 0
    for entry in academies:
        key = str(entry["key"])
        active = str(entry["modifier"])
        install = block_body(effects, f"zhx_academy_install_{key}")
        installed_then_target = re.compile(
            rf"add_permanent_province_modifier\s*=\s*\{{\s*"
            rf"name\s*=\s*{re.escape(active)}\s+duration\s*=\s*-1\s*\}}\s*"
            r"if\s*=\s*\{\s*limit\s*=\s*\{\s*owner\s*=\s*\{\s*"
            r"ai\s*=\s*no\s*\}\s*\}\s*"
            r"save_global_event_target_as\s*=\s*zhx_academy_arrival_province\s*\}",
            re.S,
        )
        matches = installed_then_target.findall(install)
        require(
            len(matches) == 3,
            f"{key}: all three successful host tiers must save their province only for a human owner",
        )
        require(
            "zhx_academy.211" not in install,
            f"{key}: install effect must never attempt to open .211 from nested province scope",
        )
        require(
            effects.count(f"zhx_academy_install_{key} = yes") == 1,
            f"{key}: installation effect must be called only by the pending-offer dispatcher",
        )
        total_target_saves += install.count(
            "save_global_event_target_as = zhx_academy_arrival_province"
        )
        require(
            install.count(
                "save_global_event_target_as = zhx_academy_arrival_province"
            )
            == 3,
            f"{key}: every successful human host tier must save its exact arrival province globally",
        )

        require(
            arrival.count(
                "event_target:zhx_academy_arrival_province = { "
                f"has_province_modifier = {active} "
                "}"
            )
            == 1,
            f"{key}: .211 must identify the installed academy on its saved province exactly once",
        )
        require(
            arrival.count(f"desc = zhx_academy_lifecycle.211.d.{key}") == 1,
            f"{key}: .211 lacks one academy-specific arrival narrative",
        )

    require(
        total_target_saves == len(academies) * 3,
        "arrival target-save count must equal twelve academies times three host tiers",
    )
    require(
        effects.count("save_global_event_target_as = zhx_academy_arrival_province")
        == total_target_saves,
        "arrival global target may only be saved from successful generated installation branches",
    )
    require(
        "country_event = { id = zhx_academy.211 }" not in effects
        and "province_event = { id = zhx_academy.211 }" not in effects,
        ".211 must not retain either unreliable nested install-event call path",
    )


def validate_decisions_and_withdrawal(effects: str, decisions: str) -> None:
    withdrawal = block_body(effects, "zhx_academy_withdraw_current_expulsion")
    for token in (
        "remove_province_modifier = zhx_academy_under_expulsion",
        "zhx_academy_clear_expulsion_state = yes",
        "name = zhx_academy_expulsion_cooldown",
        "duration = 3650",
        "zhx_refresh_academy_country_effects = yes",
    ):
        require(token in withdrawal, f"withdrawal lifecycle lacks {token}")

    country_decisions = block_body(decisions, "country_decisions")
    manage_decision = nested_block_body(
        country_decisions, "zhx_manage_unprotected_academies"
    )
    manage_allow = nested_block_body(manage_decision, "allow")
    for token in (
        "is_at_war = no",
        "stability = 1",
        "adm_power = 30",
        "NOT = { has_country_modifier = zhx_academy_expulsion_campaign }",
        "NOT = { has_country_modifier = zhx_academy_expulsion_cooldown }",
    ):
        require(token in manage_allow, f"academy management decision lacks {token}")
    require(
        manage_decision.count("country_event = { id = zhx_academy.100 }") == 1,
        "academy management decision must open the first disposal page",
    )
    require(
        country_decisions.count("zhx_withdraw_academy_expulsion = {") == 1,
        "withdrawal decision missing or duplicated",
    )
    withdraw_decision = nested_block_body(
        country_decisions, "zhx_withdraw_academy_expulsion"
    )
    require(
        withdraw_decision.count("zhx_academy_withdraw_current_expulsion = yes") == 1,
        "withdrawal decision must call the shared effect once",
    )


def validate_withdrawal_presentation(
    academies: list[dict[str, object]], effects: str, events: dict[str, str]
) -> None:
    withdrawal = block_body(effects, "zhx_academy_withdraw_current_expulsion")
    cancel = block_body(effects, "zhx_academy_cancel_expulsion_on_owner_change")
    receipt = events["zhx_academy.230"]
    event_text = EVENTS.read_text(encoding="utf-8")

    require(
        len(
            re.findall(
                r"(?m)^country_event\s*=\s*\{\s*id\s*=\s*zhx_academy\.230\b",
                event_text,
                re.S,
            )
        )
        == 1,
        ".230 must have exactly one country-event definition",
    )
    require(
        re.search(
            r"(?m)^province_event\s*=\s*\{\s*id\s*=\s*zhx_academy\.230\b",
            event_text,
            re.S,
        )
        is None,
        ".230 must not be defined as a province event",
    )

    ordered_tokens = (
        "save_global_event_target_as = zhx_academy_withdrawn_province",
        "remove_province_modifier = zhx_academy_under_expulsion",
        "zhx_academy_clear_expulsion_state = yes",
        "name = zhx_academy_expulsion_cooldown",
        "zhx_refresh_academy_country_effects = yes",
        "country_event = { id = zhx_academy.230 }",
    )
    positions = [withdrawal.find(token) for token in ordered_tokens]
    require(
        all(position >= 0 for position in positions) and positions == sorted(positions),
        "withdrawal must save target, clear pressure/process, add cooldown, refresh, then show .230",
    )
    require(
        withdrawal.count("save_global_event_target_as = zhx_academy_withdrawn_province")
        == 1,
        "withdrawal must save its unique pressed province exactly once",
    )
    require(
        withdrawal.count("ai = no") == 2,
        "withdrawal target capture and receipt dispatch must each be player-only",
    )
    require(
        withdrawal.count("has_saved_global_event_target = zhx_academy_withdrawn_province")
        == 1,
        "withdrawal receipt dispatch must require its saved province",
    )
    require(
        withdrawal.count("country_event = { id = zhx_academy.230 }") == 1
        and "id = zhx_academy.230 days" not in withdrawal,
        "withdrawal must synchronously dispatch exactly one .230 receipt",
    )
    require(
        effects.count("country_event = { id = zhx_academy.230 }") == 1,
        ".230 may only be called from the shared player-withdrawal effect",
    )
    require(
        "zhx_academy.230" not in cancel
        and "zhx_academy_withdrawn_province" not in cancel
        and "zhx_academy_result_" not in cancel,
        "owner-change cancellation must not emit player withdrawal presentation state",
    )

    first_pressure_removal = withdrawal.find(
        "remove_province_modifier = zhx_academy_under_expulsion"
    )
    for entry in academies:
        key = str(entry["key"])
        active = str(entry["modifier"])
        expelling = f"has_country_flag = zhx_academy_expelling_{key}"
        result = f"zhx_academy_result_{key}"
        require(
            withdrawal.count(expelling) == 1,
            f"{key}: withdrawal identity selection must read its expelling flag once",
        )
        require(
            withdrawal.count(f"set_country_flag = {result}") == 1,
            f"{key}: withdrawal identity selection must set its reusable result flag once",
        )
        require(
            withdrawal.find(f"set_country_flag = {result}") < first_pressure_removal,
            f"{key}: withdrawal result identity must be frozen before pressure is removed",
        )

        pair = (
            f"has_country_flag = {result} "
            "event_target:zhx_academy_withdrawn_province = { "
            f"has_province_modifier = {active} "
            "}"
        )
        require(
            receipt.count(pair) == 2,
            f"{key}: .230 must pair its result flag and matching active academy in desc and trigger",
        )
        require(
            receipt.count(f"desc = zhx_academy_lifecycle.230.d.{key}") == 1,
            f"{key}: .230 lacks one academy-specific withdrawal narrative",
        )

    for token, label in (
        ("is_triggered_only = yes", "trigger-only declaration"),
        ("ai = no", "player-only trigger"),
        (
            "has_saved_global_event_target = zhx_academy_withdrawn_province",
            "saved target trigger",
        ),
        (
            "event_target:zhx_academy_withdrawn_province = { owned_by = ROOT }",
            "current ownership check",
        ),
        ("goto = zhx_academy_withdrawn_province", "province goto"),
        ("name = zhx_academy_lifecycle.230.a", "acknowledgement option"),
        ("zhx_academy_clear_result_flags = yes", "result identity cleanup"),
        (
            "clear_global_event_target = zhx_academy_withdrawn_province",
            "withdrawn province target cleanup",
        ),
    ):
        require(receipt.count(token) == 1, f".230 lacks unique {label}")
    require(
        re.search(r"(?m)^\s*hidden\s*=", receipt) is None,
        ".230 withdrawal receipt must remain visible",
    )


def validate_ai_and_annual(events: dict[str, str]) -> None:
    ai_event = events["zhx_academy.300"]
    for token in (
        "ai = yes",
        "zhx_is_lijiao_country = yes",
        "zhx_has_doctrine = yes",
        "is_at_war = no",
        "stability = 2",
        "adm_power = 100",
        "zhx_academy_has_two_unprotected_school_types = yes",
        "chance = 8",
        "zhx_academy_begin_random_unprotected_expulsion = yes",
    ):
        require(ai_event.count(token) == 1, f"annual AI gate lacks unique {token}")
    for modifier in (
        "zhx_academy_expulsion_campaign",
        "zhx_academy_expulsion_cooldown",
    ):
        require(
            f"NOT = {{ has_country_modifier = {modifier} }}" in ai_event,
            f"annual AI gate lacks {modifier} exclusion",
        )

    revival = events["zhx_academy.301"]
    for token in (
        "zhx_is_tianzi = yes",
        "zhx_academy_has_any_dormant = yes",
        "zhx_academy_attempt_dormant_revivals = yes",
    ):
        require(revival.count(token) == 1, f"annual revival scheduler lacks {token}")


def validate_on_actions(academies: list[dict[str, object]], effects: str) -> None:
    text = ON_ACTIONS.read_text(encoding="utf-8")
    yearly = block_body(text, "on_yearly_pulse")
    ordered = (
        "zhx_academy.90",
        "zhx_academy.300",
        "zhx_academy.301",
    )
    positions = [yearly.find(event_id) for event_id in ordered]
    require(
        all(position >= 0 for position in positions) and positions == sorted(positions),
        "annual lifecycle order must be reconciliation .90, AI .300, revival .301",
    )
    for event_id in ordered:
        require(yearly.count(event_id) == 1, f"annual hook duplicates {event_id}")

    owner_change = block_body(text, "on_province_owner_change")
    for entry in academies:
        active = str(entry["modifier"])
        require(
            owner_change.count(f"has_province_modifier = {active}") == 1,
            f"owner-change hook lacks unique active academy {active}",
        )
    require(
        owner_change.count("zhx_academy_cancel_expulsion_on_owner_change = yes") == 1,
        "owner-change hook lacks the lifecycle cancellation effect",
    )
    require(
        owner_change.find("zhx_academy_cancel_expulsion_on_owner_change = yes")
        < owner_change.find("zhx_refresh_academy_country_effects = yes"),
        "owner-change cancellation must precede derived-state reconciliation",
    )
    require(
        owner_change.count("zhx_refresh_academy_country_effects = yes") == 2,
        "owner-change hook must refresh new and former owners exactly once",
    )

    cancel = block_body(effects, "zhx_academy_cancel_expulsion_on_owner_change")
    for token in (
        "has_province_modifier = zhx_academy_under_expulsion",
        "remove_province_modifier = zhx_academy_under_expulsion",
    ):
        require(cancel.count(token) == 1, f"owner-change cancellation lacks {token}")
    require(
        cancel.count("FROM = { exists = yes }") == 1
        and cancel.count("FROM = { zhx_academy_clear_expulsion_state = yes }") == 1,
        "owner-change cancellation must clear the matched former owner exactly once",
    )
    for entry in academies:
        pair = (
            f"has_province_modifier = {entry['modifier']}\n"
            "                FROM = { "
            f"has_country_flag = zhx_academy_expelling_{entry['key']}"
            " }"
        )
        require(
            cancel.count(pair) == 1,
            f"{entry['key']}: owner-change cancellation lacks its exact academy/flag pair",
        )
        require(
            cancel.count(f"has_country_flag = zhx_academy_expelling_{entry['key']}") == 1,
            f"{entry['key']}: owner-change expelling identity is duplicated",
        )
    require(
        cancel.find("FROM = { zhx_academy_clear_expulsion_state = yes }")
        < cancel.find("has_province_modifier = zhx_academy_under_expulsion"),
        "former-owner cleanup must not be nested under the disposable pressure marker",
    )
    require(
        "zhx_refresh_academy_country_effects" not in cancel,
        "owner-change cancellation must leave both reconciliations to the native hook",
    )


def localisation_keys(text: str) -> list[str]:
    return re.findall(r"(?m)^\s*([A-Za-z0-9_.]+):0\s+", text)


def validate_localisation(academies: list[dict[str, object]]) -> None:
    source = LOCALISATION_SOURCE.read_text(encoding="utf-8-sig")
    keys = localisation_keys(source)
    duplicates = sorted(key for key, count in Counter(keys).items() if count != 1)
    require(not duplicates, f"lifecycle localisation duplicates keys: {duplicates}")
    key_set = set(keys)

    required = {
        "zhx_manage_unprotected_academies_title",
        "zhx_manage_unprotected_academies_desc",
        "zhx_withdraw_academy_expulsion_title",
        "zhx_withdraw_academy_expulsion_desc",
        "zhx_academy_expulsion_campaign",
        "zhx_academy_expulsion_campaign_desc",
        "zhx_academy_under_expulsion",
        "zhx_academy_under_expulsion_desc",
        "zhx_academy_expulsion_cooldown",
        "zhx_academy_expulsion_cooldown_desc",
        "zhx_opinion_expelled_our_school",
        "zhx_academy_lifecycle.220.t",
        "zhx_academy_lifecycle.220.a",
        "zhx_academy_lifecycle.221.t",
        "zhx_academy_lifecycle.221.a",
        "zhx_academy_lifecycle.211.t",
        "zhx_academy_lifecycle.211.a",
        "zhx_academy_lifecycle.230.t",
        "zhx_academy_lifecycle.230.a",
        "zhx_academy_refuse_refuge_tt",
    }
    refusal_match = re.search(
        r'(?m)^\s*zhx_academy_refuse_refuge_tt:0\s+"([^"]*)"\s*$', source
    )
    require(
        refusal_match is not None,
        "refuge-refusal tooltip localisation is missing or malformed",
    )
    refusal_value = refusal_match.group(1)
    for fragment in (
        "不会迁入",
        "不会被永久删除",
        "保持流散",
        "当前天子",
        "10%",
        "没有合格礼教国家",
        "继续流散",
    ):
        require(
            fragment in refusal_value,
            f"refuge-refusal tooltip must explain {fragment}",
        )
    for entry in academies:
        key = str(entry["key"])
        name = str(entry["name"])
        arrival_key = f"zhx_academy_lifecycle.211.d.{key}"
        withdrawal_key = f"zhx_academy_lifecycle.230.d.{key}"
        required.update(
            {
                f"zhx_academy_lifecycle.expel_{key}",
                f"zhx_academy_lifecycle.210.d.{key}",
                arrival_key,
                f"zhx_academy_lifecycle.220.d.{key}",
                f"zhx_academy_lifecycle.221.d.{key}",
                withdrawal_key,
                f"zhx_academy_ruins_{key}",
                f"zhx_academy_ruins_{key}_desc",
            }
        )
        arrival_match = re.search(
            rf'(?m)^\s*{re.escape(arrival_key)}:0\s+"([^"]*)"\s*$', source
        )
        require(
            arrival_match is not None,
            f"{key}: arrival localisation line is missing or malformed",
        )
        arrival_value = arrival_match.group(1)
        require(
            name in arrival_value
            and "[zhx_academy_arrival_province.GetName]" in arrival_value,
            f"{key}: arrival localisation must name both the academy and its saved province",
        )
        withdrawal_match = re.search(
            rf'(?m)^\s*{re.escape(withdrawal_key)}:0\s+"([^"]*)"\s*$', source
        )
        require(
            withdrawal_match is not None,
            f"{key}: withdrawal localisation line is missing or malformed",
        )
        withdrawal_value = withdrawal_match.group(1)
        require(
            name in withdrawal_value
            and "[zhx_academy_withdrawn_province.GetName]" in withdrawal_value
            and "10年" in withdrawal_value,
            f"{key}: withdrawal localisation must name the academy, province, and ten-year cooldown",
        )
    missing = sorted(required - key_set)
    require(not missing, f"lifecycle localisation lacks keys: {missing}")

    target_name = FILES.get(LOCALISATION_SOURCE.name)
    require(
        target_name == "zhx_academy_lifecycle_l_english.yml",
        "lifecycle localisation source is not registered in the encoder",
    )
    target = MOD / "localisation" / target_name
    require(target.is_file(), f"missing encoded lifecycle localisation {target.name}")
    verify_file(LOCALISATION_SOURCE, target)


def main() -> None:
    validate_builder_projection()
    academies = load_academies()
    validate_balanced_clausewitz(
        (TRIGGERS, EFFECTS, MODIFIERS, OPINIONS, DECISIONS, EVENTS, ON_ACTIONS)
    )
    validate_unique_generated_blocks(academies)

    effects = EFFECTS.read_text(encoding="utf-8")
    decisions = DECISIONS.read_text(encoding="utf-8")
    events = event_blocks(EVENTS.read_text(encoding="utf-8"))
    require(
        set(events)
        == {
            "zhx_academy.100",
            "zhx_academy.101",
            "zhx_academy.200",
            "zhx_academy.210",
            "zhx_academy.211",
            "zhx_academy.220",
            "zhx_academy.221",
            "zhx_academy.230",
            "zhx_academy.300",
            "zhx_academy.301",
        },
        f"lifecycle event set drifted: {sorted(events)}",
    )

    validate_costs_and_diplomatic_backlash(academies, effects)
    validate_expulsion_pressure()
    validate_offer_priority(academies, effects)
    validate_per_academy_lifecycle(academies, effects, events)
    validate_player_result_presentation(academies, effects, events)
    validate_player_arrival_presentation(academies, effects, events)
    validate_decisions_and_withdrawal(effects, decisions)
    validate_withdrawal_presentation(academies, effects, events)
    validate_ai_and_annual(events)
    validate_on_actions(academies, effects)
    validate_localisation(academies)
    print(
        "ZHX academy lifecycle valid: 12 disposal/deadline/refuge/revival paths, "
        "player result, arrival, and withdrawal presentation, three-tier hosts, "
        "exact costs/backlash, AI gate, and owner-change cleanup"
    )


if __name__ == "__main__":
    main()
