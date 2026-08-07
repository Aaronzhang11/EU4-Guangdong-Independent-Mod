#!/usr/bin/env python3
"""Apply the reviewed Sichuan 36-province draft and its coupled map assets.

The reviewed draft is the geometry authority.  Only its 36 temporary colours
are copied into the canonical bitmap, so pixels outside Sichuan are preserved.
The operation is idempotent and can be rerun after regenerating the draft.
"""

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
DRAFT = ROOT / "planning/sichuan_36_province_draft.bmp"


@dataclass(frozen=True)
class Province:
    province_id: int
    chinese: str
    english: str
    area: str
    draft_colour: tuple[int, int, int]
    permanent_colour: tuple[int, int, int]
    seed: tuple[int, int]
    goods: str
    development: tuple[int, int, int]
    polity: str
    culture: str
    religion: str
    cot: int = 0
    fort: bool = False


# New colours are the reviewed draft colours.  Retained IDs keep their existing
# definition colour so existing references remain stable.
P = (
    Province(679, "成都", "Chengdu", "sichuan_area", (199,133,84), (225,110,255), (4449,888), "silk", (10,11,4), "shu", "gdd_shu", "confucianism", 2, True),
    Province(5075, "灌州", "Guanzhou", "sichuan_area", (98,79,224), (98,79,224), (4428,881), "grain", (4,4,2), "shu", "gdd_shu", "confucianism"),
    Province(5076, "邛州", "Qiongzhou", "sichuan_area", (78,199,56), (78,199,56), (4417,899), "tea", (4,4,2), "shu", "gdd_shu", "confucianism"),
    Province(5077, "眉州", "Meizhou (Sichuan)", "sichuan_area", (224,94,153), (224,94,153), (4438,902), "cloth", (5,5,2), "shu", "gdd_shu", "confucianism"),
    Province(4212, "嘉州", "Jiazhou", "jiaya_area", (70,165,199), (122,61,105), (4446,916), "tea", (5,5,2), "shu", "gdd_shu", "confucianism"),
    Province(5078, "雅州", "Yazhou", "jiaya_area", (224,219,63), (224,219,63), (4427,916), "tea", (4,5,2), "shu", "gdd_shu", "confucianism"),
    Province(5079, "黎州", "Lizhou (Sichuan)", "jiaya_area", (161,84,199), (161,84,199), (4409,913), "livestock", (2,2,2), "shu", "gdd_shu", "confucianism"),
    Province(5080, "绵州", "Mianzhou", "chuanbei_area", (79,224,134), (79,224,134), (4447,875), "cloth", (5,5,2), "shu", "gdd_shu", "confucianism"),
    Province(5081, "剑州", "Jianzhou (Sichuan)", "chuanbei_area", (199,69,56), (199,69,56), (4451,858), "iron", (3,3,2), "shu", "gdd_shu", "confucianism", 0, True),
    Province(2169, "阆中", "Langzhong", "chuanbei_area", (94,120,224), (149,33,33), (4467,869), "grain", (4,4,2), "shu", "gdd_shu", "confucianism"),
    Province(5082, "顺庆", "Shunqing", "chuanbei_area", (133,199,70), (133,199,70), (4475,886), "grain", (4,5,2), "shu", "gdd_shu", "confucianism"),
    Province(4211, "达州", "Dazhou", "chuanbei_area", (224,63,189), (72,32,16), (4498,875), "livestock", (3,3,2), "shu", "gdd_shu", "confucianism"),
    Province(5083, "资州", "Zizhou", "chuannan_area", (84,199,190), (84,199,190), (4455,912), "salt", (4,5,2), "shu", "gdd_shu", "confucianism"),
    Province(5084, "富顺", "Fushun", "chuannan_area", (224,171,79), (224,171,79), (4448,919), "salt", (3,6,2), "shu", "gdd_shu", "confucianism"),
    Province(5085, "叙州", "Xuzhou (Sichuan)", "chuannan_area", (105,56,199), (105,56,199), (4437,929), "grain", (4,4,2), "shu", "gdd_shu", "confucianism"),
    Province(4213, "泸州", "Luzhou (Sichuan)", "chuannan_area", (94,224,101), (40,46,10), (4454,929), "grain", (4,4,2), "shu", "gdd_shu", "confucianism"),
    Province(680, "重庆", "Chongqing", "chongqing_area", (199,70,101), (97,112,0), (4462,911), "cloth", (8,9,3), "ba", "gdd_shu", "confucianism", 2),
    Province(5026, "合州", "Hezhou (Chongqing)", "chongqing_area", (63,149,224), (225,90,40), (4474,900), "grain", (4,4,2), "ba", "gdd_shu", "confucianism"),
    Province(5027, "涪州", "Fuzhou (Chongqing)", "chongqing_area", (179,199,84), (70,190,155), (4491,921), "paper", (4,4,2), "ba", "miao", "confucianism"),
    Province(4987, "万州", "Wanzhou", "chongqing_area", (207,79,224), (164,45,190), (4497,896), "tea", (3,4,2), "ba", "gdd_shu", "confucianism"),
    Province(5028, "夔州", "Kuizhou", "chongqing_area", (56,199,140), (150,70,230), (4515,883), "naval_supplies", (3,3,2), "ba", "gdd_diqiang", "confucianism", 0, True),
    Province(2170, "松州", "Songzhou", "songmao_area", (224,133,94), (90,182,176), (4428,847), "livestock", (3,3,3), "songmao", "gdd_diqiang", "vajrayana", 1, True),
    Province(5086, "茂州", "Maozhou", "songmao_area", (70,70,199), (70,70,199), (4434,863), "livestock", (2,2,2), "songmao", "gdd_diqiang", "vajrayana"),
    Province(5087, "汶川", "Wenchuan", "songmao_area", (109,224,63), (109,224,63), (4428,873), "wool", (2,2,2), "songmao", "gdd_diqiang", "vajrayana"),
    Province(5088, "南坪", "Nanping", "songmao_area", (199,84,150), (199,84,150), (4434,834), "livestock", (2,2,2), "songmao", "gdd_diqiang", "vajrayana"),
    Province(5089, "马尔康", "Barkam", "aba_area", (79,205,224), (79,205,224), (4406,860), "tea", (2,3,2), "songmao", "tibetan", "vajrayana"),
    Province(5090, "金川", "Jinchuan", "aba_area", (199,176,56), (199,176,56), (4407,872), "copper", (2,2,2), "songmao", "gdd_diqiang", "vajrayana"),
    Province(5091, "阿坝", "Ngawa", "aba_area", (166,94,224), (166,94,224), (4404,842), "wool", (2,2,3), "songmao", "tibetan", "vajrayana"),
    Province(5092, "若尔盖", "Zoige", "aba_area", (70,199,103), (70,199,103), (4418,836), "livestock", (1,2,3), "songmao", "gdd_diqiang", "vajrayana"),
    Province(678, "康定", "Kangding", "ganzi_area", (224,63,69), (96,108,192), (4393,906), "tea", (3,4,2), "kham", "tibetan", "vajrayana", 1),
    Province(2133, "德格", "Dege", "ganzi_area", (84,121,199), (118,126,240), (4367,861), "paper", (3,4,2), "kham", "tibetan", "vajrayana"),
    Province(2135, "壤塘", "Rangtang", "ganzi_area", (169,224,79), (118,130,80), (4386,850), "wool", (1,2,2), "kham", "tibetan", "vajrayana"),
    Province(5093, "理塘", "Lithang", "ganzi_area", (199,56,186), (199,56,186), (4368,917), "livestock", (2,3,2), "kham", "tibetan", "vajrayana"),
    Province(2748, "嶲州", "Xizhou", "liangshan_area", (94,224,198), (80,32,128), (4420,943), "grain", (4,4,3), "liangshan", "yi", "animism", 0, True),
    Province(5094, "会理", "Huili", "liangshan_area", (199,135,70), (199,135,70), (4438,960), "copper", (3,4,2), "liangshan", "yi", "animism"),
    Province(5095, "盐源", "Yanyuan", "liangshan_area", (97,63,224), (97,63,224), (4397,958), "salt", (2,2,2), "liangshan", "yi", "animism"),
)

AREA_NAMES = {
    "sichuan_area": ("成都", "成都"), "jiaya_area": ("嘉雅", "嘉州"),
    "chuanbei_area": ("川北", "阆中"), "chuannan_area": ("川南", "叙州"),
    "chongqing_area": ("巴东", "重庆"), "songmao_area": ("松茂", "松州"),
    "aba_area": ("阿坝", "马尔康"), "ganzi_area": ("甘孜", "康定"),
    "liangshan_area": ("凉山", "嶲州"),
}


def colour_mask(values: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    return np.all(values == np.asarray(colour, dtype=np.uint8), axis=2)


def clean_tiny_components(values: np.ndarray) -> int:
    """Absorb 1–3 pixel GeoJSON raster flecks into an adjacent Sichuan cell."""
    output_colours = {p.permanent_colour for p in P}
    cleaned = 0
    height, width = values.shape[:2]
    for province in P:
        mask = colour_mask(values, province.permanent_colour)
        seen = np.zeros(mask.shape, dtype=bool)
        for start_y, start_x in zip(*np.where(mask), strict=True):
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
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if len(component) > 3:
                continue
            neighbours: list[tuple[int, int, int]] = []
            for y, x in component:
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width:
                        colour = tuple(int(v) for v in values[ny, nx])
                        if colour in output_colours and colour != province.permanent_colour:
                            neighbours.append(colour)
            if neighbours:
                replacement = max(set(neighbours), key=neighbours.count)
                for y, x in component:
                    values[y, x] = replacement
                cleaned += len(component)
    return cleaned


def replace_named_block(text: str, name: str, replacement: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    depth = 0
    end = None
    for index in range(text.find("{", match.start()), len(text)):
        if text[index] == "{": depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise ValueError(f"Unclosed block {name}")
    return text[:match.start()] + replacement.rstrip() + text[end:]


def append_ids_to_named_block(text: str, name: str, ids: list[int], comment: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"Missing block {name}")
    depth = 0
    for index in range(text.find("{", match.start()), len(text)):
        if text[index] == "{": depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                line = "\n        " + " ".join(map(str, ids)) + f" # {comment}\n"
                return text[:index].rstrip() + line + text[index:]
    raise ValueError(f"Unclosed block {name}")


def apply_geometry() -> dict[int, tuple[int, int]]:
    canonical = np.array(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    draft = np.array(Image.open(DRAFT).convert("RGB"), dtype=np.uint8)
    if canonical.shape != draft.shape:
        raise ValueError("Sichuan draft and canonical bitmap dimensions differ")
    changed = 0
    centres: dict[int, tuple[int, int]] = {}
    for province in P:
        mask = colour_mask(draft, province.draft_colour)
        if not mask.any():
            raise ValueError(f"Draft province is empty: {province.chinese}")
        before = canonical[mask].copy()
        canonical[mask] = province.permanent_colour
        changed += int(np.count_nonzero(np.any(before != canonical[mask], axis=1)))
        ys, xs = np.where(mask)
        sx, sy = province.seed
        nearest = int(np.argmin((xs - sx) ** 2 + (ys - sy) ** 2))
        centres[province.province_id] = (int(xs[nearest]), 2048 - int(ys[nearest]))
    flecks = clean_tiny_components(canonical)
    Image.fromarray(canonical, mode="RGB").save(MAP / "provinces.bmp", format="BMP")
    print(f"SICHUAN_GEOMETRY_APPLIED:{changed};FLECKS_CLEANED:{flecks}")
    return centres


def update_definition() -> None:
    path = MAP / "definition.csv"
    lines = path.read_text(encoding="cp1252").splitlines()
    by_id = {p.province_id: p for p in P}
    found: set[int] = set()
    output = []
    for line in lines:
        head = line.split(";", 1)[0]
        if head.isdigit() and int(head) in by_id:
            province = by_id[int(head)]
            r, g, b = province.permanent_colour
            output.append(f"{province.province_id};{r};{g};{b};{province.english};x")
            found.add(province.province_id)
        else:
            output.append(line)
    for province in P:
        if province.province_id not in found:
            r, g, b = province.permanent_colour
            output.append(f"{province.province_id};{r};{g};{b};{province.english};x")
    path.write_text("\n".join(output) + "\n", encoding="cp1252")


def update_areas_and_region() -> None:
    area_path = MAP / "area.txt"
    text = area_path.read_text(encoding="cp1252")
    # These three retained IDs originally belonged to the vanilla Kham state.
    # Remove them there before assigning them to the new Ganzi state; EU4 land
    # provinces must not be members of two areas.
    kham_match = re.search(r"(?ms)^kham_area\s*=\s*\{.*?^\}", text)
    if not kham_match:
        raise ValueError("Missing vanilla kham_area")
    kham_block = kham_match.group(0)
    for province_id in (678, 2133, 2135):
        kham_block = re.sub(rf"(?<!\d){province_id}(?!\d)\s*", "", kham_block)
    text = text[:kham_match.start()] + kham_block + text[kham_match.end():]
    for area in AREA_NAMES:
        ids = [p.province_id for p in P if p.area == area]
        text = replace_named_block(text, area, f"{area} = {{ # Sichuan 36-province refinement\n    {' '.join(map(str, ids))}\n}}")
    area_path.write_text(text, encoding="cp1252")

    region_path = MAP / "region.txt"
    text = region_path.read_text(encoding="cp1252")
    start = text.index("xinan_region = {")
    end = text.index("north_china_region", start)
    block = text[start:end]
    for area in ("jiaya_area", "songmao_area", "aba_area", "ganzi_area", "liangshan_area"):
        if area not in block:
            block = block.replace("        chuanbei_area\n", f"        chuanbei_area\n        {area}\n")
    region_path.write_text(text[:start] + block + text[end:], encoding="cp1252")


def history_text(province: Province) -> str:
    if province.polity in {"shu", "ba"}:
        owner = "MNG"
        cores = ("MNG", "CXI", "SHU")
        late = """\n1644.10.1 = { owner = CXI controller = CXI }\n1655.1.1 = { discovered_by = SPA }\n1659.7.1 = { owner = QNG controller = QNG }\n1673.12.1 = { controller = CZH }\n1680.1.1 = { controller = QNG }\n"""
    elif province.polity == "kham":
        owner = "KAM"
        cores = ("KAM",)
        late = "\n1709.1.1 = { discovered_by = SPA }\n1776.1.1 = { owner = QNG controller = QNG add_core = QNG }\n"
    elif province.polity == "liangshan":
        owner = "MNG"
        cores = ("MNG", "CYI", "CDL", "CXI")
        late = "\n1644.10.1 = { owner = CXI controller = CXI }\n1655.1.1 = { discovered_by = SPA }\n1662.4.1 = { owner = CZH controller = CZH add_core = CZH }\n1681.10.1 = { owner = QNG controller = QNG add_core = QNG }\n"
    else:
        owner = "MNG"
        cores = ("MNG", "CXI")
        late = "\n1644.10.1 = { owner = CXI controller = CXI }\n1646.12.1 = { owner = QNG controller = QNG add_core = QNG }\n1673.12.1 = { controller = CZH }\n1681.10.1 = { controller = QNG }\n"
    lines = [
        f"# {province.province_id} - {province.english}", "", f"owner = {owner}",
        f"controller = {owner}", *(f"add_core = {core}" for core in cores),
        f"culture = {province.culture}", f"religion = {province.religion}",
        f'capital = "{province.english.split(" (")[0]}"', f"trade_goods = {province.goods}",
        f"base_tax = {province.development[0]}", f"base_production = {province.development[1]}",
        f"base_manpower = {province.development[2]}", "is_city = yes",
    ]
    if province.cot:
        lines += [f"center_of_trade = {province.cot}"]
    if province.fort:
        lines += ["fort_15th = yes"]
    lines += ["discovered_by = chinese", "discovered_by = nomad_group"]
    if province.culture in {"tibetan", "yi"}:
        lines += ["discovered_by = indian"]
    return "\n".join(lines) + "\n" + late


def update_histories() -> None:
    directory = MOD / "history/provinces"
    for province in P:
        for old in directory.glob(f"{province.province_id} - *.txt"):
            desired = directory / f"{province.province_id} - {province.english}.txt"
            if old != desired:
                old.unlink()
        (directory / f"{province.province_id} - {province.english}.txt").write_text(
            history_text(province), encoding="utf-8"
        )


def position_block(province: Province, x: int, y: int) -> str:
    points = " ".join([f"{x:.3f} {y:.3f}"] * 6 + ["0.000 0.000"])
    return f"""#{province.english} - Sichuan 36-province refinement
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
    text = re.sub(r"(?m)^#.* - Sichuan 36-province refinement\n", "", text)
    for province in P:
        x, y = centres[province.province_id]
        text = replace_named_block(text, str(province.province_id), position_block(province, x, y))
    path.write_text(text, encoding="cp1252")


def update_memberships() -> None:
    new_ids = [p.province_id for p in P if p.province_id >= 5075]
    for filename, block in (("continent.txt", "asia"), ("climate.txt", "normal_monsoon")):
        path = MAP / filename
        text = path.read_text(encoding="cp1252")
        marker = "B18 Sichuan 36-province refinement"
        if marker not in text:
            text = append_ids_to_named_block(text, block, new_ids, marker)
            path.write_text(text, encoding="cp1252")

    node_path = MOD / "common/tradenodes/00_tradenodes.txt"
    text = node_path.read_text(encoding="cp1252")
    marker = "B18 Sichuan 36-province refinement"
    start = text.index("chengdu={")
    # The Chengdu node is bounded by its balanced braces, so a local insertion
    # cannot accidentally modify another trade node's members block.
    depth = 0
    end = None
    for i in range(text.find("{", start), len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0: end = i + 1; break
    node = text[start:end]
    if marker not in node:
        node = append_ids_to_named_block(node, "members", new_ids, marker)
        text = text[:start] + node + text[end:]
        node_path.write_text(text, encoding="cp1252")

    company_path = MOD / "common/trade_companies/00_trade_companies.txt"
    text = company_path.read_text(encoding="cp1252")
    start = text.index("trade_company_chengdu = {")
    end = text.index("trade_company_lhasa", start)
    block = text[start:end]
    if marker not in block:
        block = append_ids_to_named_block(block, "provinces", new_ids, marker)
        company_path.write_text(text[:start] + block + text[end:], encoding="cp1252")

    default_path = MAP / "default.map"
    text = default_path.read_text(encoding="cp1252")
    text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5096", text)
    default_path.write_text(text, encoding="cp1252")


def update_localisation() -> None:
    lines = ["l_english:"]
    for province in P:
        lines += [f' PROV{province.province_id}:0 "{province.chinese}"', f' PROV_ADJ{province.province_id}:0 "{province.chinese}"']
    lines.append("")
    for area, (display, capital) in AREA_NAMES.items():
        lines += [f' {area}:0 "{display}"', f' {area}_name:0 "{capital}"', f' {area}_adj:0 "{display}"']
    source = MOD / "localisation_source/gdd_b18_sichuan_map_readable_utf8.txt"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(source, MOD / "localisation/gdd_b18_sichuan_map_l_english.yml")


def main() -> None:
    centres = apply_geometry()
    update_definition()
    update_areas_and_region()
    update_histories()
    update_positions(centres)
    update_memberships()
    update_localisation()
    print("SICHUAN_36_PROVINCE_REFINEMENT_APPLIED")


if __name__ == "__main__":
    main()
