"""Freeze EU4 province IDs and RGB colors for the China map registry.

The allocation is intentionally pinned to the local EU4 1.37.5 baseline,
whose highest defined province is 4941.  Run with ``--write`` once to add the
allocation columns; later runs without ``--write`` act as a consistency check.
"""

from __future__ import annotations

import argparse
import colorsys
import csv
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "docs/map/china_province_split_registry.csv"
EXPECTED_VANILLA_MAX_ID = 4941
EXPECTED_REGISTRY_ROWS = 119
RESERVED_PROVINCE_IDS = set(range(5032, 5045))
ALLOCATION_FIELDS = ("game_id", "rgb_r", "rgb_g", "rgb_b")
COLOR_OVERRIDES = {
    "N-15": (238, 145, 35),
    "N-16": (115, 205, 175),
    "XN-09": (225, 90, 40),
    "XN-10": (70, 190, 155),
    "XN-11": (150, 70, 230),
    "XN-12": (126, 83, 54),
    "XN-13": (196, 140, 54),
    "XN-14": (62, 166, 210),
    "XN-15": (226, 116, 42),
    "XN-16": (71, 132, 198),
    "XN-17": (141, 82, 190),
    "S-19": (20, 200, 220),
    "S-20": (106, 60, 226),
    "S-21": (190, 128, 45),
    "S-22": (67, 219, 198),
    "S-23": (24, 170, 230),
    "S-24": (230, 110, 35),
    "S-25": (135, 45, 225),
    "S-26": (55, 205, 120),
    "S-27": (225, 65, 135),
    "S-28": (160, 205, 45),
    "S-29": (226, 100, 45),
    "S-30": (45, 220, 130),
    "S-31": (150, 60, 210),
    "S-32": (210, 190, 45),
    "S-33": (30, 170, 210),
    "S-34": (220, 90, 150),
    "S-35": (80, 200, 220),
    "S-36": (200, 160, 50),
    "S-37": (90, 50, 220),
    "S-38": (220, 70, 70),
    "S-39": (245, 130, 70),
    "S-40": (75, 175, 235),
    "S-41": (40, 210, 180),
    "S-42": (210, 80, 160),
    "S-43": (175, 210, 60),
    "S-44": (110, 75, 225),
    "S-45": (235, 115, 55),
    "S-46": (55, 185, 95),
    "S-47": (185, 70, 225),
    "S-48": (235, 190, 55),
    "S-49": (45, 150, 220),
    "S-50": (205, 75, 105),
    "S-51": (95, 210, 175),
    "S-52": (140, 95, 230),
    "S-53": (210, 145, 65),
    "S-54": (235, 85, 145),
    "S-55": (60, 200, 165),
    "S-56": (155, 105, 230),
    "S-57": (225, 155, 55),
    "S-58": (70, 180, 230),
    "S-59": (215, 80, 95),
    "S-60": (105, 205, 80),
    "S-61": (200, 120, 45),
    "S-62": (55, 145, 215),
    "S-63": (115, 75, 50),
    "S-64": (130, 104, 198),
    "S-65": (146, 158, 175),
}
NON_SEQUENCE_COLOR_KEYS = {
    "N-15",
    "N-16",
    "XN-09",
    "XN-10",
    "XN-11",
    "XN-12",
    "XN-13",
    "XN-14",
    "XN-15",
    "XN-16",
    "XN-17",
    "S-20",
    "S-21",
    "S-22",
    "S-23",
    "S-24",
    "S-25",
    "S-26",
    "S-27",
    "S-28",
    "S-29",
    "S-30",
    "S-31",
    "S-32",
    "S-33",
    "S-34",
    "S-35",
    "S-36",
    "S-37",
    "S-38",
    "S-39",
    "S-40",
    "S-41",
    "S-42",
    "S-43",
    "S-44",
    "S-45",
    "S-46",
    "S-47",
    "S-48",
    "S-49",
    "S-50",
    "S-51",
    "S-52",
    "S-53",
    "S-54",
    "S-55",
    "S-56",
    "S-57",
    "S-58",
    "S-59",
    "S-60",
    "S-61",
    "S-62",
    "S-63",
    "S-64",
    "S-65",
}
EARLY_ACTIVATION_KEYS = (
    "S-04",
    "S-05",
    "S-11",
    "S-12",
    "S-17",
    "S-18",
    "S-23",
    "S-24",
    "S-25",
    "S-26",
    "S-27",
    "S-28",
)
LATE_ACTIVATION_KEYS = (
    "S-29", "S-30", "S-31", "S-32",
    "S-33", "S-34", "S-35", "S-36", "S-37", "S-38",
    "S-39", "S-40", "S-41", "S-42", "S-43", "S-44",
    "S-45", "S-46", "S-47", "S-48", "S-49",
    "S-50", "S-51", "S-52", "S-53",
    "S-54", "S-55", "S-56", "S-57", "S-58",
    "S-59", "S-60", "S-61", "S-62",
    "XN-09", "XN-10", "XN-11",
    "S-63",
    "N-15", "N-16",
    "N-17", "N-18", "N-19", "N-20", "N-21", "N-22",
    "N-23", "N-24", "N-25", "N-26", "N-27",
    "S-64", "S-65",
    "XN-12", "XN-13", "XN-14", "XN-15", "XN-16", "XN-17",
)


def read_definition_colors(definition_path: Path) -> tuple[int, set[tuple[int, int, int]]]:
    ids: list[int] = []
    colors: set[tuple[int, int, int]] = set()
    with definition_path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if not row or not row[0].isdigit():
                continue
            ids.append(int(row[0]))
            colors.add((int(row[1]), int(row[2]), int(row[3])))
    if not ids:
        raise ValueError(f"No province definitions found in {definition_path}")
    return max(ids), colors


def candidate_color(index: int, attempt: int = 0) -> tuple[int, int, int]:
    """Return a deterministic, saturated color suitable for provinces.bmp."""

    hue = ((index * 137.507764 + 19 + attempt * 29) % 360) / 360
    saturation = 0.62 + (index % 3) * 0.06
    lightness = 0.46 + (index % 2) * 0.10
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return tuple(round(channel * 255) for channel in (red, green, blue))


def allocation_row_order(rows: list[dict[str, str]]) -> list[int]:
    """Return registry row indexes in original drawing-batch order."""

    indexed_rows = list(enumerate(rows))

    def batch_number(row: dict[str, str]) -> int:
        value = row.get("draw_batch", "")
        if not re.fullmatch(r"B\d{2}", value):
            raise ValueError(f"Invalid draw_batch {value!r}; expected a value such as B01")
        return int(value[1:])

    indexed_rows.sort(key=lambda item: (batch_number(item[1]), item[0]))
    return [index for index, _row in indexed_rows]


def activation_row_order(rows: list[dict[str, str]]) -> list[int]:
    """Return the contiguous in-game activation order.

    B01 is already live.  The user selected Zhejiang, Fujian, Guangxi and
    Taiwan as the next playable slice, even though their geometry belongs to
    the later B06/B08 drawing batches.  Unimplemented IDs may therefore move,
    while the design-key RGB allocation remains frozen.
    """

    original_order = allocation_row_order(rows)
    indexes_by_key = {
        row["design_key"]: index for index, row in enumerate(rows)
    }
    missing = [
        key for key in EARLY_ACTIVATION_KEYS if key not in indexes_by_key
    ]
    missing.extend(
        key for key in LATE_ACTIVATION_KEYS if key not in indexes_by_key
    )
    if missing:
        raise ValueError(f"Missing early activation design keys: {missing}")
    b01 = [
        index for index in original_order
        if rows[index]["draw_batch"] == "B01"
    ]
    early = [indexes_by_key[key] for key in EARLY_ACTIVATION_KEYS]
    late = [indexes_by_key[key] for key in LATE_ACTIVATION_KEYS]
    already_selected = set(b01 + early + late)
    remaining = [
        index for index in original_order if index not in already_selected
    ]
    return b01 + early + remaining + late


def validate_registry_design(rows: list[dict[str, str]]) -> None:
    if len(rows) != EXPECTED_REGISTRY_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_REGISTRY_ROWS} planned provinces, found {len(rows)}"
        )
    seen_keys: set[str] = set()
    split_groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = row.get("design_key", "")
        if not key or key in seen_keys:
            raise ValueError(f"Missing or duplicate design_key: {key!r}")
        seen_keys.add(key)
        split_group = row.get("split_group", "")
        if not split_group:
            raise ValueError(f"{key}: missing split_group")
        split_groups.setdefault(split_group, []).append(row)

    for split_group, members in split_groups.items():
        reference = members[0]
        for row in members[1:]:
            for field in (
                "parent_id",
                "parent_tax",
                "parent_production",
                "parent_manpower",
                "retained_tax",
                "retained_production",
                "retained_manpower",
                "group_dev_delta",
            ):
                if row[field] != reference[field]:
                    raise ValueError(
                        f"{split_group}: group members disagree on {field}"
                    )
        calculated_delta = 0
        for dimension in ("tax", "production", "manpower"):
            parent = int(reference[f"parent_{dimension}"])
            retained = int(reference[f"retained_{dimension}"])
            new_total = sum(int(row[f"new_{dimension}"]) for row in members)
            calculated_delta += retained + new_total - parent
        recorded_delta = int(reference["group_dev_delta"])
        if recorded_delta != calculated_delta:
            raise ValueError(
                f"{split_group}: group_dev_delta {recorded_delta} does not match "
                f"the calculated change {calculated_delta}"
            )
    allocation_row_order(rows)


def build_allocations(
    rows: list[dict[str, str]],
    first_id: int,
    vanilla_colors: set[tuple[int, int, int]],
) -> list[tuple[int, tuple[int, int, int]]]:
    # Once a registry is fully frozen, preserve its row-level allocations.
    # Later batches reserve navigable-water IDs and may be appended in a
    # different design order, so recomputing every historical row would move
    # already-live province IDs.
    try:
        frozen = [
            (
                int(row["game_id"]),
                (int(row["rgb_r"]), int(row["rgb_g"]), int(row["rgb_b"])),
            )
            for row in rows
        ]
    except (KeyError, TypeError, ValueError):
        frozen = []
    if len(frozen) == len(rows):
        return frozen

    allocations: list[tuple[int, tuple[int, int, int]] | None] = [None] * len(rows)
    used_colors = set(vanilla_colors)
    color_index = 0
    frozen_colors: dict[int, tuple[int, int, int]] = {}
    for row_index in allocation_row_order(rows):
        attempt = 0
        key = rows[row_index]["design_key"]
        color = COLOR_OVERRIDES.get(key, candidate_color(color_index, attempt))
        while color in used_colors:
            if key in COLOR_OVERRIDES:
                raise ValueError(f"{key}: configured RGB override {color} is not unique")
            attempt += 1
            color = candidate_color(color_index, attempt)
        used_colors.add(color)
        frozen_colors[row_index] = color
        # The three colors chosen by the user were inserted after the original
        # registry had been frozen.  They receive IDs, but do not perturb the
        # generated RGB sequence of the still-unimplemented batches.
        if key not in NON_SEQUENCE_COLOR_KEYS:
            color_index += 1

    available_ids = (
        province_id
        for province_id in range(
            first_id, first_id + len(rows) + len(RESERVED_PROVINCE_IDS)
        )
        if province_id not in RESERVED_PROVINCE_IDS
    )
    for province_id, row_index in zip(
        available_ids, activation_row_order(rows), strict=True
    ):
        allocations[row_index] = (
            province_id,
            frozen_colors[row_index],
        )
    return [allocation for allocation in allocations if allocation is not None]


def read_registry(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Registry has no header: {path}")
        return list(reader.fieldnames), list(reader)


def expected_field_order(current_fields: list[str]) -> list[str]:
    fields = [field for field in current_fields if field not in ALLOCATION_FIELDS]
    insert_at = fields.index("design_key") + 1
    return fields[:insert_at] + list(ALLOCATION_FIELDS) + fields[insert_at:]


def apply_allocations(
    rows: list[dict[str, str]],
    allocations: list[tuple[int, tuple[int, int, int]]],
) -> None:
    for row, (game_id, color) in zip(rows, allocations, strict=True):
        row["game_id"] = str(game_id)
        row["rgb_r"] = str(color[0])
        row["rgb_g"] = str(color[1])
        row["rgb_b"] = str(color[2])


def validate_allocations(
    rows: list[dict[str, str]],
    allocations: list[tuple[int, tuple[int, int, int]]],
    vanilla_colors: set[tuple[int, int, int]],
) -> None:
    seen_ids: set[int] = set()
    seen_colors = set(vanilla_colors)
    for row, (expected_id, expected_color) in zip(rows, allocations, strict=True):
        key = row["design_key"]
        try:
            actual_id = int(row["game_id"])
            actual_color = (int(row["rgb_r"]), int(row["rgb_g"]), int(row["rgb_b"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{key}: missing or invalid ID/RGB allocation") from error
        if actual_id != expected_id:
            raise ValueError(f"{key}: expected ID {expected_id}, found {actual_id}")
        if actual_color != expected_color:
            raise ValueError(f"{key}: expected RGB {expected_color}, found {actual_color}")
        if actual_id in seen_ids:
            raise ValueError(f"{key}: duplicate province ID {actual_id}")
        if actual_color in seen_colors:
            raise ValueError(f"{key}: duplicate or vanilla RGB {actual_color}")
        seen_ids.add(actual_id)
        seen_colors.add(actual_color)


def write_registry(
    path: Path,
    fields: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            quoting=csv.QUOTE_ALL,
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vanilla-root",
        type=Path,
        required=True,
        help="EU4 installation root containing map/definition.csv",
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the frozen ID/RGB allocation into the registry",
    )
    args = parser.parse_args()

    definition_path = args.vanilla_root / "map/definition.csv"
    max_vanilla_id, vanilla_colors = read_definition_colors(definition_path)
    if max_vanilla_id != EXPECTED_VANILLA_MAX_ID:
        raise ValueError(
            f"Expected EU4 1.37.5 highest province ID "
            f"{EXPECTED_VANILLA_MAX_ID}, found {max_vanilla_id}"
        )

    fields, rows = read_registry(args.registry)
    validate_registry_design(rows)
    allocations = build_allocations(
        rows=rows,
        first_id=max_vanilla_id + 1,
        vanilla_colors=vanilla_colors,
    )
    if args.write:
        fields = expected_field_order(fields)
        apply_allocations(rows, allocations)
        write_registry(args.registry, fields, rows)

    validate_allocations(rows, allocations, vanilla_colors)
    allocated_ids = [allocation[0] for allocation in allocations]
    first_id = min(allocated_ids)
    last_id = max(allocated_ids)
    print(f"{args.registry}: {len(rows)} allocations valid ({first_id}-{last_id})")


if __name__ == "__main__":
    main()
