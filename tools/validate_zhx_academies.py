#!/usr/bin/env python3
"""Validate the static named-academy MVP and its derived country state."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import apply_zhx_academies as academy_projection
from encode_eu4_chinese_localisation import FILES, verify_file


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
MANIFEST = ROOT / "planning/religion_academies/academy_manifest.json"
OPENING_MANIFEST = (
    ROOT / "planning/religion_opening_schools/opening_schools_manifest.json"
)
MODIFIERS = MOD / "common/event_modifiers/zhx_academy_modifiers.txt"
TRIGGERS = MOD / "common/scripted_triggers/zhx_academy_triggers.txt"
EFFECTS = MOD / "common/scripted_effects/zhx_academy_effects.txt"
DOCTRINE_EFFECTS = MOD / "common/scripted_effects/zhx_doctrine_effects.txt"
EVENTS = MOD / "events/zhx_academy_events.txt"
ON_ACTIONS = MOD / "common/on_actions/zhx_system_on_actions.txt"
OPENING_EVENTS = MOD / "events/zhx_opening_school_events.txt"
RELIGIONS = MOD / "common/religions/00_religion.txt"
RELIGION_BUILDER = ROOT / "tools/build_zhx_religions.py"
LOCALISATION_SOURCE = (
    MOD / "localisation_source/zhx_academies_readable_utf8.txt"
)
LOCALISATION_TARGET = MOD / "localisation/zhx_academies_l_english.yml"
PROVINCE_HISTORY = MOD / "history/provinces"
SHAANXI_GENERATOR = ROOT / "tools/map_pipeline/apply_shaanxi_refinement.py"
HISTORY_FINALIZER = ROOT / "tools/map_pipeline/finalize_zhx_province_history.py"

SCHOOLS = ("ru", "fa", "mo", "dao", "bing", "zongheng")
DOCTRINE_FLAGS = {school: f"zhx_doctrine_{school}" for school in SCHOOLS}
INVITED_MODIFIERS = {
    school: f"zhx_{school}_invited_scholar_modifier" for school in SCHOOLS
}
TENSION_MODIFIERS = (
    "zhx_academy_tension_mild",
    "zhx_academy_tension_medium",
    "zhx_academy_tension_heavy",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_balanced_clausewitz(paths: tuple[Path, ...]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
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
                require(depth >= 0, f"{path.name}: closing brace without opener")
        require(not in_string, f"{path.name}: unterminated string")
        require(depth == 0, f"{path.name}: unbalanced braces ({depth})")


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


def scalar_values(body: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for key, raw in re.findall(
        r"(?m)^\s*([a-zA-Z0-9_]+)\s*=\s*(-?(?:\d+(?:\.\d*)?|\.\d+))\s*(?:#.*)?$",
        body,
    ):
        require(key not in values, f"duplicate scalar {key}")
        values[key] = float(raw)
    return values


def initial_scalar(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^#\n]+)", text)
    require(match is not None, f"missing scalar {key}")
    return match.group(1).strip()


def province_history_id(path: Path) -> int | None:
    match = re.match(r"^(\d+)\s*-\s*.+\.txt$", path.name)
    return int(match.group(1)) if match else None


def expected_float_map(*maps: dict[str, object]) -> dict[str, float]:
    result: dict[str, float] = {}
    for mapping in maps:
        result.update({key: float(value) for key, value in mapping.items()})
    return result


def validate_manifest(data: dict[str, object]) -> list[dict[str, object]]:
    require(data.get("schema_version") == 1, "unsupported academy manifest schema")
    require(data.get("campaign_start") == "1444.11.11", "campaign start drifted")
    require(
        data.get("gameplay_authority") == "unique_permanent_province_modifier",
        "academy gameplay authority drifted",
    )
    require(
        data.get("eligible_country_religion") == "confucianism",
        "academy country eligibility drifted",
    )
    academies = data.get("academies")
    require(isinstance(academies, list), "academies must be a list")
    require(len(academies) == 12, f"expected 12 academies, found {len(academies)}")

    school_counts: Counter[str] = Counter()
    unique_fields: defaultdict[str, set[object]] = defaultdict(set)
    for academy in academies:
        require(isinstance(academy, dict), "academy entry must be an object")
        school = academy.get("school")
        require(school in SCHOOLS, f"invalid academy school {school}")
        school_counts[str(school)] += 1
        for field in ("key", "name", "province_id", "history_file", "modifier"):
            value = academy.get(field)
            require(value not in unique_fields[field], f"duplicate academy {field}: {value}")
            unique_fields[field].add(value)
        require(
            academy.get("modifier") == f"zhx_academy_{academy.get('key')}",
            f"modifier/key drift for {academy.get('name')}",
        )
        require(
            str(academy.get("history_file", "")).startswith(
                f"{academy.get('province_id')} - "
            ),
            f"province/history mismatch for {academy.get('name')}",
        )
    require(
        school_counts == Counter({school: 2 for school in SCHOOLS}),
        f"each school must have two academies: {school_counts}",
    )
    return academies


def validate_opening_alignment(academies: list[dict[str, object]]) -> None:
    opening = json.loads(OPENING_MANIFEST.read_text(encoding="utf-8"))
    tag_school: dict[str, str] = {}
    for school, config in opening["schools"].items():
        for tag in config["tags"]:
            require(tag not in tag_school, f"opening school tag duplicated: {tag}")
            tag_school[tag] = school
    for academy in academies:
        owner = str(academy["initial_owner"])
        require(
            tag_school.get(owner) == academy["school"],
            f"{academy['name']}: opening owner {owner} does not match its school",
        )


def validate_province_history(academies: list[dict[str, object]]) -> None:
    all_history = "\n".join(
        path.read_text(encoding="utf-8-sig", errors="strict")
        for path in PROVINCE_HISTORY.glob("*.txt")
    )
    histories_by_id: defaultdict[int, list[Path]] = defaultdict(list)
    for candidate in PROVINCE_HISTORY.glob("*.txt"):
        province_id = province_history_id(candidate)
        if province_id is not None:
            histories_by_id[province_id].append(candidate)
    for academy in academies:
        path = PROVINCE_HISTORY / str(academy["history_file"])
        same_id = sorted(histories_by_id[int(academy["province_id"])])
        require(
            same_id == [path],
            f"province {academy['province_id']}: local history projection is ambiguous",
        )
        require(path.is_file(), f"missing history file {path.name}")
        text = path.read_text(encoding="utf-8-sig")
        require(
            initial_scalar(text, "owner") == academy["initial_owner"],
            f"{academy['name']}: initial owner drifted",
        )
        require(
            initial_scalar(text, "religion") == "confucianism",
            f"{academy['name']}: opening province must be confucianism",
        )
        modifier = str(academy["modifier"])
        blocks = re.findall(
            r"add_permanent_province_modifier\s*=\s*\{([^{}]*)\}", text, re.S
        )
        placements = [body for body in blocks if f"name = {modifier}" in body]
        require(len(placements) == 1, f"{modifier}: expected one permanent placement")
        require(
            re.search(r"(?m)^\s*duration\s*=\s*-1\s*$", placements[0]) is not None,
            f"{modifier}: placement must be permanent",
        )
        require(
            len(re.findall(rf"(?m)^\s*name\s*=\s*{re.escape(modifier)}\s*$", all_history))
            == 1,
            f"{modifier}: must occur in province history exactly once",
        )


def validate_replay_projection() -> None:
    rendered, affected = academy_projection.render_projection()
    stale = sorted(path.name for path in affected if path.read_bytes() != rendered[path])
    require(not stale, f"academy terminal history projection is stale: {stale}")

    shaanxi = SHAANXI_GENERATOR.read_text(encoding="utf-8")
    require(
        '700: "700 - Xi\'an.txt"' in shaanxi
        and "HISTORY_FILENAMES.get(pid" in shaanxi,
        "Shaanxi replay must preserve the inherited 700 - Xi'an.txt VFS filename",
    )

    finalizer = HISTORY_FINALIZER.read_text(encoding="utf-8")
    require("    else:\n" in finalizer, "terminal history replay lacks apply branch")
    apply_branch = finalizer.split("    else:\n", 1)[1]
    required_order = (
        'call(RELIGIOUS_GEOGRAPHY, check=False)',
        'call(RELIGIOUS_GEOGRAPHY, check=True)',
        'call(ACADEMIES, check=False)',
        'call(ACADEMIES, check=True)',
    )
    positions = [apply_branch.find(token) for token in required_order]
    require(
        all(position >= 0 for position in positions)
        and positions == sorted(positions),
        "terminal province-history replay must apply/check religion before academies",
    )


def validate_modifier_values(data: dict[str, object], academies: list[dict[str, object]]) -> None:
    text = MODIFIERS.read_text(encoding="utf-8")
    common = data["common_local_effects"]
    school_local = data["school_local_effects"]
    for academy in academies:
        expected = expected_float_map(common, school_local[academy["school"]])
        actual = scalar_values(block_body(text, str(academy["modifier"])))
        require(actual == expected, f"{academy['modifier']}: local effects drifted: {actual}")

    synergies = data["country_synergies"]
    for school in SCHOOLS:
        config = synergies[school]
        modifier = config["modifier"]
        actual = scalar_values(block_body(text, modifier))
        expected = expected_float_map(config["effects"])
        require(actual == expected, f"{modifier}: synergy effects drifted: {actual}")

    tiers = data["thought_tension"]["tiers"]
    for tier in ("1", "2", "3_plus"):
        config = tiers[tier]
        actual = scalar_values(block_body(text, config["modifier"]))
        expected = expected_float_map(config["effects"])
        require(actual == expected, f"{config['modifier']}: tension effects drifted")

    expected_blocks = {
        str(academy["modifier"]) for academy in academies
    } | {
        str(data["country_synergies"][school]["modifier"]) for school in SCHOOLS
    } | set(TENSION_MODIFIERS)
    top_level_blocks = re.findall(
        r"(?m)^([a-zA-Z0-9_]+)\s*=\s*\{", text
    )
    counts = Counter(top_level_blocks)
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    require(not duplicates, f"academy modifier blocks duplicated: {duplicates}")
    require(
        set(top_level_blocks) == expected_blocks,
        "academy modifier file contains missing or unmanaged top-level blocks",
    )


def validate_script_contracts(data: dict[str, object], academies: list[dict[str, object]]) -> None:
    triggers = TRIGGERS.read_text(encoding="utf-8")
    by_school: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for academy in academies:
        by_school[str(academy["school"])].append(academy)
    for school in SCHOOLS:
        has_body = block_body(triggers, f"zhx_has_{school}_academy")
        expected_modifiers = {str(entry["modifier"]) for entry in by_school[school]}
        actual_modifiers = set(
            re.findall(r"has_province_modifier\s*=\s*(zhx_academy_[a-z]+)", has_body)
        )
        require(
            actual_modifiers == expected_modifiers,
            f"{school}: academy ownership trigger drifted",
        )
        unprotected = block_body(triggers, f"zhx_has_unprotected_{school}_academy")
        for token in (
            f"zhx_has_{school}_academy = yes",
            f"has_country_flag = {DOCTRINE_FLAGS[school]}",
            f"has_country_modifier = {INVITED_MODIFIERS[school]}",
        ):
            require(token in unprotected, f"{school}: unprotected trigger lacks {token}")

    effects = EFFECTS.read_text(encoding="utf-8")
    remove = block_body(effects, "zhx_remove_academy_country_modifiers")
    country_modifiers = [
        data["country_synergies"][school]["modifier"] for school in SCHOOLS
    ] + list(TENSION_MODIFIERS)
    for modifier in country_modifiers:
        require(
            remove.count(f"remove_country_modifier = {modifier}") == 1,
            f"{modifier}: derived cleanup missing or duplicated",
        )
    refresh = block_body(effects, "zhx_refresh_academy_country_effects")
    require("zhx_is_lijiao_country = yes" in refresh, "academy refresh lacks religion gate")
    require("zhx_has_doctrine = yes" in refresh, "academy refresh lacks doctrine gate")
    require(
        refresh.count("which = zhx_academy_unprotected_school_count") == 10,
        "academy tension counter structure drifted",
    )
    for school in SCHOOLS:
        require(
            refresh.count(f"name = zhx_academy_synergy_{school}") == 1,
            f"{school}: synergy application missing or duplicated",
        )
        require(
            refresh.count(f"zhx_has_unprotected_{school}_academy = yes") == 1,
            f"{school}: tension count branch missing or duplicated",
        )
    for modifier in TENSION_MODIFIERS:
        require(refresh.count(f"name = {modifier}") == 1, f"{modifier}: tier branch drifted")

    doctrine = DOCTRINE_EFFECTS.read_text(encoding="utf-8")
    finish = block_body(doctrine, "zhx_finish_doctrine_adoption")
    clear = block_body(doctrine, "zhx_clear_doctrine_system")
    require(
        finish.count("zhx_refresh_academy_country_effects = yes") == 1,
        "doctrine adoption must refresh academy state",
    )
    require(
        clear.count("zhx_remove_academy_country_modifiers = yes") == 1,
        "religion lifecycle cleanup must remove academy country modifiers",
    )


def validate_hooks(academies: list[dict[str, object]]) -> None:
    on_actions = ON_ACTIONS.read_text(encoding="utf-8")
    yearly = block_body(on_actions, "on_yearly_pulse")
    require(yearly.count("zhx_academy.90") == 1, "annual academy repair hook drifted")
    require(
        yearly.index("zhx_doctrine.90") < yearly.index("zhx_academy.90"),
        "academy annual repair must follow doctrine normalization",
    )
    owner_change = block_body(on_actions, "on_province_owner_change")
    for academy in academies:
        require(
            owner_change.count(f"has_province_modifier = {academy['modifier']}") == 1,
            f"{academy['modifier']}: owner-change hook missing or duplicated",
        )
    require(
        owner_change.count("zhx_refresh_academy_country_effects = yes") == 2,
        "owner-change hook must refresh both owners",
    )
    require(
        owner_change.count("zhx_academy_cancel_expulsion_on_owner_change = yes") == 1
        and owner_change.index("zhx_academy_cancel_expulsion_on_owner_change = yes")
        < owner_change.index("zhx_refresh_academy_country_effects = yes"),
        "owner-change lifecycle cancellation must run once before both refreshes",
    )

    opening = OPENING_EVENTS.read_text(encoding="utf-8")
    require(
        opening.count("zhx_refresh_academy_country_effects = yes") == 1,
        "opening school projection must initialize academy country effects",
    )
    events = EVENTS.read_text(encoding="utf-8")
    require("namespace = zhx_academy" in events, "academy namespace missing")
    event = block_body(events, "country_event")
    require(initial_scalar(event, "id") == "zhx_academy.90", "annual event id drifted")
    require(event.count("hidden = yes") == 1, "annual academy event must be hidden")
    require(
        event.count("zhx_refresh_academy_country_effects = yes") == 1,
        "annual academy event must call the shared reconciler",
    )

    builder = RELIGION_BUILDER.read_text(encoding="utf-8")
    generated = RELIGIONS.read_text(encoding="utf-8")
    require(
        builder.count("zhx_refresh_academy_country_effects = yes") == 1,
        "religion builder must emit invitation refresh",
    )
    require(
        generated.count("zhx_refresh_academy_country_effects = yes") == 6,
        "all six generated invitation branches must refresh academy state",
    )


def localisation_keys(text: str) -> list[str]:
    return re.findall(r"(?m)^\s*([a-zA-Z0-9_.]+):0\s+", text)


def validate_localisation(data: dict[str, object], academies: list[dict[str, object]]) -> None:
    source = LOCALISATION_SOURCE.read_text(encoding="utf-8-sig")
    key_list = localisation_keys(source)
    duplicates = sorted(key for key, count in Counter(key_list).items() if count != 1)
    require(not duplicates, f"academy localisation duplicates keys: {duplicates}")
    keys = set(key_list)
    required = {"zhx_academy.90.t", "zhx_academy.90.d"}
    for academy in academies:
        modifier = str(academy["modifier"])
        required.update((modifier, f"{modifier}_desc"))
    for school in SCHOOLS:
        modifier = data["country_synergies"][school]["modifier"]
        required.update((modifier, f"{modifier}_desc"))
    for modifier in TENSION_MODIFIERS:
        required.update((modifier, f"{modifier}_desc"))
    missing = required - keys
    require(not missing, f"academy localisation missing keys: {sorted(missing)}")
    require(keys == required, f"academy localisation has unmanaged keys: {sorted(keys - required)}")
    require(
        FILES.get(LOCALISATION_SOURCE.name) == LOCALISATION_TARGET.name,
        "academy localisation source is not registered in the encoder FILES map",
    )
    verify_file(LOCALISATION_SOURCE, LOCALISATION_TARGET)


def main() -> None:
    validate_balanced_clausewitz((MODIFIERS, TRIGGERS, EFFECTS, EVENTS, ON_ACTIONS))
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    academies = validate_manifest(data)
    validate_opening_alignment(academies)
    validate_province_history(academies)
    validate_replay_projection()
    validate_modifier_values(data, academies)
    validate_script_contracts(data, academies)
    validate_hooks(academies)
    validate_localisation(data, academies)
    print(
        "ZHX academies valid: 12 named province authorities, six non-stacking "
        "main-school synergies, invited-school protection, and capped distinct-school tension"
    )


if __name__ == "__main__":
    main()
