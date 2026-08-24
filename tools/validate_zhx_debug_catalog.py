#!/usr/bin/env python3
"""Static contract for the save-gated, paginated developer event catalog."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
EVENTS = MOD / "events/zzz_zhx_debug_catalog_events.txt"
DECISIONS = MOD / "decisions/zzz_zhx_debug_catalog_decisions.txt"
TRIGGERS = MOD / "common/scripted_triggers/zzz_zhx_debug_debate_triggers.txt"
LOCALISATION = MOD / "localisation_source/zhx_tianxia_debate_readable_utf8.txt"


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


def event_blocks(text: str) -> dict[str, str]:
    clean = masked(text)
    blocks: dict[str, str] = {}
    for match in re.finditer(r"\bcountry_event\s*=\s*\{", clean):
        # Only definitions live at file depth zero. Nested country_event blocks
        # are dispatch effects and must not overwrite a page definition.
        prefix = clean[:match.start()]
        if prefix.count("{") != prefix.count("}"):
            continue
        opening = clean.find("{", match.start())
        depth = 0
        end = -1
        for index in range(opening, len(clean)):
            if clean[index] == "{":
                depth += 1
            elif clean[index] == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end < 0:
            continue
        clean_block = clean[match.start():end]
        id_match = re.search(r"\bid\s*=\s*(zhx_debug\.\d+)\b", clean_block)
        if id_match:
            blocks[id_match.group(1)] = text[match.start():end]
    return blocks


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> None:
    errors: list[str] = []
    required = (EVENTS, DECISIONS, TRIGGERS, LOCALISATION)
    texts: dict[Path, str] = {}
    for path in required:
        check(path.is_file(), f"missing required file: {path.relative_to(ROOT)}", errors)
        if path.is_file():
            texts[path] = path.read_text(encoding="utf-8-sig")
    if errors:
        finish(errors)

    event_text = texts[EVENTS]
    decision_text = texts[DECISIONS]
    trigger_text = texts[TRIGGERS]
    localisation_text = texts[LOCALISATION]

    for path in (EVENTS, DECISIONS, TRIGGERS):
        check(balanced(texts[path]), f"unbalanced Clausewitz braces: {path.relative_to(ROOT)}", errors)

    combined = masked(event_text + "\n" + decision_text + "\n" + trigger_text)
    check(re.search(r"\bis_debug\s*=", combined) is None, "EU4 has no is_debug trigger", errors)
    check(re.search(r"\bdebug_mode\s*=", combined) is None, "EU4 has no debug_mode trigger", errors)

    clean_decisions = masked(decision_text)
    for token in (
        "zhx_open_debug_catalog",
        "ai = no",
        "has_country_flag = zhx_debug_catalog_enabled",
        "country_event = { id = zhx_debug.10 }",
        "ai_will_do = { factor = 0 }",
    ):
        check(token in clean_decisions, f"debug decision contract is missing: {token}", errors)

    blocks = event_blocks(event_text)
    for event_id in ("zhx_debug.1", "zhx_debug.10", "zhx_debug.20"):
        check(event_id in blocks, f"missing catalog event {event_id}", errors)
    check(len(blocks) == 3, "catalog file must define exactly three top-level events", errors)
    if all(event_id in blocks for event_id in ("zhx_debug.1", "zhx_debug.10", "zhx_debug.20")):
        activator = masked(blocks["zhx_debug.1"])
        page_one = masked(blocks["zhx_debug.10"])
        page_two = masked(blocks["zhx_debug.20"])
        check("is_triggered_only = yes" in activator, "catalog activator must be triggered-only", errors)
        check("set_country_flag = zhx_debug_catalog_enabled" in activator, "activator must set the save-local gate", errors)
        check("country_event = { id = zhx_debug.10 }" in activator, "activator must open page one", errors)
        for event_id, page in (("zhx_debug.10", page_one), ("zhx_debug.20", page_two)):
            check("is_triggered_only = yes" in page, f"{event_id} must be triggered-only", errors)
            check("has_country_flag = zhx_debug_catalog_enabled" in page, f"{event_id} lacks catalog gate", errors)
            check(len(re.findall(r"\boption\s*=", page)) == 6, f"{event_id} must have exactly six options", errors)
        check("name = zhx_debug.catalog.debate" in page_one, "page one lacks 调试天下大辩", errors)
        check("country_event = { id = zhx_debug.100 }" in page_one, "debate item must call zhx_debug.100", errors)
        check("country_event = { id = zhx_debug.20 }" in page_one, "page one lacks next-page route", errors)
        check("country_event = { id = zhx_debug.10 }" in page_two, "page two lacks previous-page route", errors)
        check("clr_country_flag = zhx_debug_catalog_enabled" in page_two, "page two lacks disable route", errors)

    for token in (
        "zhx_debug_can_prepare_ritual_breakdown_preview",
        "NOT = { zhx_tianxia_council_is_busy = yes }",
        "NOT = { has_country_flag = zhx_council_pending_ritual_breakdown }",
        "NOT = { has_country_flag = zhx_council_deadline_scheduled }",
        "NOT = { has_country_flag = zhx_council_result_ready }",
        "NOT = { has_country_modifier = zhx_ritual_breakdown_incident_cooldown }",
    ):
        check(token in masked(trigger_text), f"ritual-breakdown debug guard is missing: {token}", errors)

    for forbidden in (
        "country_event = { id = zhx_system.23",
        "country_event = { id = zhx_debate.2 }",
        "country_event = { id = zhx_debate.3 }",
        "country_event = { id = zhx_debate.4 }",
        "country_event = { id = zhx_debate.10 }",
        "country_event = { id = zhx_debate.20 }",
    ):
        check(forbidden not in masked(event_text), f"unsafe internal event exposed by catalog: {forbidden}", errors)

    for key in (
        "zhx_open_debug_catalog_title",
        "zhx_open_debug_catalog_desc",
        "zhx_debug.1.t",
        "zhx_debug.1.d",
        "zhx_debug.10.t",
        "zhx_debug.10.d",
        "zhx_debug.20.t",
        "zhx_debug.20.d",
        "zhx_debug.catalog.debate",
        "zhx_debug.catalog.next_page",
        "zhx_debug.catalog.previous_page",
        "zhx_debug.catalog.disable",
    ):
        check(re.search(rf"^\s*{re.escape(key)}:0\s", localisation_text, flags=re.MULTILINE) is not None,
              f"missing readable localisation key: {key}", errors)

    # The activator must stay console-only. Prefix-safe matching avoids treating
    # zhx_debug.10/100/199 as references to zhx_debug.1.
    activator_ref = re.compile(r"\bzhx_debug\.1(?!\d)")
    for root in (MOD / "common", MOD / "events", MOD / "decisions"):
        for path in root.rglob("*.txt"):
            if path.resolve() == EVENTS.resolve():
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            check(activator_ref.search(masked(text)) is None,
                  f"production script references console activator: {path.relative_to(ROOT)}", errors)

    finish(errors)


def finish(errors: list[str]) -> None:
    if errors:
        print(f"Debug event catalog contract: FAIL ({len(errors)})")
        for index, error in enumerate(errors, 1):
            print(f"  {index:02d}. {error}")
        raise SystemExit(1)
    print("Debug event catalog contract: PASS")
    print("  Console opt-in: event zhx_debug.1")
    print("  Save-gated decision: 调试")
    print("  Two pages, six options each, bidirectional navigation")
    print("  Great Debate item dispatches to zhx_debug.100")


if __name__ == "__main__":
    main()
