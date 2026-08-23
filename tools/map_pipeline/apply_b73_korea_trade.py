#!/usr/bin/env python3
"""Create an exact Korea trade node and matching charter-company scope."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
import shutil
import struct
import sys


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
AREA_FILE = MOD / "map/area.txt"
DEFINITION = MOD / "map/definition.csv"
PROVINCES_BMP = MOD / "map/provinces.bmp"
TRADE_NODES = MOD / "common/tradenodes/00_tradenodes.txt"
TRADE_COMPANIES = MOD / "common/trade_companies/00_trade_companies.txt"
PLAN = ROOT / "planning/korea_trade_b73"
MANIFEST = PLAN / "batch_manifest.json"
NODE_BACKUP = PLAN / "pre_b73_00_tradenodes.txt"
COMPANY_BACKUP = PLAN / "pre_b73_00_trade_companies.txt"
SOURCE = MOD / "localisation_source/014_gdd_b73_korea_trade_readable_utf8.txt"
TARGET = MOD / "localisation/replace/014_gdd_b73_korea_trade_l_english.yml"

MARKER = "GDD_B73_KOREA_TRADE"
KOREA_NODE = "korea"
KOREA_COMPANY = "trade_company_korea"
KOREA_AREAS = (
    "zhuxia_xuantu_area",
    "zhuxia_paesu_area",
    "zhuxia_lolang_area",
    "zhuxia_daifang_area",
    "samhan_gyeonggi_area",
    "samhan_gangwon_area",
    "samhan_samnam_area",
)
KOREA_ANCHOR = 1375       # Korea Bay; node shield only, never company land.
NIPPON_ANCHOR = 1389      # Amakusa Sea; returns Nippon's shield to Japan.
KOREA_COLOR = (70, 135, 164)


def block_bounds(text: str, key: str, start_at: int = 0) -> tuple[int, int]:
    match = re.search(rf"(?m)^[ \t]*{re.escape(key)}[ \t]*=[ \t]*\{{", text[start_at:])
    if not match:
        raise ValueError(f"Missing block: {key}")
    start = start_at + match.start()
    brace = text.find("{", start)
    depth = 0
    for index in range(brace, len(text)):
        depth += (text[index] == "{") - (text[index] == "}")
        if depth == 0:
            return start, index + 1
    raise ValueError(f"Unclosed block: {key}")


def top_blocks(text: str):
    position = 0
    while True:
        match = re.search(r"(?m)^([A-Za-z0-9_]+)[ \t]*=[ \t]*\{", text[position:])
        if not match:
            return
        name = match.group(1)
        start = position + match.start()
        begin, end = block_bounds(text, name, start)
        yield name, begin, end, text[begin:end]
        position = end


def nested_ids(block: str, key: str) -> set[int]:
    start, end = block_bounds(block, key)
    body = re.sub(r"#.*", "", block[start:end])
    return {int(value) for value in re.findall(r"\b\d+\b", body)}


def memberships(text: str, nested_key: str, prefix: str = "") -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    for name, _start, _end, block in top_blocks(text):
        if prefix and not name.startswith(prefix):
            continue
        try:
            result[name] = nested_ids(block, nested_key)
        except ValueError:
            pass
    return result


def area_members() -> dict[str, set[int]]:
    text = AREA_FILE.read_text(encoding="latin-1")
    result: dict[str, set[int]] = {}
    for name, _start, _end, block in top_blocks(text):
        result[name] = {int(value) for value in re.findall(r"\b\d+\b", re.sub(r"#.*", "", block))}
    return result


def korea_land() -> set[int]:
    areas = area_members()
    missing = set(KOREA_AREAS) - areas.keys()
    if missing:
        raise ValueError(f"Missing Korean areas: {sorted(missing)}")
    groups = [areas[name] for name in KOREA_AREAS]
    land = set().union(*groups)
    if sum(map(len, groups)) != len(land):
        raise ValueError("Korean areas overlap")
    if len(land) != 30:
        raise ValueError(f"Korean trade scope has {len(land)} provinces, expected 30")
    return land


def wrapped_ids(ids: set[int], indent: str = "        ") -> str:
    values = sorted(ids)
    rows = [values[index:index + 15] for index in range(0, len(values), 15)]
    return "\n".join(
        indent + " ".join(map(str, row)) + (f" # {MARKER}" if index == 0 else "")
        for index, row in enumerate(rows)
    )


def id_block(key: str, ids: set[int]) -> str:
    return f"    {key}={{\n{wrapped_ids(ids)}\n    }}"


def set_nested_ids(text: str, outer: str, key: str, ids: set[int]) -> str:
    start, end = block_bounds(text, outer)
    block = text[start:end]
    nested_start, nested_end = block_bounds(block, key)
    block = block[:nested_start] + id_block(key, ids) + block[nested_end:]
    return text[:start] + block + text[end:]


def upsert_block(text: str, key: str, rendered: str) -> str:
    names = {name for name, *_rest in top_blocks(text)}
    if key in names:
        start, end = block_bounds(text, key)
        return text[:start] + rendered + text[end:]
    return text.rstrip() + "\n\n" + rendered + "\n"


def set_scalar(text: str, outer: str, key: str, value: int) -> str:
    start, end = block_bounds(text, outer)
    block = text[start:end]
    block, count = re.subn(
        rf"(?m)^(\s*{re.escape(key)}\s*=\s*)\d+\s*$",
        rf"\g<1>{value}",
        block,
        count=1,
    )
    if count != 1:
        raise ValueError(f"{outer}: missing scalar {key}")
    return text[:start] + block + text[end:]


def render_korea_node(land: set[int]) -> str:
    red, green, blue = KOREA_COLOR
    return f'''{KOREA_NODE}={{
    location={KOREA_ANCHOR}
    color={{
        {red} {green} {blue}
    }}
    outgoing={{
        name="nippon"
        path={{
            1375 1376 1389
        }}
        control={{
            4760.000000 1288.000000 4810.000000 1238.000000 4860.000000 1197.000000
        }}
    }}
{id_block("members", land | {KOREA_ANCHOR})}
}}'''


def render_korea_company(land: set[int]) -> str:
    red, green, blue = KOREA_COLOR
    return f'''{KOREA_COMPANY} = {{
    color = {{ {red} {green} {blue} }}

{id_block("provinces", land)}

    names = {{
        name = "GDD_TRADE_COMPANY_KOREA"
    }}
}}'''


def update_nodes(land: set[int]) -> dict[str, int]:
    text = TRADE_NODES.read_text(encoding="latin-1")
    before = {name: len(ids) for name, ids in memberships(text, "members").items()}
    managed = land | {KOREA_ANCHOR, NIPPON_ANCHOR}
    for node, ids in list(memberships(text, "members").items()):
        if ids & managed:
            text = set_nested_ids(text, node, "members", ids - managed)
    nippon = memberships(text, "members").get("nippon")
    if nippon is None:
        raise ValueError("Missing Nippon trade node")
    text = set_nested_ids(text, "nippon", "members", nippon | {NIPPON_ANCHOR})
    text = set_scalar(text, "nippon", "location", NIPPON_ANCHOR)
    text = upsert_block(text, KOREA_NODE, render_korea_node(land))
    TRADE_NODES.write_text(text.rstrip() + "\n", encoding="latin-1")
    return before


def update_companies(land: set[int]) -> dict[str, int]:
    text = TRADE_COMPANIES.read_text(encoding="latin-1")
    before = {
        name: len(ids)
        for name, ids in memberships(text, "provinces", "trade_company_").items()
    }
    for company, ids in list(memberships(text, "provinces", "trade_company_").items()):
        if ids & land:
            text = set_nested_ids(text, company, "provinces", ids - land)
    text = upsert_block(text, KOREA_COMPANY, render_korea_company(land))
    TRADE_COMPANIES.write_text(text.rstrip() + "\n", encoding="latin-1")
    return before


def write_localisation() -> None:
    SOURCE.write_text(
        'l_english:\n'
        ' korea:0 "朝鲜"\n'
        ' trade_company_korea:0 "朝鲜特许公司"\n'
        ' GDD_TRADE_COMPANY_KOREA:0 "朝鲜特许公司"\n',
        encoding="utf-8-sig",
    )
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file, verify_file
    encode_file(SOURCE, TARGET)
    verify_file(SOURCE, TARGET)


def definition_rows() -> dict[int, tuple[int, int, int]]:
    result: dict[int, tuple[int, int, int]] = {}
    for line in DEFINITION.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if fields and fields[0].isdigit():
            result[int(fields[0])] = tuple(map(int, fields[1:4]))
    return result


def bmp_present_colors(targets: set[tuple[int, int, int]]) -> set[tuple[int, int, int]]:
    """Return target RGB colours that have at least one pixel in a 24-bit BMP."""
    data = PROVINCES_BMP.read_bytes()
    offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bits = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    if bits != 24 or compression != 0:
        raise ValueError("provinces.bmp must remain an uncompressed 24-bit BMP")
    width = abs(width)
    height = abs(height)
    stride = ((width * 3 + 3) // 4) * 4
    found: set[tuple[int, int, int]] = set()
    for row_index in range(height):
        row = memoryview(data)[offset + row_index * stride:offset + row_index * stride + width * 3]
        for blue, green, red in struct.iter_unpack("BBB", row):
            rgb = (red, green, blue)
            if rgb in targets:
                found.add(rgb)
        if found == targets:
            break
    return found


def validate(land: set[int]) -> dict[str, object]:
    node_text = TRADE_NODES.read_text(encoding="latin-1")
    nodes = memberships(node_text, "members")
    expected_node = land | {KOREA_ANCHOR}
    if nodes.get(KOREA_NODE) != expected_node:
        raise ValueError("Korea node is not the exact reviewed scope")
    node_owners: dict[int, list[str]] = defaultdict(list)
    for node, ids in nodes.items():
        for province_id in ids:
            node_owners[province_id].append(node)
    for province_id in land:
        if node_owners[province_id] != [KOREA_NODE]:
            raise ValueError(f"Korean province {province_id} node owners: {node_owners[province_id]}")
    korea_block = next(block for name, _s, _e, block in top_blocks(node_text) if name == KOREA_NODE)
    if not re.search(r'(?ms)outgoing\s*=\s*\{.*?name\s*=\s*"nippon"', korea_block):
        raise ValueError("Korea must flow to Nippon")
    nippon_block = next(block for name, _s, _e, block in top_blocks(node_text) if name == "nippon")
    if not re.search(r'(?ms)outgoing\s*=\s*\{.*?name\s*=\s*"hangzhou"', nippon_block):
        raise ValueError("Nippon must continue to Hangzhou")
    if not re.search(rf"(?m)^\s*location\s*=\s*{NIPPON_ANCHOR}\s*$", nippon_block):
        raise ValueError("Nippon shield was not moved to Japan")

    company_text = TRADE_COMPANIES.read_text(encoding="latin-1")
    companies = memberships(company_text, "provinces", "trade_company_")
    if companies.get(KOREA_COMPANY) != land:
        raise ValueError("Korea charter company is not the exact reviewed scope")
    company_owners: dict[int, list[str]] = defaultdict(list)
    for company, ids in companies.items():
        for province_id in ids:
            company_owners[province_id].append(company)
    for province_id in land:
        if company_owners[province_id] != [KOREA_COMPANY]:
            raise ValueError(
                f"Korean province {province_id} companies: {company_owners[province_id]}"
            )
    definitions = definition_rows()
    if not land <= definitions.keys():
        raise ValueError(f"Korean scope has undefined IDs: {sorted(land - definitions.keys())}")
    target_colors = {definitions[province_id] for province_id in land}
    present_colors = bmp_present_colors(target_colors)
    zero_pixel = [
        province_id
        for province_id in sorted(land)
        if definitions[province_id] not in present_colors
    ]
    if zero_pixel:
        raise ValueError(f"Korean company contains zero-pixel provinces: {zero_pixel}")
    return {
        "node": KOREA_NODE,
        "node_label": "朝鲜",
        "company": KOREA_COMPANY,
        "company_label": "朝鲜特许公司",
        "land_provinces": sorted(land),
        "land_count": len(land),
        "node_anchor": KOREA_ANCHOR,
        "nippon_anchor": NIPPON_ANCHOR,
        "trade_flow": ["korea", "nippon", "hangzhou"],
    }


def apply() -> None:
    PLAN.mkdir(parents=True, exist_ok=True)
    if not NODE_BACKUP.exists():
        shutil.copy2(TRADE_NODES, NODE_BACKUP)
    if not COMPANY_BACKUP.exists():
        shutil.copy2(TRADE_COMPANIES, COMPANY_BACKUP)
    land = korea_land()
    existing = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    before_nodes = existing.get("before_node_member_counts") or update_nodes(land)
    before_companies = existing.get("before_company_member_counts") or update_companies(land)
    if existing:
        update_nodes(land)
        update_companies(land)
    write_localisation()
    result = validate(land)
    MANIFEST.write_text(
        json.dumps(
            {
                "batch": "B73_KOREA_TRADE",
                "purpose": "Separate the complete Korea region into one exact trade node and charter company.",
                "terminal_order": "Run after B49, B58 and B59.",
                "area_policy": list(KOREA_AREAS),
                "before_node_member_counts": before_nodes,
                "before_company_member_counts": before_companies,
                "backups": {
                    "trade_nodes": str(NODE_BACKUP.relative_to(ROOT)),
                    "trade_companies": str(COMPANY_BACKUP.relative_to(ROOT)),
                },
                "validation": result,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        f"{MARKER}; LAND:{len(land)}; FLOW:korea->nippon->hangzhou; "
        f"COMPANY:{KOREA_COMPANY}"
    )


if __name__ == "__main__":
    apply()
