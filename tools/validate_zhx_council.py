#!/usr/bin/env python3
"""Static contracts for the shared Tianxia Council state machine.

This validator intentionally describes the target architecture, not the
pre-refactor implementation.  It reports every unmet contract in one run so
the council kernel, the incident wrapper, the debate wrapper, and the GUI can
be migrated incrementally without hiding later failures behind the first one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

SYSTEM_EFFECTS = MOD / "common/scripted_effects/zhx_system_effects.txt"
SYSTEM_TRIGGERS = MOD / "common/scripted_triggers/zhx_system_triggers.txt"
SYSTEM_EVENTS = MOD / "events/zhx_system_events.txt"
DEBATE_EFFECTS = MOD / "common/scripted_effects/zhx_tianxia_debate_effects.txt"
DEBATE_TRIGGERS = MOD / "common/scripted_triggers/zhx_tianxia_debate_triggers.txt"
DEBATE_EVENTS = MOD / "events/zhx_tianxia_debate_events.txt"
INTERFACE = MOD / "interface/topbar.gui"
CUSTOM_GUI = MOD / "common/custom_gui/zhx_tianxia_gui.txt"

CORE_PATHS = (
    SYSTEM_EFFECTS,
    SYSTEM_TRIGGERS,
    SYSTEM_EVENTS,
    DEBATE_EFFECTS,
    DEBATE_TRIGGERS,
    DEBATE_EVENTS,
    INTERFACE,
    CUSTOM_GUI,
)

OPEN_EFFECT = "zhx_open_tianxia_council"
FINISH_EFFECT = "zhx_finish_tianxia_council"
RESOLVE_EFFECT = "zhx_resolve_tianxia_council"
RECOUNT_EFFECT = "zhx_recount_tianxia_council_ballot"
RESET_EFFECT = "zhx_reset_tianxia_council_ballot"
VALID_CANDIDATES_TRIGGER = "zhx_council_has_valid_candidates"
DEADLINE_EVENT = "zhx_system.23"
DEADLINE_FLAG = "zhx_council_deadline_scheduled"
RESULT_READY_FLAG = "zhx_council_result_ready"

PHASE_FLAGS = (
    "zhx_council_phase_preparing",
    "zhx_council_phase_ballot_open",
    "zhx_council_phase_resolving",
)
KIND_FLAGS = (
    "zhx_council_kind_ritual_breakdown",
    "zhx_council_kind_debate",
)
VOTE_FLAGS = tuple(f"zhx_council_vote_{choice}" for choice in "abc")
VOTE_COUNTS = tuple(f"zhx_council_vote_{choice}_count" for choice in "abc")
TURNOUT_COUNTS = (
    "zhx_council_eligible_country_count",
    "zhx_council_voted_country_count",
    "zhx_council_unvoted_country_count",
    "zhx_council_eligible_ai_count",
    "zhx_council_voted_ai_count",
    "zhx_council_unvoted_ai_count",
)
PUBLIC_BALLOT_VARIABLES = VOTE_COUNTS + TURNOUT_COUNTS
CAST_EFFECTS = tuple(f"zhx_cast_tianxia_council_vote_{choice}" for choice in "abc")
SCHOOLS = ("ru", "fa", "mo", "dao", "bing", "zongheng")
CANDIDATE_A_FLAGS = tuple(f"zhx_council_candidate_a_{school}" for school in SCHOOLS)
CANDIDATE_B_FLAGS = tuple(f"zhx_council_candidate_b_{school}" for school in SCHOOLS)
CANDIDATE_FLAGS = CANDIDATE_A_FLAGS + CANDIDATE_B_FLAGS

# These identifiers represented the two parallel ballots.  The shared council
# migration is complete only when none survives in scripts, localisation,
# documentation, generators, or older validators.
RETIRED_IDENTIFIERS = (
    "zhx_ritual_breakdown_incident_active",
    "zhx_tianxia_debate_active",
    "zhx_incident_vote_support",
    "zhx_incident_vote_oppose",
    "zhx_incident_vote_abstain",
    "zhx_tianxia_debate_vote_a",
    "zhx_tianxia_debate_vote_b",
    "zhx_tianxia_debate_vote_plural",
    "zhx_incident_support_count",
    "zhx_incident_oppose_count",
    "zhx_incident_vote_balance",
    "zhx_tianxia_debate_a_count",
    "zhx_tianxia_debate_b_count",
    "zhx_tianxia_debate_plural_count",
    "zhx_tianxia_debate_a_vs_b",
    "zhx_tianxia_debate_a_vs_plural",
    "zhx_tianxia_debate_b_vs_a",
    "zhx_tianxia_debate_b_vs_plural",
    "zhx_tianxia_debate_pair_ru_fa",
    "zhx_tianxia_debate_pair_ru_mo",
    "zhx_tianxia_debate_pair_fa_mo",
    "zhx_clear_current_ritual_breakdown_vote",
    "zhx_cast_ritual_breakdown_support_vote",
    "zhx_cast_ritual_breakdown_oppose_vote",
    "zhx_cast_ritual_breakdown_abstain_vote",
    "zhx_reset_ritual_breakdown_incident_votes",
    "zhx_recount_ritual_breakdown_incident_votes",
    "zhx_clear_current_tianxia_debate_vote",
    "zhx_cast_tianxia_debate_vote_a",
    "zhx_cast_tianxia_debate_vote_b",
    "zhx_cast_tianxia_debate_vote_plural",
    "zhx_reset_tianxia_debate_ballot",
    "zhx_recount_tianxia_debate_ballot",
)

TEXT_SUFFIXES = {
    ".txt",
    ".gui",
    ".gfx",
    ".yml",
    ".md",
    ".py",
    ".json",
    ".csv",
    ".asset",
}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)

    def check(self, condition: bool, message: str) -> bool:
        if not condition:
            self.errors.append(message)
        return condition

    def finish(self) -> None:
        if self.errors:
            print(f"Shared Tianxia Council static contract: FAIL ({len(self.errors)})")
            for index, error in enumerate(self.errors, 1):
                print(f"  {index:02d}. {error}")
            raise SystemExit(1)

        print("Shared Tianxia Council static contract: PASS")
        print("  One phase family; one issue-kind family; one A/B/C ballot")
        print("  Deadline: zhx_system.23 after 365 days")
        print("  Public turnout: eligible/voted/unvoted countries and AI countries")
        print("  Public counters are always mutated on event_target:zhx_tianzi")
        print("  Debate candidate slots: 6 schools in A and 6 schools in B")
        print("  GUI: current council on the left; orthodoxy on the right")


@dataclass(frozen=True)
class Block:
    path: Path
    name: str
    text: str


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_text(path: Path, report: Report) -> str:
    if not report.check(path.is_file(), f"missing required file: {relative(path)}"):
        return ""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        report.errors.append(f"cannot decode {relative(path)} as UTF-8: {exc}")
        return ""


def mask_clausewitz(text: str) -> str:
    """Mask comments and strings while preserving offsets and newlines."""

    output = list(text)
    in_string = False
    in_comment = False
    escaped = False
    for index, char in enumerate(text):
        if in_comment:
            if char == "\n":
                in_comment = False
            else:
                output[index] = " "
            continue
        if in_string:
            if char == "\n":
                # Keep line boundaries useful even for a malformed string.
                pass
            else:
                output[index] = " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            output[index] = " "
            in_comment = True
        elif char == '"':
            output[index] = " "
            in_string = True
    return "".join(output)


def validate_braces(path: Path, text: str, report: Report) -> None:
    masked = mask_clausewitz(text)
    depth = 0
    for index, char in enumerate(masked):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                line = text.count("\n", 0, index) + 1
                report.errors.append(
                    f"{relative(path)}:{line}: closing brace without opener"
                )
                return
    report.check(depth == 0, f"{relative(path)}: unbalanced braces ({depth})")


def closing_brace(text: str, opening: int) -> int | None:
    masked = mask_clausewitz(text)
    depth = 0
    for index in range(opening, len(masked)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def named_definition(path: Path, text: str, name: str) -> Block | None:
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", mask_clausewitz(text))
    if match is None:
        return None
    opening = mask_clausewitz(text).find("{", match.start(), match.end())
    ending = closing_brace(text, opening)
    if ending is None:
        return None
    return Block(path=path, name=name, text=text[opening + 1 : ending])


def definition_index(paths: Iterable[Path], texts: dict[Path, str]) -> dict[str, list[Block]]:
    index: dict[str, list[Block]] = {}
    definition_pattern = re.compile(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{")
    for path in paths:
        text = texts.get(path, "")
        masked = mask_clausewitz(text)
        for match in definition_pattern.finditer(masked):
            name = match.group(1)
            opening = masked.find("{", match.start(), match.end())
            ending = closing_brace(text, opening)
            if ending is None:
                continue
            index.setdefault(name, []).append(
                Block(path=path, name=name, text=text[opening + 1 : ending])
            )
    return index


def iter_keyword_blocks(text: str, keyword: str) -> Iterator[str]:
    masked = mask_clausewitz(text)
    pattern = re.compile(rf"(?m)^\s*{re.escape(keyword)}\s*=\s*\{{")
    for match in pattern.finditer(masked):
        opening = masked.find("{", match.start(), match.end())
        ending = closing_brace(text, opening)
        if ending is not None:
            yield text[opening + 1 : ending]


def direct_child_blocks(text: str, keyword: str) -> list[str]:
    masked = mask_clausewitz(text)
    matches = []
    pattern = re.compile(rf"(?m)^\s*{re.escape(keyword)}\s*=\s*\{{")
    for match in pattern.finditer(masked):
        prefix = masked[: match.start()]
        if prefix.count("{") != prefix.count("}"):
            continue
        opening = masked.find("{", match.start(), match.end())
        ending = closing_brace(text, opening)
        if ending is not None:
            matches.append(text[opening + 1 : ending])
    return matches


def event_index(paths: Iterable[Path], texts: dict[Path, str]) -> dict[str, list[Block]]:
    index: dict[str, list[Block]] = {}
    for path in paths:
        text = texts.get(path, "")
        masked = mask_clausewitz(text)
        # Event calls use the same `country_event = {}` spelling as event
        # definitions.  Only column-zero blocks are definitions.
        definition_pattern = re.compile(r"(?m)^country_event\s*=\s*\{")
        for definition in definition_pattern.finditer(masked):
            opening = masked.find("{", definition.start(), definition.end())
            ending = closing_brace(text, opening)
            if ending is None:
                continue
            body = text[opening + 1 : ending]
            match = re.search(r"(?m)^\s*id\s*=\s*([A-Za-z0-9_.]+)\s*$", body)
            if match:
                event_id = match.group(1)
                index.setdefault(event_id, []).append(
                    Block(path=path, name=event_id, text=body)
                )
    return index


def occurrences(text: str, token: str) -> int:
    return len(re.findall(rf"\b{re.escape(token)}\b", mask_clausewitz(text)))


def operation_count(text: str, operation: str, flag: str) -> int:
    return len(
        re.findall(
            rf"\b{re.escape(operation)}\s*=\s*{re.escape(flag)}\b",
            mask_clausewitz(text),
        )
    )


def variable_operation_count(text: str, operation: str, variable: str) -> int:
    """Count ``operation = { which = variable ... }`` mutations."""

    return len(
        re.findall(
            rf"\b{re.escape(operation)}\s*=\s*\{{[^{{}}]*"
            rf"\bwhich\s*=\s*{re.escape(variable)}\b",
            mask_clausewitz(text),
            re.DOTALL,
        )
    )


def iter_repository_text() -> Iterator[tuple[Path, str]]:
    this_file = Path(__file__).resolve()
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.resolve() == this_file:
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            yield path, path.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue


def token_locations(path: Path, text: str, token: str) -> list[str]:
    locations = []
    for match in re.finditer(re.escape(token), text):
        line = text.count("\n", 0, match.start()) + 1
        locations.append(f"{relative(path)}:{line}")
    return locations


def validate_retired_identifiers(report: Report) -> None:
    repository_text = list(iter_repository_text())
    for token in RETIRED_IDENTIFIERS:
        found: list[str] = []
        for path, text in repository_text:
            found.extend(token_locations(path, text, token))
        if found:
            sample = ", ".join(found[:6])
            remainder = f" (+{len(found) - 6} more)" if len(found) > 6 else ""
            report.errors.append(
                f"retired parallel-ballot identifier remains: {token}: "
                f"{sample}{remainder}"
            )


def require_unique_definition(
    name: str, index: dict[str, list[Block]], report: Report, kind: str
) -> Block | None:
    blocks = index.get(name, [])
    if not report.check(
        len(blocks) == 1,
        f"expected exactly one {kind} definition `{name}`, found {len(blocks)}",
    ):
        return blocks[0] if blocks else None
    return blocks[0]


def effect_reaches_operation(
    text: str,
    operation: str,
    flag: str,
    effect_index: dict[str, list[Block]],
    seen: set[str] | None = None,
    depth: int = 0,
) -> bool:
    if operation_count(text, operation, flag) >= 1:
        return True
    if depth >= 3:
        return False
    seen = set() if seen is None else set(seen)
    for name in re.findall(r"\b([A-Za-z0-9_]+)\s*=\s*yes\b", mask_clausewitz(text)):
        if name in seen or len(effect_index.get(name, [])) != 1:
            continue
        seen.add(name)
        if effect_reaches_operation(
            effect_index[name][0].text,
            operation,
            flag,
            effect_index,
            seen,
            depth + 1,
        ):
            return True
    return False


def validate_state_families(
    script_text: str,
    effect_index: dict[str, list[Block]],
    report: Report,
) -> None:
    allowed = set(PHASE_FLAGS + KIND_FLAGS)
    discovered = set(
        re.findall(
            r"\bzhx_council_(?:active|phase_[a-z0-9_]+|kind_[a-z0-9_]+|"
            r"type_[a-z0-9_]+|issue_[a-z0-9_]+)\b",
            mask_clausewitz(script_text),
        )
    )
    unexpected = sorted(discovered - allowed)
    report.check(
        not unexpected,
        "parallel or unrecognised council active/phase/type state exists: "
        f"{unexpected}; use only the canonical phase_* and kind_* flags",
    )

    for flag in PHASE_FLAGS + KIND_FLAGS:
        report.check(
            operation_count(script_text, "set_country_flag", flag) >= 1,
            f"canonical state flag is never set: {flag}",
        )

    open_block = require_unique_definition(OPEN_EFFECT, effect_index, report, "effect")
    resolve_block = require_unique_definition(
        RESOLVE_EFFECT, effect_index, report, "effect"
    )
    finish_block = require_unique_definition(
        FINISH_EFFECT, effect_index, report, "effect"
    )

    if open_block:
        report.check(
            operation_count(open_block.text, "set_country_flag", PHASE_FLAGS[1]) == 1,
            f"`{OPEN_EFFECT}` must set {PHASE_FLAGS[1]} exactly once",
        )
        report.check(
            operation_count(script_text, "set_country_flag", PHASE_FLAGS[1]) == 1,
            f"{PHASE_FLAGS[1]} may only be set by `{OPEN_EFFECT}`",
        )
        report.check(
            operation_count(open_block.text, "set_country_flag", DEADLINE_FLAG) == 1,
            f"`{OPEN_EFFECT}` must set the stale-deadline sentry {DEADLINE_FLAG}",
        )
        report.check(
            operation_count(open_block.text, "clr_country_flag", PHASE_FLAGS[0]) >= 1,
            f"`{OPEN_EFFECT}` must leave preparing before opening the ballot",
        )
        report.check(
            operation_count(open_block.text, "clr_country_flag", RESULT_READY_FLAG) >= 1,
            f"`{OPEN_EFFECT}` must discard stale {RESULT_READY_FLAG} state",
        )

    if resolve_block:
        report.check(
            effect_reaches_operation(
                resolve_block.text,
                "clr_country_flag",
                PHASE_FLAGS[1],
                effect_index,
            ),
            f"`{RESOLVE_EFFECT}` must close the ballot phase before dispatch",
        )
        report.check(
            operation_count(resolve_block.text, "set_country_flag", PHASE_FLAGS[2]) == 1,
            f"`{RESOLVE_EFFECT}` must enter resolving exactly once",
        )
        report.check(
            operation_count(script_text, "set_country_flag", PHASE_FLAGS[2]) == 1,
            f"{PHASE_FLAGS[2]} may only be set by `{RESOLVE_EFFECT}`",
        )
        report.check(
            operation_count(resolve_block.text, "set_country_flag", RESULT_READY_FLAG) == 1,
            f"`{RESOLVE_EFFECT}` must freeze the ballot with {RESULT_READY_FLAG}",
        )
        report.check(
            "id = zhx_system.22" not in resolve_block.text
            and "id = zhx_debate.20" not in resolve_block.text,
            f"`{RESOLVE_EFFECT}` must not synchronously dispatch a visible result event",
        )

    if finish_block:
        for flag in PHASE_FLAGS + KIND_FLAGS:
            report.check(
                effect_reaches_operation(
                    finish_block.text,
                    "clr_country_flag",
                    flag,
                    effect_index,
                ),
                f"`{FINISH_EFFECT}` must clear canonical state flag {flag}",
            )
        report.check(
            operation_count(finish_block.text, "clr_country_flag", DEADLINE_FLAG) >= 1,
            f"`{FINISH_EFFECT}` must clear {DEADLINE_FLAG}",
        )
        report.check(
            operation_count(finish_block.text, "clr_country_flag", RESULT_READY_FLAG) >= 1,
            f"`{FINISH_EFFECT}` must clear {RESULT_READY_FLAG}",
        )
        report.check(
            f"{RESET_EFFECT} = yes" in finish_block.text,
            f"`{FINISH_EFFECT}` must call `{RESET_EFFECT}`",
        )


def validate_shared_ballot(
    script_text: str,
    effect_index: dict[str, list[Block]],
    report: Report,
) -> None:
    recount = require_unique_definition(RECOUNT_EFFECT, effect_index, report, "effect")
    reset = require_unique_definition(RESET_EFFECT, effect_index, report, "effect")

    for flag, count, cast_name in zip(VOTE_FLAGS, VOTE_COUNTS, CAST_EFFECTS):
        report.check(
            operation_count(script_text, "set_country_flag", flag) == 1,
            f"shared ballot must set {flag} in exactly one cast path",
        )
        report.check(
            operation_count(script_text, "clr_country_flag", flag) >= 1,
            f"shared ballot never clears {flag}",
        )
        report.check(
            count in script_text,
            f"missing shared live-count variable {count}",
        )
        cast = require_unique_definition(cast_name, effect_index, report, "effect")
        if cast:
            report.check(
                operation_count(cast.text, "set_country_flag", flag) == 1,
                f"`{cast_name}` must own the only set operation for {flag}",
            )
            report.check(
                f"{RECOUNT_EFFECT} = yes" in cast.text,
                f"`{cast_name}` must refresh the live A/B/C totals",
            )

    if recount:
        for flag, count in zip(VOTE_FLAGS, VOTE_COUNTS):
            report.check(
                flag in recount.text,
                f"`{RECOUNT_EFFECT}` does not scan ballot flag {flag}",
            )
            report.check(
                occurrences(recount.text, count) >= 2,
                f"`{RECOUNT_EFFECT}` must reset and increment {count}",
            )

    if reset:
        for flag, count in zip(VOTE_FLAGS, VOTE_COUNTS):
            report.check(
                effect_reaches_operation(
                    reset.text,
                    "clr_country_flag",
                    flag,
                    effect_index,
                ),
                f"`{RESET_EFFECT}` does not clear {flag}",
            )
            report.check(
                occurrences(reset.text, count) >= 1,
                f"`{RESET_EFFECT}` does not reset {count}",
            )

    resolve = effect_index.get(RESOLVE_EFFECT, [])
    if resolve:
        report.check(
            f"{RECOUNT_EFFECT} = yes" in resolve[0].text,
            f"`{RESOLVE_EFFECT}` must recount authoritative vote flags before results",
        )


def validate_public_turnout_and_counter_scope(
    effect_index: dict[str, list[Block]], report: Report
) -> None:
    """Keep AI ballots visible on the Tianzi-owned public scoreboard.

    A scripted effect called inside ``event_target:zhx_tianzi`` does not make
    ``ROOT`` become the Tianzi: ROOT remains the country which cast the vote.
    Mutating a public count through ROOT therefore creates one private count on
    each AI country and leaves the panel looking like only the player voted.
    """

    recount = require_unique_definition(RECOUNT_EFFECT, effect_index, report, "effect")
    reset = require_unique_definition(RESET_EFFECT, effect_index, report, "effect")
    if not recount or not reset:
        return

    tianzi_scopes = list(iter_keyword_blocks(recount.text, "event_target:zhx_tianzi"))
    tianzi_text = "\n".join(tianzi_scopes)
    report.check(
        bool(tianzi_scopes),
        f"`{RECOUNT_EFFECT}` has no explicit event_target:zhx_tianzi scope",
    )

    root_blocks = list(iter_keyword_blocks(recount.text, "ROOT"))
    for block in root_blocks:
        for variable in PUBLIC_BALLOT_VARIABLES:
            report.check(
                not any(
                    variable_operation_count(block, operation, variable)
                    for operation in ("set_variable", "change_variable", "subtract_variable")
                ),
                f"`{RECOUNT_EFFECT}` mutates public variable {variable} through ROOT; "
                "use event_target:zhx_tianzi explicitly",
            )

    for variable in PUBLIC_BALLOT_VARIABLES:
        report.check(
            occurrences(reset.text, variable) >= 1,
            f"`{RESET_EFFECT}` does not reset public turnout variable {variable}",
        )
        report.check(
            occurrences(recount.text, variable) >= 2,
            f"`{RECOUNT_EFFECT}` does not rebuild public turnout variable {variable}",
        )
        for operation in ("set_variable", "change_variable", "subtract_variable"):
            all_mutations = variable_operation_count(recount.text, operation, variable)
            scoped_mutations = variable_operation_count(tianzi_text, operation, variable)
            report.check(
                all_mutations == scoped_mutations,
                f"`{RECOUNT_EFFECT}` has {all_mutations - scoped_mutations} "
                f"unscoped {operation} mutation(s) for {variable}; every public "
                "counter mutation must be inside event_target:zhx_tianzi",
            )

    for variable in ("zhx_council_unvoted_country_count", "zhx_council_unvoted_ai_count"):
        report.check(
            variable_operation_count(recount.text, "subtract_variable", variable) == 1,
            f"`{RECOUNT_EFFECT}` must derive {variable} as eligible minus voted",
        )
    report.check(
        occurrences(recount.text, "ai") >= 2
        and bool(re.search(r"\bai\s*=\s*yes\b", mask_clausewitz(recount.text))),
        f"`{RECOUNT_EFFECT}` does not separately count eligible and voted AI countries",
    )


def validate_deadline(
    script_text: str,
    effect_index: dict[str, list[Block]],
    trigger_index: dict[str, list[Block]],
    events: dict[str, list[Block]],
    report: Report,
) -> None:
    open_blocks = effect_index.get(OPEN_EFFECT, [])
    schedule_pattern = re.compile(
        r"country_event\s*=\s*\{\s*id\s*=\s*zhx_system\.23\s+days\s*=\s*365\s*\}",
        re.DOTALL,
    )
    all_schedules = schedule_pattern.findall(mask_clausewitz(script_text))
    report.check(
        len(all_schedules) == 1,
        f"expected one `{DEADLINE_EVENT}` 365-day schedule, found {len(all_schedules)}",
    )
    if open_blocks:
        report.check(
            len(schedule_pattern.findall(mask_clausewitz(open_blocks[0].text))) == 1,
            f"the sole 365-day `{DEADLINE_EVENT}` schedule must live in `{OPEN_EFFECT}`",
        )

    for stale_id in ("zhx_system.22", "zhx_debate.20"):
        stale_pattern = re.compile(
            rf"country_event\s*=\s*\{{\s*id\s*=\s*{re.escape(stale_id)}\s+"
            r"days\s*=\s*365",
            re.DOTALL,
        )
        report.check(
            stale_pattern.search(mask_clausewitz(script_text)) is None,
            f"legacy result event {stale_id} is still scheduled directly for 365 days",
        )

    deadline_blocks = events.get(DEADLINE_EVENT, [])
    if not report.check(
        len(deadline_blocks) == 1,
        f"expected exactly one deadline event `{DEADLINE_EVENT}`, found {len(deadline_blocks)}",
    ):
        return
    body = deadline_blocks[0].text
    for token, explanation in (
        ("zhx_is_tianzi = yes", "restrict itself to the Tianzi anchor"),
        (DEADLINE_FLAG, "check the scheduled-deadline sentry"),
        (f"{RESOLVE_EFFECT} = yes", "call the shared resolve dispatcher"),
    ):
        report.check(token in body, f"`{DEADLINE_EVENT}` must {explanation}: missing {token}")

    valid_kind = trigger_index.get("zhx_council_has_valid_kind", [])
    checks_kind_directly = all(kind in body for kind in KIND_FLAGS)
    checks_kind_via_trigger = bool(valid_kind) and "zhx_council_has_valid_kind = yes" in body
    report.check(
        checks_kind_directly or checks_kind_via_trigger,
        f"`{DEADLINE_EVENT}` must reject a stale deadline without a valid council kind",
    )
    for kind, result_id in zip(KIND_FLAGS, ("zhx_system.22", "zhx_debate.20")):
        report.check(
            kind in body,
            f"`{DEADLINE_EVENT}` does not dispatch council kind {kind}",
        )
        delayed = re.compile(
            rf"country_event\s*=\s*\{{\s*id\s*=\s*{re.escape(result_id)}\s+"
            r"days\s*=\s*1\s*\}",
            re.DOTALL,
        )
        report.check(
            delayed.search(mask_clausewitz(body)) is not None,
            f"`{DEADLINE_EVENT}` must dispatch {result_id} on the next day",
        )


def validate_candidates(
    script_text: str,
    effect_index: dict[str, list[Block]],
    trigger_index: dict[str, list[Block]],
    report: Report,
) -> None:
    for flag in CANDIDATE_FLAGS:
        report.check(
            operation_count(script_text, "set_country_flag", flag) >= 1,
            f"candidate slot flag has no selectable setter: {flag}",
        )
        report.check(
            operation_count(script_text, "clr_country_flag", flag) >= 1,
            f"candidate slot flag is never cleared: {flag}",
        )

    valid = require_unique_definition(
        VALID_CANDIDATES_TRIGGER, trigger_index, report, "trigger"
    )
    if valid:
        calc_blocks = list(iter_keyword_blocks(valid.text, "calc_true_if"))
        a_blocks = [
            block
            for block in calc_blocks
            if all(flag in block for flag in CANDIDATE_A_FLAGS)
            and not any(flag in block for flag in CANDIDATE_B_FLAGS)
        ]
        b_blocks = [
            block
            for block in calc_blocks
            if all(flag in block for flag in CANDIDATE_B_FLAGS)
            and not any(flag in block for flag in CANDIDATE_A_FLAGS)
        ]
        and_blocks = list(iter_keyword_blocks(valid.text, "AND"))
        calc_a_is_exact = any(
            re.search(r"\bamount\s*=\s*1\b", block) for block in a_blocks
        )
        calc_b_is_exact = any(
            re.search(r"\bamount\s*=\s*1\b", block) for block in b_blocks
        )
        explicit_a_is_exact = all(
            any(
                all(candidate in block for candidate in CANDIDATE_A_FLAGS)
                and b_flag in block
                for block in and_blocks
            )
            for b_flag in CANDIDATE_B_FLAGS
        )
        explicit_b_branches = [
            block
            for block in and_blocks
            if all(candidate in block for candidate in CANDIDATE_B_FLAGS)
        ]
        explicit_b_is_exact = len(explicit_b_branches) >= len(SCHOOLS)
        report.check(
            calc_a_is_exact or explicit_a_is_exact,
            f"`{VALID_CANDIDATES_TRIGGER}` must require exactly one A-slot school",
        )
        report.check(
            calc_b_is_exact or explicit_b_is_exact,
            f"`{VALID_CANDIDATES_TRIGGER}` must require exactly one B-slot school",
        )

        for school, a_flag, b_flag in zip(
            SCHOOLS, CANDIDATE_A_FLAGS, CANDIDATE_B_FLAGS
        ):
            report.check(
                any(a_flag in block and b_flag in block for block in and_blocks),
                f"`{VALID_CANDIDATES_TRIGGER}` does not reject {school} in both A and B",
            )
        report.check(
            "NOT" in valid.text,
            f"`{VALID_CANDIDATES_TRIGGER}` must negate same-school A/B collisions",
        )

    debate_begin = effect_index.get("zhx_begin_tianxia_debate_issue", [])
    guarded_in_begin = bool(debate_begin) and all(
        token in debate_begin[0].text
        for token in (f"{VALID_CANDIDATES_TRIGGER} = yes", f"{OPEN_EFFECT} = yes")
    )
    open_blocks = effect_index.get(OPEN_EFFECT, [])
    guarded_in_open = bool(open_blocks) and all(
        token in open_blocks[0].text
        for token in (KIND_FLAGS[1], f"{VALID_CANDIDATES_TRIGGER} = yes")
    )
    report.check(
        guarded_in_begin or guarded_in_open,
        "debate must validate candidate A/B immediately before shared open; "
        "ritual-breakdown council remains candidate-free",
    )


def effect_reaches_finish(
    text: str,
    effect_index: dict[str, list[Block]],
    seen: set[str] | None = None,
    depth: int = 0,
) -> bool:
    if f"{FINISH_EFFECT} = yes" in text:
        return True
    if depth >= 3:
        return False
    seen = set() if seen is None else set(seen)
    for name in re.findall(r"\b([A-Za-z0-9_]+)\s*=\s*yes\b", mask_clausewitz(text)):
        if name in seen or name not in effect_index or len(effect_index[name]) != 1:
            continue
        seen.add(name)
        if effect_reaches_finish(effect_index[name][0].text, effect_index, seen, depth + 1):
            return True
    return False


def validate_result_paths(
    events: dict[str, list[Block]],
    effect_index: dict[str, list[Block]],
    report: Report,
) -> None:
    for event_id, kind in zip(
        ("zhx_system.22", "zhx_debate.20"),
        KIND_FLAGS,
    ):
        blocks = events.get(event_id, [])
        if not report.check(
            len(blocks) == 1,
            f"expected exactly one issue-specific result event {event_id}, found {len(blocks)}",
        ):
            continue
        for token in (PHASE_FLAGS[2], kind, RESULT_READY_FLAG):
            report.check(
                token in blocks[0].text,
                f"result event {event_id} must require frozen state token {token}",
            )
        options = direct_child_blocks(blocks[0].text, "option")
        if not report.check(options, f"result event {event_id} has no final option path"):
            continue
        for index, option in enumerate(options, 1):
            report.check(
                effect_reaches_finish(option, effect_index),
                f"result event {event_id} option {index} does not reach `{FINISH_EFFECT}`",
            )


def gui_objects(text: str) -> dict[str, list[str]]:
    objects: dict[str, list[str]] = {}
    for keyword in (
        "instantTextBoxType",
        "textBoxType",
        "guiButtonType",
        "iconType",
        "windowType",
        "custom_text_box",
        "custom_button",
        "custom_icon",
        "custom_window",
    ):
        for body in iter_keyword_blocks(text, keyword):
            match = re.search(r'(?m)^\s*name\s*=\s*"?([A-Za-z0-9_]+)"?\s*$', body)
            if match:
                objects.setdefault(match.group(1), []).append(body)
    return objects


def gui_x(body: str) -> int | None:
    match = re.search(r"position\s*=\s*\{\s*x\s*=\s*(-?\d+)", body, re.DOTALL)
    return int(match.group(1)) if match else None


def localization_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for path in sorted((MOD / "localisation_source").glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        for key, value in re.findall(r'(?m)^\s*([^\s:#]+):\d+\s+"(.*)"\s*$', text):
            values[key] = value
    return values


def header_localization_key(body: str) -> str | None:
    match = re.search(r'(?m)^\s*text\s*=\s*"([A-Za-z0-9_.]+)"\s*$', body)
    return match.group(1) if match else None


def validate_gui(interface_text: str, custom_text: str, report: Report) -> None:
    interface_objects = gui_objects(interface_text)
    custom_objects = gui_objects(custom_text)
    values = localization_values()

    topbar_windows = interface_objects.get("zhx_tianxia_topbar_window", [])
    topbar_bindings = custom_objects.get("zhx_tianxia_topbar_window", [])
    open_controls = interface_objects.get("zhx_tianxia_open_button", [])
    open_bindings = custom_objects.get("zhx_tianxia_open_button", [])
    panel_windows = interface_objects.get("zhx_tianxia_window", [])
    panel_bindings = custom_objects.get("zhx_tianxia_window", [])
    report.check(
        len(topbar_windows) == len(topbar_bindings) == 1,
        "Tianxia needs one scripted lower-right topbar window and one binding",
    )
    report.check(
        len(open_controls) == len(open_bindings) == 1,
        "Tianxia needs one scripted topbar open button and one binding",
    )
    report.check(
        len(panel_windows) == len(panel_bindings) == 1,
        "Tianxia panel must exist exactly once under topbar.gui",
    )
    if topbar_windows:
        report.check(
            re.search(r'orientation\s*=\s*"?LOWER_RIGHT"?', topbar_windows[0], re.I)
            is not None,
            "Tianxia topbar entry is not anchored to LOWER_RIGHT",
        )
    if open_controls:
        report.check(
            'quadTextureSprite = "GFX_zhx_tianxia_topbar_button"' in open_controls[0]
            and "scripted = yes" in open_controls[0],
            "Tianxia topbar entry is not the independent scripted round button",
        )
    for name in ("zhx_tianxia_topbar_window", "zhx_tianxia_open_button", "zhx_tianxia_window"):
        for body in custom_objects.get(name, []):
            report.check(
                "zhx_can_see_tianxia_gui = yes" in body,
                f"{name} is visible before China or the Far East is discovered",
            )
    if open_bindings:
        report.check(
            "set_country_flag = zhx_tianxia_gui_visible" in open_bindings[0]
            and "zhx_build_gui_roster = yes" in open_bindings[0],
            "Tianxia topbar button does not open the panel and refresh its roster",
        )
    close_bindings = custom_objects.get("zhx_gui_close_button", [])
    report.check(
        len(close_bindings) == 1
        and "clr_country_flag = zhx_tianxia_gui_visible" in close_bindings[0],
        "Tianxia close button does not clear the topbar panel visibility flag",
    )

    left_header = interface_objects.get("zhx_gui_council_header", [])
    right_header = interface_objects.get("zhx_gui_debate_header", [])
    report.check(
        len(left_header) == 1,
        "GUI left column needs one static `zhx_gui_council_header`",
    )
    report.check(
        len(right_header) == 1,
        "GUI right column needs one static `zhx_gui_debate_header` for orthodoxy",
    )
    if len(left_header) == 1 and len(right_header) == 1:
        left_x = gui_x(left_header[0])
        right_x = gui_x(right_header[0])
        report.check(
            left_x is not None and right_x is not None and left_x < right_x,
            "GUI columns are reversed or unpositioned: council must be left of orthodoxy",
        )
        left_key = header_localization_key(left_header[0])
        right_key = header_localization_key(right_header[0])
        report.check(
            bool(left_key and "公议" in values.get(left_key, "")),
            "left council header localization must visibly contain `公议`",
        )
        report.check(
            bool(right_key and "显学" in values.get(right_key, "")),
            "right orthodoxy header localization must visibly contain `显学`",
        )

    left_bindings = {
        name: bodies
        for name, bodies in custom_objects.items()
        if name.startswith("zhx_gui_council_")
    }
    report.check(
        len(left_bindings) >= 4,
        "left current-council column needs at least four scripted bindings "
        "(idle/type/counts/voter state or controls)",
    )
    for semantic in ("idle", "ritual", "debate", "count"):
        report.check(
            any(semantic in name for name in left_bindings),
            f"left current-council GUI has no `{semantic}` binding",
        )

    right_names = (
        "zhx_gui_debate_orthodoxy_none",
        *(f"zhx_gui_debate_orthodoxy_{school}" for school in SCHOOLS),
        "zhx_gui_debate_orthodoxy_plural",
    )
    for name in right_names:
        report.check(
            len(interface_objects.get(name, [])) == 1,
            f"right orthodoxy GUI is missing interface control `{name}`",
        )
        report.check(
            len(custom_objects.get(name, [])) == 1,
            f"right orthodoxy GUI is missing scripted binding `{name}`",
        )

    old_init = "zhx_tianxia_debate_initialised_v1"
    visible_bindings = dict(left_bindings)
    visible_bindings.update(
        {name: custom_objects.get(name, []) for name in right_names}
    )
    for name, bodies in visible_bindings.items():
        for body in bodies:
            report.check(
                old_init not in body,
                "base council/orthodoxy display is still hidden by the retired "
                f"debate initializer `{old_init}`: {name}",
            )

    legacy_right_votes = sorted(
        name for name in set(interface_objects) | set(custom_objects)
        if name.startswith("zhx_gui_debate_vote_")
    )
    report.check(
        not legacy_right_votes,
        f"right orthodoxy column still owns a second vote surface: {legacy_right_votes}",
    )
    legacy_left_incident = sorted(
        name for name in set(interface_objects) | set(custom_objects)
        if name.startswith("zhx_gui_incident_")
    )
    report.check(
        not legacy_left_incident,
        f"left column still uses incident-only controls instead of shared council: "
        f"{legacy_left_incident}",
    )


def main() -> None:
    report = Report()
    texts = {path: read_text(path, report) for path in CORE_PATHS}
    for path, text in texts.items():
        if text:
            validate_braces(path, text, report)

    effect_paths = tuple(sorted((MOD / "common/scripted_effects").glob("zhx_*.txt")))
    trigger_paths = tuple(sorted((MOD / "common/scripted_triggers").glob("zhx_*.txt")))
    event_paths = tuple(sorted((MOD / "events").glob("zhx_*.txt")))
    for path in effect_paths + trigger_paths + event_paths:
        if path not in texts:
            texts[path] = read_text(path, report)

    effect_index = definition_index(effect_paths, texts)
    trigger_index = definition_index(trigger_paths, texts)
    events = event_index(event_paths, texts)
    script_text = "\n".join(
        texts[path] for path in effect_paths + trigger_paths + event_paths
    )

    validate_retired_identifiers(report)
    validate_state_families(script_text, effect_index, report)
    validate_shared_ballot(script_text, effect_index, report)
    validate_public_turnout_and_counter_scope(effect_index, report)
    validate_deadline(script_text, effect_index, trigger_index, events, report)
    validate_candidates(script_text, effect_index, trigger_index, report)
    validate_result_paths(events, effect_index, report)
    validate_gui(texts[INTERFACE], texts[CUSTOM_GUI], report)
    report.finish()


if __name__ == "__main__":
    main()
