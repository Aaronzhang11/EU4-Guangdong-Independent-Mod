#!/usr/bin/env python3
"""Static contract checks for the six-school Ritual Teaching prototype."""

from __future__ import annotations

import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

SCRIPT_PATHS = (
    MOD / "common/scripted_triggers/zhx_doctrine_triggers.txt",
    MOD / "common/scripted_effects/zhx_doctrine_effects.txt",
    MOD / "common/event_modifiers/zhx_doctrine_modifiers.txt",
    MOD / "common/static_modifiers/zhx_invited_school_modifiers.txt",
    MOD / "decisions/zhx_doctrine_decisions.txt",
    MOD / "events/zhx_doctrine_events.txt",
    MOD / "events/zhx_doctrine_expansion_events.txt",
    MOD / "customizable_localization/zhx_doctrine_receipt.txt",
)
ON_ACTION_PATH = MOD / "common/on_actions/zhx_system_on_actions.txt"
NATIVE_GFX_PATH = MOD / "interface/zhx_doctrine_icons.gfx"
LIJIAO_GFX_PATH = MOD / "interface/zhx_lijiao_religion.gfx"
NATIVE_GUI_PATH = MOD / "interface/countryreligionview.gui"
NATIVE_DIPLOMACY_GUI_PATH = MOD / "interface/countrydiplomacyview.gui"
NATIVE_CUSTOM_GUI_PATH = MOD / "common/custom_gui/zhx_religion_gui.txt"
NATIVE_RELIGION_PATH = MOD / "common/religions/00_religion.txt"
NATIVE_RELIGION_BUILDER_PATH = ROOT / "tools/build_zhx_religions.py"
NATIVE_GUI_BUILDER_PATH = ROOT / "tools/build_zhx_countryreligionview.py"
NATIVE_DIPLOMACY_BUILDER_PATH = ROOT / "tools/build_zhx_countrydiplomacyview.py"
LOCALISATION_PATH = (
    MOD / "localisation_source/zhx_doctrine_readable_utf8.txt"
)
EXPANSION_LOCALISATION_PATH = (
    MOD / "localisation_source/zhx_doctrine_expansion_readable_utf8.txt"
)
NATIVE_LOCALISATION_PATH = (
    MOD / "localisation_source/zhx_native_schools_readable_utf8.txt"
)
TEMP_RUNTIME_EVENT_PATH = MOD / "events/zz_zhxtest_runtime.txt"

EXPECTED_EVENT_IDS = {
    "1", "10", "11", "12", "20", "90", "91", "92", "93", "94", "95"
}
EXPECTED_EXPANSION_EVENT_IDS = {"1", "10", "11", "12"}
EXPECTED_FLAGS = {
    "ru": "zhx_doctrine_ru",
    "fa": "zhx_doctrine_fa",
    "mo": "zhx_doctrine_mo",
    "dao": "zhx_doctrine_dao",
    "bing": "zhx_doctrine_bing",
    "zongheng": "zhx_doctrine_zongheng",
}
NATIVE_SCHOOLS = {
    "zhx_ru_school": "GFX_zhx_doctrine_ru_school",
    "zhx_fa_school": "GFX_zhx_doctrine_fa_school",
    "zhx_mo_school": "GFX_zhx_doctrine_mo_school",
    "zhx_dao_school": "GFX_zhx_doctrine_dao_school",
    "zhx_bing_school": "GFX_zhx_doctrine_bing_school",
    "zhx_zongheng_school": "GFX_zhx_doctrine_zongheng_school",
}
NO_DOCTRINE_SCHOOL = {
    "zhx_no_doctrine_school": "GFX_zhx_no_doctrine_school",
}
ALL_NATIVE_SCHOOLS = NATIVE_SCHOOLS | NO_DOCTRINE_SCHOOL
NATIVE_SCHOOL_FLAGS = {
    "zhx_ru_school": "zhx_doctrine_ru",
    "zhx_fa_school": "zhx_doctrine_fa",
    "zhx_mo_school": "zhx_doctrine_mo",
    "zhx_dao_school": "zhx_doctrine_dao",
    "zhx_bing_school": "zhx_doctrine_bing",
    "zhx_zongheng_school": "zhx_doctrine_zongheng",
}
INVITED_SCHOOL_MODIFIERS = {
    "zhx_ru_school": "zhx_ru_invited_scholar_modifier",
    "zhx_fa_school": "zhx_fa_invited_scholar_modifier",
    "zhx_mo_school": "zhx_mo_invited_scholar_modifier",
    "zhx_dao_school": "zhx_dao_invited_scholar_modifier",
    "zhx_bing_school": "zhx_bing_invited_scholar_modifier",
    "zhx_zongheng_school": "zhx_zongheng_invited_scholar_modifier",
}
INVITED_SCHOOL_OVERLAY_ICONS = {
    school: f"zhx_invited_school_{school.removeprefix('zhx_').removesuffix('_school')}_icon"
    for school in NATIVE_SCHOOLS
}
INVITED_MODIFIER_VALUES = {
    "zhx_ru_invited_scholar_modifier": {
        "advisor_cost": "-0.025",
        "stability_cost_modifier": "-0.025",
    },
    "zhx_fa_invited_scholar_modifier": {
        "global_autonomy": "-0.025",
        "core_creation": "-0.025",
    },
    "zhx_mo_invited_scholar_modifier": {
        "fort_maintenance_modifier": "-0.05",
        "defensiveness": "0.05",
    },
    "zhx_dao_invited_scholar_modifier": {
        "global_unrest": "-0.5",
        "war_exhaustion": "-0.01",
    },
    "zhx_bing_invited_scholar_modifier": {
        "manpower_recovery_speed": "0.05",
        "army_tradition_decay": "-0.005",
    },
    "zhx_zongheng_invited_scholar_modifier": {
        "improve_relation_modifier": "0.10",
        "diplomatic_reputation": "0.25",
    },
}
RELIGION_SCHOOL_TOOLTIP_ICONS = {
    school: f"zhx_religion_school_{school.removeprefix('zhx_').removesuffix('_school')}_tooltip_icon"
    for school in NATIVE_SCHOOLS
}
DIPLOMACY_SCHOOL_TOOLTIP_ICONS = {
    school: f"zhx_diplomacy_school_{school.removeprefix('zhx_').removesuffix('_school')}_tooltip_icon"
    for school in NATIVE_SCHOOLS
}
NATIVE_STATUS_FIELDS = {
    "zhx_religion_practice_hollow_value",
    "zhx_religion_practice_value",
    "zhx_religion_practice_flourishing_value",
    "zhx_religion_practice_exemplary_value",
}
PRACTICE_TIER_COLOURS = {
    "zhx_religion_practice_hollow_value": "R",
    "zhx_religion_practice_value": "Y",
    "zhx_religion_practice_flourishing_value": "G",
    "zhx_religion_practice_exemplary_value": "O",
}
HOVER_CACHE_FLAGS = {
    "zhx_doctrine_hover_positive_1",
    "zhx_doctrine_hover_positive_2",
    "zhx_doctrine_hover_positive_3",
    "zhx_doctrine_hover_negative_1",
    "zhx_doctrine_hover_negative_2",
    "zhx_doctrine_hover_negative_3",
    "zhx_doctrine_hover_mo_defender",
    "zhx_doctrine_hover_mo_peace",
}
HOVER_ROW_LOCALISATION = (
    {
        f"zhx_doctrine_hover_{school}_positive_1"
        for school in ("ru", "fa", "dao", "bing", "zongheng")
    }
    | {"zhx_doctrine_hover_mo_defender", "zhx_doctrine_hover_mo_peace"}
    | {
        f"zhx_doctrine_hover_{school}_positive_{slot}"
        for school in EXPECTED_FLAGS
        for slot in (2, 3)
    }
    | {
        f"zhx_doctrine_hover_{school}_negative_{slot}"
        for school in EXPECTED_FLAGS
        for slot in (1, 2)
    }
    | {
        f"zhx_doctrine_hover_{school}_negative_3"
        for school in ("ru", "fa", "mo", "bing", "zongheng")
    }
)
REMOVED_PRACTICE_LEDGER_BUTTONS = {
    "zhx_religion_practice_hollow_ledger_button",
    "zhx_religion_practice_established_ledger_button",
    "zhx_religion_practice_flourishing_ledger_button",
    "zhx_religion_practice_exemplary_ledger_button",
    "zhx_lijiao_school_rules_button",
}
SCHOOL_TOOLTIP_ROWS = {
    "zhx_ru_school": (
        "§R0-24 · 礼崩名乱§!：全国叛乱度 +2；稳定度花费 +15%；外交声誉 -1",
        "§Y25-49 · 儒论初行§!：顾问花费 -2.5%；稳定度花费 -2.5%",
        "§G50-74 · 礼治成章§!：顾问花费 -5%；稳定度花费 -5%；外交声誉 +0.5",
        "§O75-100 · 仁政化成§!：顾问花费 -10%；稳定度花费 -10%；外交声誉 +1；全国叛乱度 -1",
    ),
    "zhx_fa_school": (
        "§R0-24 · 法令不行§!：月度自治度变化 +0.10；造核花费 +10%；年度腐败 +0.10",
        "§Y25-49 · 法令始定§!：月度自治度变化 -0.025；造核花费 -2.5%",
        "§G50-74 · 法术势并行§!：月度自治度变化 -0.05；造核花费 -5%；年度腐败 -0.05",
        "§O75-100 · 名实一贯§!：月度自治度变化 -0.075；造核花费 -10%；年度腐败 -0.10；训练度 +2.5%",
    ),
    "zhx_mo_school": (
        "§R0-24 · 守义不修§!：要塞维护费 +25%；要塞防御 -20%；发展成本 +10%",
        "§Y25-49 · 墨守有方§!：要塞维护费 -5%；要塞防御 +5%",
        "§G50-74 · 兼爱尚贤§!：要塞维护费 -10%；要塞防御 +10%；外交声誉 +0.5",
        "§O75-100 · 非攻成治§!：要塞维护费 -20%；要塞防御 +20%；外交声誉 +1；发展成本 -5%",
    ),
    "zhx_dao_school": (
        "§R0-24 · 失道扰民§!：全国叛乱度 +2；月度厌战 +0.03；发展成本 +10%",
        "§Y25-49 · 守静初行§!：全国叛乱度 -0.5；月度厌战 -0.01",
        "§G50-74 · 清静成治§!：全国叛乱度 -1；月度厌战 -0.02；发展成本 -2.5%",
        "§O75-100 · 自然化成§!：全国叛乱度 -2；月度厌战 -0.03；发展成本 -5%；稳定度花费 -5%",
    ),
    "zhx_bing_school": (
        "§R0-24 · 武备弛废§!：人力恢复速度 -20%；陆军传统衰减 +1%；陆军士气 -10%",
        "§Y25-49 · 讲武有备§!：人力恢复速度 +5%；陆军传统衰减 -0.5%",
        "§G50-74 · 兵势相济§!：人力恢复速度 +10%；陆军传统衰减 -1%；陆军士气 +5%",
        "§O75-100 · 师律精强§!：人力恢复速度 +15%；陆军传统衰减 -1%；陆军士气 +10%；训练度 +2.5%",
    ),
    "zhx_zongheng_school": (
        "§R0-24 · 信义俱失§!：改善关系 -25%；外交声誉 -1；外交关系 -1",
        "§Y25-49 · 行人通聘§!：改善关系 +10%；外交声誉 +0.25",
        "§G50-74 · 合纵有方§!：改善关系 +15%；外交声誉 +0.5；外交关系 +1",
        "§O75-100 · 从横捭阖§!：改善关系 +25%；外交声誉 +1；外交关系 +1；外交官 +1",
    ),
}
REMOVED_RELIGION_CARD_CONTROLS = {
    "zhx_religion_school_none_window",
    "zhx_religion_school_ru_window",
    "zhx_religion_school_fa_window",
    "zhx_religion_school_mo_window",
    "zhx_religion_school_dao_window",
    "zhx_religion_school_bing_window",
    "zhx_religion_school_zongheng_window",
    "zhx_religion_tier_hollow_window",
    "zhx_religion_tier_established_window",
    "zhx_religion_tier_flourishing_window",
    "zhx_religion_tier_exemplary_window",
    "zhx_religion_last_delta",
}
EXPECTED_MODIFIERS = {
    "zhx_doctrine_ru_hollow",
    "zhx_doctrine_ru_established",
    "zhx_doctrine_ru_flourishing",
    "zhx_doctrine_ru_exemplary",
    "zhx_doctrine_fa_hollow",
    "zhx_doctrine_fa_established",
    "zhx_doctrine_fa_flourishing",
    "zhx_doctrine_fa_exemplary",
    "zhx_doctrine_mo_hollow",
    "zhx_doctrine_mo_established",
    "zhx_doctrine_mo_flourishing",
    "zhx_doctrine_mo_exemplary",
    "zhx_doctrine_dao_hollow",
    "zhx_doctrine_dao_established",
    "zhx_doctrine_dao_flourishing",
    "zhx_doctrine_dao_exemplary",
    "zhx_doctrine_bing_hollow",
    "zhx_doctrine_bing_established",
    "zhx_doctrine_bing_flourishing",
    "zhx_doctrine_bing_exemplary",
    "zhx_doctrine_zongheng_hollow",
    "zhx_doctrine_zongheng_established",
    "zhx_doctrine_zongheng_flourishing",
    "zhx_doctrine_zongheng_exemplary",
    "zhx_doctrine_change_cooldown",
}
HOLLOW_MODIFIER_VALUES = {
    "ru": {
        "global_unrest": "2",
        "stability_cost_modifier": "0.15",
        "diplomatic_reputation": "-1",
    },
    "fa": {
        "global_autonomy": "0.10",
        "core_creation": "0.10",
        "yearly_corruption": "0.10",
    },
    "mo": {
        "fort_maintenance_modifier": "0.25",
        "defensiveness": "-0.20",
        "development_cost": "0.10",
    },
    "dao": {
        "global_unrest": "2",
        "war_exhaustion": "0.03",
        "development_cost": "0.10",
    },
    "bing": {
        "manpower_recovery_speed": "-0.20",
        "army_tradition_decay": "0.01",
        "land_morale": "-0.10",
    },
    "zongheng": {
        "improve_relation_modifier": "-0.25",
        "diplomatic_reputation": "-1",
        "diplomatic_upkeep": "-1",
    },
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
    "zhx_doctrine.94.t",
    "zhx_doctrine.94.d",
    "zhx_doctrine.94.a",
    "zhx_doctrine.95.t",
    "zhx_doctrine.95.d.gained",
    "zhx_doctrine.95.d.lost",
    "zhx_doctrine.95.a",
    "zhx_doctrine_receipt_school_ru",
    "zhx_doctrine_receipt_school_fa",
    "zhx_doctrine_receipt_school_mo",
    "zhx_doctrine_receipt_school_dao",
    "zhx_doctrine_receipt_school_bing",
    "zhx_doctrine_receipt_school_zongheng",
    "zhx_doctrine_receipt_school_unknown",
    "zhx_doctrine_receipt_tier_hollow",
    "zhx_doctrine_receipt_tier_established",
    "zhx_doctrine_receipt_tier_flourishing",
    "zhx_doctrine_receipt_tier_exemplary",
    "zhx_convene_later_schools_debate_title",
    "zhx_convene_later_schools_debate_desc",
    "zhx_doctrine_expansion.1.t",
    "zhx_doctrine_expansion.1.d",
    "zhx_doctrine_expansion.1.a",
    "zhx_doctrine_expansion.1.b",
    "zhx_doctrine_expansion.1.c",
    "zhx_doctrine_expansion.1.e",
    "zhx_doctrine_expansion_postpone_tt",
    "zhx_doctrine_expansion.10.t",
    "zhx_doctrine_expansion.10.d",
    "zhx_doctrine_expansion.11.t",
    "zhx_doctrine_expansion.11.d",
    "zhx_doctrine_expansion.12.t",
    "zhx_doctrine_expansion.12.d",
    "zhx_doctrine.choose_dao",
    "zhx_doctrine.choose_bing",
    "zhx_doctrine.choose_zongheng",
    "zhx_adopt_dao_doctrine_tt",
    "zhx_adopt_bing_doctrine_tt",
    "zhx_adopt_zongheng_doctrine_tt",
    "zhx_doctrine.20.d.dao",
    "zhx_doctrine.20.d.bing",
    "zhx_doctrine.20.d.zongheng",
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


def top_level_assignment_keys(body: str) -> set[str]:
    """Return assignment keys at depth zero inside an extracted block."""
    keys: set[str] = set()
    depth = 0
    in_string = False
    escaped = False
    for raw_line in body.splitlines():
        line = raw_line.split("#", 1)[0]
        if depth == 0:
            match = re.match(r"\s*([a-z_]+)\s*=", line)
            if match is not None:
                keys.add(match.group(1))
        for char in line:
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
    require(depth == 0, "cannot read top-level keys from an unbalanced block")
    return keys


def country_event_body(text: str, event_id: str) -> str:
    """Return one directly loaded country_event body selected by its literal ID."""
    matching_bodies: list[str] = []
    for match in re.finditer(r"(?m)^country_event\s*=\s*\{", text):
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
                    body = text[opening + 1:index]
                    if re.search(
                        rf"(?m)^\s*id\s*=\s*{re.escape(event_id)}\s*$", body
                    ):
                        matching_bodies.append(body)
                    break
    require(
        len(matching_bodies) == 1,
        f"expected exactly one directly loaded country_event {event_id}",
    )
    return matching_bodies[0]


def defined_text_body(text: str, defined_name: str) -> str:
    """Return one customizable-localisation defined_text body by its name."""
    matching_bodies: list[str] = []
    for match in re.finditer(r"(?m)^defined_text\s*=\s*\{", text):
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
                    body = text[opening + 1:index]
                    if re.search(
                        rf"(?m)^\s*name\s*=\s*{re.escape(defined_name)}\s*$",
                        body,
                    ):
                        matching_bodies.append(body)
                    break
    require(
        len(matching_bodies) == 1,
        f"expected exactly one defined_text {defined_name}",
    )
    return matching_bodies[0]


def named_block_body(text: str, key: str) -> str:
    match = re.search(rf"(?m)^[ \t]*{re.escape(key)}\s*=\s*\{{", text)
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
                return text[opening + 1:index]
    raise ValueError(f"block {key} has no closing brace")


def named_window_body(text: str, name: str) -> str:
    match = re.search(
        rf'windowType\s*=\s*\{{\s*name\s*=\s*"{re.escape(name)}"', text
    )
    require(match is not None, f'missing windowType "{name}"')
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
    raise ValueError(f'windowType "{name}" has no closing brace')


def named_custom_window_body(text: str, name: str) -> str:
    match = re.search(
        rf"custom_window\s*=\s*\{{\s*name\s*=\s*{re.escape(name)}\b", text
    )
    require(match is not None, f'missing custom_window "{name}"')
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
    raise ValueError(f'custom_window "{name}" has no closing brace')


def named_instant_text_box_body(text: str, name: str) -> str:
    match = re.search(
        rf'instantTextBoxType\s*=\s*\{{\s*name\s*=\s*"{re.escape(name)}"', text
    )
    require(match is not None, f'missing instantTextBoxType "{name}"')
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
    raise ValueError(f'instantTextBoxType "{name}" has no closing brace')


def named_gui_button_body(text: str, name: str) -> str:
    match = re.search(
        rf'guiButtonType\s*=\s*\{{\s*name\s*=\s*"{re.escape(name)}"', text
    )
    require(match is not None, f'missing guiButtonType "{name}"')
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
    raise ValueError(f'guiButtonType "{name}" has no closing brace')


def named_custom_text_box_body(text: str, name: str) -> str:
    match = re.search(
        rf"custom_text_box\s*=\s*\{{\s*name\s*=\s*{re.escape(name)}\b", text
    )
    require(match is not None, f'missing custom_text_box "{name}"')
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
    raise ValueError(f'custom_text_box "{name}" has no closing brace')


def named_custom_button_body(text: str, name: str) -> str:
    match = re.search(
        rf"custom_button\s*=\s*\{{\s*name\s*=\s*{re.escape(name)}\b", text
    )
    require(match is not None, f'missing custom_button "{name}"')
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
    raise ValueError(f'custom_button "{name}" has no closing brace')


def named_icon_body(text: str, name: str) -> str:
    match = re.search(
        rf'iconType\s*=\s*\{{\s*name\s*=\s*"?{re.escape(name)}"?', text
    )
    require(match is not None, f'missing iconType "{name}"')
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
    raise ValueError(f'iconType "{name}" has no closing brace')


def named_custom_icon_body(text: str, name: str) -> str:
    match = re.search(
        rf"custom_icon\s*=\s*\{{\s*name\s*=\s*{re.escape(name)}\b", text
    )
    require(match is not None, f'missing custom_icon "{name}"')
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
    raise ValueError(f'custom_icon "{name}" has no closing brace')


def rectangle_from_body(body: str, name: str) -> tuple[int, int, int, int]:
    position = re.search(
        r"position\s*=\s*\{\s*x\s*=\s*(-?\d+)\s+y\s*=\s*(-?\d+)\s*\}",
        body,
    )
    size = re.search(
        r"size\s*=\s*\{\s*x\s*=\s*(\d+)\s+y\s*=\s*(\d+)\s*\}", body
    )
    if size is None:
        size = re.search(
            r"maxWidth\s*=\s*(\d+).*?maxHeight\s*=\s*(\d+)", body, re.S
        )
    require(position is not None and size is not None, f"{name} has no fixed rectangle")
    return tuple(int(value) for value in (*position.groups(), *size.groups()))


def window_rectangle(text: str, name: str) -> tuple[int, int, int, int]:
    body = named_window_body(text, name)
    return rectangle_from_body(body, name)


def instant_text_box_rectangle(text: str, name: str) -> tuple[int, int, int, int]:
    body = named_instant_text_box_body(text, name)
    return rectangle_from_body(body, name)


def decode_tga_alpha(texture: bytes, name: str) -> list[int]:
    """Decode alpha bytes from the uncompressed/RLE 32-bit TGAs we generate."""
    require(len(texture) >= 18, f"{name}: truncated TGA header")
    image_type = texture[2]
    width, height, depth = struct.unpack_from("<HHB", texture, 12)
    require(
        texture[1] == 0 and image_type in {2, 10} and depth == 32,
        f"{name}: unsupported TGA encoding",
    )
    pixel_count = width * height
    cursor = 18 + texture[0]
    alpha: list[int] = []
    if image_type == 2:
        end = cursor + pixel_count * 4
        require(end <= len(texture), f"{name}: truncated TGA pixel data")
        return list(texture[cursor + 3 : end : 4])

    while len(alpha) < pixel_count:
        require(cursor < len(texture), f"{name}: truncated TGA RLE packet")
        packet = texture[cursor]
        cursor += 1
        count = (packet & 0x7F) + 1
        if packet & 0x80:
            require(cursor + 4 <= len(texture), f"{name}: truncated TGA RLE pixel")
            alpha.extend([texture[cursor + 3]] * count)
            cursor += 4
        else:
            end = cursor + count * 4
            require(end <= len(texture), f"{name}: truncated TGA raw packet")
            alpha.extend(texture[cursor + 3 : end : 4])
            cursor = end
    require(len(alpha) == pixel_count, f"{name}: excess TGA RLE pixels")
    return alpha


def main() -> None:
    texts = {path: read(path) for path in SCRIPT_PATHS}
    on_action = read(ON_ACTION_PATH)
    localisation = (
        read(LOCALISATION_PATH)
        + "\n"
        + read(EXPANSION_LOCALISATION_PATH)
    )
    native_gfx = read(NATIVE_GFX_PATH)
    lijiao_gfx = read(LIJIAO_GFX_PATH)
    native_gui = read(NATIVE_GUI_PATH)
    native_diplomacy_gui = read(NATIVE_DIPLOMACY_GUI_PATH)
    native_custom_gui = read(NATIVE_CUSTOM_GUI_PATH)
    native_religion = read(NATIVE_RELIGION_PATH)
    native_religion_builder = read(NATIVE_RELIGION_BUILDER_PATH)
    native_gui_builder = read(NATIVE_GUI_BUILDER_PATH)
    native_diplomacy_builder = read(NATIVE_DIPLOMACY_BUILDER_PATH)
    native_localisation = read(NATIVE_LOCALISATION_PATH)
    religion_view_body = named_window_body(native_gui, "countryreligionview")
    diplomacy_view_body = named_window_body(
        native_diplomacy_gui, "countrydiplomacyview"
    )

    for path, text in (
        *texts.items(),
        (ON_ACTION_PATH, on_action),
        (NATIVE_GFX_PATH, native_gfx),
        (LIJIAO_GFX_PATH, lijiao_gfx),
        (NATIVE_GUI_PATH, native_gui),
        (NATIVE_DIPLOMACY_GUI_PATH, native_diplomacy_gui),
        (NATIVE_CUSTOM_GUI_PATH, native_custom_gui),
        (NATIVE_RELIGION_PATH, native_religion),
    ):
        validate_braces(path, text)

    require(
        not TEMP_RUNTIME_EVENT_PATH.exists(),
        "temporary zhxtest runtime event must not ship in the mod",
    )
    forbidden_harness_names = re.compile(r"(?:zhxtest|fatest|motest)", re.I)
    leaked_harness_files = sorted(
        path.relative_to(ROOT).as_posix()
        for path in MOD.rglob("*")
        if path.is_file() and forbidden_harness_names.search(path.name)
    )
    require(
        not leaked_harness_files,
        f"temporary religion harness files remain: {leaked_harness_files}",
    )
    production_clausewitz = {
        path: path.read_text(encoding="utf-8-sig", errors="ignore")
        for path in MOD.rglob("*.txt")
    }
    for path, text in production_clausewitz.items():
        require(
            re.search(r"\bzhxtest(?:\.\d+)?\b", text, re.I) is None
            and "ZHX_DIRECT_" not in text
            and "ZHX_DOCTRINE_CARD_ASSERT" not in text
            and "TEMP runtime harness" not in text,
            f"temporary religion probe remains in {path.relative_to(ROOT)}",
        )
    school_assignment_files = sorted(
        path.relative_to(ROOT).as_posix()
        for path, text in production_clausewitz.items()
        if "set_religious_school" in text
    )
    require(
        school_assignment_files
        == ["guangdong_independent_practice/events/zhx_doctrine_events.txt"],
        "native doctrine assignments must live only in the directly loaded "
        f"religion event file; found={school_assignment_files}",
    )

    require(
        "609e2d235f3441c64b895d9faf3927bbf1399149cffa955137ab2d070b9645a6"
        in native_religion_builder
        and 'common/religions/00_religion.txt' in native_religion_builder,
        "religion builder must remain pinned to the EU4 1.37.5 baseline",
    )
    require(
        "ab1fd87cd2c54ba2fb334fd0353edfba84c8f223366bf64f048b76c4743cfd29"
        in native_gui_builder
        and "2976470733" in native_gui_builder
        and 'interface/countryreligionview.gui' in native_gui_builder,
        "religion-view builder must remain pinned to the required Chinese 1.37 baseline",
    )
    require(
        "74a02752cfc622ebcfbac1a359a7efe07fe6cbbec4a359987f67f205e113de4a"
        in native_diplomacy_builder
        and "2976470733" in native_diplomacy_builder
        and 'interface/countrydiplomacyview.gui' in native_diplomacy_builder,
        "diplomacy builder must remain pinned to the required Chinese 1.37 baseline",
    )
    tripod_overlay_name = "zhx_lijiao_school_button_overlay"
    tripod_overlay_sprite = "GFX_zhx_lijiao_school_button"
    tripod_overlay_body = named_icon_body(religion_view_body, tripod_overlay_name)
    require(
        religion_view_body.count(f'name = "{tripod_overlay_name}"') == 1
        and re.search(
            r"position\s*=\s*\{\s*x\s*=\s*180\s+y\s*=\s*148\s*\}",
            tripod_overlay_body,
        )
        is not None
        and f'spriteType = "{tripod_overlay_sprite}"' in tripod_overlay_body
        and "alwaystransparent = yes" in tripod_overlay_body
        and "scripted = yes" in tripod_overlay_body,
        "礼教 tripod must be a mouse-transparent 42 px reskin of the native "
        "invite-scholar button",
    )
    require(
        lijiao_gfx.count(f'name = "{tripod_overlay_sprite}"') == 1,
        "礼教 scholar-button sprite must be registered exactly once",
    )
    overlay_sprite_body = lijiao_gfx.split(
        f'name = "{tripod_overlay_sprite}"', 1
    )[1][:300]
    require(
        'texturefile = "gfx/interface/zhx_lijiao_school_button.dds"'
        in overlay_sprite_body
        and 'loadType = "INGAME"' in overlay_sprite_body,
        "礼教 scholar-button sprite must load the generated in-game DDS",
    )
    overlay_texture_path = MOD / "gfx/interface/zhx_lijiao_school_button.dds"
    overlay_texture = (
        overlay_texture_path.read_bytes() if overlay_texture_path.is_file() else b""
    )
    require(
        len(overlay_texture) >= 128 and overlay_texture[:4] == b"DDS ",
        "missing or malformed 礼教 scholar-button DDS",
    )
    overlay_height, overlay_width = struct.unpack_from("<II", overlay_texture, 12)
    require(
        (overlay_width, overlay_height) == (42, 42),
        "礼教 scholar-button DDS must match the native 42x42 button",
    )
    require(
        native_custom_gui.count(f"name = {tripod_overlay_name}") == 1,
        "礼教 tripod must have exactly one passive custom-icon binding",
    )
    tripod_custom_body = named_custom_icon_body(
        native_custom_gui, tripod_overlay_name
    )
    require(
        "zhx_is_lijiao_country = yes" in tripod_custom_body
        and "zhx_has_doctrine = yes" in tripod_custom_body
        and "has_religious_school = yes" in tripod_custom_body
        and "trigger =" not in tripod_custom_body
        and "effect =" not in tripod_custom_body
        and "tooltip =" not in tripod_custom_body,
        "礼教 tripod must remain decorative so the underlying native button "
        "owns all invitation clicks",
    )
    native_invite_button_body = named_gui_button_body(
        religion_view_body, "invite_scholar_button"
    )
    require(
        religion_view_body.count('name ="invite_scholar_button"') == 1
        and re.search(
            r"position\s*=\s*\{\s*x\s*=\s*180\s+y\s*=\s*148\s*\}",
            native_invite_button_body,
        )
        is not None
        and 'quadTextureSprite = "GFX_muslim_school_button"'
        in native_invite_button_body,
        "the engine-owned invite-scholar button must remain intact beneath the tripod",
    )
    sentinel_overlay_name = "zhx_no_doctrine_school_button_overlay"
    sentinel_overlay_sprite = "GFX_zhx_no_doctrine_school_button"
    sentinel_overlay_body = named_icon_body(
        religion_view_body, sentinel_overlay_name
    )
    require(
        religion_view_body.count(f'name = "{sentinel_overlay_name}"') == 1
        and re.search(
            r"position\s*=\s*\{\s*x\s*=\s*180\s+y\s*=\s*148\s*\}",
            sentinel_overlay_body,
        )
        is not None
        and f'spriteType = "{sentinel_overlay_sprite}"' in sentinel_overlay_body
        and "alwaystransparent = yes" in sentinel_overlay_body
        and "scripted = yes" in sentinel_overlay_body,
        "no-doctrine overlay must cover the native 42 px button without "
        "intercepting its hitbox",
    )
    require(
        lijiao_gfx.count(f'name = "{sentinel_overlay_sprite}"') == 1,
        "no-doctrine school-button sprite must be registered exactly once",
    )
    sentinel_sprite_body = lijiao_gfx.split(
        f'name = "{sentinel_overlay_sprite}"', 1
    )[1][:300]
    require(
        'texturefile = "gfx/interface/zhx_no_doctrine_school_button.dds"'
        in sentinel_sprite_body
        and 'loadType = "INGAME"' in sentinel_sprite_body,
        "no-doctrine button sprite must load the generated in-game DDS",
    )
    sentinel_button_path = MOD / "gfx/interface/zhx_no_doctrine_school_button.dds"
    sentinel_button = (
        sentinel_button_path.read_bytes() if sentinel_button_path.is_file() else b""
    )
    require(
        len(sentinel_button) >= 128 and sentinel_button[:4] == b"DDS ",
        "missing or malformed no-doctrine school-button DDS",
    )
    sentinel_button_height, sentinel_button_width = struct.unpack_from(
        "<II", sentinel_button, 12
    )
    require(
        (sentinel_button_width, sentinel_button_height) == (42, 42),
        "no-doctrine school-button DDS must match the native 42x42 button",
    )
    require(
        native_custom_gui.count(f"name = {sentinel_overlay_name}") == 1,
        "no-doctrine overlay must have exactly one custom-icon binding",
    )
    sentinel_custom_body = named_custom_icon_body(
        native_custom_gui, sentinel_overlay_name
    )
    require(
        "group = eastern" in sentinel_custom_body
        and "school = zhx_no_doctrine_school" in sentinel_custom_body
        and "zhx_has_doctrine = yes" not in sentinel_custom_body,
        "no-doctrine overlay must bind only to the exact eastern sentinel",
    )
    school_icon_body = named_icon_body(
        diplomacy_view_body, "religious_school_icon"
    )
    require(
        re.search(
            r"position\s*=\s*\{\s*x\s*=\s*110\s+y\s*=\s*142\s*\}",
            school_icon_body,
        )
        is not None
        and re.search(r"scale\s*=\s*0\.5\b", school_icon_body) is not None,
        "foreign-country native school icon must retain the supported anchor and scale",
    )
    nation_label = named_instant_text_box_body(
        diplomacy_view_body, "label_nation"
    )
    fog_label = named_instant_text_box_body(diplomacy_view_body, "label_fog")
    require(
        re.search(r"position\s*=\s*\{\s*x\s*=\s*142\s+y\s*=\s*123\s*\}", nation_label)
        is not None
        and re.search(r"maxWidth\s*=\s*190\b", nation_label) is not None
        and re.search(r"position\s*=\s*\{\s*x\s*=\s*142\s+y\s*=\s*145\s*\}", fog_label)
        is not None
        and re.search(r"maxWidth\s*=\s*160\b", fog_label) is not None,
        "foreign-country labels must leave a six-pixel gutter after the school icon",
    )
    school_tooltip_sprite = "GFX_zhx_school_tooltip_hitbox"
    require(
        lijiao_gfx.count(f'name = "{school_tooltip_sprite}"') == 1,
        "school-card tooltip hitbox sprite must be registered exactly once",
    )
    school_tooltip_sprite_body = lijiao_gfx.split(
        f'name = "{school_tooltip_sprite}"', 1
    )[1][:300]
    require(
        'texturefile = "gfx/interface/zhx_school_tooltip_hitbox.dds"'
        in school_tooltip_sprite_body
        and 'loadType = "INGAME"' in school_tooltip_sprite_body,
        "school-card tooltip hitbox must load the generated in-game DDS",
    )
    school_tooltip_path = MOD / "gfx/interface/zhx_school_tooltip_hitbox.dds"
    school_tooltip_texture = (
        school_tooltip_path.read_bytes() if school_tooltip_path.is_file() else b""
    )
    require(
        len(school_tooltip_texture) >= 128
        and school_tooltip_texture[:4] == b"DDS ",
        "missing or malformed school-card tooltip DDS",
    )
    school_tooltip_height, school_tooltip_width = struct.unpack_from(
        "<II", school_tooltip_texture, 12
    )
    require(
        (school_tooltip_width, school_tooltip_height) == (26, 26)
        and not any(school_tooltip_texture[128:]),
        "school-card tooltip DDS must be a fully transparent 26x26 image",
    )
    for school, doctrine_flag in NATIVE_SCHOOL_FLAGS.items():
        for view_name, view_body, icon_name, x, y in (
            (
                "religion",
                religion_view_body,
                RELIGION_SCHOOL_TOOLTIP_ICONS[school],
                93,
                193,
            ),
            (
                "diplomacy",
                diplomacy_view_body,
                DIPLOMACY_SCHOOL_TOOLTIP_ICONS[school],
                110,
                142,
            ),
        ):
            icon_body = named_icon_body(view_body, icon_name)
            require(
                view_body.count(f'name = "{icon_name}"') == 1
                and re.search(
                    rf"position\s*=\s*\{{\s*x\s*=\s*{x}\s+y\s*=\s*{y}\s*\}}",
                    icon_body,
                )
                is not None
                and f'spriteType = "{school_tooltip_sprite}"' in icon_body
                and "scripted = yes" in icon_body
                and "alwaystransparent" not in icon_body,
                f"{view_name} {school} card must own one interactive transparent "
                "hit target on the native school emblem",
            )
            require(
                native_custom_gui.count(f"name = {icon_name}") == 1,
                f"{view_name} {school} card must have one custom-icon binding",
            )
            custom_icon_body = named_custom_icon_body(native_custom_gui, icon_name)
            require(
                "zhx_is_lijiao_country = yes" in custom_icon_body
                and f"has_country_flag = {doctrine_flag}" in custom_icon_body
                and f"tooltip = {school}_desc" in custom_icon_body,
                f"{view_name} {school} card must follow the authoritative flag "
                "and use the shared native-school description",
            )
    for school, modifier in INVITED_SCHOOL_MODIFIERS.items():
        icon_name = INVITED_SCHOOL_OVERLAY_ICONS[school]
        picture = NATIVE_SCHOOLS[school]
        icon_body = named_icon_body(religion_view_body, icon_name)
        require(
            religion_view_body.count(f'name = "{icon_name}"') == 1
            and re.search(
                r"position\s*=\s*\{\s*x\s*=\s*124\s+y\s*=\s*193\s*\}",
                icon_body,
            )
            is not None
            and f'spriteType = "{picture}"' in icon_body
            and re.search(r"scale\s*=\s*0\.5", icon_body) is not None
            and "alwaystransparent = yes" in icon_body
            and "scripted = yes" in icon_body,
            f"{school} invited emblem must cover the second native sub-modifier "
            "slot with the real 52px school picture at half scale",
        )
        require(
            native_custom_gui.count(f"name = {icon_name}") == 1,
            f"{school} invited emblem must have one custom-icon binding",
        )
        custom_icon_body = named_custom_icon_body(native_custom_gui, icon_name)
        require(
            "zhx_is_lijiao_country = yes" in custom_icon_body
            and f"has_country_modifier = {modifier}" in custom_icon_body
            and "tooltip =" not in custom_icon_body,
            f"{school} invited emblem must follow only its temporary modifier "
            "and leave the live native modifier tooltip clickable underneath",
        )
    eastern_body = named_block_body(native_religion, "eastern")
    require(
        eastern_body.count("religious_schools = {") == 1,
        "eastern must contain exactly one generated religious_schools block",
    )
    school_definitions = named_block_body(eastern_body, "religious_schools")
    actual_native_schools = set(
        re.findall(r"(?m)^\s*(zhx_[a-z0-9_]+_school)\s*=\s*\{", school_definitions)
    )
    require(
        actual_native_schools == set(ALL_NATIVE_SCHOOLS),
        "native school definition contract changed: "
        f"missing={sorted(set(ALL_NATIVE_SCHOOLS) - actual_native_schools)}, "
        f"extra={sorted(actual_native_schools - set(ALL_NATIVE_SCHOOLS))}",
    )
    invited_school_fields = {
        "potential_invite_scholar",
        "can_invite_scholar",
        "on_invite_scholar",
        "invite_scholar_modifier_display",
        "picture",
    }
    for school, picture in NATIVE_SCHOOLS.items():
        require(
            school_definitions.count(f"{school} = {{") == 1,
            f"{school} must be defined exactly once in eastern",
        )
        school_body = named_block_body(school_definitions, school)
        assigned_fields = top_level_assignment_keys(school_body)
        modifier = INVITED_SCHOOL_MODIFIERS[school]
        require(
            assigned_fields == invited_school_fields,
            f"{school} must expose only the approved native invitation fields; "
            f"fields={sorted(assigned_fields)}",
        )
        require(
            school_body.count("religion = confucianism") == 1
            and school_body.count("has_religious_school = yes") == 1
            and school_body.count("group = eastern") == 2
            and school_body.count("school = zhx_no_doctrine_school") == 1
            and school_body.count(f"school = {school}") == 1
            and "zhx_has_doctrine" not in school_body
            and "has_country_flag = zhx_doctrine_" not in school_body
            and school_body.count("knows_of_scholar_country_capital_trigger = yes") == 1
            and school_body.count(
                "reverse_has_opinion = { who = FROM value = 150 }"
            )
            == 1
            and school_body.count("zhx_clear_invited_school_modifiers = yes") == 1
            and school_body.count(
                f"add_country_modifier = {{ name = {modifier} duration = 7300 }}"
            )
            == 1
            and school_body.count(
                f"invite_scholar_modifier_display = {modifier}"
            )
            == 1
            and school_body.count("name = has_invited_scholar_recently") == 1
            and school_body.count("duration = 7300") == 2
            and f'picture = "{picture}"' in school_body
            and "religion_sub_modifier" not in school_body,
            f"{school} must require a known 150-opinion foreign source, grant one "
            f"20-year secondary modifier and use {picture}",
        )

    no_doctrine = "zhx_no_doctrine_school"
    no_doctrine_body = named_block_body(school_definitions, no_doctrine)
    require(
        top_level_assignment_keys(no_doctrine_body)
        == {
            "potential_invite_scholar",
            "can_invite_scholar",
            "on_invite_scholar",
            "picture",
        }
        and no_doctrine_body.count("always = no") == 2
        and re.search(r"on_invite_scholar\s*=\s*\{\s*\}", no_doctrine_body)
        is not None
        and f'picture = "{NO_DOCTRINE_SCHOOL[no_doctrine]}"'
        in no_doctrine_body,
        "no-doctrine sentinel must remain inert and non-invitable",
    )

    event_text = texts[MOD / "events/zhx_doctrine_events.txt"]
    event_ids = re.findall(r"(?m)^\s*id\s*=\s*zhx_doctrine\.(\d+)\s*$", event_text)
    require(len(event_ids) == len(set(event_ids)), "duplicate zhx_doctrine event ID")
    require(
        set(event_ids) == EXPECTED_EVENT_IDS,
        f"event ID contract changed: {sorted(event_ids)}",
    )
    review_event = country_event_body(event_text, "zhx_doctrine.20")
    for school in EXPECTED_FLAGS:
        require(
            f"has_country_flag = zhx_doctrine_{school}" in review_event
            and f"desc = zhx_doctrine.20.d.{school}" in review_event,
            f"current-doctrine review must describe {school}",
        )
    review_immediate = named_block_body(review_event, "immediate")
    require(
        re.fullmatch(
            r"\s*hidden_effect\s*=\s*\{\s*"
            r"zhx_prepare_doctrine_ledger\s*=\s*yes\s*\}\s*",
            review_immediate,
            re.S,
        )
        is not None,
        "the optional doctrine-review event must refresh its ledger without "
        "exposing cache-write script text",
    )

    receipt_calculator = country_event_body(event_text, "zhx_doctrine.93")
    receipt_calculator_trigger = named_block_body(receipt_calculator, "trigger")
    receipt_calculator_immediate = named_block_body(receipt_calculator, "immediate")
    require(
        receipt_calculator.count("hidden = yes") == 1
        and receipt_calculator.count("is_triggered_only = yes") == 1
        and "zhx_has_doctrine = yes" in receipt_calculator_trigger
        and receipt_calculator.count("option = {") == 1,
        "zhx_doctrine.93 must remain one hidden, triggered-only annual receipt calculator",
    )
    require(
        receipt_calculator_immediate.count("which = zhx_doctrine_last_delta") == 2
        and receipt_calculator_immediate.count(
            "which = zhx_doctrine_receipt_old_practice"
        )
        == 8
        and receipt_calculator_immediate.count(
            "which = zhx_doctrine_receipt_old_tier"
        )
        == 10
        and receipt_calculator_immediate.count(
            "which = zhx_doctrine_receipt_new_tier"
        )
        == 10
        and all(
            receipt_calculator_immediate.count(f"value = {threshold}") >= 2
            for threshold in (25, 50, 75)
        )
        and "ai = no" in receipt_calculator_immediate
        and receipt_calculator_immediate.count(
            "set_country_flag = zhx_doctrine_tier_receipt_pending"
        )
        == 1
        and receipt_calculator_immediate.count(
            "country_event = { id = zhx_doctrine.94 }"
        )
        == 1
        and receipt_calculator_immediate.count(
            "clr_country_flag = zhx_doctrine_proposal_gained_pending"
        )
        == 1
        and receipt_calculator_immediate.count(
            "clr_country_flag = zhx_doctrine_proposal_lost_pending"
        )
        == 1
        and receipt_calculator_immediate.count(
            "set_country_flag = zhx_doctrine_proposal_gained_pending"
        )
        == 1
        and receipt_calculator_immediate.count(
            "set_country_flag = zhx_doctrine_proposal_lost_pending"
        )
        == 1
        and receipt_calculator_immediate.count(
            "country_event = { id = zhx_doctrine.95 }"
        )
        == 2
        and receipt_calculator_immediate.count("value = 70") == 8
        and receipt_calculator_immediate.count(
            "zhx_is_tianxia_polity = yes"
        )
        == 3,
        "annual receipt calculator must derive actual post-clamp change, classify "
        "both 25/50/75 tiers, and dispatch player-only tier/proposal crossings; "
        "proposal feedback must be limited to Tianxia polities",
    )
    tier_receipt_prefix = receipt_calculator_immediate.split(
        "set_country_flag = zhx_doctrine_tier_receipt_pending", 1
    )[0]
    require(
        re.search(
            r"NOT\s*=\s*\{\s*AND\s*=\s*\{\s*"
            r"zhx_is_tianxia_polity\s*=\s*yes\s*OR\s*=\s*\{\s*"
            r"AND\s*=\s*\{\s*NOT\s*=\s*\{\s*check_variable\s*=\s*\{\s*"
            r"which\s*=\s*zhx_doctrine_receipt_old_practice\s*value\s*=\s*70\s*\}\s*\}\s*"
            r"check_variable\s*=\s*\{\s*which\s*=\s*zhx_doctrine_practice\s*value\s*=\s*70\s*\}\s*\}\s*"
            r"AND\s*=\s*\{\s*check_variable\s*=\s*\{\s*which\s*=\s*zhx_doctrine_receipt_old_practice\s*value\s*=\s*70\s*\}\s*"
            r"NOT\s*=\s*\{\s*check_variable\s*=\s*\{\s*which\s*=\s*zhx_doctrine_practice\s*value\s*=\s*70\s*\}",
            tier_receipt_prefix,
            re.S,
        )
        is not None,
        "the ordinary tier receipt must exclude Tianxia settlements that cross "
        "70 so the proposal-qualification receipt is the sole visible receipt",
    )
    require(
        re.search(
            r"set_country_flag\s*=\s*zhx_doctrine_proposal_gained_pending\s+"
            r"country_event\s*=\s*\{\s*id\s*=\s*zhx_doctrine\.95\s*\}\s*"
            r"\}\s*else_if\s*=\s*\{.*?"
            r"set_country_flag\s*=\s*zhx_doctrine_proposal_lost_pending\s+"
            r"country_event\s*=\s*\{\s*id\s*=\s*zhx_doctrine\.95\s*\}",
            receipt_calculator_immediate,
            re.S,
        )
        is not None,
        "proposal qualification must dispatch gained/lost through one exclusive if chain",
    )

    receipt_event = country_event_body(event_text, "zhx_doctrine.94")
    receipt_trigger = named_block_body(receipt_event, "trigger")
    receipt_immediate = named_block_body(receipt_event, "immediate")
    require(
        "hidden = yes" not in receipt_event
        and receipt_event.count("is_triggered_only = yes") == 1
        and "ai = no" in receipt_trigger
        and "zhx_has_doctrine = yes" in receipt_trigger
        and "has_country_flag = zhx_doctrine_tier_receipt_pending"
        in receipt_trigger
        and re.fullmatch(
            r"\s*clr_country_flag\s*=\s*zhx_doctrine_tier_receipt_pending\s*",
            receipt_immediate,
            re.S,
        )
        is not None
        and receipt_event.count("option = {") == 1,
        "zhx_doctrine.94 must be one visible, player-only, one-shot tier receipt",
    )

    proposal_receipt = country_event_body(event_text, "zhx_doctrine.95")
    proposal_receipt_trigger = named_block_body(
        proposal_receipt.split("is_triggered_only = yes", 1)[1], "trigger"
    )
    proposal_receipt_option = named_block_body(proposal_receipt, "option")
    proposal_receipt_option_effect = named_block_body(
        proposal_receipt_option, "hidden_effect"
    )
    require(
        "hidden = yes" not in proposal_receipt
        and proposal_receipt.count("is_triggered_only = yes") == 1
        and "ai = no" in proposal_receipt_trigger
        and "zhx_is_tianxia_polity = yes" in proposal_receipt_trigger
        and "zhx_has_doctrine = yes" in proposal_receipt_trigger
        and proposal_receipt_trigger.count(
            "has_country_flag = zhx_doctrine_proposal_gained_pending"
        )
        == 1
        and proposal_receipt_trigger.count(
            "has_country_flag = zhx_doctrine_proposal_lost_pending"
        )
        == 1
        and proposal_receipt.count("desc = zhx_doctrine.95.d.gained") == 1
        and proposal_receipt.count("desc = zhx_doctrine.95.d.lost") == 1
        and proposal_receipt.count("option = {") == 1,
        "zhx_doctrine.95 must be one visible, player-only Tianxia proposal receipt "
        "with mutually exclusive gained/lost descriptions",
    )
    require(
        proposal_receipt_option_effect.count(
            "clr_country_flag = zhx_doctrine_proposal_gained_pending"
        )
        == 1
        and proposal_receipt_option_effect.count(
            "clr_country_flag = zhx_doctrine_proposal_lost_pending"
        )
        == 1,
        "closing the proposal receipt must clear both direction markers",
    )

    expansion_event_text = texts[
        MOD / "events/zhx_doctrine_expansion_events.txt"
    ]
    expansion_event_ids = re.findall(
        r"(?m)^\s*id\s*=\s*zhx_doctrine_expansion\.(\d+)\s*$",
        expansion_event_text,
    )
    require(
        len(expansion_event_ids) == len(set(expansion_event_ids))
        and set(expansion_event_ids) == EXPECTED_EXPANSION_EVENT_IDS,
        f"expansion event ID contract changed: {sorted(expansion_event_ids)}",
    )
    expansion_entry = country_event_body(
        expansion_event_text, "zhx_doctrine_expansion.1"
    )
    require(
        expansion_entry.count("is_triggered_only = yes") == 1
        and "mean_time_to_happen" not in expansion_entry,
        "Dao/Bing/Zongheng entry must be explicit, not a random court popup",
    )
    decisions_text = texts[MOD / "decisions/zhx_doctrine_decisions.txt"]
    later_decision = named_block_body(
        decisions_text, "zhx_convene_later_schools_debate"
    )
    require(
        "zhx_is_lijiao_country = yes" in later_decision
        and "has_country_modifier = zhx_doctrine_change_cooldown" in later_decision
        and "country_event = { id = zhx_doctrine_expansion.1 }" in later_decision,
        "Dao/Bing/Zongheng must have a visible, cooldown-gated decision entry",
    )
    require(
        decisions_text.count("NOT = { is_year = 1450 }") == 2
        and len(
            re.findall(
                r"factor\s*=\s*0\s+NOT\s*=\s*\{\s*is_year\s*=\s*1450\s*\}",
                decisions_text,
            )
        )
        == 2,
        "both doctrine debates must keep AI from erasing the authored 1444 school map before 1450",
    )
    require(
        len(re.findall(r"(?m)^\s*zhx_doctrine\.90\s*$", on_action)) == 1,
        "on_yearly_pulse must contain zhx_doctrine.90 exactly once",
    )
    startup_body = named_block_body(on_action, "on_startup")
    require(
        "zhx_doctrine.91" not in startup_body
        and "zhx_doctrine.92" not in startup_body
        and "zhxtest" not in startup_body.lower(),
        "new-game doctrine lifecycle must not carry startup migration or test events",
    )
    require(
        startup_body.count("zhx_prepare_doctrine_ledger = yes") == 1
        and "ai = no" in startup_body
        and "zhx_is_lijiao_country = yes" in startup_body
        and "zhx_has_doctrine = yes" in startup_body,
        "startup must refresh the human Ritual Teaching hover-ledger cache "
        "without adding a migration event",
    )
    religion_change_body = named_block_body(on_action, "on_religion_change")
    require(
        len(re.findall(r"(?m)^\s*zhx_doctrine\.92\s*$", religion_change_body))
        == 1
        and on_action.count("zhx_doctrine.92") == 1,
        "on_religion_change must dispatch zhx_doctrine.92 exactly once",
    )
    yearly_body = named_block_body(on_action, "on_yearly_pulse")
    require(
        "zhx_doctrine.91" not in yearly_body
        and "zhx_doctrine.92" not in yearly_body,
        "the yearly pulse must reach school sync/retirement through shared effects",
    )
    monthly_body = named_block_body(on_action, "on_monthly_pulse")
    require(
        monthly_body.count("zhx_prepare_doctrine_ledger = yes") == 1
        and "ai = no" in monthly_body
        and "zhx_is_lijiao_country = yes" in monthly_body
        and "zhx_has_doctrine = yes" in monthly_body
        and "every_country" not in monthly_body
        and "any_province" not in monthly_body
        and "every_province" not in monthly_body,
        "monthly hover-ledger refresh must be human-only, country-local and "
        "free of world or province scans",
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
    for school, expected_values in HOLLOW_MODIFIER_VALUES.items():
        modifier = f"zhx_doctrine_{school}_hollow"
        modifier_body = top_level_effect_body(modifier_text, modifier)
        actual_values = dict(
            re.findall(
                r"(?m)^\s*([a-z_]+)\s*=\s*(-?\d+(?:\.\d+)?)\s*$",
                modifier_body,
            )
        )
        require(
            actual_values == expected_values,
            f"{modifier} must retain its approved severe 0-24 contradiction "
            f"penalty; expected={expected_values}, actual={actual_values}",
        )

    invited_modifier_text = texts[
        MOD / "common/static_modifiers/zhx_invited_school_modifiers.txt"
    ]
    invited_modifier_definitions = set(
        re.findall(
            r"(?m)^(zhx_[a-z]+_invited_scholar_modifier)\s*=\s*\{",
            invited_modifier_text,
        )
    )
    require(
        invited_modifier_definitions == set(INVITED_MODIFIER_VALUES),
        "invited-school modifier contract changed: "
        f"missing={sorted(set(INVITED_MODIFIER_VALUES) - invited_modifier_definitions)}, "
        f"extra={sorted(invited_modifier_definitions - set(INVITED_MODIFIER_VALUES))}",
    )
    for modifier, expected_values in INVITED_MODIFIER_VALUES.items():
        modifier_body = top_level_effect_body(invited_modifier_text, modifier)
        actual_values = dict(
            re.findall(
                r"(?m)^\s*([a-z_]+)\s*=\s*(-?\d+(?:\.\d+)?)\s*$",
                modifier_body,
            )
        )
        require(
            actual_values == expected_values
            and modifier_body.count("religion_sub_modifier = yes") == 1
            and modifier_body.count("religion = yes") == 1
            and modifier_body.count("is_scholar_modifier = yes") == 1
            and modifier_body.count(
                'expire_message_type = "RELIGIOUS_SCHOLAR_EXPIRY"'
            )
            == 1,
            f"{modifier} must remain one visible entry-tier scholar modifier; "
            f"expected={expected_values}, actual={actual_values}",
        )

    all_scripts = "\n".join(texts.values())
    referenced_modifiers = set(
        re.findall(
            r"(?:name|has_country_modifier|remove_country_modifier)\s*=\s*"
            r"(zhx_doctrine_[a-z0-9_]+)\b(?!\.)",
            all_scripts,
        )
    )
    require(
        referenced_modifiers <= modifier_definitions,
        f"undefined doctrine modifiers: {sorted(referenced_modifiers - modifier_definitions)}",
    )

    effect_text = texts[MOD / "common/scripted_effects/zhx_doctrine_effects.txt"]
    clear_invited_effect = top_level_effect_body(
        effect_text, "zhx_clear_invited_school_modifiers"
    )
    require(
        all(
            clear_invited_effect.count(f"remove_country_modifier = {modifier}")
            == 1
            for modifier in INVITED_MODIFIER_VALUES
        )
        and clear_invited_effect.count("remove_country_modifier =")
        == len(INVITED_MODIFIER_VALUES),
        "invited-school cleanup must remove exactly all six temporary modifiers",
    )
    remove_tiers_effect = top_level_effect_body(
        effect_text, "zhx_remove_doctrine_tier_modifiers"
    )
    refresh_tier_effect = top_level_effect_body(
        effect_text, "zhx_refresh_doctrine_tier"
    )
    tier_modifiers = EXPECTED_MODIFIERS - {"zhx_doctrine_change_cooldown"}
    require(
        all(
            remove_tiers_effect.count(f"remove_country_modifier = {modifier}") == 1
            for modifier in tier_modifiers
        )
        and "zhx_doctrine_practice_hollow" not in remove_tiers_effect,
        "tier cleanup must remove all 24 school-specific tier modifiers and no "
        "obsolete shared hollow modifier",
    )
    require(
        all(
            refresh_tier_effect.count(f"name = zhx_doctrine_{school}_hollow") == 1
            and refresh_tier_effect.count(
                f"has_country_flag = {EXPECTED_FLAGS[school]}"
            )
            == 4
            for school in EXPECTED_FLAGS
        )
        and refresh_tier_effect.count("value = 25") == 1
        and refresh_tier_effect.count("value = 50") == 1
        and refresh_tier_effect.count("value = 75") == 1
        and "zhx_doctrine_practice_hollow" not in refresh_tier_effect,
        "0-24 refresh must select exactly one school-specific severe penalty; "
        "25/50/75 must retain the three positive exclusive tiers",
    )
    trigger_text = texts[MOD / "common/scripted_triggers/zhx_doctrine_triggers.txt"]
    for school, flag in EXPECTED_FLAGS.items():
        setters = re.findall(rf"set_country_flag\s*=\s*{re.escape(flag)}\b", effect_text)
        require(len(setters) == 1, f"{flag} must be set exactly once")
        body = top_level_effect_body(effect_text, f"zhx_adopt_{school}_doctrine")
        require(
            re.search(rf"set_country_flag\s*=\s*{re.escape(flag)}\b", body) is not None,
            f"{flag} may only be set by its adoption effect",
        )

    all_doctrine_flags = set(NATIVE_SCHOOL_FLAGS.values())
    any_flag_trigger = named_block_body(trigger_text, "zhx_has_any_doctrine_flag")
    clear_flags_effect = top_level_effect_body(effect_text, "zhx_clear_doctrine_flags")
    for flag in all_doctrine_flags:
        require(
            any_flag_trigger.count(f"has_country_flag = {flag}") == 1
            and clear_flags_effect.count(f"clr_country_flag = {flag}") == 1,
            f"conversion lifecycle must detect and clear reserved doctrine flag {flag}",
        )
    clear_hover_effect = top_level_effect_body(
        effect_text, "zhx_clear_doctrine_hover_cache"
    )
    require(
        clear_hover_effect.count("clr_country_flag = zhx_doctrine_hover_")
        == len(HOVER_CACHE_FLAGS) + 1
        and all(
            clear_hover_effect.count(f"clr_country_flag = {flag}") == 1
            for flag in HOVER_CACHE_FLAGS
        )
        and clear_hover_effect.count(
            "clr_country_flag = zhx_doctrine_hover_cache_building"
        )
        == 1,
        "hover-cache cleanup must clear every factor slot and its temporary build flag",
    )
    clear_system_effect = top_level_effect_body(effect_text, "zhx_clear_doctrine_system")
    require(
        "zhx_remove_doctrine_tier_modifiers = yes" in clear_system_effect
        and "zhx_clear_invited_school_modifiers = yes" in clear_system_effect
        and "zhx_clear_doctrine_flags = yes" in clear_system_effect
        and "zhx_clear_doctrine_hover_cache = yes" in clear_system_effect
        and "clr_country_flag = zhx_doctrine_practice_initialised"
        in clear_system_effect
        and "remove_country_modifier = zhx_doctrine_change_cooldown"
        in clear_system_effect
        and "clr_country_flag = zhx_doctrine_tier_receipt_pending"
        in clear_system_effect
        and "clr_country_flag = zhx_doctrine_proposal_gained_pending"
        in clear_system_effect
        and "clr_country_flag = zhx_doctrine_proposal_lost_pending"
        in clear_system_effect
        and clear_system_effect.count("value = 0") == 9
        and "which = zhx_doctrine_practice" in clear_system_effect
        and "which = zhx_doctrine_last_delta" in clear_system_effect
        and "which = zhx_doctrine_ledger_to_proposal" in clear_system_effect,
        "doctrine cleanup must clear flags, tier/cooldown modifiers, practice, "
        "annual delta, ledger and tier-receipt scratch values",
    )

    calculator_effect = top_level_effect_body(
        effect_text, "zhx_calculate_doctrine_yearly_delta"
    )
    ledger_effect = top_level_effect_body(effect_text, "zhx_prepare_doctrine_ledger")
    yearly_effect = top_level_effect_body(effect_text, "zhx_yearly_doctrine_tick")
    require(
        calculator_effect.count("which = zhx_doctrine_calculated_delta") == 37
        and all(
            calculator_effect.count(f"has_country_flag = {flag}") == 1
            for flag in EXPECTED_FLAGS.values()
        )
        and calculator_effect.count(
            "has_country_flag = zhx_doctrine_hover_cache_building"
        )
        == len(HOVER_ROW_LOCALISATION)
        and calculator_effect.count(
            "set_country_flag = zhx_doctrine_hover_positive_1"
        )
        == 5
        and calculator_effect.count(
            "set_country_flag = zhx_doctrine_hover_positive_2"
        )
        == 6
        and calculator_effect.count(
            "set_country_flag = zhx_doctrine_hover_positive_3"
        )
        == 6
        and calculator_effect.count(
            "set_country_flag = zhx_doctrine_hover_negative_1"
        )
        == 6
        and calculator_effect.count(
            "set_country_flag = zhx_doctrine_hover_negative_2"
        )
        == 6
        and calculator_effect.count(
            "set_country_flag = zhx_doctrine_hover_negative_3"
        )
        == 5
        and calculator_effect.count(
            "set_country_flag = zhx_doctrine_hover_mo_defender"
        )
        == 1
        and calculator_effect.count(
            "set_country_flag = zhx_doctrine_hover_mo_peace"
        )
        == 1
        and "zhx_doctrine_last_delta" not in calculator_effect
        and "zhx_doctrine_practice" not in calculator_effect,
        "the shared projection calculator must contain all six annual formulas "
        "and mirror each contributing row only while a hover cache is being built",
    )
    require(
        ledger_effect.count("zhx_calculate_doctrine_yearly_delta = yes") == 1
        and ledger_effect.count("zhx_clear_doctrine_hover_cache = yes") == 1
        and ledger_effect.count(
            "set_country_flag = zhx_doctrine_hover_cache_building"
        )
        == 1
        and ledger_effect.count(
            "clr_country_flag = zhx_doctrine_hover_cache_building"
        )
        == 1
        and ledger_effect.count("which = zhx_doctrine_ledger_estimated_delta") == 1
        and ledger_effect.count("which = zhx_doctrine_ledger_to_next_tier") == 7
        and ledger_effect.count("which = zhx_doctrine_ledger_to_proposal") == 3
        and ledger_effect.count("which = zhx_doctrine_practice") == 8
        and ledger_effect.count("which = zhx_doctrine_calculated_delta") == 1
        and ledger_effect.count("change_variable = {") == 0
        and ledger_effect.count("subtract_variable = {") == 4
        and all(f"value = {threshold}" in ledger_effect for threshold in (25, 50, 75))
        and ledger_effect.count("value = 70") == 2
        and "value = 100" not in ledger_effect
        and ledger_effect.count("value = 0") >= 2
        and "country_event" not in ledger_effect,
        "the hover cache must reuse the annual calculator, retain its raw row sum, "
        "and derive the 25/50/75 next-tier gap plus max(70-practice, 0) proposal gap",
    )
    require(
        yearly_effect.count("zhx_calculate_doctrine_yearly_delta = yes") == 1
        and yearly_effect.count("which = zhx_doctrine_calculated_delta") == 1
        and "zhx_doctrine_last_delta" not in yearly_effect
        and yearly_effect.count("which = zhx_doctrine_practice") == 3
        and yearly_effect.count(
            "which = zhx_doctrine_receipt_old_practice"
        )
        == 1
        and yearly_effect.count("country_event = { id = zhx_doctrine.93 }") == 1
        and yearly_effect.count("zhx_clamp_doctrine_practice = yes") == 1
        and yearly_effect.count("zhx_refresh_doctrine_tier = yes") == 1
        and yearly_effect.count("zhx_prepare_doctrine_ledger = yes") == 1
        and all(
            token not in yearly_effect
            for token in (
                "stability = 1",
                "corruption = 2",
                "defender_leader = ROOT",
                "army_size_percentage = 0.80",
                "num_of_allies = 2",
            )
        ),
        "the actual yearly settlement must consume the same shared calculator, "
        "refresh the post-clamp hover cache, then route one snapshot to the receipt calculator",
    )

    registered_sprites = set(
        re.findall(r'(?m)^\s*name\s*=\s*"(GFX_zhx_doctrine_[a-z0-9_]+)"', native_gfx)
    )
    require(
        set(NATIVE_SCHOOLS.values()) <= registered_sprites,
        f"missing native school sprites: {sorted(set(NATIVE_SCHOOLS.values()) - registered_sprites)}",
    )
    for school, picture in NATIVE_SCHOOLS.items():
        slug = school.removeprefix("zhx_").removesuffix("_school")
        texture_path = MOD / f"gfx/interface/zhx_doctrine_{slug}_school.tga"
        texture = texture_path.read_bytes() if texture_path.is_file() else b""
        require(
            len(texture) >= 18,
            f"missing or truncated school texture: {texture_path.relative_to(ROOT)}",
        )
        width, height, depth = struct.unpack_from("<HHB", texture, 12)
        require(
            (width, height, depth) == (52, 52, 32)
            and texture[2] in {2, 10}
            and texture[17] & 0x0F == 8,
            f"{texture_path.name} must be a 52x52 32-bit true-colour TGA with alpha",
        )
        sprite_tail = native_gfx.split(f'name = "{picture}"', 1)[1][:260]
        require(
            f'texturefile = "gfx/interface/{texture_path.name}"' in sprite_tail
            and 'loadType = "INGAME"' in sprite_tail,
            f"{picture} must load {texture_path.name} as an in-game sprite",
        )

    no_doctrine_picture = NO_DOCTRINE_SCHOOL["zhx_no_doctrine_school"]
    require(
        native_gfx.count(f'name = "{no_doctrine_picture}"') == 1,
        "transparent no-doctrine school sprite must be registered exactly once",
    )
    no_doctrine_texture_path = MOD / "gfx/interface/zhx_no_doctrine_school.tga"
    no_doctrine_texture = (
        no_doctrine_texture_path.read_bytes()
        if no_doctrine_texture_path.is_file()
        else b""
    )
    require(
        len(no_doctrine_texture) >= 18,
        "missing or truncated transparent no-doctrine school texture",
    )
    no_doctrine_width, no_doctrine_height, no_doctrine_depth = struct.unpack_from(
        "<HHB", no_doctrine_texture, 12
    )
    require(
        (no_doctrine_width, no_doctrine_height, no_doctrine_depth) == (52, 52, 32)
        and no_doctrine_texture[2] in {2, 10}
        and no_doctrine_texture[17] & 0x0F == 8
        and not any(
            decode_tga_alpha(no_doctrine_texture, no_doctrine_texture_path.name)
        ),
        "no-doctrine school texture must be a fully transparent 52x52 RGBA TGA",
    )
    no_doctrine_sprite_tail = native_gfx.split(
        f'name = "{no_doctrine_picture}"', 1
    )[1][:260]
    require(
        'texturefile = "gfx/interface/zhx_no_doctrine_school.tga"'
        in no_doctrine_sprite_tail
        and 'loadType = "INGAME"' in no_doctrine_sprite_tail,
        "no-doctrine native sprite must load the transparent in-game TGA",
    )

    for removed_control in REMOVED_RELIGION_CARD_CONTROLS:
        require(
            removed_control not in religion_view_body
            and removed_control not in native_custom_gui,
            f"obsolete overlapping religion card control remains: {removed_control}",
        )

    practice_bindings: dict[str, str] = {}
    for text_box in NATIVE_STATUS_FIELDS:
        require(
            religion_view_body.count(f'name = "{text_box}"') == 1,
            f"{text_box} must occur exactly once inside countryreligionview",
        )
        practice_body = named_instant_text_box_body(religion_view_body, text_box)
        require(
            re.search(r'text\s*=\s*""', practice_body) is not None
            and re.search(r"scripted\s*=\s*yes", practice_body) is not None
            and re.search(r'font\s*=\s*"vic_18"', practice_body) is not None
            and re.search(r"format\s*=\s*centre", practice_body) is not None,
            f"{text_box} must be a centred, empty scripted text box",
        )
        x, y, width, height = instant_text_box_rectangle(native_gui, text_box)
        require(
            (x, y, width, height) == (151, 157, 28, 24),
            f"{text_box} must share the 28x24 native-school-row anchor",
        )
        require(
            native_custom_gui.count(f"name = {text_box}") == 1,
            f"{text_box} must have exactly one custom-text binding",
        )
        custom_body = named_custom_text_box_body(native_custom_gui, text_box)
        practice_bindings[text_box] = custom_body
        require(
            "zhx_is_lijiao_country = yes" in custom_body
            and "zhx_has_doctrine = yes" in custom_body
            and "tooltip = zhx_religion_practice_value_tt" in custom_body,
            f"{text_box} must be doctrine-gated and expose the status tooltip",
        )

    require(
        practice_bindings["zhx_religion_practice_hollow_value"].count("value = 25")
        == 1
        and practice_bindings["zhx_religion_practice_hollow_value"].count("NOT = {")
        == 1
        and practice_bindings["zhx_religion_practice_value"].count("value = 25")
        == 1
        and practice_bindings["zhx_religion_practice_value"].count("value = 50")
        == 1
        and practice_bindings["zhx_religion_practice_flourishing_value"].count(
            "value = 50"
        )
        == 1
        and practice_bindings["zhx_religion_practice_flourishing_value"].count(
            "value = 75"
        )
        == 1
        and practice_bindings["zhx_religion_practice_exemplary_value"].count(
            "value = 75"
        )
        == 1
        and "NOT = {"
        not in practice_bindings["zhx_religion_practice_exemplary_value"],
        "practice tier ranges must be mutually exclusive at 25/50/75",
    )

    for button in REMOVED_PRACTICE_LEDGER_BUTTONS:
        require(
            button not in religion_view_body
            and button not in native_custom_gui
            and button not in native_gui_builder,
            f"obsolete transparent practice hit target remains: {button}",
        )

    practice_button_name = "zhx_religion_practice_rules_button"
    practice_button_sprite = "GFX_zhx_practice_click_hitbox"
    practice_button_body = named_gui_button_body(
        religion_view_body, practice_button_name
    )
    require(
        religion_view_body.count(f'name = "{practice_button_name}"') == 1
        and re.search(
            r"position\s*=\s*\{\s*x\s*=\s*151\s+y\s*=\s*157\s*\}",
            practice_button_body,
        )
        is not None
        and f'quadTextureSprite = "{practice_button_sprite}"'
        in practice_button_body
        and "clicksound = click" in practice_button_body
        and "scripted = yes" in practice_button_body
        and "alwaystransparent" not in practice_button_body,
        "practice number must have one interactive but visually transparent "
        "28x24 scripted hit target",
    )
    require(
        lijiao_gfx.count(f'name = "{practice_button_sprite}"') == 1,
        "practice click-hitbox sprite must be registered exactly once",
    )
    practice_sprite_body = lijiao_gfx.split(
        f'name = "{practice_button_sprite}"', 1
    )[1][:300]
    require(
        'texturefile = "gfx/interface/zhx_practice_click_hitbox.dds"'
        in practice_sprite_body
        and 'loadType = "INGAME"' in practice_sprite_body,
        "practice click-hitbox sprite must load the generated in-game DDS",
    )
    practice_hitbox_path = MOD / "gfx/interface/zhx_practice_click_hitbox.dds"
    practice_hitbox = (
        practice_hitbox_path.read_bytes() if practice_hitbox_path.is_file() else b""
    )
    require(
        len(practice_hitbox) >= 128 and practice_hitbox[:4] == b"DDS ",
        "missing or malformed practice click-hitbox DDS",
    )
    practice_height, practice_width = struct.unpack_from("<II", practice_hitbox, 12)
    require(
        (practice_width, practice_height) == (28, 24)
        and not any(practice_hitbox[128:]),
        "practice click-hitbox DDS must be a fully transparent 28x24 image",
    )
    require(
        native_custom_gui.count(f"name = {practice_button_name}") == 1,
        "practice number must have exactly one custom-button binding",
    )
    practice_custom_body = named_custom_button_body(
        native_custom_gui, practice_button_name
    )
    require(
        "zhx_is_lijiao_country = yes" in practice_custom_body
        and "zhx_has_doctrine = yes" in practice_custom_body
        and re.fullmatch(
            r"\s*always\s*=\s*yes\s*",
            named_block_body(practice_custom_body, "trigger"),
            re.S,
        )
        is not None
        and re.fullmatch(
            r"\s*country_event\s*=\s*\{\s*id\s*=\s*"
            r"zhx_doctrine\.20\s*\}\s*",
            named_block_body(practice_custom_body, "effect"),
            re.S,
        )
        is not None
        and "tooltip = zhx_religion_practice_value_tt" in practice_custom_body,
        "practice hit target must keep the concise hover and open the complete rules",
    )
    require(
        native_custom_gui.count("country_event = { id = zhx_doctrine.20 }") == 1,
        "only the practice-number hit target may open the complete rules",
    )

    sync_body = top_level_effect_body(effect_text, "zhx_sync_native_doctrine_school")
    require(
        re.fullmatch(
            r"\s*country_event\s*=\s*\{\s*id\s*=\s*zhx_doctrine\.91\s*\}\s*",
            sync_body,
            re.S,
        )
        is not None
        and "set_religious_school" not in effect_text,
        "native-school scripted effect must only dispatch the directly loaded "
        "zhx_doctrine.91 mirror event",
    )
    mirror_event = country_event_body(event_text, "zhx_doctrine.91")
    mirror_trigger = named_block_body(mirror_event, "trigger")
    mirror_immediate = named_block_body(mirror_event, "immediate")
    mirror_option = named_block_body(mirror_event, "option")
    require(
        mirror_event.count("hidden = yes") == 1
        and mirror_event.count("is_triggered_only = yes") == 1
        and "zhx_is_lijiao_country = yes" in mirror_trigger,
        "zhx_doctrine.91 must be a hidden, triggered-only Ritual Teaching event",
    )
    require(
        not re.search(
            r"\b(?:mean_time_to_happen|random|random_list|days|months|years)\b",
            mirror_event,
        )
        and mirror_event.count("option = {") == 1
        and re.fullmatch(r"\s*name\s*=\s*OK\s*", mirror_option) is not None,
        "zhx_doctrine.91 must execute immediately and expose only an inert OK option",
    )
    require(
        mirror_immediate.count("set_religious_school = {") == len(NATIVE_SCHOOLS)
        and mirror_immediate.count("group = eastern") == len(NATIVE_SCHOOLS),
        "zhx_doctrine.91 must directly own six eastern native-school assignments",
    )
    retire_event = country_event_body(event_text, "zhx_doctrine.92")
    retire_trigger = named_block_body(retire_event, "trigger")
    retire_immediate = named_block_body(retire_event, "immediate")
    retire_option = named_block_body(retire_event, "option")
    require(
        retire_event.count("hidden = yes") == 1
        and retire_event.count("is_triggered_only = yes") == 1
        and "zhx_has_any_doctrine_flag = yes" in retire_trigger
        and "has_religious_school = yes" in retire_trigger
        and "NOT = { zhx_is_lijiao_country = yes }" in retire_trigger
        and "NOT = { zhx_has_any_doctrine_flag = yes }" in retire_trigger,
        "zhx_doctrine.92 must cover departure from 礼教 and stale-mirror "
        "retirement when returning without a doctrine",
    )
    require(
        retire_event.count("option = {") == 1
        and re.fullmatch(r"\s*name\s*=\s*OK\s*", retire_option) is not None
        and retire_immediate.count("set_religious_school = {") == 1
        and retire_immediate.count("group = eastern") == 2
        and retire_immediate.count("school = zhx_no_doctrine_school") == 1
        and "limit = { religion_group = eastern }" in retire_immediate
        and retire_immediate.count("zhx_clear_doctrine_system = yes") == 1,
        "zhx_doctrine.92 must gate one direct eastern sentinel assignment, then "
        "clear authoritative doctrine state",
    )
    retire_body = top_level_effect_body(effect_text, "zhx_retire_doctrine_system")
    require(
        re.fullmatch(
            r"\s*country_event\s*=\s*\{\s*id\s*=\s*zhx_doctrine\.92\s*\}\s*",
            retire_body,
            re.S,
        )
        is not None
        and "zhx_retire_doctrine_system = yes"
        in country_event_body(event_text, "zhx_doctrine.90"),
        "the annual safety path must dispatch the direct zhx_doctrine.92 "
        "lifecycle event through the retirement effect",
    )
    require(
        event_text.count("set_religious_school = {")
        == len(NATIVE_SCHOOLS) + len(NO_DOCTRINE_SCHOOL)
        and all(
            "set_religious_school" not in script
            for path, script in texts.items()
            if path != MOD / "events/zhx_doctrine_events.txt"
        )
        and "set_religious_school" not in on_action,
        "all production native-school assignments must live only in the direct "
        "zhx_doctrine.91/.92 events",
    )
    route_kinds = re.findall(r"(?m)^\s*(if|else_if)\s*=", mirror_immediate)
    require(
        route_kinds == ["if", "else_if", "else_if", "else_if", "else_if", "else_if"],
        "zhx_doctrine.91 must route the six doctrine flags through one exclusive if chain",
    )
    branch_offsets: list[int] = []
    for school, flag in NATIVE_SCHOOL_FLAGS.items():
        branch = re.search(
            rf"(?:if|else_if)\s*=\s*\{{\s*"
            rf"limit\s*=\s*\{{[^}}]*has_country_flag\s*=\s*{re.escape(flag)}"
            rf"[^}}]*\}}\s*set_religious_school\s*=\s*\{{\s*"
            rf"group\s*=\s*eastern\s*school\s*=\s*{re.escape(school)}\s*\}}\s*\}}",
            mirror_immediate,
            re.S,
        )
        require(
            branch is not None
            and mirror_trigger.count(f"has_country_flag = {flag}") == 1
            and mirror_immediate.count(f"has_country_flag = {flag}") == 1
            and mirror_immediate.count(f"school = {school}") == 1,
            f"zhx_doctrine.91 does not map {flag} to {school} exactly once",
        )
        branch_offsets.append(branch.start())
    require(
        branch_offsets == sorted(branch_offsets),
        "zhx_doctrine.91 school priority must remain Ru, Fa, Mo, Dao, Bing, Zongheng",
    )
    require(
        not re.search(
            r"\b(?:set_country_flag|clr_country_flag|set_variable|change_variable|"
            r"add_country_modifier|add_adm_power|add_dip_power|add_mil_power|"
            r"change_religion|change_province_religion|country_event|province_event|"
            r"hidden_effect|after)\b",
            mirror_immediate,
        ),
        "native-school mirror event must not mutate authoritative doctrine gameplay state",
    )
    finish_adoption = top_level_effect_body(effect_text, "zhx_finish_doctrine_adoption")
    require(
        "zhx_sync_native_doctrine_school = yes" in finish_adoption
        and finish_adoption.count("zhx_prepare_doctrine_ledger = yes") == 1,
        "doctrine adoption must sync its native mirror and immediately refresh "
        "the hover-ledger cache",
    )
    require(
        "zhx_sync_native_doctrine_school = yes"
        in top_level_effect_body(effect_text, "zhx_yearly_doctrine_tick"),
        "the yearly tick must retain the compatibility hook for existing saves",
    )
    require(
        len(
            re.findall(
                r"(?m)^\s*zhx_sync_native_doctrine_school\s*=\s*yes\s*$",
                all_scripts,
            )
        )
        == 2,
        "only doctrine adoption and the yearly tick may call the native-school sync hook",
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
    require(
        expansion_event_text.count("duration = 1825") == 3,
        "each expansion no-verdict path needs five years",
    )
    require(
        expansion_event_text.count("duration = 730") == 1,
        "expansion postponement needs two years",
    )

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
    require(
        "zhx_doctrine_practice_hollow" not in actual_localisation
        and "zhx_doctrine_practice_hollow_desc" not in actual_localisation,
        "obsolete shared 0-24 modifier localisation must not return; each school "
        "now owns a distinct contradiction penalty",
    )
    require(
        localisation.count("[Root.zhx_doctrine_practice.GetValue]") >= 6
        and localisation.count(
            "[Root.zhx_doctrine_ledger_to_next_tier.GetValue]"
        )
        == 6
        and localisation.count(
            "[Root.zhx_doctrine_ledger_to_proposal.GetValue]"
        )
        == 6
        and localisation.count(
            "达到后仍需本派三国采用，并有另一同派国家践履50"
        )
        == 6
        and localisation.count("[Root.GetZhxDoctrinePracticeHoverTotal]") == 6
        and localisation.count("§Y完整准则§!") == 6
        and localisation.count("[Root.zhx_doctrine_last_delta.GetValue]") == 1,
        "all six doctrine ledger descriptions must show current practice, the "
        "next-tier and Tianxia-proposal gaps, the current raw factor total and the "
        "complete rules without repeating last year's result",
    )
    for proposal_key in (
        "zhx_doctrine.95.d.gained",
        "zhx_doctrine.95.d.lost",
    ):
        proposal_line = re.search(
            rf'(?m)^\s*{re.escape(proposal_key)}:\d+\s+"(.*)"\s*$',
            localisation,
        )
        require(
            proposal_line is not None
            and "[Root.GetZhxDoctrineReceiptSchool]" in proposal_line.group(1)
            and "周天下" in proposal_line.group(1)
            and "礼教" in proposal_line.group(1),
            f"{proposal_key} must show the current school and retain both identity conditions",
        )

    receipt_custom_localisation = texts[
        MOD / "customizable_localization/zhx_doctrine_receipt.txt"
    ]
    receipt_school_text = defined_text_body(
        receipt_custom_localisation, "GetZhxDoctrineReceiptSchool"
    )
    receipt_old_tier_text = defined_text_body(
        receipt_custom_localisation, "GetZhxDoctrineReceiptOldTier"
    )
    receipt_new_tier_text = defined_text_body(
        receipt_custom_localisation, "GetZhxDoctrineReceiptNewTier"
    )
    hover_total_text = defined_text_body(
        receipt_custom_localisation, "GetZhxDoctrinePracticeHoverTotal"
    )
    hover_slot_names = (
        "GetZhxDoctrinePracticeHoverPositiveOne",
        "GetZhxDoctrinePracticeHoverPositiveTwo",
        "GetZhxDoctrinePracticeHoverPositiveThree",
        "GetZhxDoctrinePracticeHoverNegativeOne",
        "GetZhxDoctrinePracticeHoverNegativeTwo",
        "GetZhxDoctrinePracticeHoverNegativeThree",
    )
    hover_slot_texts = {
        name: defined_text_body(receipt_custom_localisation, name)
        for name in hover_slot_names
    }
    hover_empty_text = defined_text_body(
        receipt_custom_localisation, "GetZhxDoctrinePracticeHoverEmptyState"
    )
    require(
        receipt_custom_localisation.count("defined_text = {") == 11
        and receipt_school_text.count("random = no") == 1
        and all(
            receipt_school_text.count(f"has_country_flag = {flag}") == 1
            and receipt_school_text.count(
                f"localisation_key = zhx_doctrine_receipt_school_{school}"
            )
            == 1
            for school, flag in EXPECTED_FLAGS.items()
        )
        and receipt_school_text.count(
            "localisation_key = zhx_doctrine_receipt_school_unknown"
        )
        == 1,
        "tier receipt must resolve all six doctrine names through one deterministic defined_text",
    )
    require(
        hover_total_text.count("random = no") == 1
        and hover_total_text.count(
            "which = zhx_doctrine_ledger_estimated_delta"
        )
        == 2
        and all(
            hover_total_text.count(f"localisation_key = {key}") == 1
            for key in (
                "zhx_doctrine_practice_hover_total_positive",
                "zhx_doctrine_practice_hover_total_negative",
                "zhx_doctrine_practice_hover_total_zero",
            )
        ),
        "practice hover total must deterministically format positive, negative and zero sums",
    )
    combined_hover_slots = "\n".join(hover_slot_texts.values())
    require(
        all(body.count("random = no") == 1 for body in hover_slot_texts.values())
        and all(
            combined_hover_slots.count(f"localisation_key = {key}") == 1
            for key in HOVER_ROW_LOCALISATION
        )
        and all(
            body.count("localisation_key = zhx_doctrine_practice_hover_blank") == 1
            for body in hover_slot_texts.values()
        ),
        "six deterministic hover slots must list every possible positive row before "
        "every possible negative row, with one blank fallback per slot",
    )
    require(
        hover_empty_text.count("random = no") == 1
        and all(
            hover_empty_text.count(f"has_country_flag = {flag}") == 1
            for flag in HOVER_CACHE_FLAGS
        )
        and hover_empty_text.count(
            "localisation_key = zhx_doctrine_practice_hover_empty"
        )
        == 1
        and hover_empty_text.count(
            "localisation_key = zhx_doctrine_practice_hover_blank"
        )
        == 1,
        "hover empty state must appear only when no cached factor row is active",
    )
    for name, body, variable in (
        (
            "old",
            receipt_old_tier_text,
            "zhx_doctrine_receipt_old_tier",
        ),
        (
            "new",
            receipt_new_tier_text,
            "zhx_doctrine_receipt_new_tier",
        ),
    ):
        require(
            body.count("random = no") == 1
            and body.count(f"which = {variable}") == 3
            and all(body.count(f"value = {tier}") == 1 for tier in (1, 2, 3))
            and all(
                body.count(
                    f"localisation_key = zhx_doctrine_receipt_tier_{tier_name}"
                )
                == 1
                for tier_name in (
                    "hollow",
                    "established",
                    "flourishing",
                    "exemplary",
                )
            ),
            f"tier receipt {name}-tier text must map the four 25/50/75 bands exactly once",
        )

    native_localisation_keys = re.findall(
        r'(?m)^\s*([^\s:#]+):\d+\s+"', native_localisation
    )
    require(
        len(native_localisation_keys) == len(set(native_localisation_keys)),
        "duplicate keys in native-school readable localisation",
    )
    expected_native_localisation = set(ALL_NATIVE_SCHOOLS) | {
        f"{school}_desc" for school in ALL_NATIVE_SCHOOLS
    } | set(INVITED_MODIFIER_VALUES) | {
        f"{modifier}_desc" for modifier in INVITED_MODIFIER_VALUES
    } | NATIVE_STATUS_FIELDS | {
        "zhx_invite_school_country_tt",
        "zhx_religion_practice_value_tt",
        "zhx_doctrine_practice_hover_total_positive",
        "zhx_doctrine_practice_hover_total_negative",
        "zhx_doctrine_practice_hover_total_zero",
        "zhx_doctrine_practice_hover_blank",
        "zhx_doctrine_practice_hover_empty",
    } | HOVER_ROW_LOCALISATION
    require(
        set(native_localisation_keys) == expected_native_localisation,
        "native school localisation contract changed",
    )
    invite_tooltip = re.search(
        r'(?m)^\s*zhx_invite_school_country_tt:0\s+"(.*)"\s*$',
        native_localisation,
    )
    require(
        invite_tooltip is not None
        and "[From.GetName]" in invite_tooltip.group(1)
        and "二十年" in invite_tooltip.group(1)
        and "不改变本国主学派或践履" in invite_tooltip.group(1),
        "invitation tooltip must identify source, duration and doctrine boundary",
    )
    for field, colour in PRACTICE_TIER_COLOURS.items():
        require(
            re.search(
                rf'(?m)^\s*{re.escape(field)}:0\s+"§{colour}\[Root\.zhx_doctrine_practice\.GetValue\]§!"\s*$',
                native_localisation,
            )
            is not None,
            f"{field} must retain its tier colour §{colour}",
        )
    tooltip_line = re.search(
        r'(?m)^\s*zhx_religion_practice_value_tt:0\s+"(.*)"\s*$',
        native_localisation,
    )
    require(
        tooltip_line is not None
        and "按本月国情触发合计" in tooltip_line.group(1)
        and all(
            tooltip_line.group(1).count(f"[Root.{name}]") == 1
            for name in (
                "GetZhxDoctrinePracticeHoverTotal",
                *hover_slot_names,
                "GetZhxDoctrinePracticeHoverEmptyState",
            )
        )
        and tooltip_line.group(1).index(
            "GetZhxDoctrinePracticeHoverPositiveThree"
        )
        < tooltip_line.group(1).index("GetZhxDoctrinePracticeHoverNegativeOne")
        and "last_delta" not in tooltip_line.group(1)
        and "GetZhxDoctrinePracticeLedger" not in tooltip_line.group(1),
        "practice hover must show the monthly raw total, positive rows before "
        "negative rows, and the empty state without embedding the full rulebook",
    )
    require(
        tooltip_line is not None
        and tooltip_line.group(1).endswith(
            "\\n\\n§Y点击查看本派完整践履准则§!"
        ),
        "practice hover must advertise that the full 28x24 number slot is clickable",
    )
    for school, expected_rows in SCHOOL_TOOLTIP_ROWS.items():
        description_match = re.search(
            rf'(?m)^\s*{re.escape(school)}_desc:0\s+"(.*)"\s*$',
            native_localisation,
        )
        require(
            description_match is not None,
            f"missing native-school description for {school}",
        )
        description = description_match.group(1)
        separator = "\\n\\n§Y践履境界§!\\n"
        require(
            description.count(separator) == 1,
            f"{school} tooltip must separate its short history from the four tiers",
        )
        introduction, tier_text = description.split(separator)
        require(
            introduction.count("。") == 2 and 50 <= len(introduction) <= 90,
            f"{school} tooltip history must remain two concise real/worldline sentences",
        )
        require(
            tuple(tier_text.split("\\n")) == expected_rows,
            f"{school} tooltip must list the exact R/Y/G/O full-effect tier rows",
        )
    require(
        all(
            re.search(
                rf'(?m)^\s*{re.escape(key)}:0\s+"\\n[^"\n]*：§B[+-]\d+§!"\s*$',
                native_localisation,
            )
            is not None
            for key in HOVER_ROW_LOCALISATION
        ),
        "every possible active factor must occupy one line and colour its signed value blue",
    )
    require(
        re.search(
            r'(?m)^\s*zhx_doctrine_practice_hover_empty:0\s+"\\n§g当前没有影响践履的已触发因素。§!"\s*$',
            native_localisation,
        )
        is not None,
        "zero-trigger hover must display an explicit empty-state line",
    )

    print("Ritual Teaching doctrine prototype static contract: PASS")
    print(f"  Clausewitz files: {len(SCRIPT_PATHS) + 1}")
    print(f"  Events: {len(event_ids) + len(expansion_event_ids)}")
    print(f"  Doctrine modifiers: {len(modifier_definitions)}")
    print(f"  Mutually-exclusive tier practice displays: {len(NATIVE_STATUS_FIELDS)}")
    print("  Transparent practice-ledger hit targets: 1")
    print(f"  Tier-coloured hover-factor readouts: {len(NATIVE_STATUS_FIELDS)}")
    print(f"  Blue signed factor rows: {len(HOVER_ROW_LOCALISATION)}")
    print("  School-card tooltip hit targets: 12")
    print(f"  Native visible school mirrors: {len(NATIVE_SCHOOLS)}")
    print(f"  Native invited-school modifiers: {len(INVITED_MODIFIER_VALUES)}")
    print(f"  Invited-school emblem overlays: {len(INVITED_SCHOOL_OVERLAY_ICONS)}")
    print(f"  Native no-doctrine sentinels: {len(NO_DOCTRINE_SCHOOL)}")
    print(f"  Readable localisation keys: {len(localisation_keys)}")


if __name__ == "__main__":
    main()
