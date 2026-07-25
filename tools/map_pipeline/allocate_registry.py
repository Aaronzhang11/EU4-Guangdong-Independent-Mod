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
EXPECTED_REGISTRY_ROWS = 44
ALLOCATION_FIELDS = ("game_id", "rgb_r", "rgb_g", "rgb_b")
COLOR_OVERRIDES = {
    "S-19": (20, 200, 220),
    "S-20": (106, 60, 226),
    "S-21": (190, 128, 45),
    "S-22": (67, 219, 198),
}
NON_SEQUENCE_COLOR_KEYS = {"S-20", "S-21", "S-22"}


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
    """Return registry row indexes in incremental deployment order."""

    indexed_rows = list(enumerate(rows))

    def batch_number(row: dict[str, str]) -> int:
        value = row.get("draw_batch", "")
        if not re.fullmatch(r"B\d{2}", value):
            raise ValueError(f"Invalid draw_batch {value!r}; expected a value such as B01")
        return int(value[1:])

    indexed_rows.sort(key=lambda item: (batch_number(item[1]), item[0]))
    return [index for index, _row in indexed_rows]


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
    allocations: list[tuple[int, tuple[int, int, int]] | None] = [None] * len(rows)
    used_colors = set(vanilla_colors)
    color_index = 0
    for allocation_offset, row_index in enumerate(allocation_row_order(rows)):
        attempt = 0
        key = rows[row_index]["design_key"]
        color = COLOR_OVERRIDES.get(key, candidate_color(color_index, attempt))
        while color in used_colors:
            if key in COLOR_OVERRIDES:
                raise ValueError(f"{key}: configured RGB override {color} is not unique")
            attempt += 1
            color = candidate_color(color_index, attempt)
        used_colors.add(color)
        allocations[row_index] = (first_id + allocation_offset, color)
        # The three colors chosen by the user were inserted after the original
        # registry had been frozen.  They receive IDs, but do not perturb the
        # generated RGB sequence of the still-unimplemented batches.
        if key not in NON_SEQUENCE_COLOR_KEYS:
            color_index += 1
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
