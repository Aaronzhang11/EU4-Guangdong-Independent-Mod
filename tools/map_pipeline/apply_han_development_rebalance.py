#!/usr/bin/env python3
"""Apply the 2026-08 Han-region development balance pass.

This pass raises five under-strength regions without changing geometry,
ownership, trade goods, centers of trade, forts, cultures, or religions.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
HISTORY = MOD / "history/provinces"
REGISTRY = ROOT / "docs/map/china_province_split_registry.csv"


DEVELOPMENT = {
    "Jiangxi": {
        670: (6, 7, 5), 683: (9, 10, 6), 1833: (7, 7, 5),
        2151: (7, 9, 4), 4979: (7, 8, 5), 4980: (6, 7, 4),
        4992: (5, 5, 4), 4993: (5, 6, 3), 4994: (3, 4, 3),
        4995: (3, 3, 2),
    },
    "Hunan": {
        671: (8, 9, 4), 672: (5, 6, 4), 2173: (3, 4, 6),
        2174: (4, 4, 5), 4982: (7, 8, 4), 4983: (3, 3, 4),
        4996: (2, 4, 4), 4997: (4, 4, 4), 4998: (4, 5, 3),
        4999: (3, 3, 5), 5000: (3, 3, 4), 5001: (4, 6, 4),
    },
    "Hubei": {
        681: (4, 4, 3), 682: (6, 7, 4), 2171: (6, 6, 5),
        2172: (5, 5, 4), 4197: (3, 3, 2), 4981: (4, 3, 2),
        5008: (2, 3, 3), 5009: (3, 2, 3), 5010: (3, 3, 2),
        5011: (6, 10, 3), 5012: (4, 4, 2), 5013: (2, 2, 2),
        5014: (2, 4, 3), 5015: (2, 2, 2), 5016: (3, 4, 3),
    },
    "Shandong": {
        5101: (4, 6, 3), 5102: (3, 3, 3), 2138: (3, 4, 3),
        5103: (3, 3, 3), 691: (6, 6, 3), 5104: (4, 5, 3),
        5105: (4, 5, 3), 2139: (4, 4, 3), 690: (4, 4, 3),
        5106: (3, 3, 2), 5107: (4, 4, 3), 5108: (3, 3, 3),
        2140: (5, 4, 4), 5109: (5, 4, 3), 5110: (5, 5, 4),
        5111: (3, 3, 4), 5112: (3, 3, 3),
    },
    "Guizhou": {
        2168: (3, 3, 3), 5069: (2, 2, 3), 5070: (3, 2, 3),
        5071: (2, 2, 2), 674: (3, 3, 2), 5072: (2, 2, 2),
        673: (2, 2, 2), 5073: (1, 1, 1), 5074: (1, 1, 1),
        4199: (2, 1, 1),
    },
}

EXPECTED_TOTALS = {
    "Jiangxi": (58, 66, 41),
    "Hunan": (50, 59, 51),
    "Hubei": (55, 62, 43),
    "Shandong": (66, 69, 53),
    "Guizhou": (21, 19, 20),
}

# Registry only records newly split provinces. Retained values are repeated on
# each row belonging to the same parent split group.
REGISTRY_NEW = {
    pid: dev
    for region in ("Jiangxi", "Hunan", "Hubei", "Guizhou")
    for pid, dev in DEVELOPMENT[region].items()
    if pid >= 4979
}
REGISTRY_RETAINED = {
    670: (6, 7, 5), 683: (9, 10, 6), 1833: (7, 7, 5), 2151: (7, 9, 4),
    671: (8, 9, 4), 672: (5, 6, 4), 2173: (3, 4, 6), 2174: (4, 4, 5),
    681: (4, 4, 3), 682: (6, 7, 4), 2171: (6, 6, 5),
    2172: (5, 5, 4), 4197: (3, 3, 2),
    674: (3, 3, 2), 673: (2, 2, 2),
}
GROUP_DELTAS = {
    "p683-threeway": "44", "p1833-threeway": "36", "p2151-a": "26",
    "p670-a": "16", "p671-fourway": "48", "p672-a": "17",
    "p2173-a": "16", "p2174-fourway": "38", "p682-fiveway": "42",
    "p2171-threeway": "22", "p2172-threeway": "23", "p4197-two-way": "13",
    "p681-two-way": "9", "p674-guizhou-tenway": "27",
    "p673-guizhou-tenway": "9",
}


def history_path(province_id: int) -> Path:
    matches = list(HISTORY.glob(f"{province_id} - *.txt"))
    if len(matches) != 1:
        raise ValueError(f"Province {province_id} has {len(matches)} history files")
    return matches[0]


def read_dev(path: Path) -> tuple[int, int, int]:
    text = path.read_text(encoding="cp1252")
    values = []
    for key in ("base_tax", "base_production", "base_manpower"):
        match = re.search(rf"(?m)^{key}\s*=\s*(\d+)", text)
        if not match:
            raise ValueError(f"{path.name}: missing {key}")
        values.append(int(match.group(1)))
    return tuple(values)


def write_dev(path: Path, values: tuple[int, int, int]) -> None:
    text = path.read_text(encoding="cp1252")
    for key, value in zip(
        ("base_tax", "base_production", "base_manpower"), values
    ):
        text, count = re.subn(
            rf"(?m)^{key}\s*=\s*\d+", f"{key} = {value}", text, count=1
        )
        if count != 1:
            raise ValueError(f"{path.name}: could not replace {key}")
    path.write_text(text, encoding="cp1252")


def update_registry() -> None:
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0])
    for row in rows:
        province_id = int(row["game_id"])
        if province_id in REGISTRY_NEW:
            tax, production, manpower = REGISTRY_NEW[province_id]
            row["new_tax"], row["new_production"], row["new_manpower"] = (
                str(tax), str(production), str(manpower)
            )
        parent_id = int(row["parent_id"])
        if province_id in REGISTRY_NEW and parent_id in REGISTRY_RETAINED:
            tax, production, manpower = REGISTRY_RETAINED[parent_id]
            row["retained_tax"], row["retained_production"], row["retained_manpower"] = (
                str(tax), str(production), str(manpower)
            )
        if province_id in REGISTRY_NEW and row["split_group"] in GROUP_DELTAS:
            row["group_dev_delta"] = GROUP_DELTAS[row["split_group"]]
        if province_id in REGISTRY_NEW:
            row["claims_or_uncertainty"] = row["claims_or_uncertainty"].replace(
                "百点诸侯重平衡", "汉地发展度平衡"
            )
    with REGISTRY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, quoting=csv.QUOTE_ALL, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def validate() -> None:
    for region, provinces in DEVELOPMENT.items():
        actual = {province_id: read_dev(history_path(province_id)) for province_id in provinces}
        if actual != provinces:
            wrong = {pid: value for pid, value in actual.items() if value != provinces[pid]}
            raise ValueError(f"{region}: incorrect province development {wrong}")
        totals = tuple(sum(value[index] for value in actual.values()) for index in range(3))
        if totals != EXPECTED_TOTALS[region]:
            raise ValueError(f"{region}: totals {totals}, expected {EXPECTED_TOTALS[region]}")
        print(f"{region}: {totals[0]}/{totals[1]}/{totals[2]} = {sum(totals)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        for provinces in DEVELOPMENT.values():
            for province_id, values in provinces.items():
                write_dev(history_path(province_id), values)
        update_registry()
    validate()


if __name__ == "__main__":
    main()
