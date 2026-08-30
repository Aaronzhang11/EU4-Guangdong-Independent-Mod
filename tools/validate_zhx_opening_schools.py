#!/usr/bin/env python3
"""Validate the authoritative 1444 Ritual Teaching school projection."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
MANIFEST = (
    ROOT
    / "planning/religion_opening_schools/opening_schools_manifest.json"
)
EVENTS = MOD / "events/zhx_opening_school_events.txt"
ON_ACTIONS = MOD / "common/on_actions/zhx_system_on_actions.txt"
COUNTRY_HISTORY = MOD / "history/countries"

SCHOOL_ORDER = ("ru", "fa", "mo", "dao", "bing", "zongheng")
SCHOOL_COUNTS = {
    "ru": 14,
    "fa": 6,
    "mo": 12,
    "dao": 9,
    "bing": 11,
    "zongheng": 13,
}
SCHOOL_BINDINGS = {
    "ru": ("zhx_doctrine_ru", "zhx_ru_school"),
    "fa": ("zhx_doctrine_fa", "zhx_fa_school"),
    "mo": ("zhx_doctrine_mo", "zhx_mo_school"),
    "dao": ("zhx_doctrine_dao", "zhx_dao_school"),
    "bing": ("zhx_doctrine_bing", "zhx_bing_school"),
    "zongheng": ("zhx_doctrine_zongheng", "zhx_zongheng_school"),
}
FORBIDDEN_TAGS = {"LIO", "KOR", "DAI", "GZH", "LIL", "NUN", "TZZ", "WLM"}
EVENT_ID = "zhx_opening_school.1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def matching_close(text: str, opening: int) -> int:
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
            require(depth >= 0, "closing brace without opener")
            if depth == 0:
                return index
    raise ValueError("block has no matching closing brace")


def block_body(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    require(match is not None, f"missing block {key}")
    opening = text.find("{", match.start())
    closing = matching_close(text, opening)
    return text[opening + 1 : closing]


def named_blocks(text: str, key_pattern: str) -> list[tuple[str, str]]:
    pattern = re.compile(rf"(?m)^\s*({key_pattern})\s*=\s*\{{")
    blocks: list[tuple[str, str]] = []
    cursor = 0
    while match := pattern.search(text, cursor):
        opening = text.find("{", match.start())
        closing = matching_close(text, opening)
        blocks.append((match.group(1), text[opening + 1 : closing]))
        cursor = closing + 1
    return blocks


def initial_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^#\n]+)", text)
    require(match is not None, f"missing {key}")
    return match.group(1).strip()


def tags_in(text: str) -> list[str]:
    return re.findall(r"(?m)^\s*tag\s*=\s*([A-Z0-9]{3})\s*$", text)


def strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def load_manifest() -> tuple[dict[str, dict[str, object]], list[str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest.get("schema_version") == 1, "unsupported manifest schema")
    require(manifest.get("campaign_start") == "1444.11.11", "campaign start drifted")
    require(
        manifest.get("eligible_religion") == "confucianism",
        "opening school eligibility must remain confucianism",
    )
    require(manifest.get("initial_practice") == 25, "initial practice must be 25")
    require(manifest.get("expected_total") == 65, "manifest total must be 65")

    schools = manifest.get("schools")
    require(isinstance(schools, dict), "manifest schools must be an object")
    require(tuple(schools) == SCHOOL_ORDER, "manifest school order or keys drifted")

    all_tags: list[str] = []
    for school in SCHOOL_ORDER:
        config = schools[school]
        require(isinstance(config, dict), f"{school} manifest entry must be an object")
        expected_flag, expected_native = SCHOOL_BINDINGS[school]
        require(config.get("flag") == expected_flag, f"{school} flag binding drifted")
        require(
            config.get("native_school") == expected_native,
            f"{school} native-school binding drifted",
        )
        require(
            config.get("expected_count") == SCHOOL_COUNTS[school],
            f"{school} expected count must be {SCHOOL_COUNTS[school]}",
        )
        tags = config.get("tags")
        require(isinstance(tags, list), f"{school} tags must be a list")
        require(
            len(tags) == SCHOOL_COUNTS[school],
            f"{school} has {len(tags)} tags, expected {SCHOOL_COUNTS[school]}",
        )
        require(
            all(isinstance(tag, str) and re.fullmatch(r"[A-Z0-9]{3}", tag) for tag in tags),
            f"{school} contains an invalid country tag",
        )
        require(len(tags) == len(set(tags)), f"{school} contains duplicate tags")
        all_tags.extend(tags)

    require(len(all_tags) == 65, f"manifest has {len(all_tags)} tags, expected 65")
    require(len(set(all_tags)) == 65, "a tag is assigned to more than one school")
    forbidden = FORBIDDEN_TAGS.intersection(all_tags)
    require(not forbidden, f"non-Lijiao tags entered the opening mapping: {sorted(forbidden)}")
    return schools, all_tags


def validate_event_projection(
    schools: dict[str, dict[str, object]], all_tags: list[str]
) -> None:
    text = EVENTS.read_text(encoding="utf-8")
    require(
        re.search(r"(?m)^namespace\s*=\s*zhx_opening_school\s*$", text) is not None,
        "opening event namespace drifted",
    )
    event = block_body(text, "country_event")
    require(initial_value(event, "id") == EVENT_ID, f"event must be {EVENT_ID}")
    require(event.count("hidden = yes") == 1, "opening event must be hidden")
    require(
        event.count("is_triggered_only = yes") == 1,
        "opening event must be triggered-only",
    )

    trigger = block_body(event, "trigger")
    require(initial_value(trigger, "tag") == "CZH", "CZH must carry initialization")
    require(
        trigger.count("has_global_flag = zhx_opening_schools_initialised") == 1,
        "opening event must be globally one-shot",
    )

    immediate = block_body(event, "immediate")
    every_country = block_body(immediate, "every_country")
    country_limit = block_body(every_country, "limit")
    require(
        "religion = confucianism" in country_limit,
        "opening assignment must be gated to Ritual Teaching countries",
    )
    require(
        "NOT = { has_country_flag = zhx_opening_school_initialised }" in country_limit,
        "each country must carry an idempotent opening marker",
    )
    whitelist = tags_in(country_limit)
    require(len(whitelist) == 65, "event whitelist must contain 65 tags exactly once")
    require(len(set(whitelist)) == 65, "event whitelist contains duplicate tags")
    require(
        set(whitelist) == set(all_tags),
        "event whitelist differs from the authoritative manifest",
    )
    require(
        not FORBIDDEN_TAGS.intersection(whitelist),
        "a representative non-Lijiao tag entered the event whitelist",
    )

    actual_mapping: dict[str, set[str]] = {}
    branch_order: list[str] = []
    doctrine_flags = {binding[0]: school for school, binding in SCHOOL_BINDINGS.items()}
    for _kind, branch in named_blocks(every_country, r"(?:if|else_if)"):
        assigned = re.findall(
            r"(?m)^\s*set_country_flag\s*=\s*(zhx_doctrine_(?:ru|fa|mo|dao|bing|zongheng))\s*$",
            branch,
        )
        if not assigned:
            continue
        require(len(assigned) == 1, "one mapping branch assigns multiple doctrine flags")
        school = doctrine_flags[assigned[0]]
        require(school not in actual_mapping, f"event assigns {school} in multiple branches")
        branch_tags = tags_in(block_body(branch, "limit"))
        require(len(branch_tags) == len(set(branch_tags)), f"{school} branch duplicates a tag")
        actual_mapping[school] = set(branch_tags)
        branch_order.append(school)

    require(tuple(branch_order) == SCHOOL_ORDER, "event school branch order drifted")
    require(set(actual_mapping) == set(SCHOOL_ORDER), "event does not assign all six schools")
    for school in SCHOOL_ORDER:
        expected = set(schools[school]["tags"])
        require(
            actual_mapping[school] == expected,
            f"event {school} mapping differs from the manifest",
        )
        flag = SCHOOL_BINDINGS[school][0]
        require(
            text.count(f"set_country_flag = {flag}") == 1,
            f"{flag} must be assigned exactly once in the opening event",
        )

    variable_assignments: dict[str, str] = {}
    for _key, body in named_blocks(every_country, r"set_variable"):
        which = initial_value(body, "which")
        require(which not in variable_assignments, f"opening event assigns {which} twice")
        variable_assignments[which] = initial_value(body, "value")
    require(
        variable_assignments
        == {"zhx_doctrine_practice": "25", "zhx_doctrine_last_delta": "0"},
        f"opening variables drifted: {variable_assignments}",
    )
    require(
        every_country.count("set_country_flag = zhx_doctrine_practice_initialised") == 1,
        "opening event must initialize doctrine practice exactly once",
    )
    require(
        every_country.count("set_country_flag = zhx_opening_school_initialised") == 1,
        "opening event must set each country's opening marker exactly once",
    )
    require(
        every_country.count("zhx_refresh_doctrine_tier = yes") == 1,
        "opening event must apply the 25-practice tier before the first yearly pulse",
    )
    require(
        every_country.count("zhx_prepare_doctrine_ledger = yes") == 1,
        "opening event must prepare the hover-ledger cache before the first monthly pulse",
    )
    require(
        every_country.count("zhx_clear_doctrine_flags = yes") == 1,
        "opening event must clear stale doctrine flags before assignment",
    )
    require(
        every_country.count("country_event = { id = zhx_doctrine.91 }") == 1,
        "opening event must dispatch the direct native-school mirror exactly once",
    )
    require(
        immediate.count("set_global_flag = zhx_opening_schools_initialised") == 1,
        "opening event must close its global one-shot lifecycle",
    )

    executable = strip_comments(text)
    forbidden_tokens = {
        "zhx_finish_doctrine_adoption": "opening state must not use adoption",
        "zhx_adopt_": "opening state must not call a school-adoption effect",
        "zhx_doctrine_change_cooldown": "opening state must not add a cooldown",
        "add_country_modifier": "opening state must not add an adoption modifier",
        "set_religious_school": "native assignment must remain in zhx_doctrine.91",
    }
    for token, reason in forbidden_tokens.items():
        require(token not in executable, f"{reason}: found {token}")


def validate_on_startup() -> None:
    text = ON_ACTIONS.read_text(encoding="utf-8")
    startup = block_body(text, "on_startup")
    events = block_body(startup, "events")
    require(events.count(EVENT_ID) == 1, f"on_startup must dispatch {EVENT_ID} exactly once")
    require(
        events.find("zhx_system.1") < events.find(EVENT_ID) < events.find("zhx_debate.1"),
        "opening schools must initialize after the Tianxia kernel and before the debate",
    )


def validate_country_histories(all_tags: list[str]) -> None:
    for tag in all_tags:
        paths = sorted(COUNTRY_HISTORY.glob(f"{tag} - *.txt"))
        require(len(paths) == 1, f"{tag} has {len(paths)} country-history files")
        data = paths[0].read_bytes()
        match = re.search(
            rb"(?m)^[ \t]*religion[ \t]*=[ \t]*([a-z0-9_]+)",
            data,
        )
        require(match is not None, f"{tag} country history has no opening religion")
        religion = match.group(1).decode("ascii")
        require(
            religion == "confucianism",
            f"{tag} opening religion is {religion}, expected confucianism",
        )


def main() -> None:
    schools, all_tags = load_manifest()
    validate_event_projection(schools, all_tags)
    validate_on_startup()
    validate_country_histories(all_tags)
    counts = ", ".join(f"{school}={SCHOOL_COUNTS[school]}" for school in SCHOOL_ORDER)
    print(
        "ZHX_OPENING_SCHOOLS_VALID; total=65; "
        f"{counts}; histories=65_confucianism; startup={EVENT_ID}"
    )


if __name__ == "__main__":
    main()
