#!/usr/bin/env python3
"""Aggregate static contracts for the mature Six-Schools Great Debate.

The shared Tianxia Council validator owns the generic A/B/C ballot kernel.
This companion validator owns the layer above it: voluntary petitions,
six-school candidate selection, the fifteen-year orthodoxy term, AI entry,
and the proposal/orthodoxy presentation in the council view.

It deliberately reports every unmet contract in one run.  The checks are
structural rather than a Clausewitz interpreter, but they are strict enough
to prevent the prototype's two most damaging regressions:

* treating the first country at 70 practice as a formal proposal; and
* leaving an orthodoxy's international effects active after its term ends.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from validate_zhx_council import (
        Block,
        closing_brace,
        definition_index,
        event_index,
        iter_keyword_blocks,
        mask_clausewitz,
        operation_count,
        validate_braces,
    )
except ImportError:  # Supports `python -m tools.validate_zhx_mature_debate`.
    from tools.validate_zhx_council import (  # type: ignore[no-redef]
        Block,
        closing_brace,
        definition_index,
        event_index,
        iter_keyword_blocks,
        mask_clausewitz,
        operation_count,
        validate_braces,
    )


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

DEBATE_EFFECTS = MOD / "common/scripted_effects/zhx_tianxia_debate_effects.txt"
DEBATE_TRIGGERS = MOD / "common/scripted_triggers/zhx_tianxia_debate_triggers.txt"
COUNCIL_EFFECTS = MOD / "common/scripted_effects/zhx_council_effects.txt"
COUNCIL_TRIGGERS = MOD / "common/scripted_triggers/zhx_council_triggers.txt"
SYSTEM_EFFECTS = MOD / "common/scripted_effects/zhx_system_effects.txt"
DEBATE_EVENTS = MOD / "events/zhx_tianxia_debate_events.txt"
DOCTRINE_EVENTS = MOD / "events/zhx_doctrine_events.txt"
ON_ACTIONS = MOD / "common/on_actions/zhx_system_on_actions.txt"
MODIFIERS = MOD / "common/event_modifiers/zhx_tianxia_debate_modifiers.txt"
INTERFACE = MOD / "interface/countrydecisionsview.gui"
CUSTOM_GUI = MOD / "common/custom_gui/zhx_tianxia_gui.txt"

CORE_PATHS = (
    DEBATE_EFFECTS,
    DEBATE_TRIGGERS,
    COUNCIL_EFFECTS,
    COUNCIL_TRIGGERS,
    SYSTEM_EFFECTS,
    DEBATE_EVENTS,
    DOCTRINE_EVENTS,
    ON_ACTIONS,
    MODIFIERS,
    INTERFACE,
    CUSTOM_GUI,
)

SCHOOLS = ("ru", "fa", "mo", "dao", "bing", "zongheng")
DOCTRINE_FLAGS = tuple(f"zhx_doctrine_{school}" for school in SCHOOLS)
PETITION_MODIFIERS = tuple(f"zhx_debate_petition_{school}" for school in SCHOOLS)
PROPOSER_TARGETS = tuple(f"zhx_debate_proposer_{school}" for school in SCHOOLS)
ACTIVE_PETITION_TRIGGERS = tuple(
    f"zhx_tianxia_has_{school}_petition" for school in SCHOOLS
)
CANDIDATE_A_FLAGS = tuple(f"zhx_council_candidate_a_{school}" for school in SCHOOLS)
CANDIDATE_B_FLAGS = tuple(f"zhx_council_candidate_b_{school}" for school in SCHOOLS)
CANDIDATE_A_SETTERS = tuple(
    f"zhx_set_council_candidate_a_{school}" for school in SCHOOLS
)
CANDIDATE_B_SETTERS = tuple(
    f"zhx_set_council_candidate_b_{school}" for school in SCHOOLS
)
ORTHODOXY_FLAGS = tuple(f"zhx_tianxia_orthodoxy_{school}" for school in SCHOOLS)
ORTHODOXY_PLURAL = "zhx_tianxia_orthodoxy_plural"

PETITION_QUALIFICATION = "zhx_can_file_tianxia_debate_petition"
PETITION_ATTEMPT = "zhx_can_attempt_tianxia_debate_petition"
TWO_PETITIONS = "zhx_tianxia_has_two_petitions"
EXACTLY_TWO_PETITIONS = "zhx_tianxia_has_exactly_two_petitions"
THREE_PETITIONS = "zhx_tianxia_has_three_petitions"
AUTO_SELECT = "zhx_auto_select_tianxia_debate_candidates"
CLEAR_PETITIONS = "zhx_clear_tianxia_debate_petitions"
TRY_AI_PETITION = "zhx_ai_try_file_tianxia_debate_petition"
CAN_CONVENE = "zhx_can_convene_tianxia_debate"
RESOLVE_DEBATE = "zhx_resolve_tianxia_debate"
FINISH_DEBATE = "zhx_finish_tianxia_debate"
SHARED_BEGIN = "zhx_begin_tianxia_debate_council"
SHARED_RESOLVE = "zhx_resolve_tianxia_council"
SHARED_RECOUNT = "zhx_recount_tianxia_council_ballot"
SHARED_CLEAR_VOTE = "zhx_clear_current_tianxia_council_vote"

TERM_MODIFIER = "zhx_tianxia_orthodoxy_term"
RETIRED_COOLDOWN = "zhx_tianxia_debate_cooldown"
PETITION_DAYS = 1095
TERM_DAYS = 5475

SHARED_VOTES = tuple(f"zhx_council_vote_{choice}" for choice in "abc")
BONUS_FLAG = "zhx_council_vote_bonus"
CAST_A = "zhx_cast_tianxia_council_vote_a"
CAST_B = "zhx_cast_tianxia_council_vote_b"
CAST_C = "zhx_cast_tianxia_council_vote_c"


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)

    def check(self, condition: bool, message: str) -> bool:
        if not condition:
            self.errors.append(message)
        return condition

    def finish(self) -> None:
        if self.errors:
            print(f"Mature Six-Schools Debate static contract: FAIL ({len(self.errors)})")
            for index, error in enumerate(self.errors, 1):
                print(f"  {index:02d}. {error}")
            raise SystemExit(1)

        print("Mature Six-Schools Debate static contract: PASS")
        print("  Practice 70 grants petition eligibility, not an automatic proposal")
        print("  Six coexisting 1095-day petitions; 3 adopters plus a 50-practice endorser")
        print("  Exactly two petitions auto-select; three or more use two-step A/B selection")
        print("  Shared frozen A/B/C ballot; ties preserve Hundred-Schools pluralism")
        print("  Deadline freezes once, marks result-ready, then dispatches next-day results")
        print("  Orthodoxy effects and new debates are bounded by one 5475-day term")
        print("  GUI: current council left; orthodoxy and six petition states right")


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


def require_unique(
    index: dict[str, list[Block]], name: str, report: Report, kind: str
) -> Block | None:
    blocks = index.get(name, [])
    if not report.check(
        len(blocks) == 1,
        f"expected exactly one {kind} `{name}`, found {len(blocks)}",
    ):
        return None
    return blocks[0]


def occurrences(text: str, token: str) -> int:
    return len(re.findall(rf"\b{re.escape(token)}\b", mask_clausewitz(text)))


def has_practice_threshold(text: str, threshold: int) -> bool:
    return bool(
        re.search(
            rf"check_variable\s*=\s*\{{[^{{}}]*"
            rf"which\s*=\s*zhx_doctrine_practice\b[^{{}}]*"
            rf"value\s*=\s*{threshold}\b",
            mask_clausewitz(text),
            re.DOTALL,
        )
    )


def any_keyword_blocks(text: str, keyword: str) -> list[str]:
    """Return keyword blocks even when compact Clausewitz puts them inline."""

    masked = mask_clausewitz(text)
    blocks: list[str] = []
    pattern = re.compile(rf"\b{re.escape(keyword)}\s*=\s*\{{")
    for match in pattern.finditer(masked):
        opening = masked.find("{", match.start(), match.end())
        ending = closing_brace(text, opening)
        if ending is not None:
            blocks.append(text[opening + 1 : ending])
    return blocks


def modifier_additions(text: str, name: str) -> list[str]:
    additions: list[str] = []
    for body in any_keyword_blocks(text, "add_country_modifier"):
        if re.search(rf"\bname\s*=\s*{re.escape(name)}\b", mask_clausewitz(body)):
            additions.append(body)
    return additions


def effect_reaches_token(
    text: str,
    token: str,
    effects: dict[str, list[Block]],
    *,
    seen: set[str] | None = None,
    depth: int = 0,
) -> bool:
    """Follow simple `effect = yes` calls while looking for one token."""

    if token in mask_clausewitz(text):
        return True
    if depth >= 5:
        return False
    visited = set() if seen is None else set(seen)
    for name in re.findall(r"\b([A-Za-z0-9_]+)\s*=\s*yes\b", mask_clausewitz(text)):
        if name in visited or len(effects.get(name, [])) != 1:
            continue
        visited.add(name)
        if effect_reaches_token(
            effects[name][0].text,
            token,
            effects,
            seen=visited,
            depth=depth + 1,
        ):
            return True
    return False


def all_effect_texts(
    paths: Iterable[Path], texts: dict[Path, str]
) -> tuple[dict[str, list[Block]], str]:
    index = definition_index(paths, texts)
    return index, "\n".join(texts.get(path, "") for path in paths)


def validate_petition_qualification(
    trigger_index: dict[str, list[Block]], script_text: str, report: Report
) -> None:
    attempt = require_unique(
        trigger_index, PETITION_ATTEMPT, report, "scripted trigger"
    )
    qualification = require_unique(
        trigger_index, PETITION_QUALIFICATION, report, "scripted trigger"
    )
    if attempt:
        report.check(
            has_practice_threshold(attempt.text, 70),
            f"`{PETITION_ATTEMPT}` must make practice 70 the filing threshold",
        )
        for token in ("zhx_is_tianxia_polity", "zhx_is_lijiao_country"):
            report.check(
                token in attempt.text,
                f"`{PETITION_ATTEMPT}` is missing {token}",
            )
        report.check(
            TERM_MODIFIER in attempt.text and "NOT" in attempt.text,
            f"`{PETITION_ATTEMPT}` must close filing during the orthodoxy term",
        )
        report.check(
            "all_country" not in attempt.text and "any_country" not in attempt.text,
            f"`{PETITION_ATTEMPT}` must remain a cheap GUI gate without country iteration",
        )
    if qualification:
        report.check(
            PETITION_ATTEMPT in qualification.text,
            f"`{PETITION_QUALIFICATION}` must include the cheap 70-practice gate",
        )

    for school, trigger_name, modifier, target in zip(
        SCHOOLS,
        ACTIVE_PETITION_TRIGGERS,
        PETITION_MODIFIERS,
        PROPOSER_TARGETS,
    ):
        active = require_unique(trigger_index, trigger_name, report, "scripted trigger")
        if active:
            report.check(
                modifier in active.text and "has_country_modifier" in active.text,
                f"active {school} petition must read its independent timer {modifier}",
            )
            report.check(
                not has_practice_threshold(active.text, 70),
                f"active {school} petition still derives directly from practice 70",
            )

        retired = f"zhx_tianxia_has_{school}_proposal"
        report.check(
            occurrences(script_text, retired) == 0,
            f"retired automatic proposal trigger remains: {retired}",
        )

        report.check(
            target in script_text
            and bool(
                re.search(
                    rf"save_global_event_target_as\s*=\s*{re.escape(target)}\b",
                    mask_clausewitz(script_text),
                )
            ),
            f"formal {school} filing never records proposer metadata {target}",
        )


def validate_petition_timers(
    modifier_index: dict[str, list[Block]],
    script_text: str,
    effect_index: dict[str, list[Block]],
    events: dict[str, list[Block]],
    report: Report,
) -> None:
    for school, modifier in zip(SCHOOLS, PETITION_MODIFIERS):
        require_unique(modifier_index, modifier, report, "event modifier")
        additions = modifier_additions(script_text, modifier)
        report.check(
            bool(additions),
            f"formal {school} petition is never created with {modifier}",
        )
        for addition in additions:
            report.check(
                bool(re.search(rf"\bduration\s*=\s*{PETITION_DAYS}\b", addition)),
                f"{modifier} must always last exactly {PETITION_DAYS} days",
            )

    report.check(
        "zhx_debate_petition_active" not in script_text,
        "one shared petition-active flag would let the first school block all others",
    )

    # A filing container may add one school's timer, but must not clear every
    # other school at the same time.  Full cleanup belongs only to debate start.
    filing_containers = [
        block
        for blocks in effect_index.values()
        for block in blocks
        if any(modifier in block.text for modifier in PETITION_MODIFIERS)
        and "add_country_modifier" in block.text
    ]
    filing_containers.extend(
        block
        for blocks in events.values()
        for block in blocks
        if any(modifier in block.text for modifier in PETITION_MODIFIERS)
        and "add_country_modifier" in block.text
    )
    for block in filing_containers:
        report.check(
            f"{CLEAR_PETITIONS} = yes" not in block.text,
            f"filing container `{block.name}` clears parallel petitions",
        )


def validate_support_thresholds(
    trigger_index: dict[str, list[Block]], report: Report
) -> None:
    """Each school needs three adopters and a different 50-practice endorser.

    EU4's `calc_true_if` counts matches yielded by an `all_country` iterator.
    A boolean `any_country` clause can contribute at most one true item, so it
    must never be used for the three-adopter threshold. The separate
    `any_country` endorser must explicitly exclude ROOT and carry practice 50.
    """

    for school, doctrine_flag in zip(SCHOOLS, DOCTRINE_FLAGS):
        name = f"zhx_tianxia_{school}_has_social_basis"
        basis = require_unique(trigger_index, name, report, "scripted trigger")
        if not basis:
            continue
        report.check(
            "calc_true_if" in basis.text
            and "all_country" in basis.text
            and bool(re.search(r"\bamount\s*=\s*3\b", basis.text)),
            f"`{name}` must require at least three same-school adopters",
        )
        report.check(
            occurrences(basis.text, doctrine_flag) >= 2,
            f"`{name}` does not keep adopter and endorser in {doctrine_flag}",
        )
        report.check(
            has_practice_threshold(basis.text, 50)
            and bool(
                re.search(
                    r"NOT\s*=\s*\{\s*tag\s*=\s*ROOT\s*\}",
                    mask_clausewitz(basis.text),
                )
            ),
            f"`{name}` needs another country (not ROOT) at 50 practice",
        )


def validate_petition_counts_and_selection(
    trigger_index: dict[str, list[Block]],
    effect_index: dict[str, list[Block]],
    events: dict[str, list[Block]],
    script_text: str,
    report: Report,
) -> None:
    two = require_unique(trigger_index, TWO_PETITIONS, report, "scripted trigger")
    exact = require_unique(
        trigger_index, EXACTLY_TWO_PETITIONS, report, "scripted trigger"
    )
    three = require_unique(trigger_index, THREE_PETITIONS, report, "scripted trigger")

    if two:
        for active, modifier in zip(ACTIVE_PETITION_TRIGGERS, PETITION_MODIFIERS):
            report.check(
                active in two.text or modifier in two.text,
                f"`{TWO_PETITIONS}` omits active state for {modifier}",
            )
        report.check(
            bool(re.search(r"\bamount\s*=\s*2\b", two.text)),
            f"`{TWO_PETITIONS}` must require at least two active petitions",
        )
    if exact:
        report.check(
            TWO_PETITIONS in exact.text
            or bool(re.search(r"\bamount\s*=\s*2\b", exact.text)),
            f"`{EXACTLY_TWO_PETITIONS}` never proves that two petitions exist",
        )
        report.check(
            THREE_PETITIONS in exact.text and "NOT" in exact.text,
            f"`{EXACTLY_TWO_PETITIONS}` must exclude three-or-more petitions",
        )
    if three:
        for active, modifier in zip(ACTIVE_PETITION_TRIGGERS, PETITION_MODIFIERS):
            report.check(
                active in three.text or modifier in three.text,
                f"`{THREE_PETITIONS}` omits active state for {modifier}",
            )
        report.check(
            bool(re.search(r"\bamount\s*=\s*3\b", three.text)),
            f"`{THREE_PETITIONS}` must require at least three active petitions",
        )

    can_convene = require_unique(trigger_index, CAN_CONVENE, report, "scripted trigger")
    if can_convene:
        for token in (TWO_PETITIONS, TERM_MODIFIER, "zhx_tianxia_council_is_busy"):
            report.check(
                token in can_convene.text,
                f"`{CAN_CONVENE}` is missing {token}",
            )
        report.check(
            "NOT" in can_convene.text,
            f"`{CAN_CONVENE}` must negate the term and busy-state gates",
        )
        report.check(
            not has_practice_threshold(can_convene.text, 70),
            f"`{CAN_CONVENE}` still convenes directly from a 70-practice exemplar",
        )

    auto = require_unique(effect_index, AUTO_SELECT, report, "scripted effect")
    if auto:
        for setter in CANDIDATE_A_SETTERS + CANDIDATE_B_SETTERS:
            report.check(
                setter in auto.text,
                f"`{AUTO_SELECT}` cannot populate candidate slot via {setter}",
            )

    # Exactly two uses the deterministic selector; 3+ dispatches a first-stage
    # choice.  This may live in the annual scheduler or a shared dispatch effect.
    dispatch_blocks = [
        block
        for blocks in list(effect_index.values()) + list(events.values())
        for block in blocks
        if EXACTLY_TWO_PETITIONS in block.text or THREE_PETITIONS in block.text
    ]
    report.check(
        any(
            EXACTLY_TWO_PETITIONS in block.text and f"{AUTO_SELECT} = yes" in block.text
            for block in dispatch_blocks
        ),
        "exactly two petitions must enter the deterministic auto-selection path",
    )
    report.check(
        any(
            (
                THREE_PETITIONS in block.text
                or (EXACTLY_TWO_PETITIONS in block.text and "else" in block.text)
            )
            and re.search(r"id\s*=\s*zhx_debate\.3\b", block.text)
            for block in dispatch_blocks
        ),
        "three-or-more petitions must dispatch the first Tianzi selection event",
    )

    select_a = events.get("zhx_debate.3", [])
    select_b = events.get("zhx_debate.4", [])
    if report.check(
        len(select_a) == 1,
        f"expected one first-stage candidate event zhx_debate.3, found {len(select_a)}",
    ):
        body = select_a[0].text
        for setter in CANDIDATE_A_SETTERS:
            report.check(setter in body, f"zhx_debate.3 is missing option {setter}")
        report.check(
            bool(re.search(r"id\s*=\s*zhx_debate\.4\b", body)),
            "zhx_debate.3 must continue to the B-candidate selection event",
        )
    if report.check(
        len(select_b) == 1,
        f"expected one second-stage candidate event zhx_debate.4, found {len(select_b)}",
    ):
        body = select_b[0].text
        for setter in CANDIDATE_B_SETTERS:
            report.check(setter in body, f"zhx_debate.4 is missing option {setter}")
        report.check(
            effect_reaches_token(body, SHARED_BEGIN, effect_index),
            f"zhx_debate.4 must finish selection through `{SHARED_BEGIN}`",
        )

    for flag, setter in zip(CANDIDATE_A_FLAGS, CANDIDATE_A_SETTERS):
        report.check(flag in script_text and setter in script_text, f"A slot omits {flag}")
    for flag, setter in zip(CANDIDATE_B_FLAGS, CANDIDATE_B_SETTERS):
        report.check(flag in script_text and setter in script_text, f"B slot omits {flag}")


def validate_petition_cleanup(
    effect_index: dict[str, list[Block]], report: Report
) -> None:
    cleanup = require_unique(effect_index, CLEAR_PETITIONS, report, "scripted effect")
    if cleanup:
        for modifier, target in zip(PETITION_MODIFIERS, PROPOSER_TARGETS):
            report.check(
                modifier in cleanup.text and "remove_country_modifier" in cleanup.text,
                f"`{CLEAR_PETITIONS}` does not remove {modifier}",
            )
            report.check(
                bool(
                    re.search(
                        rf"clear_global_event_target\s*=\s*{re.escape(target)}\b",
                        mask_clausewitz(cleanup.text),
                    )
                ),
                f"`{CLEAR_PETITIONS}` does not clear {target}",
            )

    launchers = [
        block
        for blocks in effect_index.values()
        for block in blocks
        if f"{SHARED_BEGIN} = yes" in block.text
    ]
    report.check(bool(launchers), f"no mature launcher calls `{SHARED_BEGIN}`")
    report.check(
        any(
            effect_reaches_token(block.text, CLEAR_PETITIONS, effect_index)
            and block.text.find(CLEAR_PETITIONS) < block.text.find(SHARED_BEGIN)
            for block in launchers
        ),
        "debate start must clear all six petitions before opening the shared ballot",
    )


def validate_term(
    modifier_index: dict[str, list[Block]],
    effect_index: dict[str, list[Block]],
    script_text: str,
    report: Report,
) -> None:
    require_unique(modifier_index, TERM_MODIFIER, report, "event modifier")
    additions = modifier_additions(script_text, TERM_MODIFIER)
    report.check(bool(additions), f"{TERM_MODIFIER} is never started")
    for addition in additions:
        report.check(
            bool(re.search(rf"\bduration\s*=\s*{TERM_DAYS}\b", addition)),
            f"{TERM_MODIFIER} must always last exactly {TERM_DAYS} days",
        )

    finish = require_unique(effect_index, FINISH_DEBATE, report, "scripted effect")
    if finish:
        report.check(
            effect_reaches_token(finish.text, TERM_MODIFIER, effect_index),
            f"`{FINISH_DEBATE}` must start the fifteen-year orthodoxy term",
        )

    report.check(
        RETIRED_COOLDOWN not in script_text,
        f"retired cooldown `{RETIRED_COOLDOWN}` remains; the term is authoritative",
    )

    # Gameplay effects that branch on orthodoxy must read the timer in the same
    # effect.  State setters, result mapping, and read-only event descriptions
    # are intentionally outside this scan.
    gameplay_markers = (
        "change_variable",
        "add_country_modifier",
        "add_prestige",
        "add_stability",
        "add_legitimacy",
    )
    for name, blocks in effect_index.items():
        if name.startswith(("zhx_set_tianxia_orthodoxy_", "zhx_apply_council_candidate_")):
            continue
        for block in blocks:
            if not any(flag in block.text for flag in ORTHODOXY_FLAGS + (ORTHODOXY_PLURAL,)):
                continue
            if not any(marker in block.text for marker in gameplay_markers):
                continue
            report.check(
                TERM_MODIFIER in block.text,
                f"international orthodoxy effect `{name}` is not gated by {TERM_MODIFIER}",
            )


def validate_shared_frozen_ballot(
    effect_index: dict[str, list[Block]], script_text: str, report: Report
) -> None:
    for flag in SHARED_VOTES:
        report.check(flag in script_text, f"shared ballot flag is missing: {flag}")
    for retired in (
        "zhx_tianxia_" "debate_vote_a",
        "zhx_tianxia_" "debate_vote_b",
        "zhx_tianxia_" "debate_vote_plural",
    ):
        report.check(retired not in script_text, f"parallel debate ballot remains: {retired}")

    clear_vote = require_unique(
        effect_index, SHARED_CLEAR_VOTE, report, "scripted effect"
    )
    if clear_vote:
        for flag in SHARED_VOTES + (BONUS_FLAG,):
            report.check(
                operation_count(clear_vote.text, "clr_country_flag", flag) == 1,
                f"`{SHARED_CLEAR_VOTE}` must clear {flag}",
            )

    for cast_name, candidate_match in (
        (CAST_A, "zhx_council_vote_matches_candidate_a"),
        (CAST_B, "zhx_council_vote_matches_candidate_b"),
    ):
        cast = require_unique(effect_index, cast_name, report, "scripted effect")
        if cast:
            report.check(
                has_practice_threshold(cast.text, 75),
                f"`{cast_name}` must freeze the exemplary bonus at practice 75",
            )
            report.check(
                candidate_match in cast.text
                and operation_count(cast.text, "set_country_flag", BONUS_FLAG) == 1,
                f"`{cast_name}` must freeze a bonus only for the matching school",
            )
    cast_c = require_unique(effect_index, CAST_C, report, "scripted effect")
    if cast_c:
        report.check(
            BONUS_FLAG not in cast_c.text,
            "shared choice C (pluralism/abstention) must never receive the 75 bonus",
        )

    recount = require_unique(effect_index, SHARED_RECOUNT, report, "scripted effect")
    if recount:
        report.check(BONUS_FLAG in recount.text, "recount must read the frozen bonus flag")
        report.check(
            not has_practice_threshold(recount.text, 75),
            "recount recalculates practice 75 instead of reading the frozen ballot bonus",
        )


def validate_result_handoff(
    effect_index: dict[str, list[Block]],
    events: dict[str, list[Block]],
    report: Report,
) -> None:
    resolve = require_unique(effect_index, SHARED_RESOLVE, report, "scripted effect")
    finish = require_unique(
        effect_index, "zhx_finish_tianxia_council", report, "scripted effect"
    )
    deadline = require_unique(events, "zhx_system.23", report, "country event")
    if not resolve or not finish or not deadline:
        return
    report.check(
        operation_count(resolve.text, "set_country_flag", "zhx_council_result_ready") == 1,
        "deadline resolver must set exactly one result-ready flag",
    )
    report.check(
        operation_count(finish.text, "clr_country_flag", "zhx_council_result_ready") == 1,
        "council finish must clear the result-ready flag",
    )
    for event_id in ("zhx_debate.20", "zhx_system.22"):
        report.check(
            bool(
                re.search(
                    rf"country_event\s*=\s*\{{[^{{}}]*id\s*=\s*"
                    rf"{re.escape(event_id)}\b[^{{}}]*days\s*=\s*1\b[^{{}}]*\}}",
                    mask_clausewitz(deadline.text),
                    re.DOTALL,
                )
            ),
            f"deadline must delay {event_id} by one day",
        )
        report.check(
            event_id not in mask_clausewitz(resolve.text),
            f"hidden deadline must not synchronously dispatch {event_id}",
        )
        result = require_unique(events, event_id, report, "country event")
        if result:
            report.check(
                "zhx_council_result_ready" in mask_clausewitz(result.text),
                f"{event_id} must require the result-ready flag",
            )


def validate_plural_tie(
    effect_index: dict[str, list[Block]], report: Report
) -> None:
    resolve = require_unique(effect_index, RESOLVE_DEBATE, report, "scripted effect")
    if not resolve:
        return
    for comparison in (
        "zhx_council_a_vs_b",
        "zhx_council_a_vs_c",
        "zhx_council_b_vs_a",
        "zhx_council_b_vs_c",
    ):
        report.check(
            bool(
                re.search(
                    rf"check_variable\s*=\s*\{{[^{{}}]*which\s*=\s*"
                    rf"{re.escape(comparison)}\b[^{{}}]*value\s*=\s*1\b",
                    mask_clausewitz(resolve.text),
                    re.DOTALL,
                )
            ),
            f"strict-win comparison is missing or non-strict: {comparison}",
        )
    report.check(
        "else" in resolve.text
        and "zhx_council_result_c" in resolve.text
        and (
            ORTHODOXY_PLURAL in resolve.text
            or "zhx_set_tianxia_orthodoxy_plural" in resolve.text
        ),
        "all non-strict results, including first-place ties, must resolve to pluralism",
    )


def validate_ai_yearly(
    effect_index: dict[str, list[Block]],
    events: dict[str, list[Block]],
    on_actions: str,
    report: Report,
) -> None:
    report.check(
        "on_yearly_pulse" in on_actions and "zhx_doctrine.90" in on_actions,
        "AI petition attempts must run from the existing yearly doctrine pulse",
    )
    annual = events.get("zhx_doctrine.90", [])
    if report.check(
        len(annual) == 1,
        f"expected one annual doctrine event zhx_doctrine.90, found {len(annual)}",
    ):
        report.check(
            f"{TRY_AI_PETITION} = yes" in annual[0].text,
            f"zhx_doctrine.90 must call `{TRY_AI_PETITION}` after practice settlement",
        )
    ai_effect = require_unique(effect_index, TRY_AI_PETITION, report, "scripted effect")
    if ai_effect:
        report.check(
            bool(re.search(r"\bai\s*=\s*yes\b", ai_effect.text)),
            f"`{TRY_AI_PETITION}` must be AI-only",
        )
        report.check(
            has_practice_threshold(ai_effect.text, 70)
            or PETITION_QUALIFICATION in ai_effect.text,
            f"`{TRY_AI_PETITION}` must respect the 70-practice filing qualification",
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


def control_text_key(body: str) -> str | None:
    match = re.search(r'(?m)^\s*text\s*=\s*"([A-Za-z0-9_.]+)"\s*$', body)
    return match.group(1) if match else None


def validate_gui(interface: str, custom_gui: str, report: Report) -> None:
    interface_objects = gui_objects(interface)
    custom_objects = gui_objects(custom_gui)
    values = localization_values()

    report.check(
        PETITION_QUALIFICATION not in mask_clausewitz(custom_gui),
        "custom GUI must not run the authoritative cross-country petition scan per frame",
    )
    report.check(
        PETITION_ATTEMPT in mask_clausewitz(custom_gui),
        "petition button must use the cheap 70-practice GUI gate",
    )

    left = interface_objects.get("zhx_gui_council_header", [])
    right = interface_objects.get("zhx_gui_debate_header", [])
    if report.check(len(left) == 1, "missing one left `zhx_gui_council_header`") and report.check(
        len(right) == 1, "missing one right `zhx_gui_debate_header`"
    ):
        left_x = gui_x(left[0])
        right_x = gui_x(right[0])
        report.check(
            left_x is not None and right_x is not None and left_x < right_x,
            "current public council must remain left of the orthodoxy column",
        )
        left_key = control_text_key(left[0])
        right_key = control_text_key(right[0])
        report.check(
            bool(left_key and "公议" in values.get(left_key, "")),
            "left header localization must visibly contain `公议`",
        )
        report.check(
            bool(right_key and "显学" in values.get(right_key, "")),
            "right header localization must visibly contain `显学`",
        )

    for school, active, modifier, target in zip(
        SCHOOLS,
        ACTIVE_PETITION_TRIGGERS,
        PETITION_MODIFIERS,
        PROPOSER_TARGETS,
    ):
        interface_names = {
            name
            for name in interface_objects
            if school in name and ("petition" in name or "proposal" in name)
        }
        custom_names = {
            name
            for name in custom_objects
            if school in name and ("petition" in name or "proposal" in name)
        }
        shared_names = sorted(interface_names & custom_names)
        report.check(
            bool(shared_names),
            f"GUI has no bound {school} petition-status control",
        )
        if shared_names:
            binding_text = "\n".join(
                body for name in shared_names for body in custom_objects[name]
            )
            report.check(
                active in binding_text or modifier in binding_text or target in binding_text,
                f"{school} petition-status GUI does not read authoritative state",
            )

    report.check(
        any(name.startswith("zhx_gui_council_") for name in custom_objects),
        "left current-council column has no scripted bindings",
    )
    report.check(
        all(
            f"zhx_gui_debate_orthodoxy_{school}" in custom_objects
            for school in SCHOOLS
        ),
        "right orthodoxy column does not expose all six schools",
    )

    resolving_name = "zhx_gui_council_debate_resolving"
    report.check(
        resolving_name in interface_objects and resolving_name in custom_objects,
        "resolving phase has no bound current-council status control",
    )
    if resolving_name in custom_objects:
        resolving_text = "\n".join(custom_objects[resolving_name])
        report.check(
            "zhx_council_phase_resolving" in resolving_text
            and "zhx_council_phase_ballot_open" not in resolving_text,
            "resolving status must be exclusive to the frozen-result phase",
        )
        report.check(
            "定论" in values.get(resolving_name, ""),
            "resolving status localization must distinguish it from live voting",
        )


def main() -> None:
    report = Report()
    texts = {path: read_text(path, report) for path in CORE_PATHS}
    for path, text in texts.items():
        if text:
            # The imported parser only needs the report's `check`/`errors`
            # protocol; keeping one report preserves aggregate diagnostics.
            validate_braces(path, text, report)  # type: ignore[arg-type]

    effect_paths = tuple(sorted((MOD / "common/scripted_effects").glob("zhx_*.txt")))
    trigger_paths = tuple(sorted((MOD / "common/scripted_triggers").glob("zhx_*.txt")))
    event_paths = tuple(sorted((MOD / "events").glob("zhx_*.txt")))
    for path in effect_paths + trigger_paths + event_paths:
        if path not in texts:
            texts[path] = read_text(path, report)

    effect_index, _ = all_effect_texts(effect_paths, texts)
    trigger_index = definition_index(trigger_paths, texts)
    events = event_index(event_paths, texts)
    modifier_index = definition_index((MODIFIERS,), texts)
    script_text = "\n".join(
        texts.get(path, "") for path in effect_paths + trigger_paths + event_paths
    )

    validate_petition_qualification(trigger_index, script_text, report)
    validate_petition_timers(
        modifier_index, script_text, effect_index, events, report
    )
    validate_support_thresholds(trigger_index, report)
    validate_petition_counts_and_selection(
        trigger_index, effect_index, events, script_text, report
    )
    validate_petition_cleanup(effect_index, report)
    validate_term(modifier_index, effect_index, script_text, report)
    validate_shared_frozen_ballot(effect_index, script_text, report)
    validate_result_handoff(effect_index, events, report)
    validate_plural_tie(effect_index, report)
    validate_ai_yearly(effect_index, events, texts.get(ON_ACTIONS, ""), report)
    validate_gui(texts.get(INTERFACE, ""), texts.get(CUSTOM_GUI, ""), report)
    report.finish()


if __name__ == "__main__":
    main()
