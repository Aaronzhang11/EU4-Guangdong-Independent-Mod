#!/usr/bin/env python3
"""Apply the reviewed B49 eight-node Chinese trade network.

The transaction derives the 382 core land-province assignments from the
canonical area file, preserves the B48 opening centre hierarchy, redirects
four frontier groups to existing external nodes, and makes Hangzhou/Wuyue the
only terminal node inside the Chinese core network.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
TRADE_NODES = MOD / "common/tradenodes/00_tradenodes.txt"
TRADE_COMPANIES = MOD / "common/trade_companies/00_trade_companies.txt"
AREA_FILE = MOD / "map/area.txt"
HISTORY = MOD / "history/provinces"
PLAN = ROOT / "planning/trade_nodes_b49"
BACKUP = PLAN / "pre_b49_00_tradenodes.txt"
COMPANY_BACKUP = PLAN / "pre_b49_user_fix_00_trade_companies.txt"
MANIFEST = PLAN / "batch_manifest.json"
SOURCE = MOD / "localisation_source/003_gdd_b49_trade_node_overrides_readable_utf8.txt"
TARGET = MOD / "localisation/replace/003_gdd_b49_trade_node_overrides_l_english.yml"
MARKER = "GDD_B49_EIGHT_NODE_TRADE_NETWORK"


NODE_AREAS = {
    "hangzhou": (
        "zhejiang_area", "east_zhejiang_area", "jinqu_chuzhou_area",
        "wanjiang_area", "huining_area", "yingtian_area",
        "jinling_wuhui_area", "xuhuai_haizhou_area",
        "huaiyang_tongtai_area", "huaiying_area", "jianghuai_area",
    ),
    "canton": (
        "pearl_river_delta_area", "guangdong_area", "dongjiang_area",
        "chaoshan_area", "west_guangdong_area", "hainan_area",
        "fujian_area", "minnan_area", "west_fujian_area", "taiwan_area",
        "guangxi_area", "guidong_area", "youjiang_area",
    ),
    "huguang": (
        "jiangxi_area", "south_jiangxi_area", "xunyang_area", "gannan_area",
        "dongting_area", "hunan_area", "southwest_hunan_area",
        "wuling_hunan_area", "lishui_area", "hengchen_area",
        "dean_qihuang_area", "wuhan_enan_area", "hanshang_area",
        "yunmeng_jingmen_area", "jingyi_area", "yigui_area",
    ),
    "chengdu": (
        "sichuan_area", "chongqing_area", "baqu_area", "fuling_area",
        "xiajiang_area", "chuannan_area", "chuanbei_area", "liangshan_area",
        "ganzi_area", "aba_area", "songmao_area", "jiaya_area",
    ),
    "yungui": (
        "yunnan_area", "diannan_area", "dianxinan_area", "diandong_area",
        "dianxi_area", "dianxibei_area", "qianxi_area", "qiandong_area",
    ),
    "xian": (
        "gansu_area", "hexi_area", "longnan_area", "longyou_area",
        "ningxia_area", "shaanxi_area", "xi_shaanxi_area",
        "nan_shaanxi_area", "bei_shaanxi_area", "changan_area",
    ),
    "zhongyuan": (
        "luxi_area", "qizhou_area", "denglai_area", "lunan_area",
        "guide_xuchen_area", "chengzhou_area", "hebei_zhangwei_area",
        "wangji_area", "wandeng_area", "rucai_area",
    ),
    "beijing": (
        "hebei_area", "zhong_hebei_area", "dong_hebei_area", "yandu_area",
        "shanxi_area", "hedong_area", "shangdang_area", "yanmen_area",
        "xi_liaoning_area", "south_hebei_area",
    ),
}

NODE_LABELS = {
    "hangzhou": "吴越",
    "canton": "百越",
    "huguang": "荆楚",
    "chengdu": "巴蜀",
    "yungui": "滇夜郎",
    "xian": "秦陇",
    "zhongyuan": "河济",
    "beijing": "幽燕",
}

EXPECTED_LAND_COUNTS = {
    "hangzhou": 49,
    "canton": 57,
    "huguang": 62,
    "chengdu": 48,
    "yungui": 36,
    "xian": 46,
    "zhongyuan": 39,
    "beijing": 45,
}

BASE_AREA_LAND_COUNTS = {
    "hangzhou": 49,
    "canton": 57,
    "huguang": 62,
    "chengdu": 48,
    "yungui": 36,
    "xian": 46,
    "zhongyuan": 39,
    "beijing": 45,
}

# "Zhaodi" means the complete localized Area, not the starting territory of
# the Zhao country tag. Freeze its current membership so an area rewrite
# cannot silently change this reviewed trade policy.
ZHAODI_AREA = "south_hebei_area"
ZHAODI_IDS = {696, 2137, 4195, 5218, 5220, 5221}
ANNAM_IDS = {610, 613, 616, 1016, 2372, 2373, 4819, 4820, 4821}
CORE_LAND_OVERRIDES: dict[str, set[int]] = {}
NODE_EXTRA_MEMBERS = {"canton": ANNAM_IDS}
TRADE_COMPANY_BY_NODE = {
    "hangzhou": "trade_company_east_china",
    "canton": "trade_company_south_china",
    "huguang": "trade_company_huguang",
    "chengdu": "trade_company_chengdu",
    "yungui": "trade_company_yungui",
    "xian": "trade_company_xian",
    "zhongyuan": "trade_company_zhongyuan",
    "beijing": "trade_company_north_china",
}

EXTERNAL_COMPANY_BY_NODE = {
    "yumen": "trade_company_yumen",
    "girin": "trade_company_girin",
    "lhasa": "trade_company_lhasa",
}

# Water anchors make the node shields and arrows sit in readable positions.
NODE_ANCHORS = {
    "hangzhou": {1373},       # Yang Tse Delta
    "canton": {1371},        # Guangzhou Bay
    "huguang": {1897},       # Dongting
    "chengdu": set(),
    "yungui": set(),
    "xian": set(),
    "zhongyuan": set(),
    "beijing": {4233},       # Bohai Sea
}

# These provinces were historically carried by one of the five vanilla China
# nodes, but they are deliberately outside the new eight-node core.
EXTERNAL_REALLOCATION = {
    "yumen": {701, 702, 709, 2114, 2191, 2747, 4223, 4670, 4671, 4676},
    "girin": {726, 2112, 2113, 4652, 5204, 5205},
    "lhasa": {2131, 2132},
}

NODE_STYLE = {
    "hangzhou": {"location": 1373, "color": (236, 196, 52), "inland": False, "end": True},
    "canton": {"location": 1371, "color": (38, 166, 126), "inland": False, "end": False},
    "huguang": {"location": 1897, "color": (112, 174, 76), "inland": False, "end": False},
    "chengdu": {"location": 679, "color": (186, 96, 96), "inland": True, "end": False},
    "yungui": {"location": 662, "color": (145, 104, 181), "inland": True, "end": False},
    "xian": {"location": 700, "color": (205, 142, 55), "inland": True, "end": False},
    "zhongyuan": {"location": 688, "color": (76, 137, 194), "inland": True, "end": False},
    "beijing": {"location": 4233, "color": (87, 106, 151), "inland": False, "end": False},
}

# (target, path province IDs, control-point x/y pairs).  Paths are intentionally
# authored against the current map instead of copied from another mod's bitmap.
CORE_ROUTES = {
    "hangzhou": (),
    "canton": (
        ("huguang", (1371, 1897), (4611, 989, 4565, 1130)),
        ("hangzhou", (1371, 1372, 1373), (4611, 989, 4723, 1165)),
    ),
    "huguang": (
        ("zhongyuan", (1897, 681, 687, 688), (4565, 1130, 4589, 1230)),
        ("hangzhou", (1897, 683, 684, 1373), (4565, 1130, 4723, 1165)),
    ),
    "chengdu": (
        ("xian", (679, 689, 700), (4440, 1155, 4511, 1220)),
        ("huguang", (679, 681, 1897), (4440, 1155, 4565, 1130)),
        ("yungui", (679, 662), (4440, 1155, 4420, 1059)),
    ),
    "yungui": (
        ("canton", (662, 663, 1371), (4420, 1059, 4611, 989)),
        ("huguang", (662, 675, 1897), (4420, 1059, 4565, 1130)),
    ),
    "xian": (
        ("beijing", (700, 693, 1816, 4233), (4511, 1220, 4678, 1304)),
        ("zhongyuan", (700, 1836, 688), (4511, 1220, 4589, 1230)),
        ("huguang", (700, 689, 681, 1897), (4511, 1220, 4565, 1130)),
    ),
    "zhongyuan": (
        ("beijing", (688, 696, 1816, 4233), (4589, 1230, 4678, 1304)),
        ("hangzhou", (688, 685, 1373), (4589, 1230, 4723, 1165)),
    ),
    "beijing": (
        ("hangzhou", (4233, 1375, 1374, 1373), (4678, 1304, 4723, 1165)),
    ),
}

EXTERNAL_ROUTES = {
    ("malacca", "canton"): ((1361, 1362, 1367, 1371), (4470, 623, 4611, 989)),
    ("philippines", "canton"): ((1397, 1394, 1371), (4711, 876, 4611, 989)),
    ("yumen", "xian"): ((707, 698, 689, 700), (4436, 1282, 4511, 1220)),
}


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
    try:
        start, end = block_bounds(block, key)
    except ValueError:
        return set()
    body = re.sub(r"#.*", "", block[start:end])
    return {int(value) for value in re.findall(r"\b\d+\b", body)}


def wrapped_ids(ids: set[int], indent: str = "        ") -> str:
    values = sorted(ids)
    rows = [values[index:index + 16] for index in range(0, len(values), 16)]
    rendered = []
    for index, row in enumerate(rows):
        suffix = f" # {MARKER}" if index == 0 else ""
        rendered.append(indent + " ".join(map(str, row)) + suffix)
    return "\n".join(rendered)


def id_block(key: str, ids: set[int]) -> str:
    return f"    {key}={{\n" + wrapped_ids(ids) + "\n    }"


def members_block(ids: set[int]) -> str:
    return id_block("members", ids)


def set_outer_ids(text: str, outer: str, key: str, ids: set[int]) -> str:
    start, end = block_bounds(text, outer)
    block = text[start:end]
    member_start, member_end = block_bounds(block, key)
    block = block[:member_start] + id_block(key, ids) + block[member_end:]
    return text[:start] + block + text[end:]


def set_node_members(text: str, node: str, ids: set[int]) -> str:
    return set_outer_ids(text, node, "members", ids)


def remove_outer_ids(text: str, outer: str, key: str, ids: set[int]) -> str:
    start, end = block_bounds(text, outer)
    block = text[start:end]
    nested_start, nested_end = block_bounds(block, key)
    nested = block[nested_start:nested_end]
    open_brace = nested.find("{")
    close_brace = nested.rfind("}")
    pattern = re.compile(
        r"(?<!\d)(?:" + "|".join(map(str, sorted(ids, reverse=True))) + r")(?!\d)"
    )
    output = []
    for line in nested[open_brace + 1:close_brace].splitlines():
        if f"# {MARKER}" in line:
            continue
        code, separator, comment = line.partition("#")
        indent = code[:len(code) - len(code.lstrip(" \t"))]
        content = pattern.sub("", code[len(indent):])
        content = re.sub(r"[ \t]{2,}", " ", content).strip()
        code = indent + content
        if not code.strip() and not separator:
            continue
        output.append(code + ((" # " + comment.strip()) if separator else ""))
    body = "\n" + "\n".join(output).rstrip() + "\n    "
    nested = nested[:open_brace + 1] + body + nested[close_brace:]
    block = block[:nested_start] + nested + block[nested_end:]
    return text[:start] + block + text[end:]


def append_outer_ids(text: str, outer: str, key: str, ids: set[int]) -> str:
    start, end = block_bounds(text, outer)
    block = text[start:end]
    nested_start, nested_end = block_bounds(block, key)
    nested = block[nested_start:nested_end]
    close = nested.rfind("}")
    line = "        " + " ".join(map(str, sorted(ids))) + f" # {MARKER}"
    nested = nested[:close].rstrip() + "\n" + line + "\n    " + nested[close:]
    block = block[:nested_start] + nested + block[nested_end:]
    return text[:start] + block + text[end:]


def render_outgoing(target: str, path: tuple[int, ...], control: tuple[int, ...]) -> str:
    if len(control) % 2:
        raise ValueError(f"Odd control coordinate count for {target}")
    path_text = " ".join(map(str, path))
    control_text = " ".join(f"{value:.6f}" for value in control)
    return (
        "    outgoing={\n"
        f'        name="{target}"\n'
        "        path={\n"
        f"            {path_text}\n"
        "        }\n"
        "        control={\n"
        f"            {control_text}\n"
        "        }\n"
        "    }"
    )


def render_node(node: str, ids: set[int]) -> str:
    style = NODE_STYLE[node]
    red, green, blue = style["color"]
    lines = [
        f"{node}={{",
        f"    location={style['location']}",
        "    color={",
        f"        {red} {green} {blue}",
        "    }",
    ]
    if style["inland"]:
        lines.append("    inland=yes")
    for target, path, control in CORE_ROUTES[node]:
        lines.append(render_outgoing(target, path, control))
    lines.append(members_block(ids))
    if style["end"]:
        lines.append("    end=yes")
    lines.append("}")
    return "\n".join(lines)


def render_trade_company(company: str, node: str, ids: set[int]) -> str:
    red, green, blue = NODE_STYLE[node]["color"]
    return (
        f"{company} = {{\n"
        f"    color = {{ {red} {green} {blue} }}\n\n"
        f"{id_block('provinces', ids)}\n\n"
        "    names = {\n"
        f'        name = "GDD_TRADE_COMPANY_{node.upper()}"\n'
        "    }\n"
        "}"
    )


def upsert_top_block(text: str, node: str, rendered: str) -> str:
    names = {name for name, *_rest in top_blocks(text)}
    if node in names:
        start, end = block_bounds(text, node)
        return text[:start] + rendered + text[end:]
    return text.rstrip() + "\n\n" + rendered + "\n"


def outgoing_spans(block: str):
    position = 0
    while True:
        match = re.search(r"(?m)^[ \t]*outgoing[ \t]*=[ \t]*\{", block[position:])
        if not match:
            return
        start = position + match.start()
        begin, end = block_bounds(block, "outgoing", start)
        target = re.search(r'(?m)^\s*name\s*=\s*"([A-Za-z0-9_]+)"', block[begin:end])
        if not target:
            raise ValueError("Outgoing block lacks a target name")
        yield target.group(1), begin, end
        position = end


def upsert_external_route(
    text: str,
    node: str,
    target: str,
    path: tuple[int, ...],
    control: tuple[int, ...],
) -> str:
    start, end = block_bounds(text, node)
    block = text[start:end]
    spans = [(begin, finish) for name, begin, finish in outgoing_spans(block) if name == target]
    for begin, finish in reversed(spans):
        block = block[:begin] + block[finish:]
    # Removing and reinserting an outgoing block must not accumulate blank
    # separator lines on every terminal replay.
    block = re.sub(r"\n(?:[ \t]*\n){2,}", "\n\n", block)
    member_start, _member_end = block_bounds(block, "members")
    insertion = render_outgoing(target, path, control) + "\n"
    block = block[:member_start] + insertion + block[member_start:]
    return text[:start] + block + text[end:]


def area_members(path: Path) -> dict[str, set[int]]:
    text = path.read_text(encoding="cp1252")
    result = {}
    for name, _start, _end, block in top_blocks(text):
        body = re.sub(r"#.*", "", block)
        result[name] = {int(value) for value in re.findall(r"\b\d+\b", body)}
    return result


def target_members(mod_root: Path = MOD) -> tuple[dict[str, set[int]], dict[str, set[int]]]:
    areas = area_members(mod_root / "map/area.txt")
    if areas.get(ZHAODI_AREA) != ZHAODI_IDS:
        raise ValueError(
            f"{ZHAODI_AREA} membership drifted: {sorted(areas.get(ZHAODI_AREA, set()))}, "
            f"expected {sorted(ZHAODI_IDS)}"
        )
    land = {}
    claimed_areas = set()
    for node, area_names in NODE_AREAS.items():
        if claimed_areas & set(area_names):
            raise ValueError(f"B49 area policy overlaps at {claimed_areas & set(area_names)}")
        claimed_areas.update(area_names)
        missing = set(area_names) - areas.keys()
        if missing:
            raise ValueError(f"Missing B49 areas for {node}: {sorted(missing)}")
        land[node] = set().union(*(areas[name] for name in area_names))
        if len(land[node]) != BASE_AREA_LAND_COUNTS[node]:
            raise ValueError(
                f"{node} area-derived land count is {len(land[node])}, "
                f"expected {BASE_AREA_LAND_COUNTS[node]}"
            )
    all_land = set().union(*land.values())
    if sum(map(len, land.values())) != len(all_land):
        raise ValueError("A province is assigned to multiple B49 core nodes")
    for node, ids in CORE_LAND_OVERRIDES.items():
        if not ids <= all_land:
            raise ValueError(f"Core override contains non-core IDs: {sorted(ids - all_land)}")
        for current in land.values():
            current.difference_update(ids)
        land[node].update(ids)
    for node, expected_count in EXPECTED_LAND_COUNTS.items():
        if len(land[node]) != expected_count:
            raise ValueError(
                f"{node} post-override land count is {len(land[node])}, expected {expected_count}"
            )
    if not ZHAODI_IDS <= land["beijing"] or ZHAODI_IDS & land["zhongyuan"]:
        raise ValueError("The complete Zhaodi area must belong to Youyan, not Heji")
    full = {
        node: ids | NODE_ANCHORS[node] | NODE_EXTRA_MEMBERS.get(node, set())
        for node, ids in land.items()
    }
    return land, full


def trade_company_policy(mod_root: Path = MOD) -> tuple[dict[str, set[int]], dict[str, set[int]]]:
    """Return exact core-company sets and targeted external-company additions."""
    land, _full = target_members(mod_root)
    core = {
        TRADE_COMPANY_BY_NODE[node]: set(ids)
        for node, ids in land.items()
    }
    core[TRADE_COMPANY_BY_NODE["canton"]].update(ANNAM_IDS)
    external = {
        EXTERNAL_COMPANY_BY_NODE[node]: set(ids)
        for node, ids in EXTERNAL_REALLOCATION.items()
    }
    return core, external


def node_memberships(text: str) -> dict[str, set[int]]:
    return {
        name: nested_ids(block, "members")
        for name, _start, _end, block in top_blocks(text)
        if "members" in block
    }


def company_memberships(text: str) -> dict[str, set[int]]:
    return {
        name: nested_ids(block, "provinces")
        for name, _start, _end, block in top_blocks(text)
        if name.startswith("trade_company_") and "provinces" in block
    }


def node_routes(text: str) -> dict[str, tuple[str, ...]]:
    result = {}
    for name, _start, _end, block in top_blocks(text):
        result[name] = tuple(target for target, _begin, _end in outgoing_spans(block))
    return result


def opening_history_values(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="cp1252")
    dated = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", text)
    opening = text[:dated.start()] if dated else text
    development = 0
    for key in ("base_tax", "base_production", "base_manpower"):
        match = re.search(rf"(?m)^\s*{key}\s*=\s*(\d+)\b", opening)
        if not match:
            raise ValueError(f"{path.name}: missing {key}")
        development += int(match.group(1))
    cot = re.search(r"(?m)^\s*center_of_trade\s*=\s*(\d+)\b", opening)
    return development, int(cot.group(1)) if cot else 0


def history_index(mod_root: Path) -> dict[int, list[Path]]:
    result: dict[int, list[Path]] = defaultdict(list)
    for path in (mod_root / "history/provinces").glob("*.txt"):
        match = re.match(r"^(\d+)", path.name)
        if match:
            result[int(match.group(1))].append(path)
    return result


def assert_acyclic(routes: dict[str, tuple[str, ...]]) -> None:
    missing = {target for targets in routes.values() for target in targets if target not in routes}
    if missing:
        raise ValueError(f"Trade routes target missing nodes: {sorted(missing)}")
    state: dict[str, int] = {}
    trail: list[str] = []

    def visit(node: str) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            start = trail.index(node)
            raise ValueError(f"Trade route cycle: {' -> '.join(trail[start:] + [node])}")
        state[node] = 1
        trail.append(node)
        for target in routes[node]:
            visit(target)
        trail.pop()
        state[node] = 2

    for node in routes:
        visit(node)


def load_encoder():
    path = ROOT / "tools/encode_eu4_chinese_localisation.py"
    spec = importlib.util.spec_from_file_location("gdd_b49_encoder", path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load localisation encoder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_localisation() -> None:
    lines = ["l_english:"]
    for key, value in NODE_LABELS.items():
        lines.append(f' {key}:0 "{value}"')
    for node, value in NODE_LABELS.items():
        company = TRADE_COMPANY_BY_NODE[node]
        # The raw company key labels the charter region in the map mode; the
        # GDD key names the actual trade-company organisation. Both consumers
        # must be localized or one of the two screens falls back to English.
        lines.append(f' {company}:0 "{value}特许贸易区"')
        lines.append(f' GDD_TRADE_COMPANY_{node.upper()}:0 "{value}贸易公司"')
    SOURCE.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    encoder = load_encoder()
    encoder.encode_file(SOURCE, TARGET)
    encoder.verify_file(SOURCE, TARGET)


def validate(mod_root: Path = MOD) -> dict[str, object]:
    land, expected = target_members(mod_root)
    node_path = mod_root / "common/tradenodes/00_tradenodes.txt"
    text = node_path.read_text(encoding="cp1252")
    memberships = node_memberships(text)
    routes = node_routes(text)
    for node, ids in expected.items():
        actual = memberships.get(node)
        if actual != ids:
            missing = sorted(ids - (actual or set()))
            extra = sorted((actual or set()) - ids)
            raise ValueError(f"{node} membership drift; missing={missing}, extra={extra}")
    owners: dict[int, list[str]] = defaultdict(list)
    for node, ids in memberships.items():
        for province_id in ids:
            owners[province_id].append(node)
    for node, ids in expected.items():
        for province_id in ids:
            if owners[province_id] != [node]:
                raise ValueError(f"Province {province_id} trade owners: {owners[province_id]}")
    for node, ids in EXTERNAL_REALLOCATION.items():
        for province_id in ids:
            if owners[province_id] != [node]:
                raise ValueError(f"External province {province_id} trade owners: {owners[province_id]}")
    company_text = (mod_root / "common/trade_companies/00_trade_companies.txt").read_text(
        encoding="cp1252"
    )
    companies = company_memberships(company_text)
    company_owners: dict[int, list[str]] = defaultdict(list)
    for company, ids in companies.items():
        for province_id in ids:
            company_owners[province_id].append(company)
    core_company_policy, external_company_policy = trade_company_policy(mod_root)
    all_company_policy = core_company_policy | external_company_policy
    for company, ids in all_company_policy.items():
        for province_id in ids:
            if company_owners[province_id] != [company]:
                raise ValueError(
                    f"Province {province_id} trade companies: {company_owners[province_id]}, expected {company}"
                )
    for company, ids in core_company_policy.items():
        if companies.get(company) != ids:
            missing = sorted(ids - companies.get(company, set()))
            extra = sorted(companies.get(company, set()) - ids)
            raise ValueError(
                f"{company} membership drift; missing={missing}, extra={extra}"
            )
    company_anchors = set().union(*NODE_ANCHORS.values())
    leaked_anchors = {
        province_id: company_owners[province_id]
        for province_id in company_anchors
        if company_owners[province_id]
    }
    if leaked_anchors:
        raise ValueError(f"Water anchors remain in trade companies: {leaked_anchors}")
    expected_routes = {
        node: tuple(target for target, _path, _control in CORE_ROUTES[node])
        for node in NODE_AREAS
    }
    for node, targets in expected_routes.items():
        if routes.get(node) != targets:
            raise ValueError(f"{node} routes are {routes.get(node)}, expected {targets}")
    for (node, target), _route in EXTERNAL_ROUTES.items():
        if routes.get(node, ()).count(target) != 1:
            raise ValueError(f"{node} must have exactly one route to {target}")
    hangzhou_block = next(block for name, _s, _e, block in top_blocks(text) if name == "hangzhou")
    if not re.search(r"(?m)^\s*end\s*=\s*yes\s*$", hangzhou_block):
        raise ValueError("Wuyue/Hangzhou is not an end node")
    for node in set(NODE_AREAS) - {"hangzhou"}:
        block = next(block for name, _s, _e, block in top_blocks(text) if name == node)
        if re.search(r"(?m)^\s*end\s*=\s*yes\s*$", block):
            raise ValueError(f"{node} must not be an end node")
    assert_acyclic(routes)

    histories = history_index(mod_root)
    development = {}
    centers = {}
    for node, ids in expected.items():
        node_development = 0
        levels = Counter()
        for province_id in ids - NODE_ANCHORS[node]:
            paths = histories.get(province_id, [])
            if len(paths) != 1:
                raise ValueError(f"Province {province_id} has {len(paths)} local histories")
            province_development, level = opening_history_values(paths[0])
            node_development += province_development
            if level:
                levels[level] += 1
        development[node] = node_development
        centers[node] = dict(sorted(levels.items()))

    source = mod_root / SOURCE.relative_to(MOD)
    target = mod_root / TARGET.relative_to(MOD)
    if not source.exists() or not target.exists():
        raise ValueError("B49 localisation source/target pair is missing")
    encoder = load_encoder()
    encoder.verify_file(source, target)
    source_text = source.read_text(encoding="utf-8-sig")
    for node, label in NODE_LABELS.items():
        company = TRADE_COMPANY_BY_NODE[node]
        required_lines = (
            f' {node}:0 "{label}"',
            f' {company}:0 "{label}特许贸易区"',
            f' GDD_TRADE_COMPANY_{node.upper()}:0 "{label}贸易公司"',
        )
        missing_lines = [line for line in required_lines if line not in source_text]
        if missing_lines:
            raise ValueError(f"B49 localisation is incomplete: {missing_lines}")
    return {
        "core_nodes": list(NODE_AREAS),
        "core_land_provinces": sum(map(len, land.values())),
        "node_land_counts": {node: len(ids) for node, ids in land.items()},
        "node_playable_counts": {
            node: len(expected[node] - NODE_ANCHORS[node]) for node in NODE_AREAS
        },
        "node_total_members": {node: len(expected[node]) for node in NODE_AREAS},
        "node_development": development,
        "opening_centers": centers,
        "external_reallocated": {node: len(ids) for node, ids in EXTERNAL_REALLOCATION.items()},
        "trade_company_by_node": TRADE_COMPANY_BY_NODE,
        "trade_company_member_counts": {
            company: len(ids) for company, ids in core_company_policy.items()
        },
        "external_trade_company_policy": {
            company: sorted(ids) for company, ids in external_company_policy.items()
        },
        "wuyue_end_node": True,
        "acyclic": True,
    }


def update_trade_nodes() -> dict[str, int]:
    text = TRADE_NODES.read_text(encoding="cp1252")
    before = {node: len(ids) for node, ids in node_memberships(text).items()}
    land, target = target_members(MOD)
    managed = set().union(*target.values(), *EXTERNAL_REALLOCATION.values())

    # Remove every managed ID before rebuilding assignments, so older
    # generators cannot leave duplicate trade-node ownership behind.
    for node, ids in list(node_memberships(text).items()):
        if ids & managed:
            text = set_node_members(text, node, ids - managed)

    for node, ids in target.items():
        text = upsert_top_block(text, node, render_node(node, ids))

    for node, ids in EXTERNAL_REALLOCATION.items():
        current = node_memberships(text).get(node)
        if current is None:
            raise ValueError(f"Missing external node: {node}")
        text = set_node_members(text, node, current | ids)

    for (node, target_node), (path, control) in EXTERNAL_ROUTES.items():
        text = upsert_external_route(text, node, target_node, path, control)

    TRADE_NODES.write_text(text.rstrip() + "\n", encoding="cp1252")
    return before


def update_trade_companies() -> dict[str, int]:
    text = TRADE_COMPANIES.read_text(encoding="cp1252")
    before = {company: len(ids) for company, ids in company_memberships(text).items()}
    core_policy, external_policy = trade_company_policy(MOD)
    managed = set().union(
        *core_policy.values(),
        *external_policy.values(),
        *NODE_ANCHORS.values(),
    )
    for company, ids in list(company_memberships(text).items()):
        if ids & managed:
            text = remove_outer_ids(text, company, "provinces", managed)

    # The eight Chinese core companies are exact mirrors of the eight land
    # nodes. Re-rendering their complete blocks also gives all eight stable,
    # Spring-and-Autumn-themed display names and matching map colours.
    for node, company in TRADE_COMPANY_BY_NODE.items():
        text = upsert_top_block(
            text,
            company,
            render_trade_company(company, node, core_policy[company]),
        )

    # Frontier companies keep their other vanilla members; only the provinces
    # deliberately sent to Yumen, Girin, or Lhasa are repaired here.
    for company, ids in external_policy.items():
        current = company_memberships(text).get(company)
        if current is None:
            raise ValueError(f"Missing trade company: {company}")
        text = append_outer_ids(text, company, "provinces", ids)
    TRADE_COMPANIES.write_text(text.rstrip() + "\n", encoding="cp1252")
    return before


def apply() -> None:
    PLAN.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(TRADE_NODES, BACKUP)
    if not COMPANY_BACKUP.exists():
        shutil.copy2(TRADE_COMPANIES, COMPANY_BACKUP)
    existing = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    before = existing.get("before_node_member_counts") or update_trade_nodes()
    before_companies = existing.get("before_company_member_counts") or update_trade_companies()
    if existing:
        update_trade_nodes()
        update_trade_companies()
    write_localisation()
    report = validate(MOD)
    payload = {
        "batch": "B49_eight_node_trade_network",
        "marker": MARKER,
        "purpose": "Replace the five oversized Chinese core nodes with eight balanced Spring-and-Autumn-themed nodes and a Wuyue sink.",
        "backups": {
            "trade_nodes": str(BACKUP.relative_to(ROOT)),
            "trade_companies": str(COMPANY_BACKUP.relative_to(ROOT)),
        },
        "node_labels": NODE_LABELS,
        "node_area_policy": {node: list(areas) for node, areas in NODE_AREAS.items()},
        "core_routes": {node: [target for target, _path, _control in routes] for node, routes in CORE_ROUTES.items()},
        "external_reallocation": {node: sorted(ids) for node, ids in EXTERNAL_REALLOCATION.items()},
        "user_overrides": {
            "zhaodi_area_to_youyan": {
                "area": ZHAODI_AREA,
                "province_ids": sorted(ZHAODI_IDS),
            },
            "annam_to_baiyue": sorted(ANNAM_IDS),
        },
        "trade_company_by_node": TRADE_COMPANY_BY_NODE,
        "external_company_by_node": EXTERNAL_COMPANY_BY_NODE,
        "before_node_member_counts": before,
        "before_company_member_counts": before_companies,
        "validation": report,
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"{MARKER}; CORE_NODES:{len(NODE_AREAS)}; "
        f"LAND:{report['core_land_provinces']}; END:hangzhou; ACYCLIC:yes"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(validate(MOD), ensure_ascii=False))
    else:
        apply()


if __name__ == "__main__":
    main()
