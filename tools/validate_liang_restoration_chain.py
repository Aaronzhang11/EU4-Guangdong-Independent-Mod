#!/usr/bin/env python3
"""Static contract for the dormant-Liang restoration event chain."""

from __future__ import annotations

from collections import Counter
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

EVENTS = MOD / "events/gdd_liang_restoration_events.txt"
ON_ACTIONS = MOD / "common/on_actions/gdd_liang_restoration_on_actions.txt"
EFFECTS = MOD / "common/scripted_effects/gdd_liang_restoration_effects.txt"
CHARACTER_EFFECTS = (
    MOD / "common/scripted_effects/gdd_liang_restoration_character_effects.txt"
)
CHARACTER_SOURCE = (
    ROOT / "tools/event_sources/gdd_liang_restoration_character_effects_readable_utf8.txt"
)
TRIGGERS = MOD / "common/scripted_triggers/gdd_liang_restoration_triggers.txt"
MODIFIERS = MOD / "common/event_modifiers/gdd_liang_restoration_modifiers.txt"
LOCALISATION = MOD / "localisation_source/gdd_liang_restoration_readable_utf8.txt"
HISTORY = MOD / "history/countries/LGU - Liang.txt"

SCRIPT_FILES = (
    EVENTS,
    ON_ACTIONS,
    EFFECTS,
    CHARACTER_EFFECTS,
    TRIGGERS,
    MODIFIERS,
)
REQUIRED_FILES = (*SCRIPT_FILES, LOCALISATION, HISTORY, CHARACTER_SOURCE)
HOMELAND_IDS = ("708", "2182", "5295")
TOKEN_EDGE = r"A-Za-z0-9_.:-"

# Replay/design sources are scanned too: either one could silently restore the
# invalid religion even after the live country history had been corrected.
FORBIDDEN_SCAN_FILES = (
    *SCRIPT_FILES,
    LOCALISATION,
    HISTORY,
    MOD / "common/countries/B76_Liang.txt",
    ROOT / "tools/apply_liang_restoration_tag.py",
    ROOT / "tools/validate_liang_restoration_tag.py",
    ROOT / "planning/liang_restoration_b76/tag_manifest.json",
)


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def masked(text: str) -> str:
    """Mask Clausewitz comments and strings without changing character offsets."""
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
            out.append("\n" if char == "\n" else " ")
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


def validate_braces(path: Path, code: str, errors: list[str]) -> None:
    stack: list[int] = []
    line = 1
    for char in code:
        if char == "\n":
            line += 1
        elif char == "{":
            stack.append(line)
        elif char == "}":
            if not stack:
                errors.append(
                    f"unbalanced Clausewitz braces: {relative(path)}:{line} "
                    "has a closing brace without an opener"
                )
                return
            stack.pop()
    if stack:
        errors.append(
            f"unbalanced Clausewitz braces: {relative(path)} has "
            f"{len(stack)} unclosed opener(s), earliest at line {stack[0]}"
        )


def brace_depth(code: str, position: int) -> int:
    depth = 0
    for char in code[:position]:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
    return depth


def matching_brace(code: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(code)):
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def assignment_blocks(
    code: str, key: str, required_depth: int | None = None
) -> list[str]:
    pattern = re.compile(
        rf"(?<![{TOKEN_EDGE}]){re.escape(key)}\s*=\s*\{{"
    )
    result: list[str] = []
    for match in pattern.finditer(code):
        if required_depth is not None and brace_depth(code, match.start()) != required_depth:
            continue
        opening = code.find("{", match.start(), match.end())
        closing = matching_brace(code, opening)
        if closing is not None:
            result.append(code[match.start() : closing + 1])
    return result


def named_block(
    code: str,
    key: str,
    errors: list[str],
    *,
    context: str,
    required_depth: int = 0,
) -> str:
    blocks = assignment_blocks(code, key, required_depth)
    check(
        len(blocks) == 1,
        f"{context}: expected exactly one block {key}, found {len(blocks)}",
        errors,
    )
    return blocks[0] if len(blocks) == 1 else ""


def scalar_values(code: str, key: str, depth: int | None = None) -> list[str]:
    pattern = re.compile(
        rf"(?<![{TOKEN_EDGE}]){re.escape(key)}\s*=\s*([^\s{{}}#=]+)"
    )
    values: list[str] = []
    for match in pattern.finditer(code):
        if depth is None or brace_depth(code, match.start()) == depth:
            values.append(match.group(1))
    return values


def direct_scalar_pairs(code: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        rf"(?<![{TOKEN_EDGE}])([{TOKEN_EDGE}]+)\s*=\s*([^\s{{}}#=]+)"
    )
    return [
        (match.group(1), match.group(2))
        for match in pattern.finditer(code)
        if brace_depth(code, match.start()) == 1
    ]


def direct_numeric_blocks(code: str) -> list[str]:
    pattern = re.compile(rf"(?<![{TOKEN_EDGE}])(\d+)\s*=\s*\{{")
    return [
        match.group(1)
        for match in pattern.finditer(code)
        if brace_depth(code, match.start()) == 1
    ]


def direct_child(
    code: str, key: str, errors: list[str], *, context: str
) -> str:
    return named_block(
        code,
        key,
        errors,
        context=context,
        required_depth=1,
    )


def event_definitions(event_code: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for block in assignment_blocks(event_code, "country_event", required_depth=0):
        ids = scalar_values(block, "id", depth=1)
        if len(ids) == 1:
            result.setdefault(ids[0], []).append(block)
    return result


def required_event(
    definitions: dict[str, list[str]], event_id: str, errors: list[str]
) -> str:
    blocks = definitions.get(event_id, [])
    check(
        len(blocks) == 1,
        f"events: expected exactly one definition of {event_id}, found {len(blocks)}",
        errors,
    )
    return blocks[0] if len(blocks) == 1 else ""


def scheduled_edge_count(event_block: str, target: str, days: str) -> int:
    count = 0
    for block in assignment_blocks(event_block, "country_event"):
        if scalar_values(block, "id", depth=1) == [target] and scalar_values(
            block, "days", depth=1
        ) == [days]:
            count += 1
    return count


def modifier_application_count(code: str, name: str, duration: str) -> int:
    count = 0
    for block in assignment_blocks(code, "add_country_modifier"):
        if scalar_values(block, "name", depth=1) == [name] and scalar_values(
            block, "duration", depth=1
        ) == [duration]:
            count += 1
    return count


def validate_localisation(
    event_code: str, localisation: str, errors: list[str]
) -> int:
    references = re.findall(
        r"(?<![A-Za-z0-9_.:-])(?:title|desc|name|custom_tooltip)\s*=\s*"
        r"(gdd_liang_restoration\.[A-Za-z0-9_.-]+)",
        event_code,
    )
    keys = re.findall(
        r"(?m)^[ \t]*([^\s:#]+):\d+(?=\s|$)",
        localisation,
    )
    key_counts = Counter(keys)
    duplicates = sorted(key for key, count in key_counts.items() if count != 1)
    check(
        not duplicates,
        "readable localisation has duplicate keys: " + ", ".join(duplicates),
        errors,
    )
    check(bool(references), "events contain no Liang localisation references", errors)
    missing = sorted(set(references) - set(keys))
    check(
        not missing,
        "event localisation references missing from readable source: "
        + ", ".join(missing),
        errors,
    )
    return len(set(references))


def validate_modifiers(modifier_code: str, effects: str, errors: list[str]) -> None:
    expected = {
        "gdd_liang_preserver_of_fallen_state": Counter(
            {("diplomatic_reputation", "0.33"): 1}
        ),
        "gdd_liang_repudiated_restoration_compact": Counter(
            {
                ("diplomatic_reputation", "-0.5"): 1,
                ("improve_relation_modifier", "-0.10"): 1,
                ("prestige", "-0.5"): 1,
            }
        ),
    }
    for modifier, expected_pairs in expected.items():
        block = named_block(
            modifier_code,
            modifier,
            errors,
            context="event modifiers",
        )
        if block:
            actual_pairs = Counter(direct_scalar_pairs(block))
            check(
                actual_pairs == expected_pairs,
                f"event modifier {modifier} values drifted: "
                f"expected {dict(expected_pairs)}, found {dict(actual_pairs)}",
                errors,
            )

    check(
        modifier_application_count(
            effects, "gdd_liang_preserver_of_fallen_state", "-1"
        )
        == 1,
        "positive Liang modifier must be applied exactly once with duration = -1",
        errors,
    )
    check(
        modifier_application_count(
            effects, "gdd_liang_repudiated_restoration_compact", "7300"
        )
        == 1,
        "repudiation modifier must be applied exactly once for 7300 days",
        errors,
    )


def validate_restoration_creation(effects: str, errors: list[str]) -> dict[str, str]:
    names = (
        "gdd_liang_prepare_restored_country",
        "gdd_liang_restore_in_temporary_grant",
        "gdd_liang_restore_directly_in_homeland",
        "gdd_liang_select_lowest_grant_province",
        "gdd_liang_clear_original_grant_tracking",
        "gdd_liang_apply_repudiation_without_liberty_desire",
        "gdd_liang_apply_repudiation_with_liberty_desire",
        "gdd_liang_honor_homeland_settlement",
    )
    blocks = {
        name: named_block(effects, name, errors, context="scripted effects")
        for name in names
    }

    prepare = blocks["gdd_liang_prepare_restored_country"]
    if prepare:
        lgu_scope = direct_child(
            prepare, "LGU", errors, context="prepare restored Liang"
        )
        if lgu_scope:
            check(
                scalar_values(lgu_scope, "zhx_register_tianxia_member", depth=1)
                == ["yes"],
                "LGU preparation must call zhx_register_tianxia_member = yes "
                "inside LGU scope",
                errors,
            )
            check(
                scalar_values(lgu_scope, "change_religion", depth=1)
                == ["confucianism"],
                "restored LGU must be changed to confucianism",
                errors,
            )
        subject = direct_child(
            prepare, "create_subject", errors, context="prepare restored Liang"
        )
        if subject:
            check(
                scalar_values(subject, "subject_type", depth=1) == ["march"],
                "restored LGU subject type must be march",
                errors,
            )
            check(
                scalar_values(subject, "subject", depth=1) == ["LGU"],
                "restored march subject must be LGU",
                errors,
            )

    for name in (
        "gdd_liang_restore_in_temporary_grant",
        "gdd_liang_restore_directly_in_homeland",
    ):
        block = blocks[name]
        if not block:
            continue
        releases = list(
            re.finditer(r"(?<![A-Za-z0-9_.:-])release\s*=\s*LGU(?![A-Za-z0-9_.:-])", block)
        )
        prepares = list(
            re.finditer(
                r"(?<![A-Za-z0-9_.:-])gdd_liang_prepare_restored_country\s*=\s*yes"
                r"(?![A-Za-z0-9_.:-])",
                block,
            )
        )
        check(
            len(releases) == 1,
            f"{name} must contain exactly one release = LGU",
            errors,
        )
        check(
            len(prepares) == 1,
            f"{name} must call the march-creation preparation exactly once",
            errors,
        )
        if len(releases) == 1 and len(prepares) == 1:
            check(
                releases[0].start() < prepares[0].start(),
                f"{name} must release LGU before create_subject march preparation",
                errors,
            )
    return blocks


def validate_rhythm(
    events: str, on_actions: str, errors: list[str]
) -> dict[str, str]:
    definitions = event_definitions(events)
    event_ids = (
        "gdd_liang_restoration.100",
        "gdd_liang_restoration.1",
        "gdd_liang_restoration.2",
        "gdd_liang_restoration.10",
        "gdd_liang_restoration.20",
        "gdd_liang_restoration.30",
        "gdd_liang_restoration.39",
        "gdd_liang_restoration.40",
        "gdd_liang_restoration.90",
    )
    required = {
        event_id: required_event(definitions, event_id, errors)
        for event_id in event_ids
    }
    edges = (
        ("gdd_liang_restoration.100", "gdd_liang_restoration.1", "90"),
        ("gdd_liang_restoration.1", "gdd_liang_restoration.2", "90"),
        ("gdd_liang_restoration.2", "gdd_liang_restoration.2", "30"),
        ("gdd_liang_restoration.10", "gdd_liang_restoration.2", "180"),
        ("gdd_liang_restoration.90", "gdd_liang_restoration.39", "30"),
    )
    for source, target, days in edges:
        block = required[source]
        if block:
            check(
                scheduled_edge_count(block, target, days) == 1,
                f"timing contract requires exactly one {source} -> {target} "
                f"delay of {days} days",
                errors,
            )

    startup = named_block(
        on_actions, "on_startup", errors, context="Liang on_actions"
    )
    monthly = named_block(
        on_actions, "on_monthly_pulse", errors, context="Liang on_actions"
    )
    integrate = named_block(
        on_actions, "on_integrate", errors, context="Liang on_actions"
    )
    annexed = named_block(
        on_actions, "on_annexed", errors, context="Liang on_actions"
    )
    if startup:
        check(
            re.search(r"(?<![A-Za-z0-9_.:-])gdd_liang_restoration\.100(?![A-Za-z0-9_.:-])", startup)
            is not None,
            "on_startup must register gdd_liang_restoration.100",
            errors,
        )
    if monthly:
        check(
            re.search(r"(?<![A-Za-z0-9_.:-])gdd_liang_restoration\.90(?![A-Za-z0-9_.:-])", monthly)
            is not None,
            "on_monthly_pulse must register gdd_liang_restoration.90",
            errors,
        )
    if integrate:
        check(
            scalar_values(
                integrate,
                "gdd_liang_apply_repudiation_without_liberty_desire",
            )
            == ["yes"],
            "on_integrate must apply the no-liberty-desire repudiation effect",
            errors,
        )
    if annexed:
        check(
            scalar_values(
                annexed,
                "gdd_liang_apply_repudiation_without_liberty_desire",
            )
            == ["yes"],
            "on_annexed must apply the no-liberty-desire repudiation effect",
            errors,
        )
    return required


def validate_petition_observability(
    events: str,
    effects: str,
    event_blocks: dict[str, str],
    restoration_blocks: dict[str, str],
    errors: list[str],
) -> None:
    """Lock the debug mirror without making it production authority."""
    target = "gdd_liang_current_petition_target"
    clear_target = named_block(
        effects,
        "gdd_liang_clear_current_petition_target",
        errors,
        context="scripted effects",
    )
    clear_roster = named_block(
        effects,
        "gdd_liang_clear_petition_roster",
        errors,
        context="scripted effects",
    )
    startup = event_blocks.get("gdd_liang_restoration.100", "")
    petition = event_blocks.get("gdd_liang_restoration.10", "")
    failure = event_blocks.get("gdd_liang_restoration.30", "")
    prepare = restoration_blocks.get("gdd_liang_prepare_restored_country", "")

    check(
        scalar_values(events, "save_global_event_target_as") == [target],
        "the valid petition event must be the sole writer of the target mirror",
        errors,
    )
    if petition:
        check(
            scalar_values(petition, "save_global_event_target_as") == [target],
            "the valid petition event must save the selected country globally",
            errors,
        )
        check(
            scalar_values(
                petition, "gdd_liang_clear_current_petition_target"
            )
            == [],
            "petition rejection must retain the last target during its 180-day wait",
            errors,
        )
    if clear_target:
        check(
            scalar_values(clear_target, "has_saved_global_event_target")
            == [target],
            "target cleanup must guard the saved global target",
            errors,
        )
        check(
            scalar_values(clear_target, "clear_global_event_target") == [target],
            "target cleanup must clear exactly the Liang target mirror",
            errors,
        )
    if clear_roster:
        check(
            scalar_values(
                clear_roster, "gdd_liang_clear_current_petition_target"
            )
            == ["yes"],
            "shared roster cleanup must also clear the target mirror",
            errors,
        )
    if startup:
        check(
            scalar_values(
                startup, "gdd_liang_clear_current_petition_target"
            )
            == ["yes"],
            "new-campaign bootstrap must clear any stale target mirror",
            errors,
        )
    for context, block in (
        ("successful restoration", prepare),
        ("exhausted-roster failure", failure),
    ):
        if block:
            check(
                scalar_values(block, "gdd_liang_clear_petition_roster")
                == ["yes"],
                f"{context} must use shared roster/target cleanup",
                errors,
            )


def validate_homeland(
    triggers: str, blocks: dict[str, str], errors: list[str]
) -> None:
    owns = named_block(
        triggers,
        "gdd_liang_patron_owns_all_homeland",
        errors,
        context="scripted triggers",
    )
    jointly = named_block(
        triggers,
        "gdd_liang_jointly_holds_homeland",
        errors,
        context="scripted triggers",
    )
    unoccupied = named_block(
        triggers,
        "gdd_liang_homeland_is_unoccupied",
        errors,
        context="scripted triggers",
    )
    if owns:
        check(
            Counter(scalar_values(owns, "owns", depth=1)) == Counter(HOMELAND_IDS),
            f"all-homeland trigger must own exactly {', '.join(HOMELAND_IDS)}",
            errors,
        )
    for name, block in (("joint ownership", jointly), ("unoccupied", unoccupied)):
        if block:
            check(
                Counter(direct_numeric_blocks(block)) == Counter(HOMELAND_IDS),
                f"{name} homeland trigger must scope exactly "
                f"{', '.join(HOMELAND_IDS)}",
                errors,
            )
    if jointly:
        for province_id in HOMELAND_IDS:
            child = direct_child(
                jointly,
                province_id,
                errors,
                context="joint homeland trigger",
            )
            if child:
                check(
                    Counter(scalar_values(child, "owned_by"))
                    == Counter(("ROOT", "LGU")),
                    f"homeland {province_id} must accept only ROOT or LGU ownership",
                    errors,
                )
    if unoccupied:
        for province_id in HOMELAND_IDS:
            child = direct_child(
                unoccupied,
                province_id,
                errors,
                context="unoccupied homeland trigger",
            )
            if child:
                check(
                    scalar_values(child, "controlled_by", depth=1) == ["owner"],
                    f"homeland {province_id} must be controlled by its owner",
                    errors,
                )

    for effect_name in (
        "gdd_liang_restore_in_temporary_grant",
        "gdd_liang_restore_directly_in_homeland",
        "gdd_liang_honor_homeland_settlement",
    ):
        block = blocks[effect_name]
        if block:
            check(
                set(direct_numeric_blocks(block)) == set(HOMELAND_IDS),
                f"{effect_name} must scope exactly homeland IDs "
                f"{', '.join(HOMELAND_IDS)}",
                errors,
            )


def validate_lowest_grant(
    effects: str, events: dict[str, str], blocks: dict[str, str], errors: list[str]
) -> None:
    select = blocks["gdd_liang_select_lowest_grant_province"]
    if not select:
        return
    check(
        scalar_values(select, "is_city").count("yes") >= 2,
        "lowest-development scans must exclude unfinished colonies with is_city = yes",
        errors,
    )
    check(
        scalar_values(select, "is_capital").count("no") >= 2,
        "lowest-development scans must exclude the patron capital",
        errors,
    )
    not_blocks = assignment_blocks(select, "NOT")
    for province_id in HOMELAND_IDS:
        exclusions = sum(
            scalar_values(block, "province_id", depth=1) == [province_id]
            for block in not_blocks
        )
        check(
            exclusions == 2,
            f"lowest-development two-pass scan must exclude homeland "
            f"{province_id} exactly twice",
            errors,
        )

    initialisers = [
        block
        for block in assignment_blocks(select, "set_variable")
        if scalar_values(block, "which", depth=1)
        == ["gdd_liang_minimum_grant_development"]
        and scalar_values(block, "value", depth=1) == ["10000"]
    ]
    check(
        len(initialisers) == 1,
        "lowest-development selector must initialise its minimum to 10000 once",
        errors,
    )
    exports = [
        block
        for block in assignment_blocks(select, "export_to_variable")
        if scalar_values(block, "which", depth=1)
        == ["gdd_liang_scanned_grant_development"]
        and scalar_values(block, "value", depth=1)
        == ["trigger_value:development"]
        and scalar_values(block, "who", depth=1) == ["PREV"]
    ]
    check(
        len(exports) == 2,
        "lowest-development selector must export development in both scan passes",
        errors,
    )
    comparisons = [
        tuple(scalar_values(block, "which", depth=1))
        for block in assignment_blocks(select, "check_variable")
    ]
    check(
        (
            "gdd_liang_scanned_grant_development",
            "gdd_liang_minimum_grant_development",
        )
        in comparisons
        and (
            "gdd_liang_minimum_grant_development",
            "gdd_liang_scanned_grant_development",
        )
        in comparisons,
        "tie marking must compare scanned and minimum development in both directions",
        errors,
    )
    check(
        scalar_values(select, "set_province_flag").count(
            "gdd_liang_lowest_grant_candidate"
        )
        == 1,
        "exact minimum ties must be marked with the candidate province flag",
        errors,
    )
    random_blocks = assignment_blocks(select, "random_owned_province")
    check(
        len(random_blocks) == 1,
        f"lowest-development selector needs one random_owned_province, found {len(random_blocks)}",
        errors,
    )
    if len(random_blocks) == 1:
        random_block = random_blocks[0]
        check(
            scalar_values(random_block, "has_province_flag")
            == ["gdd_liang_lowest_grant_candidate"],
            "random grant must be limited to exact minimum ties",
            errors,
        )
        check(
            scalar_values(random_block, "save_event_target_as")
            == ["gdd_liang_proposed_grant"],
            "random minimum grant must save gdd_liang_proposed_grant",
            errors,
        )
    petition = events.get("gdd_liang_restoration.10", "")
    if petition:
        check(
            scalar_values(petition, "gdd_liang_select_lowest_grant_province")
            == ["yes"],
            "petition event must call the lowest-development grant selector once",
            errors,
        )


def validate_grant_and_settlement(
    effects: str,
    on_actions: str,
    events: dict[str, str],
    blocks: dict[str, str],
    errors: list[str],
) -> None:
    temporary = blocks["gdd_liang_restore_in_temporary_grant"]
    direct = blocks["gdd_liang_restore_directly_in_homeland"]
    cleanup = blocks["gdd_liang_clear_original_grant_tracking"]
    honor = blocks["gdd_liang_honor_homeland_settlement"]
    repudiation = blocks["gdd_liang_apply_repudiation_without_liberty_desire"]
    repudiation_ld = blocks["gdd_liang_apply_repudiation_with_liberty_desire"]

    check(
        scalar_values(effects, "set_province_flag").count(
            "gdd_liang_original_grant"
        )
        == 1,
        "the original-grant province flag must be set exactly once in all effects",
        errors,
    )
    if temporary:
        check(
            scalar_values(temporary, "set_province_flag")
            == ["gdd_liang_original_grant"],
            "temporary restoration must mark its original grant",
            errors,
        )
        check(
            scalar_values(temporary, "set_country_flag").count(
                "gdd_liang_restoration_used_grant"
            )
            == 1,
            "temporary restoration must mark the grant branch",
            errors,
        )
    if direct:
        check(
            "gdd_liang_original_grant"
            not in scalar_values(direct, "set_province_flag"),
            "direct homeland restoration must not create an original-grant flag",
            errors,
        )
    for name, block in (("grant cleanup", cleanup), ("honor settlement", honor)):
        if block:
            check(
                "gdd_liang_original_grant"
                in scalar_values(block, "has_province_flag"),
                f"{name} must find the original grant by province flag",
                errors,
            )
            check(
                "gdd_liang_original_grant"
                in scalar_values(block, "clr_province_flag"),
                f"{name} must clear the original-grant province flag",
                errors,
            )

    if honor:
        for province_id in HOMELAND_IDS:
            child = direct_child(
                honor,
                province_id,
                errors,
                context="honor homeland settlement",
            )
            if child:
                for key, value in (
                    ("add_core", "LGU"),
                    ("cede_province", "LGU"),
                    ("remove_core", "ROOT"),
                ):
                    check(
                        scalar_values(child, key).count(value) == 1,
                        f"honor effect for {province_id} must contain "
                        f"{key} = {value} once",
                        errors,
                    )
        check(
            scalar_values(honor, "cede_province").count("ROOT") == 1,
            "honor effect must return the flagged original grant to ROOT once",
            errors,
        )
        check(
            scalar_values(honor, "set_country_flag").count(
                "gdd_liang_restoration_compact_fulfilled"
            )
            == 1,
            "honor effect must set the fulfilled compact flag",
            errors,
        )

    if repudiation:
        check(
            scalar_values(repudiation, "remove_country_modifier")
            == ["gdd_liang_preserver_of_fallen_state"],
            "repudiation must remove the permanent positive modifier",
            errors,
        )
        check(
            modifier_application_count(
                repudiation, "gdd_liang_repudiated_restoration_compact", "7300"
            )
            == 1,
            "repudiation must apply the 7300-day negative modifier",
            errors,
        )
        check(
            scalar_values(repudiation, "set_country_flag").count(
                "gdd_liang_restoration_compact_repudiated"
            )
            == 1,
            "repudiation must set the repudiated compact flag",
            errors,
        )
    if repudiation_ld:
        check(
            scalar_values(repudiation_ld, "add_liberty_desire") == ["100"],
            "active-subject repudiation must add exactly 100 liberty desire",
            errors,
        )
        check(
            scalar_values(
                repudiation_ld,
                "gdd_liang_apply_repudiation_without_liberty_desire",
            )
            == ["yes"],
            "active-subject repudiation must delegate to the base repudiation effect",
            errors,
        )

    settlement = events.get("gdd_liang_restoration.40", "")
    if settlement:
        check(
            scalar_values(settlement, "gdd_liang_honor_homeland_settlement")
            == ["yes"],
            "settlement event must expose the honor effect once",
            errors,
        )
        check(
            scalar_values(
                settlement, "gdd_liang_apply_repudiation_with_liberty_desire"
            )
            == ["yes"],
            "settlement event must expose the repudiation effect once",
            errors,
        )
    check(
        scalar_values(
            on_actions, "gdd_liang_apply_repudiation_without_liberty_desire"
        ).count("yes")
        == 2,
        "integration and annexation breaches must each call the "
        "no-liberty-desire repudiation once",
        errors,
    )


def validate_religion(history: str, effects: str, errors: list[str]) -> None:
    check(
        scalar_values(history, "religion") == ["confucianism"],
        "LGU country history must contain exactly religion = confucianism",
        errors,
    )
    check(
        scalar_values(effects, "change_religion").count("confucianism") == 1,
        "restoration preparation must set country religion to confucianism once",
        errors,
    )
    forbidden = "zhx_lijiao"
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(forbidden)}(?![A-Za-z0-9_])")
    for path in FORBIDDEN_SCAN_FILES:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(
                f"forbidden old Liang religion {forbidden} remains at "
                f"{relative(path)}:{line}"
            )


def validate_character(source: str, errors: list[str]) -> None:
    code = masked(source)
    effect = named_block(
        code,
        "gdd_liang_define_zhang_chengzuo",
        errors,
        context="readable Liang ruler source",
    )
    ruler = (
        direct_child(effect, "define_ruler", errors, context="Liang ruler effect")
        if effect
        else ""
    )
    expected_scalars = {
        "age": "27",
        "adm": "3",
        "dip": "5",
        "mil": "2",
        "claim": "90",
        "culture": "gdd_long",
        "religion": "confucianism",
        "male": "yes",
    }
    for key, value in expected_scalars.items():
        if ruler:
            check(
                scalar_values(ruler, key, depth=1) == [value],
                f"Liang ruler must have exactly {key} = {value}",
                errors,
            )
    for key, value in (("name", "承祚"), ("dynasty", "张")):
        matches = re.findall(
            rf'(?m)^[ \t]*{key}\s*=\s*"{re.escape(value)}"[ \t]*$',
            source,
        )
        check(
            len(matches) == 1,
            f'Liang ruler source must have exactly {key} = "{value}"',
            errors,
        )


def finish(errors: list[str], reference_count: int = 0) -> None:
    if errors:
        print(f"Liang restoration chain contract: FAIL ({len(errors)})")
        for index, error in enumerate(errors, 1):
            print(f"  {index:02d}. {error}")
        raise SystemExit(1)
    print("Liang restoration chain contract: PASS")
    print(
        f"  {len(SCRIPT_FILES)} Clausewitz chain files exist and have balanced braces"
    )
    print(f"  {reference_count} event localisation keys resolve in readable source")
    print("  LGU release -> March creation -> Tianxia registration is locked")
    print("  90/180/30-day cadence, homeland, grant, honor, and repudiation are locked")
    print("  Debug target mirror is guarded, retained between stops, and terminally cleared")
    print("  Zhang Chengzuo's name, displayed-age input, and 3/5/2 stats are locked")
    print("  LGU history and restoration setup use confucianism")


def main() -> None:
    errors: list[str] = []
    texts: dict[Path, str] = {}
    for path in REQUIRED_FILES:
        check(path.is_file(), f"missing required file: {relative(path)}", errors)
        if path.is_file():
            texts[path] = path.read_text(encoding="utf-8-sig")
    if errors:
        finish(errors)

    codes = {path: masked(text) for path, text in texts.items() if path != LOCALISATION}
    for path in SCRIPT_FILES:
        validate_braces(path, codes[path], errors)
    validate_braces(HISTORY, codes[HISTORY], errors)

    event_code = codes[EVENTS]
    on_action_code = codes[ON_ACTIONS]
    effect_code = codes[EFFECTS]
    trigger_code = codes[TRIGGERS]
    modifier_code = codes[MODIFIERS]

    reference_count = validate_localisation(
        event_code, texts[LOCALISATION], errors
    )
    validate_modifiers(modifier_code, effect_code, errors)
    effect_blocks = validate_restoration_creation(effect_code, errors)
    event_blocks = validate_rhythm(event_code, on_action_code, errors)
    validate_homeland(trigger_code, effect_blocks, errors)
    validate_lowest_grant(effect_code, event_blocks, effect_blocks, errors)
    validate_grant_and_settlement(
        effect_code,
        on_action_code,
        event_blocks,
        effect_blocks,
        errors,
    )
    validate_petition_observability(
        event_code,
        effect_code,
        event_blocks,
        effect_blocks,
        errors,
    )
    validate_character(texts[CHARACTER_SOURCE], errors)
    validate_religion(codes[HISTORY], effect_code, errors)
    finish(errors, reference_count)


if __name__ == "__main__":
    main()
