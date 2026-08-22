#!/usr/bin/env python3
"""Static contract checks for the international Hundred Schools debate."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

TRIGGERS = MOD / "common/scripted_triggers/zhx_tianxia_debate_triggers.txt"
EFFECTS = MOD / "common/scripted_effects/zhx_tianxia_debate_effects.txt"
EVENTS = MOD / "events/zhx_tianxia_debate_events.txt"
DECISIONS = MOD / "decisions/zhx_tianxia_debate_decisions.txt"
MODIFIERS = MOD / "common/event_modifiers/zhx_tianxia_debate_modifiers.txt"
ON_ACTIONS = MOD / "common/on_actions/zhx_system_on_actions.txt"
SYSTEM_EFFECTS = MOD / "common/scripted_effects/zhx_system_effects.txt"
LOCALISATION = MOD / "localisation_source/zhx_tianxia_debate_readable_utf8.txt"
SYSTEM_LOCALISATION = MOD / "localisation_source/zhx_system_readable_utf8.txt"
INTERFACE = MOD / "interface/countrydecisionsview.gui"
CUSTOM_GUI = MOD / "common/custom_gui/zhx_tianxia_gui.txt"

CLAUSEWITZ_FILES = (
    TRIGGERS,
    EFFECTS,
    EVENTS,
    DECISIONS,
    MODIFIERS,
    ON_ACTIONS,
    SYSTEM_EFFECTS,
    INTERFACE,
    CUSTOM_GUI,
)
EXPECTED_EVENT_IDS = {"1", "2", "10", "11", "12", "20", "30", "90"}
ORTHODOXY_FLAGS = {
    "ru": "zhx_tianxia_orthodoxy_ru",
    "fa": "zhx_tianxia_orthodoxy_fa",
    "mo": "zhx_tianxia_orthodoxy_mo",
    "plural": "zhx_tianxia_orthodoxy_plural",
}
EXPECTED_LOCALISATION = {
    "zhx_debate.1.t",
    "zhx_debate.1.d",
    "zhx_debate.2.t",
    "zhx_debate.2.d",
    "zhx_debate.2.a",
    "zhx_debate.2.b",
    "zhx_debate.2.c",
    "zhx_debate.10.t",
    "zhx_debate.10.d",
    "zhx_debate.11.t",
    "zhx_debate.11.d",
    "zhx_debate.12.t",
    "zhx_debate.12.d",
    "zhx_debate.vote_ru",
    "zhx_debate.vote_fa",
    "zhx_debate.vote_mo",
    "zhx_debate.vote_plural",
    "zhx_debate.20.t",
    "zhx_debate.20.d.ru",
    "zhx_debate.20.d.fa",
    "zhx_debate.20.d.mo",
    "zhx_debate.20.d.plural",
    "zhx_debate.20.a",
    "zhx_debate_result_tt",
    "zhx_debate.30.t",
    "zhx_debate.30.d.ru",
    "zhx_debate.30.d.fa",
    "zhx_debate.30.d.mo",
    "zhx_debate.30.d.plural",
    "zhx_debate.30.d.none",
    "zhx_debate.30.a",
    "zhx_debate.90.t",
    "zhx_debate.90.d",
    "zhx_review_tianxia_orthodoxy_title",
    "zhx_review_tianxia_orthodoxy_desc",
    "zhx_debug_convene_tianxia_debate_title",
    "zhx_debug_convene_tianxia_debate_desc",
    "zhx_tianxia_debate_cooldown",
    "zhx_tianxia_debate_cooldown_desc",
    "ZHX_GUI_DEBATE_HEADER",
    "ZHX_GUI_DEBATE_REVIEW_BUTTON",
    "ZHX_GUI_DEBATE_CONVENE_BUTTON",
    "ZHX_GUI_DEBATE_VOTE_RU_BUTTON",
    "ZHX_GUI_DEBATE_VOTE_FA_BUTTON",
    "ZHX_GUI_DEBATE_VOTE_MO_BUTTON",
    "ZHX_GUI_DEBATE_VOTE_PLURAL_BUTTON",
    "zhx_gui_debate_orthodoxy_none",
    "zhx_gui_debate_orthodoxy_ru",
    "zhx_gui_debate_orthodoxy_fa",
    "zhx_gui_debate_orthodoxy_mo",
    "zhx_gui_debate_orthodoxy_plural",
    "zhx_gui_debate_status_active_ru_fa",
    "zhx_gui_debate_status_active_ru_mo",
    "zhx_gui_debate_status_active_fa_mo",
    "zhx_gui_debate_status_settled",
    "zhx_gui_debate_status_ready",
    "zhx_gui_debate_status_waiting",
    "zhx_gui_debate_live_counts_ru_fa",
    "zhx_gui_debate_live_counts_ru_mo",
    "zhx_gui_debate_live_counts_fa_mo",
    "zhx_gui_debate_description_idle",
    "zhx_gui_debate_vote_none",
    "zhx_gui_debate_vote_ru",
    "zhx_gui_debate_vote_fa",
    "zhx_gui_debate_vote_mo",
    "zhx_gui_debate_vote_plural",
    "zhx_gui_debate_vote_observer",
    "zhx_gui_debate_tt",
    "zhx_gui_debate_live_counts_tt",
    "zhx_gui_debate_vote_status_tt",
    "zhx_gui_debate_review_button_tt",
    "zhx_gui_debate_convene_button_tt",
    "zhx_gui_debate_vote_ru_button_tt",
    "zhx_gui_debate_vote_fa_button_tt",
    "zhx_gui_debate_vote_mo_button_tt",
    "zhx_gui_debate_vote_plural_button_tt",
}
GUI_BINDINGS = {
    "zhx_gui_debate_orthodoxy_none",
    "zhx_gui_debate_orthodoxy_ru",
    "zhx_gui_debate_orthodoxy_fa",
    "zhx_gui_debate_orthodoxy_mo",
    "zhx_gui_debate_orthodoxy_plural",
    "zhx_gui_debate_status_active_ru_fa",
    "zhx_gui_debate_status_active_ru_mo",
    "zhx_gui_debate_status_active_fa_mo",
    "zhx_gui_debate_status_settled",
    "zhx_gui_debate_status_ready",
    "zhx_gui_debate_status_waiting",
    "zhx_gui_debate_live_counts_ru_fa",
    "zhx_gui_debate_live_counts_ru_mo",
    "zhx_gui_debate_live_counts_fa_mo",
    "zhx_gui_debate_description_idle",
    "zhx_gui_debate_vote_none",
    "zhx_gui_debate_vote_ru",
    "zhx_gui_debate_vote_fa",
    "zhx_gui_debate_vote_mo",
    "zhx_gui_debate_vote_plural",
    "zhx_gui_debate_vote_observer",
    "zhx_gui_debate_review_button_solo",
    "zhx_gui_debate_review_button_split",
    "zhx_gui_debate_convene_button",
    "zhx_gui_debate_vote_ru_a_button",
    "zhx_gui_debate_vote_fa_a_button",
    "zhx_gui_debate_vote_fa_b_button",
    "zhx_gui_debate_vote_mo_b_button",
    "zhx_gui_debate_vote_plural_button",
}
RETIRED_COUNCIL_GUI_TOKENS = {
    "zhx_gui_reform_enacted",
    "zhx_gui_reform_available",
    "zhx_gui_reform_tt",
    "ZHX_GUI_REFORM_HEADER",
    "ZHX_GUI_REFORM_DESCRIPTION",
    "zhx_gui_overview_button",
    "ZHX_GUI_OVERVIEW_BUTTON",
}
FORBIDDEN = {
    "change_religion": "the international norm must not replace country religion",
    "change_province_religion": "the debate must not convert provinces",
    "set_country_flag = zhx_doctrine_ru": "international state must not set domestic doctrine",
    "set_country_flag = zhx_doctrine_fa": "international state must not set domestic doctrine",
    "set_country_flag = zhx_doctrine_mo": "international state must not set domestic doctrine",
    "on_monthly_pulse": "the debate scheduler must remain annual",
    "on_daily_pulse": "the debate scheduler must remain annual",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8-sig")


def validate_braces(path: Path, text: str) -> None:
    depth = 0
    in_string = False
    in_comment = False
    escaped = False
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


def top_level_body(text: str, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    require(match is not None, f"missing top-level block {name}")
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
    raise ValueError(f"block {name} has no closing brace")


def main() -> None:
    texts = {path: read(path) for path in CLAUSEWITZ_FILES}
    localisation = read(LOCALISATION)
    system_localisation = read(SYSTEM_LOCALISATION)
    for path, text in texts.items():
        validate_braces(path, text)

    event_text = texts[EVENTS]
    event_ids = re.findall(r"(?m)^\s*id\s*=\s*zhx_debate\.(\d+)\s*$", event_text)
    require(len(event_ids) == len(set(event_ids)), "duplicate zhx_debate event ID")
    require(set(event_ids) == EXPECTED_EVENT_IDS, f"event contract changed: {event_ids}")

    on_actions = texts[ON_ACTIONS]
    require(on_actions.count("zhx_debate.1") == 1, "startup initializer must occur once")
    require(on_actions.count("zhx_debate.90") == 1, "annual scheduler must occur once")
    require("on_yearly_pulse" in on_actions, "missing annual pulse")

    trigger_text = texts[TRIGGERS]
    require(
        trigger_text.count("which = zhx_doctrine_practice") == 3
        and trigger_text.count("value = 70") == 3,
        "each of Ru, Fa and Mo must require one 70-practice exemplar",
    )
    require(
        "zhx_can_convene_tianxia_debate" in trigger_text,
        "missing shared Tianxia debate convening trigger",
    )
    require(
        "zhx_can_vote_in_tianxia_debate" in trigger_text,
        "missing shared active-ballot voter trigger",
    )

    effects = texts[EFFECTS]
    for school, flag in ORTHODOXY_FLAGS.items():
        setters = re.findall(rf"set_country_flag\s*=\s*{re.escape(flag)}\b", effects)
        require(len(setters) == 1, f"{flag} must be set exactly once")
        body = top_level_body(effects, f"zhx_set_tianxia_orthodoxy_{school}")
        require(flag in body, f"{flag} must be owned by its shared setter")

    require(effects.count("days = 365") == 3, "each candidate pair must schedule one-year resolution")
    require(
        effects.count("duration = 5475") == 1,
        "a resolved debate must establish one fifteen-year settlement",
    )
    require(
        "value = 75" in effects,
        "75-practice exemplar weighting must remain explicit",
    )
    require(
        "zhx_tianxia_debate_a_vs_b" in effects
        and "zhx_tianxia_debate_b_vs_a" in effects,
        "strict pairwise winner comparisons are required",
    )
    for ballot in ("a", "b", "plural"):
        cast_body = top_level_body(effects, f"zhx_cast_tianxia_debate_vote_{ballot}")
        require(
            "zhx_can_vote_in_tianxia_debate" in cast_body,
            f"{ballot} ballot must reject inactive or non-member voters",
        )
        require(
            "zhx_recount_tianxia_debate_ballot" in cast_body,
            f"{ballot} ballot must refresh live totals",
        )
    recount_body = top_level_body(effects, "zhx_recount_tianxia_debate_ballot")
    require(
        recount_body.count("event_target:zhx_tianzi") >= 6,
        "live recount must store totals and comparisons on the Tianzi anchor",
    )

    combined_new = "\n".join(
        texts[path] for path in (TRIGGERS, EFFECTS, EVENTS, DECISIONS, MODIFIERS)
    )
    for token, reason in FORBIDDEN.items():
        require(token not in combined_new, f"forbidden token {token}: {reason}")

    modifier_definitions = re.findall(
        r"(?m)^(zhx_tianxia_debate_[a-z0-9_]+)\s*=\s*\{",
        texts[MODIFIERS],
    )
    require(
        modifier_definitions == ["zhx_tianxia_debate_cooldown"],
        f"unexpected debate modifiers: {modifier_definitions}",
    )

    system_effects = texts[SYSTEM_EFFECTS]
    reward_body = top_level_body(system_effects, "zhx_reward_external_war_victory")
    for flag in ORTHODOXY_FLAGS.values():
        require(flag in reward_body, f"external-war rules do not read {flag}")
    annual_body = top_level_body(system_effects, "zhx_yearly_ritual_authority_tick")
    for flag in (
        ORTHODOXY_FLAGS["ru"],
        ORTHODOXY_FLAGS["fa"],
        ORTHODOXY_FLAGS["mo"],
    ):
        require(flag in annual_body, f"annual Tianxia rules do not read {flag}")

    keys = re.findall(r"(?m)^\s*([^\s:#]+):\d+\s+\"", localisation)
    require(len(keys) == len(set(keys)), "duplicate debate localisation keys")
    missing = EXPECTED_LOCALISATION - set(keys)
    require(not missing, f"missing debate localisation: {sorted(missing)}")

    interface_text = texts[INTERFACE]
    custom_gui_text = texts[CUSTOM_GUI]
    for name in GUI_BINDINGS:
        interface_matches = re.findall(
            rf'(?m)^\s*name\s*=\s*"{re.escape(name)}"\s*$',
            interface_text,
        )
        custom_matches = re.findall(
            rf"(?m)^\s*name\s*=\s*{re.escape(name)}\s*$",
            custom_gui_text,
        )
        require(len(interface_matches) == 1, f"interface binding count for {name} is not one")
        require(len(custom_matches) == 1, f"custom GUI binding count for {name} is not one")
        start = interface_text.find(f'name = "{name}"')
        require(
            "scripted = yes" in interface_text[start:start + 550],
            f"interface control {name} is not scripted",
        )

    require(
        custom_gui_text.count("country_event = { id = zhx_debate.30 }") == 2,
        "both read-only debate buttons must invoke zhx_debate.30",
    )
    require(
        custom_gui_text.count("country_event = { id = zhx_debate.2 }") == 1,
        "the convene button must invoke zhx_debate.2 exactly once",
    )
    require(
        custom_gui_text.count("effect = { zhx_cast_tianxia_debate_vote_a = yes }") == 2,
        "exactly two pair-specific GUI buttons must cast candidate A",
    )
    require(
        custom_gui_text.count("effect = { zhx_cast_tianxia_debate_vote_b = yes }") == 2,
        "exactly two pair-specific GUI buttons must cast candidate B",
    )
    require(
        custom_gui_text.count("effect = { zhx_cast_tianxia_debate_vote_plural = yes }") == 1,
        "exactly one GUI button must cast plurality",
    )
    require(
        "zhx_can_convene_tianxia_debate = yes" in event_text,
        "the debate invitation event must share the GUI convening trigger",
    )
    retired_haystack = "\n".join((interface_text, custom_gui_text, system_localisation))
    for token in RETIRED_COUNCIL_GUI_TOKENS:
        require(token not in retired_haystack, f"retired council reform GUI token remains: {token}")

    print("Tianxia Great Debate static contract: PASS")
    print(f"  Clausewitz files: {len(CLAUSEWITZ_FILES)}")
    print(f"  Events: {len(event_ids)}")
    print("  Candidate threshold: 70; exemplar threshold: 75")
    print("  Debate duration: 365 days; settlement: 5475 days")
    print(f"  Council GUI bindings: {len(GUI_BINDINGS)}")
    print(f"  Readable localisation keys: {len(keys)}")


if __name__ == "__main__":
    main()
