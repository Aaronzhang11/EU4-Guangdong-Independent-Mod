#!/usr/bin/env python3
"""Static safety contract for the maintained Great Debate developer preview."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
TRIGGERS = MOD / "common/scripted_triggers/zzz_zhx_debug_debate_triggers.txt"
EFFECTS = MOD / "common/scripted_effects/zzz_zhx_debug_debate_effects.txt"
EVENTS = MOD / "events/zzz_zhx_debug_debate_events.txt"
CATALOG_EVENTS = MOD / "events/zzz_zhx_debug_catalog_events.txt"
CATALOG_DECISIONS = MOD / "decisions/zzz_zhx_debug_catalog_decisions.txt"
LOCALISATION = MOD / "localisation_source/zhx_tianxia_debate_readable_utf8.txt"

DEBUG_FILES = {
    TRIGGERS.resolve(),
    EFFECTS.resolve(),
    EVENTS.resolve(),
    CATALOG_EVENTS.resolve(),
    CATALOG_DECISIONS.resolve(),
}
EVENT_IDS = ("zhx_debug.100", "zhx_debug.199")


def masked(text: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False
    in_comment = False
    for char in text:
        if in_comment:
            if char == "\n":
                in_comment = False
                out.append(char)
            else:
                out.append(" ")
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            out.append(" ")
            continue
        if char == "#":
            in_comment = True
            out.append(" ")
        elif char == '"':
            in_string = True
            out.append(" ")
        else:
            out.append(char)
    return "".join(out)


def balanced(text: str) -> bool:
    depth = 0
    for char in masked(text):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> None:
    errors: list[str] = []
    texts: dict[Path, str] = {}
    for path in (*DEBUG_FILES, LOCALISATION.resolve()):
        check(path.is_file(), f"missing required file: {path.relative_to(ROOT)}", errors)
        if path.is_file():
            texts[path] = path.read_text(encoding="utf-8-sig")

    if errors:
        finish(errors)

    trigger_text = texts[TRIGGERS.resolve()]
    effect_text = texts[EFFECTS.resolve()]
    event_text = texts[EVENTS.resolve()]
    localisation_text = texts[LOCALISATION.resolve()]

    for path in DEBUG_FILES:
        check(balanced(texts[path]), f"unbalanced Clausewitz braces: {path.relative_to(ROOT)}", errors)

    check("namespace = zhx_debug" in event_text, "missing zhx_debug namespace", errors)
    for event_id in EVENT_IDS:
        check(
            len(re.findall(rf"\bid\s*=\s*{re.escape(event_id)}\b", masked(event_text))) == 1,
            f"expected exactly one event {event_id}",
            errors,
        )
    check(
        masked(event_text).count("is_triggered_only = yes") == 2,
        "both debug events must be triggered-only",
        errors,
    )
    check("mean_time_to_happen" not in masked(event_text), "debug events must never pulse automatically", errors)
    check("name = zhx_debug.100.cancel" in masked(event_text), "preview event lacks a unique cancel key", errors)

    prepare = "zhx_debug_can_prepare_debate_preview"
    cleanup = "zhx_debug_can_cleanup_debate_preview"
    for token in (
        "zhx_is_tianzi = yes",
        "has_global_flag = zhx_council_initialised_v1",
        "has_saved_global_event_target = zhx_tianzi",
        "NOT = { zhx_tianxia_council_is_busy = yes }",
        "NOT = { has_country_flag = zhx_council_pending_ritual_breakdown }",
        "NOT = { has_country_flag = zhx_council_deadline_scheduled }",
        "NOT = { has_country_flag = zhx_council_result_ready }",
    ):
        check(token in trigger_text, f"preview guard is missing: {token}", errors)
    check("has_country_flag = zhx_debug_debate_preview_active" in trigger_text, "cleanup guard lacks preview marker", errors)

    for effect_name in (
        "zhx_debug_start_two_school_debate_preview",
        "zhx_debug_start_three_school_debate_preview",
    ):
        check(effect_name in effect_text, f"missing start effect {effect_name}", errors)
    check(effect_text.count(f"{prepare} = yes") >= 2, "both start effects must use the idle-council guard", errors)
    check(f"{cleanup} = yes" in effect_text, "cleanup effect must use its guarded trigger", errors)
    check(effect_text.count("country_event = { id = zhx_debate.2 }") == 2, "both previews must enter through the production convene event", errors)

    for modifier in ("mo", "dao", "ru", "bing", "zongheng"):
        pattern = rf"name\s*=\s*zhx_debate_petition_{modifier}\s+duration\s*=\s*1095"
        check(re.search(pattern, masked(effect_text)) is not None, f"missing 1095-day debug petition: {modifier}", errors)

    for token in (
        "zhx_clear_tianxia_debate_petitions = yes",
        "remove_country_modifier = zhx_tianxia_orthodoxy_term",
        "zhx_clear_tianxia_orthodoxy_flags = yes",
        "zhx_reset_tianxia_council_ballot = yes",
        "zhx_clear_tianxia_council_phase = yes",
        "zhx_clear_tianxia_council_kind = yes",
        "zhx_clear_tianxia_council_candidates = yes",
        "zhx_clear_tianxia_council_results = yes",
        "clr_country_flag = zhx_council_result_ready",
        "clr_country_flag = zhx_council_deadline_scheduled",
        "clr_country_flag = zhx_debug_debate_preview_active",
    ):
        check(token in effect_text, f"debug cleanup is missing: {token}", errors)

    for forbidden in ("zhx_system.23", "zhx_debate.20", "zhx_finish_tianxia_council = yes"):
        check(forbidden not in masked(effect_text), f"unsafe fast-finish path in debug effects: {forbidden}", errors)
    check(
        "clr_country_flag = zhx_council_pending_ritual_breakdown" not in masked(effect_text),
        "debug cleanup must not swallow a queued ritual-breakdown incident",
        errors,
    )

    for event_id in EVENT_IDS:
        for suffix in ("t", "d"):
            key = f"{event_id}.{suffix}:0"
            check(key in localisation_text, f"missing readable localisation key {key}", errors)
    check("zhx_debug.100.cancel:0" in localisation_text, "missing preview cancel localisation", errors)

    localisation_keys = re.findall(r"^\s*([A-Za-z0-9_.-]+):\d+\s", localisation_text, flags=re.MULTILINE)
    for key in sorted(set(localisation_keys)):
        check(localisation_keys.count(key) == 1, f"duplicate readable localisation key: {key}", errors)

    # Only the explicit developer harness and save-gated catalog may reference
    # this namespace. Localisation and documentation are deliberately outside
    # this scan.
    for root in (MOD / "common", MOD / "events", MOD / "decisions"):
        for path in root.rglob("*.txt"):
            if path.resolve() in DEBUG_FILES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            check("zhx_debug" not in masked(text), f"production path references debug harness: {path.relative_to(ROOT)}", errors)

    finish(errors)


def finish(errors: list[str]) -> None:
    if errors:
        print(f"Great Debate debug preview contract: FAIL ({len(errors)})")
        for index, error in enumerate(errors, 1):
            print(f"  {index:02d}. {error}")
        raise SystemExit(1)
    print("Great Debate debug preview contract: PASS")
    print("  Developer entry: event zhx_debug.100 CZH or save-gated debug catalog")
    print("  Two-school direct ballot and three-school Tianzi selector")
    print("  Cleanup requires an idle council; no forced deadline or result path")


if __name__ == "__main__":
    main()
