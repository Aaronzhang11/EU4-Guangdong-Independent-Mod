#!/usr/bin/env python3
"""Apply the B48 opening center-of-trade hierarchy rebalance."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
HISTORY = MOD / "history/provinces"
TRADE_NODES = MOD / "common/tradenodes/00_tradenodes.txt"
PLAN = ROOT / "planning/trade_center_rebalance_b48"
MANIFEST = PLAN / "batch_manifest.json"
MARKER = "GDD_B48_TRADE_CENTER_REBALANCE"

# Zero means that the opening center is deliberately removed.  The policy
# covers every center that existed immediately before B48, so additions cannot
# hide outside the reviewed table.
TARGET_LEVELS = {
    613: 1, 661: 1, 662: 1, 667: 3, 668: 0, 669: 1, 670: 1,
    678: 1, 679: 2, 680: 1, 684: 2, 685: 2, 688: 1, 693: 1,
    697: 1, 699: 1, 726: 1, 735: 1, 1816: 2, 1822: 2,
    1829: 2, 1836: 2, 1845: 1, 2142: 0, 2149: 1, 2162: 1,
    2170: 1, 2172: 1, 2174: 0, 2745: 2, 4948: 0, 4958: 0,
    4979: 1, 4982: 1, 5011: 2, 5059: 0, 5066: 1, 5296: 1,
}

EXPECTED_NODE_LEVELS = {
    "beijing": {1: 2, 2: 1},
    "canton": {1: 3, 2: 1, 3: 1},
    "chengdu": {1: 3, 2: 1},
    "girin": {1: 1},
    "hangzhou": {1: 2, 2: 3},
    "huguang": {1: 4, 2: 1},
    "nippon": {1: 2, 2: 1},
    "xian": {1: 2},
    "yungui": {1: 2},
    "zhongyuan": {1: 1, 2: 1},
}

GENERATOR_REPLACEMENTS = {
    "tools/map_pipeline/apply_fujian_refinement.py": (
        ('Province(4958, "厦门", "Xiamen", "minnan_area", (135,45,225), (135,45,225), (4648,997), "fish", (4,6,2), 2)',
         'Province(4958, "厦门", "Xiamen", "minnan_area", (135,45,225), (135,45,225), (4648,997), "fish", (4,6,2))'),
    ),
    "tools/map_pipeline/apply_b45_hunan_jiangxi_refinement.py": (
        ('Province(2174, "衡州", "Hengzhou", 2174, None, (2174, 5270, 5268, 5269), "hengchen_area", "HNG", "gdd_chu", "confucianism", "Hengyang", "gold", (2, 2, 2), ("HNG",), cot=1)',
         'Province(2174, "衡州", "Hengzhou", 2174, None, (2174, 5270, 5268, 5269), "hengchen_area", "HNG", "gdd_chu", "confucianism", "Hengyang", "gold", (2, 2, 2), ("HNG",))'),
    ),
    "tools/map_pipeline/apply_b46_chuandongbei_chongqing_refinement.py": (
        ('Province(680, "重庆", "Chongqing", 680, None, "chongqing_area", "BAA", "gdd_shu", "confucianism", "Chongqing", "cloth", (4, 5, 2), cot=2)',
         'Province(680, "重庆", "Chongqing", 680, None, "chongqing_area", "BAA", "gdd_shu", "confucianism", "Chongqing", "cloth", (4, 5, 2), cot=1)'),
    ),
    "tools/map_pipeline/apply_yunnan_refinement.py": (
        ('"bai", "buddhism", cot=2, fort=True)', '"bai", "buddhism", cot=1, fort=True)'),
        ('"gdd_dian", "buddhism", cot=2, fort=True)', '"gdd_dian", "buddhism", cot=1, fort=True)'),
    ),
    "tools/map_pipeline/apply_gansu_ningxia_refinement.py": (
        ('"gdd_long","confucianism",cot=2)', '"gdd_long","confucianism",cot=1)'),
    ),
    "tools/map_pipeline/apply_shanxi_refinement.py": (
        ('"cloth",(8,8,4),2,True)', '"cloth",(8,8,4),1,True'),
    ),
    "tools/map_pipeline/apply_sichuan_refinement.py": (
        ('"ba", "gdd_shu", "confucianism", 2)', '"ba", "gdd_shu", "confucianism", 1)'),
    ),
}


def history_path(province_id: int) -> Path:
    matches = sorted(HISTORY.glob(f"{province_id} - *.txt"))
    if len(matches) != 1:
        raise ValueError(f"Province {province_id} has {len(matches)} local history files")
    return matches[0]


def opening_level(text: str) -> int:
    dated = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", text)
    opening = text[:dated.start()] if dated else text
    match = re.search(r"(?m)^\s*center_of_trade\s*=\s*(\d+)\s*(?:#.*)?$", opening)
    return int(match.group(1)) if match else 0


def set_opening_level(text: str, level: int) -> str:
    dated = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", text)
    split = dated.start() if dated else len(text)
    opening, later = text[:split], text[split:]
    opening, count = re.subn(
        r"(?m)^\s*center_of_trade\s*=\s*\d+\s*(?:#.*)?$\n?", "", opening
    )
    if count > 1:
        raise ValueError("Multiple opening center_of_trade entries")
    if level:
        replacement = f"is_city = yes\ncenter_of_trade = {level} # {MARKER}"
        opening, city_count = re.subn(r"(?m)^is_city\s*=\s*yes\s*$", replacement, opening)
        if city_count != 1:
            raise ValueError("Opening history needs exactly one is_city = yes")
    return opening.rstrip() + "\n" + ("\n" + later.lstrip() if later else "")


def named_blocks(text: str):
    for match in re.finditer(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text):
        cursor, depth = match.end(), 1
        while cursor < len(text) and depth:
            depth += (text[cursor] == "{") - (text[cursor] == "}")
            cursor += 1
        if not depth:
            yield match.group(1), text[match.start():cursor]


def node_members() -> dict[str, set[int]]:
    result = {}
    for name, block in named_blocks(TRADE_NODES.read_text(encoding="cp1252")):
        match = re.search(r"(?ms)^\s*members\s*=\s*\{(.*?)^\s*\}", block)
        if match:
            result[name] = {int(value) for value in re.findall(r"\b\d+\b", re.sub(r"#.*", "", match.group(1)))}
    return result


def patch_generators() -> None:
    for relative, replacements in GENERATOR_REPLACEMENTS.items():
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        for old, new in replacements:
            if old in text:
                text = text.replace(old, new, 1)
            elif new not in text:
                raise ValueError(f"{relative}: cannot find reviewed B48 generator policy")
        path.write_text(text, encoding="utf-8")


def current_policy() -> dict[int, int]:
    return {province_id: opening_level(history_path(province_id).read_text(encoding="cp1252")) for province_id in TARGET_LEVELS}


def node_summary(policy: dict[int, int]) -> dict[str, dict[int, int]]:
    members = node_members()
    summary: dict[str, Counter] = defaultdict(Counter)
    for province_id, level in policy.items():
        if not level:
            continue
        matches = [name for name, ids in members.items() if province_id in ids]
        if len(matches) != 1:
            raise ValueError(f"Province {province_id} belongs to {len(matches)} trade nodes")
        summary[matches[0]][level] += 1
    return {name: dict(sorted(counts.items())) for name, counts in sorted(summary.items())}


def validate() -> dict[str, object]:
    policy = current_policy()
    if policy != TARGET_LEVELS:
        drift = {key: (TARGET_LEVELS[key], policy[key]) for key in TARGET_LEVELS if TARGET_LEVELS[key] != policy[key]}
        raise ValueError(f"B48 center policy drift: {drift}")
    summary = node_summary(policy)
    if summary != EXPECTED_NODE_LEVELS:
        raise ValueError(f"B48 node hierarchy drift: {summary}")
    totals = Counter(level for level in policy.values() if level)
    if totals != Counter({1: 22, 2: 9, 3: 1}):
        raise ValueError(f"B48 level totals drift: {totals}")
    for relative, replacements in GENERATOR_REPLACEMENTS.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for _old, new in replacements:
            if new not in text:
                raise ValueError(f"{relative}: replay policy is stale")
    return {
        "managed_provinces": len(policy),
        "active_centers": sum(bool(level) for level in policy.values()),
        "level_totals": dict(sorted(totals.items())),
        "node_levels": summary,
    }


def apply() -> None:
    PLAN.mkdir(parents=True, exist_ok=True)
    current = current_policy()
    if MANIFEST.exists():
        previous = json.loads(MANIFEST.read_text(encoding="utf-8"))
        before = {int(key): int(value) for key, value in previous.get("before", {}).items()}
        if set(before) != set(TARGET_LEVELS):
            raise ValueError("Existing B48 manifest has an incompatible baseline")
    else:
        before = current
    for province_id, level in TARGET_LEVELS.items():
        path = history_path(province_id)
        text = path.read_text(encoding="cp1252")
        path.write_text(set_opening_level(text, level), encoding="cp1252")
    patch_generators()
    validation = validate()
    payload = {
        "batch": "B48_trade_center_rebalance",
        "marker": MARKER,
        "purpose": "Restore a three-tier trade hierarchy and remove redundant opening centers.",
        "before": before,
        "target_levels": TARGET_LEVELS,
        "removed": [key for key, value in TARGET_LEVELS.items() if not value],
        "demoted": [key for key, value in TARGET_LEVELS.items() if value and before[key] > value],
        "validation": validation,
        "replay_generators": sorted(GENERATOR_REPLACEMENTS),
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{MARKER}; ACTIVE:{validation['active_centers']}; LEVELS:{validation['level_totals']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(validate(), ensure_ascii=False))
    else:
        apply()


if __name__ == "__main__":
    main()
