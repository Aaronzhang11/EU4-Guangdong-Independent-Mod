#!/usr/bin/env python3
"""Apply the reviewed 23-province Gansu–Ningxia formal-base draft."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
DRAFT = ROOT / "planning/gansu_ningxia_23_formal_base_draft.bmp"
BACKUP = ROOT / "planning/pre_gansu_ningxia_23_provinces.bmp"
PREVIEW = ROOT / "docs/map/previews/B26_gansu_ningxia_23_formal.png"
MARKER = "B26 Gansu-Ningxia 23-province refinement"


@dataclass(frozen=True)
class Province:
    province_id: int
    chinese: str
    english: str
    area: str
    colour: tuple[int, int, int]
    goods: str
    development: tuple[int, int, int]
    culture: str
    religion: str
    owner: str = "MNG"
    cot: int = 0
    fort: bool = False


P = (
    Province(698,"宁夏","Ningxia","ningxia_area",(52,96,168),"salt",(4,4,3),"mongol","confucianism",fort=True),
    Province(5286,"中卫","Zhongwei","ningxia_area",(135,233,113),"livestock",(2,2,2),"gdd_long","confucianism"),
    Province(5287,"灵州","Lingzhou","ningxia_area",(218,124,58),"grain",(3,4,2),"gdd_long","confucianism"),
    Province(5288,"松山","Songshan","ningxia_area",(55,15,249),"livestock",(1,2,2),"gdd_long","confucianism"),
    Province(2180,"秦州","Qinzhou Gansu","longnan_area",(138,152,194),"grain",(4,4,3),"gdd_zhongyuan","confucianism"),
    Province(2183,"洮州","Taozhou","longnan_area",(221,43,139),"livestock",(2,2,3),"gdd_long","vajrayana"),
    Province(5289,"阶州","Jiezhou Gansu","longnan_area",(58,180,84),"livestock",(2,2,1),"gdd_diqiang","confucianism"),
    Province(5290,"岷州","Minzhou","longnan_area",(141,71,29),"livestock",(2,2,2),"gdd_diqiang","vajrayana"),
    Province(5291,"巩昌","Gongchang","longnan_area",(224,208,220),"grain",(3,3,2),"gdd_long","confucianism"),
    Province(2184,"西宁","Xining","gansu_area",(61,99,165),"salt",(4,3,3),"gdd_long","vajrayana"),
    Province(699,"兰州","Lanzhou","gansu_area",(144,236,110),"copper",(5,5,3),"gdd_long","confucianism",cot=1),
    Province(5292,"碾伯","Nianbo","gansu_area",(227,127,55),"grain",(2,2,2),"gdd_long","vajrayana"),
    Province(5293,"河州","Hezhou Gansu","gansu_area",(64,18,246),"livestock",(2,3,2),"gdd_long","vajrayana"),
    Province(5294,"狄道","Didao","gansu_area",(147,155,191),"grain",(3,2,2),"gdd_long","confucianism"),
    Province(708,"武威","Wuwei","hexi_area",(230,46,136),"livestock",(4,3,3),"gdd_long","confucianism",fort=True),
    Province(2182,"靖远","Jingyuan","hexi_area",(67,183,81),"grain",(2,2,2),"gdd_long","confucianism"),
    Province(5295,"永昌","Yongchang","hexi_area",(150,74,26),"wool",(2,2,2),"gdd_long","confucianism"),
    Province(5296,"张掖","Zhangye","hexi_area",(233,211,217),"grain",(4,4,2),"gdd_long","confucianism",cot=1),
    Province(5297,"嘉峪","Jiayu","hexi_area",(70,102,162),"iron",(2,2,2),"gdd_long","confucianism",fort=True),
    Province(707,"玉门","Yumen","west_gansu_area",(153,239,107),"gems",(2,3,2),"oirats","vajrayana","HMI"),
    Province(5298,"瓜州","Guazhou","west_gansu_area",(236,130,52),"wool",(1,2,2),"oirats","vajrayana","HMI"),
    Province(5299,"苦峪","Kuyu","west_gansu_area",(73,21,243),"livestock",(1,2,2),"oirats","vajrayana","HMI"),
    Province(5300,"沙州","Shazhou","west_gansu_area",(156,158,188),"silk",(3,3,2),"oirats","vajrayana","HMI"),
)

AREA_NAMES = {
    "ningxia_area": ("宁夏", "宁夏"),
    "longnan_area": ("陇南", "秦州"),
    "gansu_area": ("陇中", "兰州"),
    "hexi_area": ("河西", "张掖"),
    "west_gansu_area": ("瓜沙", "沙州"),
}


def block_bounds(text: str, name: str) -> tuple[int, int] | None:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        return None
    depth = 0
    for index in range(text.find("{", match.start()), len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return match.start(), index + 1
    raise ValueError(f"Unclosed block: {name}")


def replace_block(text: str, name: str, replacement: str) -> str:
    bounds = block_bounds(text, name)
    if bounds is None:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[:bounds[0]] + replacement.rstrip() + text[bounds[1]:]


def append_ids(text: str, block_name: str, ids: list[int], marker: str) -> str:
    bounds = block_bounds(text, block_name)
    if bounds is None:
        raise ValueError(f"Missing block: {block_name}")
    block = text[bounds[0]:bounds[1]]
    block = re.sub(rf"(?m)^\s*.*# {re.escape(marker)}\n?", "", block)
    close = block.rfind("}")
    block = block[:close].rstrip() + "\n    " + " ".join(map(str, ids)) + f" # {marker}\n" + block[close:]
    return text[:bounds[0]] + block + text[bounds[1]:]


def append_nested_ids(text: str, top: str, nested: str, ids: list[int], marker: str) -> str:
    bounds = block_bounds(text, top)
    if bounds is None:
        raise ValueError(f"Missing top block: {top}")
    block = append_ids(text[bounds[0]:bounds[1]], nested, ids, marker)
    return text[:bounds[0]] + block + text[bounds[1]:]


def actual_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    x, y = int(np.median(xs)), int(np.median(ys))
    nearest = int(np.argmin((xs - x) ** 2 + (ys - y) ** 2))
    return int(xs[nearest]), int(ys[nearest])


def apply_geometry() -> tuple[np.ndarray, dict[int, tuple[int, int]]]:
    if not BACKUP.exists():
        shutil.copy2(MAP / "provinces.bmp", BACKUP)
    base = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    draft = np.asarray(Image.open(DRAFT).convert("RGB"))
    if base.shape != draft.shape:
        raise ValueError("Draft dimensions differ from formal provinces.bmp")
    formal_ids = (698, 699, 707, 708, 2180, 2182, 2183, 2184)
    definitions: dict[int, tuple[int, int, int]] = {}
    for line in (MAP / "definition.csv").read_text(encoding="cp1252").splitlines():
        fields = line.split(";")
        if fields[0].isdigit():
            definitions[int(fields[0])] = tuple(map(int, fields[1:4]))
    # On the first run this verifies that the reviewed draft changes exactly
    # the current eight-province Gansu mask. On a repeat run the map already
    # consists of the 23 final colours, so the draft is simply reapplied.
    already_applied = all(
        province.province_id in definitions
        and definitions[province.province_id] == province.colour
        for province in P
    )
    if not already_applied and all(pid in definitions for pid in formal_ids):
        old_mask = np.zeros(base.shape[:2], dtype=bool)
        for pid in formal_ids:
            old_mask |= np.all(base == definitions[pid], axis=2)
    else:
        old_mask = np.zeros(base.shape[:2], dtype=bool)
    output = base.copy()
    union = np.zeros(base.shape[:2], dtype=bool)
    centres: dict[int, tuple[int, int]] = {}
    for province in P:
        province_mask = np.all(draft == province.colour, axis=2)
        if not province_mask.any():
            raise ValueError(f"Empty draft province: {province.chinese}")
        union |= province_mask
        output[province_mask] = province.colour
        x, y = actual_point(province_mask)
        centres[province.province_id] = (x, output.shape[0] - y)
    if old_mask.any() and not np.all(union <= old_mask):
        raise ValueError("Draft crosses the current formal Gansu outer border")
    Image.fromarray(output, mode="RGB").save(MAP / "provinces.bmp", format="BMP")
    return output, centres


def update_definition() -> None:
    path = MAP / "definition.csv"
    records = {province.province_id: province for province in P}
    lines = path.read_text(encoding="cp1252").splitlines()
    output: list[str] = []
    seen: set[int] = set()
    for line in lines:
        head = line.split(";", 1)[0]
        if head.isdigit() and int(head) in records:
            province = records[int(head)]
            r, g, b = province.colour
            output.append(f"{province.province_id};{r};{g};{b};{province.english};x")
            seen.add(province.province_id)
        else:
            output.append(line)
    for province in P:
        if province.province_id not in seen:
            r, g, b = province.colour
            output.append(f"{province.province_id};{r};{g};{b};{province.english};x")
    path.write_text("\n".join(output) + "\n", encoding="cp1252")


def update_areas_and_region() -> None:
    path = MAP / "area.txt"
    text = path.read_text(encoding="cp1252")
    for area in AREA_NAMES:
        ids = [province.province_id for province in P if province.area == area]
        text = replace_block(text, area, f"{area} = {{ # {MARKER}\n    {' '.join(map(str, ids))}\n}}")
    path.write_text(text, encoding="cp1252")

    path = MAP / "region.txt"
    text = path.read_text(encoding="cp1252")
    bounds = block_bounds(text, "north_china_region")
    if bounds is None:
        raise ValueError("Missing north_china_region")
    block = text[bounds[0]:bounds[1]]
    for area in ("ningxia_area", "longnan_area", "hexi_area"):
        if re.search(rf"(?m)^\s*{area}\s*$", block) is None:
            block = block.replace("        gansu_area\n", f"        gansu_area\n        {area}\n", 1)
    path.write_text(text[:bounds[0]] + block + text[bounds[1]:], encoding="cp1252")


def history_text(province: Province) -> str:
    tax, production, manpower = province.development
    lines = [
        f"# {province.province_id} - {province.english}", "",
        f"owner = {province.owner}", f"controller = {province.owner}", f"add_core = {province.owner}",
    ]
    if province.owner != "MNG":
        lines.append("add_core = MNG")
    lines += [
        f"culture = {province.culture}", f"religion = {province.religion}",
        f'capital = "{province.english}"', f"trade_goods = {province.goods}",
        f"base_tax = {tax}", f"base_production = {production}", f"base_manpower = {manpower}",
        "is_city = yes",
    ]
    if province.cot:
        lines.append(f"center_of_trade = {province.cot}")
    if province.fort:
        lines.append("fort_15th = yes")
    lines += ["discovered_by = chinese", "discovered_by = nomad_group"]
    return "\n".join(lines) + "\n"


def update_histories() -> None:
    directory = MOD / "history/provinces"
    for province in P:
        for old in directory.glob(f"{province.province_id} - *.txt"):
            old.unlink()
        (directory / f"{province.province_id} - {province.english}.txt").write_text(
            history_text(province), encoding="utf-8")


def position_block(province: Province, x: int, y: int) -> str:
    points = " ".join([f"{x:.3f} {y:.3f}"] * 6 + ["0.000 0.000"])
    return f"""#{province.english} - {MARKER}
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
    text = re.sub(rf"(?m)^#.* - {re.escape(MARKER)}\n", "", text)
    for province in P:
        text = replace_block(text, str(province.province_id), position_block(province, *centres[province.province_id]))
    path.write_text(text, encoding="cp1252")


def update_memberships() -> None:
    new_ids = list(range(5286, 5301))
    xian_new = [5286,5287,5288,5289,5290,5291,5292,5293,5294,5295,5296,5297]
    # 5298 is a retired zero-pixel orphan; only Kuyu and Shazhou remain in Yumen.
    yumen_new = [5299,5300]

    path = MAP / "continent.txt"
    text = append_ids(path.read_text(encoding="cp1252"), "asia", new_ids, MARKER)
    path.write_text(text, encoding="cp1252")

    path = MAP / "climate.txt"
    text = path.read_text(encoding="cp1252")
    text = append_ids(text, "mild_winter", list(range(5286, 5298)), MARKER)
    text = append_ids(text, "arid", [5298,5299,5300], MARKER)
    path.write_text(text, encoding="cp1252")

    path = MAP / "terrain.txt"
    text = path.read_text(encoding="cp1252")
    terrain = {
        "farmlands": [5287,5291,5296],
        "hills": [5289,5290,5294],
        "grasslands": [5286,5292,5295],
        "drylands": [5288,5293,5297],
        "desert": [5298,5299,5300],
    }
    for name, ids in terrain.items():
        text = append_nested_ids(text, name, "terrain_override", ids, f"{MARKER} {name}")
    path.write_text(text, encoding="cp1252")

    path = MOD / "common/tradenodes/00_tradenodes.txt"
    text = path.read_text(encoding="cp1252")
    text = append_nested_ids(text, "xian", "members", xian_new, f"{MARKER} Xian")
    text = append_nested_ids(text, "yumen", "members", yumen_new, f"{MARKER} Yumen")
    path.write_text(text, encoding="cp1252")

    path = MOD / "common/trade_companies/00_trade_companies.txt"
    text = path.read_text(encoding="cp1252")
    text = append_nested_ids(text, "trade_company_xian", "provinces", xian_new, f"{MARKER} Xian")
    text = append_nested_ids(text, "trade_company_yumen", "provinces", yumen_new, f"{MARKER} Yumen")
    path.write_text(text, encoding="cp1252")

    path = MAP / "default.map"
    text = path.read_text(encoding="cp1252")
    current = int(re.search(r"(?m)^max_provinces\s*=\s*(\d+)", text).group(1))
    text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", f"max_provinces = {max(current, 5301)}", text)
    path.write_text(text, encoding="cp1252")


def update_localisation() -> None:
    lines = ["l_english:"]
    for province in P:
        lines += [f' PROV{province.province_id}:0 "{province.chinese}"',
                  f' PROV_ADJ{province.province_id}:0 "{province.chinese}"']
    for area, (display, capital) in AREA_NAMES.items():
        lines += [f' {area}:0 "{display}"', f' {area}_name:0 "{capital}"', f' {area}_adj:0 "{display}"']
    source = MOD / "localisation_source/gdd_b26_gansu_ningxia_map_readable_utf8.txt"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(source, MOD / "localisation/gdd_b26_gansu_ningxia_map_l_english.yml")


def render_preview(bitmap: np.ndarray) -> None:
    crop = bitmap[665:870, 4230:4495]
    shown = Image.fromarray(crop).resize((1060, 820), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (1500, 900), (247,245,239))
    canvas.paste(shown, (25,60))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 16)
    small = ImageFont.truetype(font_path, 13)
    draw.text((25,18), "甘肃—宁夏二十三省 · 正式实装", font=title, fill=(30,34,36))
    x, y = 1110, 78
    for area in AREA_NAMES:
        members = [province.chinese for province in P if province.area == area]
        draw.text((x,y), AREA_NAMES[area][0], font=body, fill=(35,39,41))
        draw.text((x+55,y), " · ".join(members), font=small, fill=(70,72,69))
        y += 48
    y += 18
    draw.text((x,y), "23省 · 总发展度174", font=body, fill=(35,39,41)); y += 38
    draw.text((x,y), "新增不可通行省份：0", font=body, fill=(35,39,41)); y += 38
    draw.text((x,y), "兰州二级、张掖一级贸易中心", font=small, fill=(65,68,66)); y += 32
    draw.text((x,y), "商品全部为原版贸易品", font=small, fill=(65,68,66))
    canvas.save(PREVIEW)


def main() -> None:
    bitmap, centres = apply_geometry()
    update_definition()
    update_areas_and_region()
    update_histories()
    update_positions(centres)
    update_memberships()
    update_localisation()
    render_preview(bitmap)
    print("GANSU_NINGXIA_23_PROVINCE_REFINEMENT_APPLIED")


if __name__ == "__main__":
    main()
