#!/usr/bin/env python3
"""Apply the B36 area-contiguity and Yunnan trade-company correction."""

from __future__ import annotations

import re
from pathlib import Path

import audit_area_connectivity as audit


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
MARKER = "B36 area and trade-company consistency"

AREA_MEMBERS = {
    # Qinzhou remains with Guyuan, while both four-province areas are connected.
    "xi_shaanxi_area": (2180, 5277, 5291, 5306),
    "longyou_area": (2181, 5276, 5278, 5305),
    # Kuizhou belongs to Ba; Shizhou belongs to Jing-Chu.
    "chongqing_area": (680, 5026, 5027, 4987, 5028),
    "jingyi_shinan_area": (2172, 5015, 5010, 5013),
}

YUNNAN_CHENGDU_CORRECTION = (662, 663, 5230, 5231, 5232, 5233, 5234, 5240, 5241)
YUNNAN_ALL = {
    5224, 5225, 2167, 5226,
    5227, 661, 5228, 2166,
    5229, 662, 5230, 5231,
    5232, 5233, 5234, 675,
    5235, 5236, 5238, 660, 5239,
    5240, 5241, 663, 2165, 5237,
}

ADJACENCY = "2172;5013;sea;5037;-1;-1;-1;-1;Jingzhou-Shizhou Yichang crossing"


def block_bounds(text: str, key: str, start_at: int = 0) -> tuple[int, int]:
    match = re.search(
        rf"(?m)^[ \t]*{re.escape(key)}[ \t]*=[ \t]*\{{",
        text[start_at:],
    )
    if not match:
        raise ValueError(f"Missing block: {key}")
    start = start_at + match.start()
    brace = text.find("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise ValueError(f"Unclosed block: {key}")


def update_areas() -> None:
    path = MAP / "area.txt"
    text = path.read_text(encoding="cp1252", errors="strict")
    for key, province_ids in AREA_MEMBERS.items():
        start, end = block_bounds(text, key)
        replacement = (
            f"{key} = {{ # {MARKER}\n"
            f"    {' '.join(map(str, province_ids))}\n"
            "}"
        )
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="cp1252")


def remove_ids_from_lines(body: str, province_ids: set[int]) -> str:
    pattern = re.compile(r"(?<!\d)(?:" + "|".join(map(str, sorted(province_ids, reverse=True))) + r")(?!\d)")
    output = []
    for line in body.splitlines():
        if f"# {MARKER}" in line or "# B36 Yunnan trade-company correction" in line:
            continue
        code, separator, comment = line.partition("#")
        code = pattern.sub("", code)
        code = re.sub(r"(?<=\S)[ \t]{2,}", " ", code).rstrip()
        if separator:
            line = code + (" " if code.strip() else "") + "#" + comment
        else:
            line = code
        if line.strip():
            output.append(line)
    return "\n".join(output)


def update_company_block(text: str, company: str, add_to_chengdu: bool) -> str:
    start, end = block_bounds(text, company)
    block = text[start:end]
    nested_start, nested_end = block_bounds(block, "provinces")
    open_brace = block.find("{", nested_start)
    close_brace = nested_end - 1
    body = remove_ids_from_lines(
        block[open_brace + 1:close_brace],
        set(YUNNAN_CHENGDU_CORRECTION),
    )
    if add_to_chengdu:
        body = (
            "\n"
            + body.rstrip()
            + "\n        "
            + " ".join(map(str, YUNNAN_CHENGDU_CORRECTION))
            + f" # {MARKER}\n    "
        )
    else:
        body = "\n" + body.rstrip() + "\n    "
    block = block[:open_brace + 1] + body + block[close_brace:]
    return text[:start] + block + text[end:]


def update_trade_companies() -> None:
    path = MOD / "common/trade_companies/00_trade_companies.txt"
    text = path.read_text(encoding="cp1252", errors="strict")
    text = update_company_block(text, "trade_company_south_china", False)
    text = update_company_block(text, "trade_company_chengdu", True)
    path.write_text(text, encoding="cp1252")


def update_adjacency() -> None:
    path = MAP / "adjacencies.csv"
    text = path.read_text(encoding="cp1252", errors="strict")
    lines = text.splitlines()
    target_pair = {2172, 5013}
    for line in lines:
        fields = line.split(";")
        if len(fields) >= 2 and fields[0].isdigit() and fields[1].isdigit():
            if {int(fields[0]), int(fields[1])} == target_pair:
                return
    sentinel = next((index for index, line in enumerate(lines) if line.startswith("-1;-1;")), len(lines))
    lines.insert(sentinel, ADJACENCY)
    path.write_text("\n".join(lines) + "\n", encoding="cp1252")


def nested_ids(text: str, company: str) -> set[int]:
    start, end = block_bounds(text, company)
    block = text[start:end]
    nested_start, nested_end = block_bounds(block, "provinces")
    body = block[nested_start:nested_end]
    body = re.sub(r"#.*", "", body)
    return {int(value) for value in re.findall(r"\b\d+\b", body)}


def verify() -> None:
    area_text = (MAP / "area.txt").read_text(encoding="cp1252", errors="strict")
    areas = {key: audit.area_ids(body) for key, body in audit.blocks(area_text, "_area").items()}
    for key, expected in AREA_MEMBERS.items():
        if tuple(areas.get(key, ())) != expected:
            raise ValueError(f"{key}: expected {expected}, got {areas.get(key)}")

    targeted = {province_id for values in AREA_MEMBERS.values() for province_id in values}
    owners = {
        province_id: [key for key, values in areas.items() if province_id in values]
        for province_id in targeted
    }
    bad_owners = {province_id: values for province_id, values in owners.items() if len(values) != 1}
    if bad_owners:
        raise ValueError(f"Area membership is not unique: {bad_owners}")

    adjacency_text = (MAP / "adjacencies.csv").read_text(encoding="cp1252", errors="strict")
    pairs = {
        frozenset((int(fields[0]), int(fields[1])))
        for line in adjacency_text.splitlines()
        if len(fields := line.split(";")) >= 2 and fields[0].isdigit() and fields[1].isdigit()
    }
    if frozenset((2172, 5013)) not in pairs:
        raise ValueError("Missing Jingzhou-Shizhou river crossing")

    company_text = (MOD / "common/trade_companies/00_trade_companies.txt").read_text(
        encoding="cp1252", errors="strict"
    )
    south = nested_ids(company_text, "trade_company_south_china")
    chengdu = nested_ids(company_text, "trade_company_chengdu")
    if YUNNAN_ALL - chengdu:
        raise ValueError(f"Yunnan provinces missing from Chengdu company: {sorted(YUNNAN_ALL - chengdu)}")
    if YUNNAN_ALL & south:
        raise ValueError(f"Yunnan provinces remain in South China company: {sorted(YUNNAN_ALL & south)}")


def main() -> None:
    update_areas()
    update_trade_companies()
    update_adjacency()
    verify()
    print(
        f"{MARKER}; AREAS:{len(AREA_MEMBERS)}; "
        f"YUNNAN_TO_CHENGDU:{len(YUNNAN_CHENGDU_CORRECTION)}; ADJACENCIES:1"
    )


if __name__ == "__main__":
    main()
