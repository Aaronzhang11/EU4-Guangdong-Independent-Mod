#!/usr/bin/env python3
"""Apply the reviewed 26-province Yunnan GeoJSON draft and coupled assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
DRAFT = ROOT / "planning/yunnan_26_province_draft.bmp"


@dataclass(frozen=True)
class Province:
    province_id: int
    chinese: str
    english: str
    area: str
    draft_colour: tuple[int, int, int]
    colour: tuple[int, int, int]
    seed: tuple[int, int]
    goods: str
    development: tuple[int, int, int]
    culture: str
    religion: str
    owner: str = "MNG"
    cot: int = 0
    fort: bool = False


# Retained IDs preserve their canonical RGB values; new IDs begin after the
# currently occupied 5223 block. Total starting development is 153, with the
# two intended commercial anchors at Dali and Kunming.
P = (
    Province(5224, "德钦", "Deqin", "dianxibei_area", (199,104,151), (199,104,151), (4357,927), "wool", (1,2,1), "tibetan", "vajrayana"),
    Province(5225, "独克宗", "Dukezong", "dianxibei_area", (150,193,55), (150,193,55), (4376,932), "livestock", (2,2,1), "tibetan", "vajrayana", fort=True),
    Province(2167, "丽江", "Lijiang", "dianxibei_area", (61,171,211), (75,240,74), (4384,949), "tea", (3,3,2), "bai", "buddhism"),
    Province(5226, "剑川", "Jianchuan", "dianxibei_area", (232,192,56), (232,192,56), (4374,966), "livestock", (2,2,1), "bai", "buddhism"),
    Province(5227, "泸水", "Lushui", "dianxi_area", (218,108,54), (218,108,54), (4347,967), "tropical_wood", (1,1,1), "shan", "buddhism", "MMA"),
    Province(661, "大理", "Dali", "dianxi_area", (232,154,55), (222,74,64), (4376,985), "tea", (5,5,2), "bai", "buddhism", cot=2, fort=True),
    Province(5228, "保山", "Baoshan", "dianxi_area", (202,168,74), (202,168,74), (4354,996), "iron", (2,3,1), "bai", "buddhism"),
    Province(2166, "德宏", "Dehong", "dianxi_area", (74,159,125), (69,205,50), (4343,1012), "tropical_wood", (2,2,1), "shan", "buddhism", "MMA"),
    Province(5229, "楚雄", "Chuxiong", "yunnan_area", (221,107,52), (221,107,52), (4396,987), "livestock", (2,3,1), "yi", "animism"),
    Province(662, "昆明", "Kunming", "yunnan_area", (238,224,204), (94,76,128), (4413,990), "copper", (6,5,2), "bai", "buddhism", cot=2, fort=True),
    Province(5230, "玉溪", "Yuxi", "yunnan_area", (239,194,127), (239,194,127), (4415,1005), "grain", (3,3,1), "bai", "buddhism"),
    Province(5231, "东川", "Dongchuan", "yunnan_area", (206,55,43), (206,55,43), (4417,968), "copper", (1,3,1), "yi", "animism"),
    Province(5232, "昭通", "Zhaotong", "diandong_area", (244,182,62), (244,182,62), (4440,938), "livestock", (2,2,1), "yi", "animism"),
    Province(5233, "镇雄", "Zhenxiong", "diandong_area", (107,156,51), (107,156,51), (4457,953), "iron", (1,2,1), "yi", "animism"),
    Province(5234, "宣威", "Xuanwei", "diandong_area", (25,130,90), (25,130,90), (4445,968), "livestock", (2,2,1), "yi", "animism"),
    Province(675, "曲靖", "Qujing", "diandong_area", (80,78,115), (224,102,0), (4440,986), "copper", (3,3,2), "yi", "animism"),
    Province(5235, "临沧", "Lincang", "dianxinan_area", (145,202,55), (145,202,55), (4376,1017), "tea", (2,2,1), "yi", "animism"),
    Province(5236, "耿马", "Gengma", "dianxinan_area", (231,40,37), (231,40,37), (4359,1021), "tropical_wood", (1,1,1), "shan", "buddhism", "MMA"),
    Province(2165, "思茅", "Simao", "dianxinan_area", (226,168,151), (255,216,0), (4392,1031), "tea", (2,3,1), "bai", "buddhism"),
    Province(5237, "镇沅", "Zhenyuan", "dianxinan_area", (73,172,207), (73,172,207), (4396,1019), "tea", (1,2,1), "yi", "animism"),
    Province(5238, "勐连", "Menglian", "dianxinan_area", (112,218,194), (112,218,194), (4374,1038), "tropical_wood", (1,1,1), "shan", "buddhism", "MMA"),
    Province(660, "版纳", "Banna", "diannan_area", (246,151,27), (94,72,0), (4387,1047), "tea", (3,3,1), "shan", "buddhism", "MMA"),
    Province(5239, "勐腊", "Mengla", "diannan_area", (57,88,139), (57,88,139), (4401,1048), "tropical_wood", (1,2,1), "shan", "buddhism", "MMA"),
    Province(5240, "蒙自", "Mengzi", "diannan_area", (36,133,156), (36,133,156), (4425,1018), "grain", (3,3,1), "bai", "buddhism"),
    Province(5241, "红河", "Honghe", "diannan_area", (241,224,45), (241,224,45), (4415,1032), "tea", (2,2,1), "yi", "animism"),
    Province(663, "文山", "Wenshan", "diannan_area", (143,209,24), (222,78,192), (4450,1020), "iron", (2,2,1), "yi", "animism", "NUN"),
)

AREA_NAMES = {
    "dianxibei_area": ("滇西北", "丽江"),
    "dianxi_area": ("滇西", "大理"),
    "yunnan_area": ("滇中", "昆明"),
    "diandong_area": ("滇东", "曲靖"),
    "dianxinan_area": ("滇西南", "思茅"),
    "diannan_area": ("滇南", "蒙自"),
}


def mask(values: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    return np.all(values == np.asarray(colour, dtype=np.uint8), axis=2)


def components(province_mask: np.ndarray) -> list[list[tuple[int, int]]]:
    seen = np.zeros(province_mask.shape, dtype=bool)
    result: list[list[tuple[int, int]]] = []
    height, width = province_mask.shape
    for start_y, start_x in zip(*np.where(province_mask), strict=True):
        if seen[start_y, start_x]:
            continue
        stack = [(int(start_y), int(start_x))]
        seen[start_y, start_x] = True
        component: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            component.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width and province_mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        result.append(component)
    return sorted(result, key=len, reverse=True)


def make_contiguous(values: np.ndarray) -> int:
    """Resolve four county-raster enclaves into contiguous EU4 provinces."""
    by_id = {p.province_id: p for p in P}
    changes: list[tuple[list[tuple[int, int]], tuple[int, int, int]]] = []
    # Tiny west/south raster flecks are absorbed by their enclosing neighbour.
    for source_id, target_id in ((5230, 5229), (5232, 5233)):
        cc = components(mask(values, by_id[source_id].colour))
        for component in cc[1:]:
            changes.append((component, by_id[target_id].colour))
    # Modern county grouping creates interlocking Simao/Zhenyuan islands.
    # Swap the two secondary components so both gameplay provinces are whole.
    simao = components(mask(values, by_id[2165].colour))
    zhenyuan = components(mask(values, by_id[5237].colour))
    for component in simao[1:]:
        changes.append((component, by_id[5237].colour))
    for component in zhenyuan[1:]:
        changes.append((component, by_id[2165].colour))
    for component, colour in changes:
        for y, x in component:
            values[y, x] = colour
    return sum(len(component) for component, _colour in changes)


def replace_named_block(text: str, name: str, replacement: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    depth = 0
    for index in range(text.find("{", match.start()), len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[:match.start()] + replacement.rstrip() + text[index + 1:]
    raise ValueError(f"Unclosed block {name}")


def remove_all_named_blocks(text: str, name: str) -> str:
    """Remove every top-level occurrence, including leftovers from old drafts."""
    while True:
        match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
        if not match:
            return text
        depth = 0
        end = None
        for index in range(text.find("{", match.start()), len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise ValueError(f"Unclosed block {name}")
        text = text[:match.start()] + text[end:].lstrip("\n")


def append_ids(text: str, block_name: str, ids: list[int], comment: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(block_name)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"Missing block {block_name}")
    depth = 0
    for index in range(text.find("{", match.start()), len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                insertion = "\n        " + " ".join(map(str, ids)) + f" # {comment}\n"
                return text[:index].rstrip() + insertion + text[index:]
    raise ValueError(f"Unclosed block {block_name}")


def apply_geometry() -> dict[int, tuple[int, int]]:
    canonical = np.array(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    draft = np.array(Image.open(DRAFT).convert("RGB"), dtype=np.uint8)
    if canonical.shape != draft.shape:
        raise ValueError("Yunnan draft and canonical bitmap dimensions differ")
    centres: dict[int, tuple[int, int]] = {}
    changed = 0
    for province in P:
        province_mask = mask(draft, province.draft_colour)
        if not province_mask.any():
            raise ValueError(f"Empty draft province: {province.chinese}")
        before = canonical[province_mask].copy()
        canonical[province_mask] = province.colour
        changed += int(np.count_nonzero(np.any(before != canonical[province_mask], axis=1)))
        ys, xs = np.where(province_mask)
        sx, sy = province.seed
        nearest = int(np.argmin((xs - sx) ** 2 + (ys - sy) ** 2))
        centres[province.province_id] = (int(xs[nearest]), 2048 - int(ys[nearest]))
    contiguous_pixels = make_contiguous(canonical)
    Image.fromarray(canonical, mode="RGB").save(MAP / "provinces.bmp", format="BMP")
    print(f"YUNNAN_GEOMETRY_APPLIED:{changed};CONTIGUITY_PIXELS:{contiguous_pixels}")
    return centres


def update_definition() -> None:
    path = MAP / "definition.csv"
    lines = path.read_text(encoding="cp1252").splitlines()
    by_id = {p.province_id: p for p in P}
    found: set[int] = set()
    output: list[str] = []
    for line in lines:
        head = line.split(";", 1)[0]
        if head.isdigit() and int(head) in by_id:
            province = by_id[int(head)]
            r, g, b = province.colour
            output.append(f"{province.province_id};{r};{g};{b};{province.english};x")
            found.add(province.province_id)
        else:
            output.append(line)
    for province in P:
        if province.province_id not in found:
            r, g, b = province.colour
            output.append(f"{province.province_id};{r};{g};{b};{province.english};x")
    path.write_text("\n".join(output) + "\n", encoding="cp1252")


def update_areas_region() -> None:
    path = MAP / "area.txt"
    text = path.read_text(encoding="cp1252")
    # Retire the former mixed Yunnan-borderland area and clear any duplicate
    # blocks left by an interrupted/older run before writing the six states.
    for area in ("yun_gui_borderland_area", *AREA_NAMES):
        text = remove_all_named_blocks(text, area)
    for area in AREA_NAMES:
        ids = [p.province_id for p in P if p.area == area]
        text = text.rstrip() + f"\n\n{area} = {{ # Yunnan 26-province refinement\n    {' '.join(map(str, ids))}\n}}\n"
    path.write_text(text, encoding="cp1252")

    path = MAP / "region.txt"
    text = path.read_text(encoding="cp1252")
    start = text.index("xinan_region = {")
    end = text.index("north_china_region", start)
    block = text[start:end].replace("        yun_gui_borderland_area\n", "")
    for area in ("dianxibei_area", "dianxi_area", "diandong_area", "dianxinan_area", "diannan_area"):
        if area not in block:
            block = block.replace("        yunnan_area\n", f"        yunnan_area\n        {area}\n")
    path.write_text(text[:start] + block + text[end:], encoding="cp1252")


def history_text(province: Province) -> str:
    cores = [province.owner]
    if province.owner != "MNG" and province.province_id != 663:
        cores.append("MNG")
    if province.province_id == 663:
        cores.append("CDL")
    if province.owner == "MNG" and province.culture in {"bai", "yi"}:
        cores.append("CDL")
    lines = [
        f"# {province.province_id} - {province.english}", "",
        f"owner = {province.owner}", f"controller = {province.owner}",
        *(f"add_core = {core}" for core in dict.fromkeys(cores)),
        f"culture = {province.culture}", f"religion = {province.religion}",
        f'capital = "{province.english}"', f"trade_goods = {province.goods}",
        f"base_tax = {province.development[0]}",
        f"base_production = {province.development[1]}",
        f"base_manpower = {province.development[2]}", "is_city = yes",
    ]
    if province.cot:
        lines.append(f"center_of_trade = {province.cot}")
    if province.fort:
        lines.append("fort_15th = yes")
    lines += ["discovered_by = chinese", "discovered_by = indian", "discovered_by = nomad_group"]
    if province.owner == "MMA":
        lines += ["", "1449.1.1 = { owner = MNG controller = MNG add_core = MNG }"]
    lines += [
        "", "1655.1.1 = { discovered_by = SPA }",
        "1662.4.1 = { owner = CZH controller = CZH add_core = CZH }",
        "1681.10.1 = { owner = QNG controller = QNG add_core = QNG }",
    ]
    return "\n".join(lines) + "\n"


def update_histories() -> None:
    directory = MOD / "history/provinces"
    for province in P:
        desired = directory / f"{province.province_id} - {province.english}.txt"
        for old in directory.glob(f"{province.province_id} - *.txt"):
            if old != desired:
                old.unlink()
        desired.write_text(history_text(province), encoding="utf-8")


def position_block(province: Province, x: int, y: int) -> str:
    points = " ".join([f"{x:.3f} {y:.3f}"] * 6 + ["0.000 0.000"])
    return f"""#{province.english} - Yunnan 26-province refinement
{province.province_id}={{
    position={{
        {points}
    }}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 1.000 0.000 0.000 0.000 0.000
    }}
}}"""


def update_positions(centres: dict[int, tuple[int, int]]) -> None:
    path = MAP / "positions.txt"
    text = path.read_text(encoding="cp1252")
    text = re.sub(r"(?m)^#.* - Yunnan 26-province refinement\n", "", text)
    for province in P:
        x, y = centres[province.province_id]
        text = replace_named_block(text, str(province.province_id), position_block(province, x, y))
    path.write_text(text, encoding="cp1252")


def update_terrain() -> None:
    path = MAP / "terrain.txt"
    text = path.read_text(encoding="cp1252")
    marker = "B22 Yunnan 26-province refinement"
    if marker not in text:
        highland_ids = [5224,5225,5226,5227,5228,5229,5231,5232,5233,5234,5235,5236,5237,5238,5241]
        jungle_ids = [5239,5240]
        # append_ids finds the first terrain_override, so target the named
        # terrain blocks explicitly before modifying their inner lists.
        def add_to_terrain(src: str, terrain: str, ids: list[int], note: str) -> str:
            start = src.index(f"    {terrain} = {{")
            depth = 0
            end = None
            for i in range(src.find("{", start), len(src)):
                if src[i] == "{": depth += 1
                elif src[i] == "}":
                    depth -= 1
                    if depth == 0: end = i + 1; break
            block = src[start:end]
            if note not in block:
                block = append_ids(block, "terrain_override", ids, note)
            return src[:start] + block + src[end:]
        text = add_to_terrain(text, "highlands", highland_ids, marker + " highlands")
        text = add_to_terrain(text, "jungle", jungle_ids, marker + " jungle")
        path.write_text(text, encoding="cp1252")


def add_to_top_level_block(path: Path, top_name: str, nested_name: str, ids: list[int], marker: str) -> None:
    text = path.read_text(encoding="cp1252")
    start = text.index(f"{top_name} = {{") if f"{top_name} = {{" in text else text.index(f"{top_name}={{")
    depth = 0
    end = None
    for i in range(text.find("{", start), len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0: end = i + 1; break
    block = text[start:end]
    if marker not in block:
        block = append_ids(block, nested_name, ids, marker)
        path.write_text(text[:start] + block + text[end:], encoding="cp1252")


def update_memberships() -> None:
    new_ids = [p.province_id for p in P if p.province_id >= 5224]
    marker = "B22 Yunnan 26-province refinement"
    for filename, block_name in (("continent.txt", "asia"), ("climate.txt", "normal_monsoon")):
        path = MAP / filename
        text = path.read_text(encoding="cp1252")
        if marker not in text:
            path.write_text(append_ids(text, block_name, new_ids, marker), encoding="cp1252")
    climate = MAP / "climate.txt"
    text = climate.read_text(encoding="cp1252")
    tropical_marker = marker + " tropical south"
    if tropical_marker not in text:
        text = append_ids(text, "tropical", [5235,5236,5237,5238,5239,5240,5241], tropical_marker)
        climate.write_text(text, encoding="cp1252")

    # All modern-Yunnan provinces belong to the Chengdu trade node.  Keep the
    # company and node semantics aligned when this historical builder is rerun.
    chengdu_ids = [
        5224,5225,5226,5227,5228,5229,
        5230,5231,5232,5233,5234,5235,5236,5237,5238,5239,5240,5241,
    ]
    node_path = MOD / "common/tradenodes/00_tradenodes.txt"
    add_to_top_level_block(node_path, "chengdu", "members", chengdu_ids, marker + " Chengdu node")

    company_path = MOD / "common/trade_companies/00_trade_companies.txt"
    add_to_top_level_block(
        company_path,
        "trade_company_chengdu",
        "provinces",
        chengdu_ids,
        marker + " Chengdu company",
    )

    default = MAP / "default.map"
    text = default.read_text(encoding="cp1252")
    text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5242", text)
    default.write_text(text, encoding="cp1252")


def update_localisation() -> None:
    lines = ["l_english:"]
    for province in P:
        lines += [
            f' PROV{province.province_id}:0 "{province.chinese}"',
            f' PROV_ADJ{province.province_id}:0 "{province.chinese}"',
        ]
    lines.append("")
    for area, (display, capital) in AREA_NAMES.items():
        lines += [
            f' {area}:0 "{display}"',
            f' {area}_name:0 "{capital}"',
            f' {area}_adj:0 "{display}"',
        ]
    source = MOD / "localisation_source/gdd_b22_yunnan_map_readable_utf8.txt"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(source, MOD / "localisation/gdd_b22_yunnan_map_l_english.yml")


def render_preview() -> None:
    left, top, right, bottom = 4315, 900, 4485, 1070
    scale = 6
    source = Image.open(MAP / "provinces.bmp").convert("RGB").crop((left, top, right, bottom))
    preview = source.resize((source.width * scale, source.height * scale), Image.Resampling.NEAREST)
    output = ROOT / "docs/map/previews/B22_yunnan_26_formal.png"
    preview.save(output)
    print(f"YUNNAN_PREVIEW:{output}")


def main() -> None:
    centres = apply_geometry()
    update_definition()
    update_areas_region()
    update_histories()
    update_positions(centres)
    update_terrain()
    update_memberships()
    update_localisation()
    render_preview()
    print("YUNNAN_26_PROVINCE_REFINEMENT_APPLIED")


if __name__ == "__main__":
    main()
