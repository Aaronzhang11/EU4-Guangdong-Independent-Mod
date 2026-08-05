#!/usr/bin/env python3
"""Apply the reviewed 1444 ownership of Yuebei, Dongjiang, and Puning."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
HISTORY = MOD / "history/provinces"
OUT = ROOT / "planning/guangdong_ownership"

POLICY = {
    # Yuebei
    2158: "GDD", 5216: "GDD", 4948: "GDD",
    # Dongjiang
    2157: "GDD", 5214: "GDD", 5215: "GDD", 4944: "GDD",
    # Chaoshan: Chaozhou and Puning belong to CZC; Haifeng remains GDD.
    2156: "CZC", 5217: "CZC",
}


def history_path(province_id: int) -> Path:
    matches = sorted(HISTORY.glob(f"{province_id} - *.txt"))
    if len(matches) != 1:
        raise ValueError(f"Province {province_id} has {len(matches)} history files")
    return matches[0]


def initial_section(text: str) -> tuple[str, str]:
    match = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", text)
    return (text[:match.start()], text[match.start():]) if match else (text, "")


def apply_owner(text: str, owner: str) -> str:
    initial, dated = initial_section(text)
    for key in ("owner", "controller"):
        initial, count = re.subn(
            rf"(?m)^(\s*{key}\s*=\s*)\S+\s*$",
            rf"\g<1>{owner}",
            initial,
            count=1,
        )
        if count != 1:
            raise ValueError(f"Missing initial {key}")
    cores = re.findall(r"(?m)^\s*add_core\s*=\s*(\S+)", initial)
    if owner not in cores:
        marker = re.search(r"(?m)^\s*controller\s*=\s*\S+\s*$", initial)
        initial = initial[:marker.end()] + f"\nadd_core = {owner}" + initial[marker.end():]
    return initial + dated


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    changed = []
    for province_id, owner in POLICY.items():
        path = history_path(province_id)
        old = path.read_text(encoding="utf-8-sig")
        new = apply_owner(old, owner)
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed.append(province_id)
    report = {
        "batch": "B33_guangdong_area_ownership",
        "policy": {str(key): value for key, value in POLICY.items()},
        "changed_ids": changed,
        "validation": "skipped_by_user_request",
    }
    (OUT / "ownership_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
