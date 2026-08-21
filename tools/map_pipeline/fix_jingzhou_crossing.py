#!/usr/bin/env python3
"""Keep Jingzhou's only special river crossing pointed at Gongan."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "guangdong_independent_practice/map"
ADJACENCY_PATH = MAP / "adjacencies.csv"
CANONICAL_ROW = "2172;5014;sea;5036;-1;-1;-1;-1;Jingzhou-Gongan Yangtze crossing"
CANONICAL_PAIR = frozenset((2172, 5014))
OBSOLETE_PAIRS = {
    frozenset((2172, 681)),
    frozenset((2172, 5013)),
}


def row_pair(line: str) -> frozenset[int] | None:
    fields = line.split(";")
    if len(fields) < 2 or not fields[0].isdigit() or not fields[1].isdigit():
        return None
    return frozenset((int(fields[0]), int(fields[1])))


def apply() -> None:
    lines = ADJACENCY_PATH.read_text(encoding="cp1252").splitlines()
    lines = [
        line for line in lines
        if (pair := row_pair(line)) != CANONICAL_PAIR and pair not in OBSOLETE_PAIRS
    ]
    sentinel = next(
        (index for index, line in enumerate(lines) if line.startswith("-1;-1;")),
        len(lines),
    )
    lines.insert(sentinel, CANONICAL_ROW)
    ADJACENCY_PATH.write_text("\n".join(lines) + "\n", encoding="cp1252")


def definition_colours() -> dict[int, tuple[int, int, int]]:
    wanted = {681, 2172, 5013, 5014, 5036}
    colours: dict[int, tuple[int, int, int]] = {}
    with (MAP / "definition.csv").open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if len(row) >= 4 and row[0].isdigit() and int(row[0]) in wanted:
                colours[int(row[0])] = tuple(map(int, row[1:4]))
    if colours.keys() != wanted:
        raise ValueError(f"Missing definition rows: {sorted(wanted - colours.keys())}")
    return colours


def mask(bitmap: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    return np.all(bitmap == np.asarray(colour, dtype=np.uint8), axis=2)


def touches(a: np.ndarray, b: np.ndarray) -> bool:
    return bool(
        np.any(a[:, :-1] & b[:, 1:])
        or np.any(a[:, 1:] & b[:, :-1])
        or np.any(a[:-1, :] & b[1:, :])
        or np.any(a[1:, :] & b[:-1, :])
    )


def verify() -> None:
    lines = ADJACENCY_PATH.read_text(encoding="cp1252").splitlines()
    canonical = [line for line in lines if row_pair(line) == CANONICAL_PAIR]
    if canonical != [CANONICAL_ROW]:
        raise ValueError(f"Expected exactly one canonical Jingzhou-Gongan row, got {canonical}")
    obsolete = [line for line in lines if row_pair(line) in OBSOLETE_PAIRS]
    if obsolete:
        raise ValueError(f"Obsolete direct Jingzhou crossings remain: {obsolete}")

    colours = definition_colours()
    bitmap = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    masks = {province_id: mask(bitmap, colour) for province_id, colour in colours.items()}
    if not touches(masks[2172], masks[5036]) or not touches(masks[5014], masks[5036]):
        raise ValueError("Jingzhou and Gongan must both touch navigable reach 5036")
    if touches(masks[2172], masks[5014]):
        raise ValueError("Jingzhou and Gongan already have a direct land border")
    if touches(masks[2172], masks[681]) or touches(masks[2172], masks[5013]):
        raise ValueError("Jingzhou must not have a direct bitmap border with Yiling or Shizhou")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate without rewriting")
    args = parser.parse_args()
    if not args.check:
        apply()
    verify()
    print("JINGZHOU_CROSSING_OK:2172-5014-through-5036")


if __name__ == "__main__":
    main()
