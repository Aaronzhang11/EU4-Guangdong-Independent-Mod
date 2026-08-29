#!/usr/bin/env python3
"""Static contract checks for the Lijiao main-doctrine reform state machine.

This validator deliberately lives beside, rather than inside,
``validate_zhx_doctrine.py``.  The latter owns the established six-school and
practice contracts; this file owns only the later main-school reform lifecycle.
Static success is not runtime proof.  See
``planning/religion_reform/runtime_test_matrix.md`` for the evidence matrix.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

TRIGGER_PATH = MOD / "common/scripted_triggers/zhx_doctrine_reform_triggers.txt"
EFFECT_PATH = MOD / "common/scripted_effects/zhx_doctrine_reform_effects.txt"
MODIFIER_PATH = MOD / "common/event_modifiers/zhx_doctrine_reform_modifiers.txt"
SECONDARY_MODIFIER_PATH = (
    MOD / "common/static_modifiers/zhx_doctrine_reform_secondary_modifiers.txt"
)
OPINION_PATH = MOD / "common/opinion_modifiers/zhx_doctrine_reform_opinions.txt"
DECISION_PATH = MOD / "decisions/zhx_doctrine_reform_decisions.txt"
EVENT_PATH = MOD / "events/zhx_doctrine_reform_events.txt"
LOCALISATION_PATH = (
    MOD / "localisation_source/zhx_doctrine_reform_readable_utf8.txt"
)

LEGACY_DECISION_PATH = MOD / "decisions/zhx_doctrine_decisions.txt"
DOCTRINE_EFFECT_PATH = MOD / "common/scripted_effects/zhx_doctrine_effects.txt"
DOCTRINE_EVENT_PATH = MOD / "events/zhx_doctrine_events.txt"
TIANXIA_TRIGGER_PATH = (
    MOD / "common/scripted_triggers/zhx_tianxia_debate_triggers.txt"
)
ACADEMY_TRIGGER_PATH = MOD / "common/scripted_triggers/zhx_academy_triggers.txt"
ACADEMY_LIFECYCLE_TRIGGER_PATH = (
    MOD / "common/scripted_triggers/zhx_academy_lifecycle_triggers.txt"
)
ACADEMY_LIFECYCLE_BUILDER_PATH = ROOT / "tools/build_zhx_academy_lifecycle.py"
RELIGION_PATH = MOD / "common/religions/00_religion.txt"
RELIGION_BUILDER_PATH = ROOT / "tools/build_zhx_religions.py"
REFORM_BUILDER_PATH = ROOT / "tools/build_zhx_doctrine_reform.py"
RELIGION_CUSTOM_GUI_PATH = MOD / "common/custom_gui/zhx_religion_gui.txt"
GUEST_SCHOOL_TRIGGER_PATH = (
    MOD / "common/scripted_triggers/zhx_guest_school_triggers.txt"
)

SCHOOLS = ("ru", "fa", "mo", "dao", "bing", "zongheng")
MAIN_FLAGS = {school: f"zhx_doctrine_{school}" for school in SCHOOLS}
TARGET_FLAGS = {
    school: f"zhx_doctrine_reform_target_{school}" for school in SCHOOLS
}
OLD_FLAGS = {school: f"zhx_doctrine_reform_old_{school}" for school in SCHOOLS}
INVITED_MODIFIERS = {
    school: f"zhx_{school}_invited_scholar_modifier" for school in SCHOOLS
}
GUEST_CONTRACT_ACTIVE_FLAG = "zhx_guest_school_contract_active"
GUEST_CONTRACT_FLAGS = {
    school: f"zhx_guest_school_contract_{school}" for school in SCHOOLS
}
GUEST_CONTRACT_REFORM_WINDOW_DAYS = 5475

REQUIRED_PATHS = (
    TRIGGER_PATH,
    EFFECT_PATH,
    MODIFIER_PATH,
    SECONDARY_MODIFIER_PATH,
    OPINION_PATH,
    DECISION_PATH,
    EVENT_PATH,
    LOCALISATION_PATH,
    LEGACY_DECISION_PATH,
    DOCTRINE_EFFECT_PATH,
    DOCTRINE_EVENT_PATH,
    TIANXIA_TRIGGER_PATH,
    ACADEMY_TRIGGER_PATH,
    ACADEMY_LIFECYCLE_TRIGGER_PATH,
    ACADEMY_LIFECYCLE_BUILDER_PATH,
    RELIGION_PATH,
    RELIGION_BUILDER_PATH,
    REFORM_BUILDER_PATH,
    RELIGION_CUSTOM_GUI_PATH,
    GUEST_SCHOOL_TRIGGER_PATH,
)

REQUIRED_TRIGGERS = (
    "zhx_doctrine_reform_is_active",
    "zhx_doctrine_reform_is_cultivating",
    "zhx_doctrine_reform_is_in_transition",
    "zhx_doctrine_reform_invitation_locked",
    "zhx_doctrine_reform_may_file_tianxia_proposal",
    *(f"zhx_doctrine_reform_can_target_{school}" for school in SCHOOLS),
    *(f"zhx_doctrine_reform_has_{school}_invited_root_now" for school in SCHOOLS),
    *(
        f"zhx_doctrine_reform_has_{school}_invited_root_with_five_years"
        for school in SCHOOLS
    ),
    *(f"zhx_doctrine_reform_has_{school}_root_now" for school in SCHOOLS),
    *(f"zhx_doctrine_reform_target_{school}_retains_root" for school in SCHOOLS),
    *(f"zhx_doctrine_reform_protects_{school}_academies" for school in SCHOOLS),
)

REQUIRED_EFFECTS = (
    *(f"zhx_doctrine_reform_begin_{school}" for school in SCHOOLS),
    "zhx_doctrine_reform_cancel",
    "zhx_doctrine_reform_clear_secondary_modifiers",
    "zhx_doctrine_reform_add_old_secondary_10y",
    "zhx_doctrine_reform_add_old_secondary_5y",
    "zhx_doctrine_reform_add_target_secondary_10y",
    "zhx_doctrine_reform_formal_adopt_target",
    "zhx_doctrine_reform_settle_transition",
    "zhx_doctrine_reform_force_new_school",
    "zhx_doctrine_reform_restore_old_school",
    "zhx_doctrine_reform_finish_forced_extension",
    "zhx_doctrine_reform_reconcile",
    "zhx_doctrine_reform_clear_process_state",
    "zhx_doctrine_reform_clear_all_state",
    "zhx_doctrine_reform_yearly_tick",
    "zhx_doctrine_reform_after_initial_foundation",
)

REQUIRED_MODIFIERS = (
    "zhx_doctrine_reform_cultivation",
    "zhx_doctrine_reform_conflict",
    "zhx_doctrine_reform_forced_extension",
    "zhx_doctrine_reform_new_order",
    "zhx_doctrine_reform_reversal",
    "zhx_doctrine_reform_indecision",
    "zhx_doctrine_reform_cooldown",
)

EXPECTED_EVENT_IDS = {
    "1",
    "2",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "50",
    "90",
    "91",
    "100",
    "101",
    "200",
    "201",
    "202",
    "210",
    "300",
    "301",
    "400",
}

MODIFIER_VALUES = {
    "zhx_doctrine_reform_cultivation": {
        "global_unrest": 1,
        "stability_cost_modifier": 0.15,
        "advisor_cost": 0.15,
    },
    "zhx_doctrine_reform_conflict": {
        "global_unrest": 2,
        "stability_cost_modifier": 0.25,
        "governing_capacity_modifier": -0.10,
        "global_tax_modifier": -0.10,
        "manpower_recovery_speed": -0.10,
    },
    "zhx_doctrine_reform_new_order": {
        "global_unrest": -1,
        "stability_cost_modifier": -0.10,
        "reform_progress_growth": 0.15,
        "advisor_cost": -0.10,
    },
    "zhx_doctrine_reform_reversal": {
        "all_power_cost": 0.05,
        "reform_progress_growth": -0.25,
        "diplomatic_reputation": -1,
        "stability_cost_modifier": 0.20,
    },
    "zhx_doctrine_reform_indecision": {
        "stability_cost_modifier": 0.10,
        "diplomatic_reputation": -1,
    },
}

VISIBLE_LOCALISATION_KEYS = {
    "zhx_begin_doctrine_reform_title",
    "zhx_begin_doctrine_reform_desc",
    "zhx_cancel_doctrine_reform_title",
    "zhx_cancel_doctrine_reform_desc",
    *REQUIRED_MODIFIERS,
    *(f"{modifier}_desc" for modifier in REQUIRED_MODIFIERS),
    "zhx_opinion_abandoned_our_doctrine",
    "zhx_opinion_joined_our_doctrine",
    *(f"zhx_doctrine_reform.{event_id}.t" for event_id in ("1", "2", "91", "101", "201", "202", "210", "301")),
    *(f"zhx_doctrine_reform.{event_id}.d" for event_id in ("1", "2", "91", "101", "201", "202", "210", "301")),
    *(f"zhx_doctrine_reform.confirm_{school}.t" for school in SCHOOLS),
    *(f"zhx_doctrine_reform.confirm_{school}.d" for school in SCHOOLS),
    *(f"zhx_doctrine_reform.confirm_{school}.a" for school in SCHOOLS),
    *(f"zhx_doctrine_reform_secondary_{school}" for school in SCHOOLS),
    *(f"zhx_doctrine_reform_secondary_{school}_desc" for school in SCHOOLS),
}

TEMP_FIXTURE_PATTERNS = (
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"zhxtest",
        r"zhxrt\d*",
        r"fatest",
        r"motest",
        r"zzz?_zhx.*runtime.*test",
        r"doctrine_reform_runtime_test",
        r"namespace\s*=\s*zhx_.*test",
    )
)


class Contract:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def strip_comments(text: str) -> str:
    """Remove # comments without treating # inside a quoted string as syntax."""

    lines: list[str] = []
    for line in text.splitlines():
        quoted = False
        escaped = False
        kept: list[str] = []
        for char in line:
            if escaped:
                kept.append(char)
                escaped = False
                continue
            if char == "\\" and quoted:
                kept.append(char)
                escaped = True
                continue
            if char == '"':
                quoted = not quoted
                kept.append(char)
                continue
            if char == "#" and not quoted:
                break
            kept.append(char)
        lines.append("".join(kept))
    return "\n".join(lines)


def balanced_braces(text: str) -> bool:
    depth = 0
    quoted = False
    escaped = False
    for char in strip_comments(text):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quoted:
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
        elif not quoted and char == "{":
            depth += 1
        elif not quoted and char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not quoted


def assignment_blocks(text: str, key: str) -> list[str]:
    """Return every ``key = { ... }`` block, including the outer braces."""

    clean = strip_comments(text)
    pattern = re.compile(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{")
    blocks: list[str] = []
    for match in pattern.finditer(clean):
        start = clean.find("{", match.start())
        depth = 0
        quoted = False
        escaped = False
        for index in range(start, len(clean)):
            char = clean[index]
            if escaped:
                escaped = False
                continue
            if char == "\\" and quoted:
                escaped = True
                continue
            if char == '"':
                quoted = not quoted
                continue
            if quoted:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(clean[match.start() : index + 1])
                    break
    return blocks


def event_block(text: str, event_id: str) -> str | None:
    for block in assignment_blocks(text, "country_event"):
        if re.search(
            rf"(?m)^\s*id\s*=\s*zhx_doctrine_reform\.{re.escape(event_id)}\s*$",
            block,
        ):
            return block
    return None


def named_block(text: str, block_key: str, name: str) -> str | None:
    matches = [
        block
        for block in assignment_blocks(text, block_key)
        if re.search(
            rf"(?m)^\s*name\s*=\s*\"?{re.escape(name)}\"?\s*$", block
        )
    ]
    return matches[0] if len(matches) == 1 else None


def numbers_for_key(block: str, key: str) -> list[float]:
    return [
        float(value)
        for value in re.findall(
            rf"\b{re.escape(key)}\s*=\s*(-?(?:\d+(?:\.\d*)?|\.\d+))\b",
            block,
        )
    ]


def has_number(block: str, key: str, expected: float) -> bool:
    return any(abs(value - expected) < 1e-9 for value in numbers_for_key(block, key))


def has_duration(block: str, days: int) -> bool:
    return has_number(block, "duration", float(days))


def require_single_block(
    contract: Contract, text: str, key: str, label: str
) -> str:
    blocks = assignment_blocks(text, key)
    contract.require(
        len(blocks) == 1,
        f"{label}: expected exactly one `{key}` block, found {len(blocks)}",
    )
    return blocks[0] if blocks else ""


def require_tokens(
    contract: Contract, text: str, tokens: Iterable[str], label: str
) -> None:
    for token in tokens:
        contract.require(token in text, f"{label}: missing `{token}`")


def loaded_script_text(*, excluding: Iterable[Path] = ()) -> str:
    """Concatenate loaded plaintext scripts, excluding generated reform owners."""

    excluded = {path.resolve() for path in excluding}
    chunks: list[str] = []
    for directory in (MOD / "common", MOD / "decisions", MOD / "events"):
        for path in sorted(directory.rglob("*.txt")):
            if path.resolve() in excluded:
                continue
            try:
                chunks.append(strip_comments(read_text(path)))
            except UnicodeDecodeError:
                continue
    return "\n".join(chunks)


def check_required_files(contract: Contract) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    missing = [path for path in REQUIRED_PATHS if not path.is_file()]
    for path in missing:
        contract.errors.append(
            f"missing required reform contract file: {path.relative_to(ROOT)}"
        )
    if missing:
        return texts
    for path in REQUIRED_PATHS:
        text = read_text(path)
        texts[path] = text
        contract.require(
            balanced_braces(text),
            f"unbalanced braces or quote in {path.relative_to(ROOT)}",
        )
    return texts


def check_declared_blocks(contract: Contract, texts: dict[Path, str]) -> None:
    trigger_text = texts[TRIGGER_PATH]
    effect_text = texts[EFFECT_PATH]
    modifier_text = texts[MODIFIER_PATH]
    decision_text = texts[DECISION_PATH]

    for key in REQUIRED_TRIGGERS:
        require_single_block(contract, trigger_text, key, "reform triggers")
    for key in REQUIRED_EFFECTS:
        require_single_block(contract, effect_text, key, "reform effects")
    for key in REQUIRED_MODIFIERS:
        require_single_block(contract, modifier_text, key, "reform modifiers")
    for key in ("zhx_begin_doctrine_reform", "zhx_cancel_doctrine_reform"):
        require_single_block(contract, decision_text, key, "reform decisions")


def check_six_school_state(contract: Contract, texts: dict[Path, str]) -> None:
    trigger_text = texts[TRIGGER_PATH]
    effect_text = texts[EFFECT_PATH]
    event_text = texts[EVENT_PATH]

    clear_process_block = require_single_block(
        contract,
        effect_text,
        "zhx_doctrine_reform_clear_process_state",
        "reform state cleanup",
    )
    clear_target_block = require_single_block(
        contract,
        effect_text,
        "zhx_doctrine_reform_clear_target_flags",
        "target-state cleanup",
    )
    clear_old_block = require_single_block(
        contract,
        effect_text,
        "zhx_doctrine_reform_clear_old_flags",
        "old-school cleanup",
    )
    require_tokens(
        contract,
        clear_process_block,
        (
            "zhx_doctrine_reform_clear_target_flags",
            "zhx_doctrine_reform_clear_old_flags",
        ),
        "reform state cleanup",
    )
    formal_block = require_single_block(
        contract,
        effect_text,
        "zhx_doctrine_reform_formal_adopt_target",
        "formal adoption",
    )

    for index, school in enumerate(SCHOOLS, start=10):
        invited_root_now = require_single_block(
            contract,
            trigger_text,
            f"zhx_doctrine_reform_has_{school}_invited_root_now",
            f"live invited root {school}",
        )
        require_tokens(
            contract,
            invited_root_now,
            (
                f"has_country_modifier = {INVITED_MODIFIERS[school]}",
                f"has_country_flag = {GUEST_CONTRACT_ACTIVE_FLAG}",
                f"has_country_flag = {GUEST_CONTRACT_FLAGS[school]}",
            ),
            f"live invited root {school}",
        )
        invited_modifiers = set(
            re.findall(r"\bhas_country_modifier\s*=\s*([A-Za-z0-9_]+)", invited_root_now)
        )
        contract_flags = set(
            re.findall(r"\bhas_country_flag\s*=\s*([A-Za-z0-9_]+)", invited_root_now)
        )
        contract.require(
            invited_modifiers == {INVITED_MODIFIERS[school]},
            f"live invited root {school}: must require exactly the matching invited modifier",
        )
        contract.require(
            contract_flags
            == {GUEST_CONTRACT_ACTIVE_FLAG, GUEST_CONTRACT_FLAGS[school]},
            f"live invited root {school}: must require the active contract and matching school flags",
        )

        invited_root_with_five_years = require_single_block(
            contract,
            trigger_text,
            f"zhx_doctrine_reform_has_{school}_invited_root_with_five_years",
            f"five-year invited root {school}",
        )
        require_tokens(
            contract,
            invited_root_with_five_years,
            (f"zhx_doctrine_reform_has_{school}_invited_root_now = yes",),
            f"five-year invited root {school}",
        )
        five_year_window_pattern = re.compile(
            rf"NOT\s*=\s*\{{\s*had_country_flag\s*=\s*\{{\s*"
            rf"flag\s*=\s*{re.escape(GUEST_CONTRACT_ACTIVE_FLAG)}\s+"
            rf"days\s*=\s*{GUEST_CONTRACT_REFORM_WINDOW_DAYS}\s*"
            rf"\}}\s*\}}",
            re.DOTALL,
        )
        contract.require(
            five_year_window_pattern.search(invited_root_with_five_years) is not None,
            f"five-year invited root {school}: must require the active contract to be younger than "
            f"{GUEST_CONTRACT_REFORM_WINDOW_DAYS} days",
        )
        contract.require(
            invited_root_with_five_years.count("had_country_flag") == 1,
            f"five-year invited root {school}: expected exactly one contract-age check",
        )

        root_now = require_single_block(
            contract,
            trigger_text,
            f"zhx_doctrine_reform_has_{school}_root_now",
            f"current root {school}",
        )
        require_tokens(
            contract,
            root_now,
            (
                f"zhx_doctrine_reform_has_{school}_invited_root_now = yes",
                f"zhx_doctrine_reform_has_active_{school}_academy_root = yes",
            ),
            f"current root {school}",
        )
        contract.require(
            INVITED_MODIFIERS[school] not in root_now
            and f"zhx_doctrine_reform_root_invited_{school}" not in root_now,
            f"current root {school}: must consume the live invited-root interface, not raw or snapshot state",
        )

        target_trigger = require_single_block(
            contract,
            trigger_text,
            f"zhx_doctrine_reform_can_target_{school}",
            f"target gate {school}",
        )
        require_tokens(
            contract,
            target_trigger,
            (
                "zhx_doctrine_reform_can_begin = yes",
                f"zhx_doctrine_reform_has_{school}_invited_root_with_five_years = yes",
                f"zhx_doctrine_reform_has_active_{school}_academy_root = yes",
                "zhx_guest_school_has_active_contract = yes",
                GUEST_CONTRACT_FLAGS[school],
                MAIN_FLAGS[school],
            ),
            f"target gate {school}",
        )
        contract.require(
            f"zhx_doctrine_reform_has_{school}_root_now" not in target_trigger,
            f"target gate {school}: generic root bypasses the five-year invited-contract window",
        )
        contract.require(
            target_trigger.count("NOT = { zhx_guest_school_has_active_contract = yes }")
            == 1
            and target_trigger.count(
                f"has_country_flag = {GUEST_CONTRACT_FLAGS[school]}"
            )
            == 1,
            f"target gate {school}: an unrelated active guest must block reform",
        )
        contract.require(
            re.search(
                rf"NOT\s*=\s*\{{[^{{}}]*has_country_flag\s*=\s*{re.escape(MAIN_FLAGS[school])}",
                target_trigger,
                re.DOTALL,
            )
            is not None,
            f"target gate {school}: current main school is not explicitly excluded",
        )

        retained_root = require_single_block(
            contract,
            trigger_text,
            f"zhx_doctrine_reform_target_{school}_retains_root",
            f"retained root {school}",
        )
        require_tokens(
            contract,
            retained_root,
            (
                f"has_country_flag = {TARGET_FLAGS[school]}",
                f"zhx_doctrine_reform_has_{school}_invited_root_now = yes",
                f"zhx_doctrine_reform_has_active_{school}_academy_root = yes",
            ),
            f"retained root {school}",
        )
        contract.require(
            f"zhx_doctrine_reform_root_invited_{school}" not in retained_root,
            f"retained root {school}: must not permanently trust the begin-time invited snapshot",
        )
        contract.require(
            "had_country_flag" not in retained_root,
            f"retained root {school}: contract age is not a substitute for a currently live root",
        )

        begin_block = require_single_block(
            contract,
            effect_text,
            f"zhx_doctrine_reform_begin_{school}",
            f"begin effect {school}",
        )
        require_tokens(
            contract,
            begin_block,
            (
                "zhx_doctrine_reform_clear_process_state",
                TARGET_FLAGS[school],
                "zhx_doctrine_reform_cultivation",
                f"zhx_doctrine_reform_has_{school}_invited_root_now = yes",
                f"zhx_doctrine_reform_root_invited_{school}",
                *MAIN_FLAGS.values(),
                *OLD_FLAGS.values(),
            ),
            f"begin effect {school}",
        )
        snapshot_pattern = re.compile(
            rf"if\s*=\s*\{{\s*limit\s*=\s*\{{\s*"
            rf"zhx_doctrine_reform_has_{school}_invited_root_now\s*=\s*yes\s*"
            rf"\}}\s*set_country_flag\s*=\s*"
            rf"zhx_doctrine_reform_root_invited_{school}\s*\}}",
            re.DOTALL,
        )
        contract.require(
            snapshot_pattern.search(begin_block) is not None,
            f"begin effect {school}: invited snapshot must be gated by the live matching contract",
        )
        contract.require(
            INVITED_MODIFIERS[school] not in begin_block,
            f"begin effect {school}: must not snapshot from the raw invited modifier alone",
        )
        contract.require(
            begin_block.count(f"set_country_flag = zhx_doctrine_reform_root_invited_{school}")
            == 1,
            f"begin effect {school}: expected exactly one matching invited-root snapshot write",
        )
        contract.require(
            has_duration(begin_block, 1825),
            f"begin effect {school}: cultivation must last 1825 days (5 years)",
        )
        contract.require(
            not any(
                other_flag in begin_block
                for other, other_flag in TARGET_FLAGS.items()
                if other != school
            ),
            f"begin effect {school}: writes another target-school flag",
        )

        event = event_block(event_text, str(index))
        contract.require(event is not None, f"missing confirmation event .{index}")
        if event:
            require_tokens(
                contract,
                event,
                (f"zhx_doctrine_reform_begin_{school}",),
                f"confirmation event .{index}",
            )

        require_tokens(
            contract,
            clear_target_block,
            (f"clr_country_flag = {TARGET_FLAGS[school]}",),
            "target-state cleanup",
        )
        require_tokens(
            contract,
            clear_old_block,
            (f"clr_country_flag = {OLD_FLAGS[school]}",),
            "old-school cleanup",
        )
        require_tokens(
            contract,
            formal_block,
            (TARGET_FLAGS[school], MAIN_FLAGS[school]),
            "formal adoption",
        )

    first_page = event_block(event_text, "1") or ""
    second_page = event_block(event_text, "2") or ""
    for event_id in ("10", "11", "12"):
        require_tokens(
            contract,
            first_page,
            (f"zhx_doctrine_reform.{event_id}",),
            "first target page",
        )
    for event_id in ("13", "14", "15"):
        require_tokens(
            contract,
            second_page,
            (f"zhx_doctrine_reform.{event_id}",),
            "second target page",
        )
    require_tokens(
        contract,
        first_page,
        ("zhx_doctrine_reform.2",),
        "first target page navigation",
    )
    require_tokens(
        contract,
        second_page,
        ("zhx_doctrine_reform.1",),
        "second target page navigation",
    )


def check_events(contract: Contract, texts: dict[Path, str]) -> None:
    text = texts[EVENT_PATH]
    contract.require(
        re.search(r"(?m)^\s*namespace\s*=\s*zhx_doctrine_reform\s*$", text)
        is not None,
        "reform events: missing `namespace = zhx_doctrine_reform`",
    )
    ids = re.findall(
        r"(?m)^\s*id\s*=\s*zhx_doctrine_reform\.([A-Za-z0-9_]+)\s*$", text
    )
    contract.require(
        len(ids) == len(set(ids)),
        f"reform events: duplicate IDs present ({ids})",
    )
    contract.require(
        set(ids) == EXPECTED_EVENT_IDS,
        "reform events: expected IDs "
        f"{sorted(EXPECTED_EVENT_IDS)}, found {sorted(set(ids))}",
    )

    failure = event_block(text, "210") or ""
    require_tokens(
        contract,
        failure,
        (
            "zhx_doctrine_reform_force_new_school",
            "zhx_doctrine_reform_restore_old_school",
        ),
        "failure event .210",
    )
    contract.require(
        failure.count("option = {") == 2,
        "failure event .210 must expose exactly the two substantive exits",
    )

    for event_id, effect in (
        ("90", "zhx_doctrine_reform_reconcile"),
        ("100", "zhx_doctrine_reform_formal_adopt_target"),
        ("200", "zhx_doctrine_reform_settle_transition"),
        ("300", "zhx_doctrine_reform_finish_forced_extension"),
    ):
        block = event_block(text, event_id) or ""
        require_tokens(contract, block, (effect,), f"event .{event_id}")


def check_modifier_numbers(contract: Contract, texts: dict[Path, str]) -> None:
    text = texts[MODIFIER_PATH]
    for modifier, expected_values in MODIFIER_VALUES.items():
        block = require_single_block(
            contract, text, modifier, f"modifier values for {modifier}"
        )
        for key, expected in expected_values.items():
            contract.require(
                has_number(block, key, expected),
                f"{modifier}: expected `{key} = {expected:g}`",
            )


def check_secondary_presentation(contract: Contract, texts: dict[Path, str]) -> None:
    static_modifiers = texts[SECONDARY_MODIFIER_PATH]
    effects = texts[EFFECT_PATH]
    events = texts[EVENT_PATH]
    custom_gui = texts[RELIGION_CUSTOM_GUI_PATH]

    metadata_keys = {
        "religion_sub_modifier",
        "religion",
        "is_scholar_modifier",
    }
    for school in SCHOOLS:
        modifier = f"zhx_doctrine_reform_secondary_{school}"
        block = require_single_block(
            contract,
            static_modifiers,
            modifier,
            f"secondary presentation modifier {school}",
        )
        assignments = re.findall(
            r"(?m)^\s*([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_.-]+)\s*$",
            block,
        )
        contract.require(
            {key for key, _ in assignments} == metadata_keys
            and all(value == "yes" for _, value in assignments),
            f"{modifier}: must be a metadata-only native religion sub-modifier",
        )

        icon_blocks = [
            candidate
            for candidate in assignment_blocks(custom_gui, "custom_icon")
            if re.search(
                rf"(?m)^\s*name\s*=\s*zhx_invited_school_{school}_icon\s*$",
                candidate,
            )
        ]
        contract.require(
            len(icon_blocks) == 1,
            f"secondary presentation {school}: expected one custom icon binding",
        )
        if icon_blocks:
            require_tokens(
                contract,
                icon_blocks[0],
                (
                    f"zhx_{school}_invited_scholar_modifier",
                    modifier,
                    "OR =",
                ),
                f"secondary presentation icon {school}",
            )

    for effect_name, duration in (
        ("zhx_doctrine_reform_add_old_secondary_10y", 3650),
        ("zhx_doctrine_reform_add_old_secondary_5y", 1825),
        ("zhx_doctrine_reform_add_target_secondary_10y", 3650),
    ):
        block = require_single_block(
            contract, effects, effect_name, f"secondary routing {effect_name}"
        )
        require_tokens(
            contract,
            block,
            tuple(f"zhx_doctrine_reform_secondary_{school}" for school in SCHOOLS),
            f"secondary routing {effect_name}",
        )
        contract.require(
            block.count(f"duration = {duration}") == len(SCHOOLS),
            f"{effect_name}: every school branch must use duration {duration}",
        )

    for owner, required_route in (
        ("zhx_doctrine_reform_formal_adopt_target", "zhx_doctrine_reform_add_old_secondary_10y"),
        ("zhx_doctrine_reform_force_new_school", "zhx_doctrine_reform_add_old_secondary_5y"),
        ("zhx_doctrine_reform_restore_old_school", "zhx_doctrine_reform_add_target_secondary_10y"),
    ):
        block = require_single_block(contract, effects, owner, owner)
        require_tokens(contract, block, (required_route,), owner)

    for owner in (
        "zhx_doctrine_reform_clear_all_state",
        "zhx_doctrine_reform_finish_success",
        "zhx_doctrine_reform_finish_without_reward",
        "zhx_doctrine_reform_finish_forced_extension",
        "zhx_doctrine_reform_reconcile",
    ):
        block = require_single_block(contract, effects, owner, owner)
        require_tokens(
            contract,
            block,
            ("zhx_doctrine_reform_clear_secondary_modifiers",),
            owner,
        )

    expiry_event = event_block(events, "400") or ""
    require_tokens(
        contract,
        expiry_event,
        ("zhx_doctrine_reform_clear_secondary_modifiers",),
        "secondary expiry event .400",
    )


def check_timing_and_outcomes(contract: Contract, texts: dict[Path, str]) -> None:
    effects = texts[EFFECT_PATH]
    events = texts[EVENT_PATH]

    formal = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_formal_adopt_target",
        "formal adoption",
    )
    require_tokens(
        contract,
        formal,
        ("zhx_doctrine_reform_conflict", "zhx_doctrine_practice"),
        "formal adoption",
    )
    contract.require(
        has_duration(formal, 3650),
        "formal adoption: conflict must last 3650 days (10 years)",
    )
    contract.require(
        has_number(formal, "value", 15),
        "formal adoption: new-school practice must be set to 15",
    )
    contract.require(
        has_number(formal, "add_stability", -1),
        "formal adoption: missing one-time stability -1",
    )
    contract.require(
        has_number(formal, "add_prestige", -25),
        "formal adoption: missing one-time prestige -25",
    )

    settlement = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_settle_transition",
        "transition settlement",
    )
    require_tokens(
        contract,
        settlement,
        (
            "zhx_doctrine_practice",
            "zhx_doctrine_reform_finish_success",
            "zhx_doctrine_reform_finish_without_reward",
            "zhx_doctrine_reform.210",
        ),
        "transition settlement",
    )
    contract.require(
        re.search(
            r"check_variable\s*=\s*\{[^{}]*which\s*=\s*zhx_doctrine_practice[^{}]*value\s*=\s*50",
            settlement,
            re.DOTALL,
        )
        is not None,
        "transition settlement: success does not require practice >= 50",
    )
    contract.require(
        re.search(r"\bstability\s*=\s*1\b", settlement) is not None,
        "transition settlement: success does not require stability >= 1",
    )
    contract.require(
        re.search(
            r"check_variable\s*=\s*\{[^{}]*which\s*=\s*zhx_doctrine_practice[^{}]*value\s*=\s*25",
            settlement,
            re.DOTALL,
        )
        is not None
        and re.search(r"\belse\s*=\s*\{", settlement) is not None,
        "transition settlement: failure must be the fallback below the >=25 branch",
    )

    success = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_finish_success",
        "successful settlement",
    )
    require_tokens(
        contract,
        success,
        ("zhx_doctrine_reform_new_order", "zhx_doctrine_reform_cooldown"),
        "successful settlement",
    )
    contract.require(
        success.count("duration = 3650") >= 2,
        "successful settlement: reward and cooldown must each last 10 years",
    )
    ordinary = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_finish_without_reward",
        "ordinary settlement",
    )
    contract.require(
        has_duration(ordinary, 3650),
        "ordinary settlement: cooldown must last 10 years",
    )
    contract.require(
        "zhx_doctrine_reform_new_order" not in ordinary,
        "ordinary settlement must not grant the success reward",
    )

    force = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_force_new_school",
        "force-new-school exit",
    )
    require_tokens(
        contract,
        force,
        ("zhx_doctrine_reform_forced_extension",),
        "force-new-school exit",
    )
    contract.require(
        has_duration(force, 1825),
        "force-new-school exit: extension must last 1825 days (5 years)",
    )
    contract.require(
        "zhx_doctrine_reform_new_order" not in force,
        "force-new-school exit must not grant the success reward",
    )

    finish_force = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_finish_forced_extension",
        "forced-extension settlement",
    )
    contract.require(
        has_duration(finish_force, 3650),
        "forced-extension settlement: post-extension cooldown must last 10 years",
    )
    contract.require(
        "zhx_doctrine_reform_new_order" not in finish_force,
        "forced-extension settlement must never grant the success reward",
    )

    restore = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_restore_old_school",
        "restore-old-school exit",
    )
    require_tokens(
        contract,
        restore,
        ("zhx_doctrine_reform_reversal", "zhx_doctrine_reform_cooldown"),
        "restore-old-school exit",
    )
    contract.require(
        has_number(restore, "value", 25),
        "restore-old-school exit: restored practice must be 25",
    )
    contract.require(
        has_duration(restore, 3650),
        "restore-old-school exit: reversal penalty must last 10 years",
    )
    contract.require(
        has_duration(restore, 5475),
        "restore-old-school exit: reform cooldown must last 15 years",
    )
    contract.require(
        not has_number(restore, "add_stability", -1),
        "restore-old-school exit must not charge an extra stability point",
    )

    cancel = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_cancel",
        "cultivation cancellation",
    )
    require_tokens(
        contract,
        cancel,
        ("zhx_doctrine_reform_indecision", "zhx_doctrine_reform_cooldown"),
        "cultivation cancellation",
    )
    contract.require(
        has_duration(cancel, 1825),
        "cultivation cancellation: indecision must last 5 years",
    )
    contract.require(
        has_duration(cancel, 3650),
        "cultivation cancellation: restart lock must last 10 years",
    )


def check_invitation_lock(contract: Contract, texts: dict[Path, str]) -> None:
    trigger_text = texts[TRIGGER_PATH]
    invitation = require_single_block(
        contract,
        trigger_text,
        "zhx_doctrine_reform_invitation_locked",
        "invitation lock",
    )
    require_tokens(
        contract,
        invitation,
        (
            "zhx_doctrine_reform_is_active",
            "zhx_doctrine_reform_has_reversal_secondary",
        ),
        "invitation lock",
    )
    for forbidden in (
        "zhx_doctrine_reform_cooldown",
        "zhx_doctrine_reform_new_order",
        "zhx_doctrine_reform_reversal",
        "zhx_doctrine_reform_indecision",
    ):
        contract.require(
            forbidden not in invitation,
            f"invitation lock incorrectly follows `{forbidden}` after transition",
        )

    for path in (RELIGION_PATH, RELIGION_BUILDER_PATH):
        text = texts[path]
        contract.require(
            "zhx_guest_school_may_invite = yes" in text,
            f"{path.relative_to(ROOT)}: native invitation gate is not wired to the guest-school wrapper",
        )

    guest_gate = require_single_block(
        contract,
        texts[GUEST_SCHOOL_TRIGGER_PATH],
        "zhx_guest_school_may_invite",
        "guest-school invitation gate",
    )
    contract.require(
        re.search(
            r"NOT\s*=\s*\{\s*zhx_doctrine_reform_invitation_locked\s*=\s*yes\s*\}",
            guest_gate,
            re.DOTALL,
        )
        is not None,
        "guest-school invitation gate must reject countries locked by doctrine reform",
    )


def check_tianxia_contract(contract: Contract, texts: dict[Path, str]) -> None:
    reform_triggers = texts[TRIGGER_PATH]
    reform_effects = texts[EFFECT_PATH]
    reform_events = texts[EVENT_PATH]
    tianxia_triggers = texts[TIANXIA_TRIGGER_PATH]

    filing = require_single_block(
        contract,
        reform_triggers,
        "zhx_doctrine_reform_may_file_tianxia_proposal",
        "Tianxia filing gate",
    )
    require_tokens(
        contract,
        filing,
        ("zhx_doctrine_reform_is_cultivating",),
        "Tianxia filing gate",
    )
    contract.require(
        re.search(
            r"NOT\s*=\s*\{[^{}]*zhx_doctrine_reform_is_cultivating\s*=\s*yes",
            filing,
            re.DOTALL,
        )
        is not None,
        "Tianxia filing gate must reject cultivating countries",
    )
    contract.require(
        "zhx_doctrine_reform_may_file_tianxia_proposal" in tianxia_triggers,
        "Tianxia petition trigger does not consume the reform filing gate",
    )

    combined = reform_effects + "\n" + reform_events
    contract.require(
        "zhx_doctrine_reform_hook_cancel_pending_tianxia_petition" in combined,
        "reform/Tianxia boundary: missing pending-petition cancellation hook",
    )
    blocked = require_single_block(
        contract,
        reform_triggers,
        "zhx_doctrine_reform_formal_adoption_blocked",
        "formal-adoption Tianxia gate",
    )
    contract.require(
        "zhx_tianxia_council_is_busy" in blocked,
        "formal adoption must consume the authoritative Tianxia busy trigger directly",
    )
    contract.require(
        "zhx_doctrine_reform_external_tianxia_debate_open" not in combined + reform_triggers,
        "obsolete external Tianxia-open mirror remains in reform state",
    )

    external = loaded_script_text(
        excluding=(TRIGGER_PATH, EFFECT_PATH, EVENT_PATH)
    )
    contract.require(
        "has_country_flag = zhx_doctrine_reform_hook_cancel_pending_tianxia_petition"
        in external,
        "no loaded integration consumer handles the pending-petition cancellation hook",
    )
    contract.require(
        "zhx_doctrine_reform_acknowledge_integration_hooks" in external,
        "no loaded integration consumer acknowledges reform output hooks",
    )


def check_cleanup_and_pulses(contract: Contract, texts: dict[Path, str]) -> None:
    effects = texts[EFFECT_PATH]
    doctrine_effects = texts[DOCTRINE_EFFECT_PATH]

    clear_all = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_clear_all_state",
        "religion-change cleanup",
    )
    clear_process = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_clear_process_state",
        "process cleanup",
    )
    clear_targets = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_clear_target_flags",
        "target cleanup",
    )
    clear_old = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_clear_old_flags",
        "old-school cleanup",
    )
    require_tokens(
        contract,
        clear_all,
        ("zhx_doctrine_reform_clear_process_state",),
        "religion-change cleanup",
    )
    require_tokens(
        contract,
        clear_process,
        ("zhx_doctrine_reform_clear_target_flags", "zhx_doctrine_reform_clear_old_flags"),
        "process cleanup",
    )
    for school in SCHOOLS:
        require_tokens(
            contract,
            clear_targets,
            (TARGET_FLAGS[school],),
            "target cleanup",
        )
        require_tokens(
            contract,
            clear_old,
            (OLD_FLAGS[school],),
            "old-school cleanup",
        )
    for modifier in (
        "zhx_doctrine_reform_cultivation",
        "zhx_doctrine_reform_conflict",
        "zhx_doctrine_reform_forced_extension",
    ):
        require_tokens(contract, clear_process, (modifier,), "process cleanup")
    for modifier in (
        "zhx_doctrine_reform_new_order",
        "zhx_doctrine_reform_reversal",
        "zhx_doctrine_reform_indecision",
        "zhx_doctrine_reform_cooldown",
    ):
        require_tokens(
            contract,
            clear_all,
            (modifier,),
            "religion-change cleanup",
        )

    doctrine_clear = require_single_block(
        contract,
        doctrine_effects,
        "zhx_clear_doctrine_system",
        "authoritative doctrine cleanup",
    )
    doctrine_yearly = require_single_block(
        contract,
        doctrine_effects,
        "zhx_yearly_doctrine_tick",
        "authoritative doctrine yearly tick",
    )
    contract.require(
        "zhx_doctrine_reform_clear_all_state" in doctrine_clear,
        "authoritative religion-change path does not call reform cleanup",
    )
    contract.require(
        "zhx_doctrine_reform_yearly_tick" in doctrine_yearly,
        "loaded yearly path does not call the reform yearly tick",
    )


def check_academy_protection(contract: Contract, texts: dict[Path, str]) -> None:
    for path in (
        ACADEMY_TRIGGER_PATH,
        ACADEMY_LIFECYCLE_TRIGGER_PATH,
    ):
        text = texts[path]
        for school in SCHOOLS:
            token = f"zhx_doctrine_reform_protects_{school}_academies"
            contract.require(
                token in text,
                f"{path.relative_to(ROOT)}: old-school academy protection does not consume `{token}`",
            )
    builder = texts[ACADEMY_LIFECYCLE_BUILDER_PATH]
    contract.require(
        "zhx_doctrine_reform_protects_{school}_academies" in builder,
        "academy lifecycle builder does not template the old-school protection interface",
    )


def check_ai_safety(contract: Contract, texts: dict[Path, str]) -> None:
    triggers = texts[TRIGGER_PATH]
    effects = texts[EFFECT_PATH]
    events = texts[EVENT_PATH]
    gate = require_single_block(
        contract,
        triggers,
        "zhx_doctrine_reform_ai_may_attempt",
        "AI reform gate",
    )
    require_tokens(
        contract,
        gate,
        (
            "ai = yes",
            "is_year = 1475",
            "zhx_doctrine_reform_can_begin",
            "stability = 1",
            "has_any_disaster = no",
            "is_bankrupt = no",
            "zhx_doctrine_reform_ai_low_practice_years",
            "value = 5",
            *(
                f"zhx_doctrine_reform_has_{school}_invited_root_with_five_years"
                for school in SCHOOLS
            ),
        ),
        "AI reform gate",
    )
    contract.require(
        not any(modifier in gate for modifier in INVITED_MODIFIERS.values()),
        "AI reform gate must not use raw invited modifiers without active matching contracts",
    )
    yearly = require_single_block(
        contract,
        effects,
        "zhx_doctrine_reform_yearly_tick",
        "AI annual reform tick",
    )
    require_tokens(
        contract,
        yearly,
        ("chance = 8", "zhx_doctrine_reform.50"),
        "AI annual reform tick",
    )
    dispatcher = event_block(events, "50") or ""
    for school in SCHOOLS:
        require_tokens(
            contract,
            dispatcher,
            (
                f"zhx_doctrine_reform_has_{school}_invited_root_with_five_years",
                f"zhx_doctrine_reform_begin_{school}",
            ),
            "AI target dispatcher",
        )
    contract.require(
        not any(modifier in dispatcher for modifier in INVITED_MODIFIERS.values()),
        "AI target dispatcher must not use raw invited modifiers without active matching contracts",
    )


def check_legacy_bypass(contract: Contract, texts: dict[Path, str]) -> None:
    decisions = texts[LEGACY_DECISION_PATH]
    doctrine_effects = texts[DOCTRINE_EFFECT_PATH]

    initial_decisions = assignment_blocks(
        decisions, "zhx_convene_hundred_schools_debate"
    )
    contract.require(
        len(initial_decisions) == 1,
        "there must be exactly one unified first-doctrine decision",
    )
    contract.require(
        not assignment_blocks(decisions, "zhx_convene_later_schools_debate"),
        "legacy Dao/Bing/Zongheng decision still exists as a bypass",
    )
    contract.require(
        "id = zhx_doctrine_expansion.1" not in decisions,
        "legacy later-school event remains reachable from a production decision",
    )
    for block in initial_decisions:
        contract.require(
            "zhx_has_doctrine" in block and "NOT =" in block,
            "unified first-doctrine decision is not restricted to countries without a doctrine",
        )
    contract.require(
        not re.search(
            r"change_variable\s*=\s*\{[^{}]*which\s*=\s*zhx_doctrine_practice[^{}]*value\s*=\s*5",
            doctrine_effects,
            re.DOTALL,
        ),
        "legacy click-to-reaffirm +5 practice path still exists",
    )
    for school in SCHOOLS:
        adoption = require_single_block(
            contract,
            doctrine_effects,
            f"zhx_adopt_{school}_doctrine",
            f"first-adoption effect {school}",
        )
        contract.require(
            "zhx_has_doctrine" in adoption and "NOT =" in adoption,
            f"first-adoption effect {school} can still overwrite an existing main school",
        )


def check_opinions(contract: Contract, texts: dict[Path, str]) -> None:
    opinions = texts[OPINION_PATH]
    expected = {
        "zhx_opinion_abandoned_our_doctrine": (-20, 2),
        "zhx_opinion_joined_our_doctrine": (10, 1),
    }
    for key, (value, decay) in expected.items():
        block = require_single_block(contract, opinions, key, "reform opinions")
        contract.require(
            has_number(block, "opinion", value),
            f"{key}: expected opinion {value:+g}",
        )
        contract.require(
            has_number(block, "yearly_decay", decay),
            f"{key}: expected yearly decay {decay:g} (a 10-year tail)",
        )


def check_localisation(contract: Contract, texts: dict[Path, str]) -> None:
    localisation = texts[LOCALISATION_PATH]
    keys = set(re.findall(r"(?m)^\s*([A-Za-z0-9_.-]+):\d+\s+", localisation))
    for key in sorted(VISIBLE_LOCALISATION_KEYS):
        contract.require(key in keys, f"reform localisation: missing `{key}`")


def check_no_test_fixtures(contract: Contract) -> None:
    production_roots = (
        MOD / "common",
        MOD / "decisions",
        MOD / "events",
        MOD / "interface",
        MOD / "localisation_source",
    )
    for root in production_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = str(path.relative_to(MOD))
            path_match = any(pattern.search(relative) for pattern in TEMP_FIXTURE_PATTERNS)
            text_match = False
            if path.suffix.lower() in {".txt", ".gui", ".gfx"}:
                try:
                    text = read_text(path)
                except UnicodeDecodeError:
                    text = ""
                text_match = any(
                    pattern.search(strip_comments(text))
                    for pattern in TEMP_FIXTURE_PATTERNS
                )
            contract.require(
                not (path_match or text_match),
                f"temporary runtime fixture remains in production tree: {relative}",
            )


def main() -> int:
    contract = Contract()
    texts = check_required_files(contract)
    if len(texts) != len(REQUIRED_PATHS):
        print("Doctrine reform static validation FAILED:")
        for error in contract.errors:
            print(f" - {error}")
        print(
            "The reform implementation is absent or incomplete; create all seven "
            "reform files before treating this validator as a passing gate."
        )
        return 1

    check_declared_blocks(contract, texts)
    check_six_school_state(contract, texts)
    check_events(contract, texts)
    check_modifier_numbers(contract, texts)
    check_secondary_presentation(contract, texts)
    check_timing_and_outcomes(contract, texts)
    check_invitation_lock(contract, texts)
    check_tianxia_contract(contract, texts)
    check_cleanup_and_pulses(contract, texts)
    check_academy_protection(contract, texts)
    check_ai_safety(contract, texts)
    check_legacy_bypass(contract, texts)
    check_opinions(contract, texts)
    check_localisation(contract, texts)
    check_no_test_fixtures(contract)

    if contract.errors:
        print("Doctrine reform static validation FAILED:")
        for error in contract.errors:
            print(f" - {error}")
        return 1

    print(
        "Doctrine reform static validation PASSED: six targets, mutually "
        "exclusive state, 5/10-year lifecycle, outcome gates, invitation and "
        "Tianxia boundaries, religion cleanup, legacy-bypass closure, "
        "localisation, and fixture hygiene are present."
    )
    print(
        "Runtime status is intentionally not inferred; execute "
        "planning/religion_reform/runtime_test_matrix.md for in-game evidence."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
