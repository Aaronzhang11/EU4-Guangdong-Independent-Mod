#!/usr/bin/env python3
"""Remove obsolete vanilla Chinese releasable cores from the 1444 setup."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "guangdong_independent_practice/history/provinces"
PLAN = ROOT / "planning/legacy_mainland_cores_b70"
REPORT = PLAN / "removal_report.json"

# These are legacy vanilla claim layers, not the current polity occupying a province.
LEGACY_TAGS = {"CXI", "CDL", "NNG", "CYI", "LNG", "CMI", "MNG", "CSH"}
EXPECTED_COUNTS = {
    "CXI": 23,
    "CDL": 22,
    "NNG": 20,
    "CYI": 9,
    "LNG": 8,
    "CMI": 4,
    "MNG": 6,
    "CSH": 3,
}

OWNER_RE = re.compile(r"^\s*owner\s*=\s*([A-Z0-9]{3})\b")
CORE_RE = re.compile(r"^\s*add_core\s*=\s*([A-Z0-9]{3})\b")


def initial_owner(lines: list[str]) -> str | None:
    depth = 0
    for raw in lines:
        code = raw.split("#", 1)[0]
        if depth == 0:
            match = OWNER_RE.match(code)
            if match:
                return match.group(1)
        depth += code.count("{") - code.count("}")
    return None


def removable_cores(lines: list[str], owner: str | None) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    depth = 0
    for index, raw in enumerate(lines):
        code = raw.split("#", 1)[0]
        if depth == 0:
            match = CORE_RE.match(code)
            if match and match.group(1) in LEGACY_TAGS and match.group(1) != owner:
                result.append((index, match.group(1)))
        depth += code.count("{") - code.count("}")
    return result


def audit_remaining() -> list[dict[str, object]]:
    remaining: list[dict[str, object]] = []
    for path in sorted(HISTORY.glob("*.txt")):
        lines = path.read_text(encoding="latin-1").splitlines(keepends=True)
        owner = initial_owner(lines)
        for _index, tag in removable_cores(lines, owner):
            remaining.append({"file": path.name, "owner": owner, "tag": tag})
    return remaining


def main() -> None:
    PLAN.mkdir(parents=True, exist_ok=True)
    previous_entries: list[dict[str, object]] = []
    if REPORT.exists():
        previous_entries = json.loads(REPORT.read_text(encoding="utf-8")).get(
            "removed_entries", []
        )
    removed: list[dict[str, object]] = []
    counts: Counter[str] = Counter()

    for path in sorted(HISTORY.glob("*.txt")):
        lines = path.read_text(encoding="latin-1").splitlines(keepends=True)
        owner = initial_owner(lines)
        targets = removable_cores(lines, owner)
        if not targets:
            continue
        remove_indices = {index for index, _tag in targets}
        for _index, tag in targets:
            counts[tag] += 1
            removed.append({"file": path.name, "owner": owner, "tag": tag})
        path.write_text(
            "".join(line for index, line in enumerate(lines) if index not in remove_indices),
            encoding="latin-1",
        )

    remaining = audit_remaining()
    if remaining:
        raise RuntimeError(f"Legacy non-owner cores remain: {remaining}")
    # The cleanup batch can grow when another inherited tag is discovered.
    # Merge the prior audit with newly removed rows instead of requiring every
    # historical core to reappear in one run.
    recorded_entries: list[dict[str, object]] = []
    seen_entries: set[tuple[object, object]] = set()
    for entry in (*previous_entries, *removed):
        key = (entry.get("file"), entry.get("tag"))
        if key in seen_entries:
            continue
        seen_entries.add(key)
        recorded_entries.append(entry)
    recorded_counts = Counter(str(entry["tag"]) for entry in recorded_entries)
    if dict(sorted(recorded_counts.items())) != dict(sorted(EXPECTED_COUNTS.items())):
        raise RuntimeError(
            f"Recorded legacy-core set: {dict(sorted(recorded_counts.items()))}; "
            f"expected {dict(sorted(EXPECTED_COUNTS.items()))}"
        )
    if len(recorded_entries) != sum(EXPECTED_COUNTS.values()):
        raise RuntimeError(
            f"Removal audit has {len(recorded_entries)} entries; "
            f"expected {sum(EXPECTED_COUNTS.values())}"
        )

    REPORT.write_text(
        json.dumps(
            {
                "batch": "B70_REMOVE_LEGACY_MAINLAND_CORES",
                "policy": "remove top-level legacy cores when tag differs from initial owner",
                "legacy_tags": sorted(LEGACY_TAGS),
                "expected_counts": EXPECTED_COUNTS,
                "removed_total": len(recorded_entries),
                "removed_by_tag": dict(recorded_counts),
                "remaining": remaining,
                "removed_entries": recorded_entries,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Removed {len(removed)} legacy non-owner cores from {len({x['file'] for x in removed})} provinces")
    print("Remaining legacy non-owner starting cores: 0")


if __name__ == "__main__":
    main()
