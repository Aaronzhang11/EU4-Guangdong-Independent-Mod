#!/usr/bin/env python3
"""Apply the reviewed 13-province Fujian GeoJSON draft and coupled assets."""

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
DRAFT = ROOT / "planning/fujian_13_province_draft.bmp"


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
    cot: int = 0
    fort: bool = False


P = (
    Province(669, "福州", "Fuzhou", "fujian_area", (230,137,66), (223,90,255), (4665,963), "tea", (7,7,3), 1, True),
    Province(5096, "福宁", "Funing", "fujian_area", (80,156,200), (80,156,200), (4675,954), "tea", (4,4,2)),
    Province(5097, "福清", "Fuqing", "fujian_area", (220,184,69), (220,184,69), (4665,976), "fish", (5,5,2)),
    Province(4952, "兴化", "Xinghua", "fujian_area", (77,170,118), (226,189,60), (4664,982), "fish", (5,5,2)),
    Province(1829, "泉州", "Quanzhou", "minnan_area", (201,92,78), (79,116,126), (4658,990), "chinaware", (8,8,3), 2),
    Province(5098, "永春", "Yongchun", "minnan_area", (151,103,190), (151,103,190), (4648,986), "tea", (3,4,2)),
    Province(4958, "厦门", "Xiamen", "minnan_area", (135,45,225), (135,45,225), (4648,997), "fish", (4,6,2)),
    Province(4953, "漳州", "Zhangzhou", "minnan_area", (69,157,151), (45,180,190), (4641,1004), "sugar", (5,5,2)),
    Province(2152, "建宁", "Jianning", "west_fujian_area", (105,145,76), (144,37,37), (4648,942), "paper", (3,3,2)),
    Province(4957, "邵武", "Shaowu", "west_fujian_area", (198,137,57), (230,110,35), (4629,950), "paper", (3,3,2)),
    Province(5099, "延平", "Yanping", "west_fujian_area", (83,111,176), (83,111,176), (4641,967), "naval_supplies", (4,4,2)),
    Province(2153, "汀州", "Tingzhou", "west_fujian_area", (176,78,103), (67,84,112), (4623,983), "iron", (4,4,2)),
    Province(5100, "龙岩", "Longyan", "west_fujian_area", (113,163,157), (113,163,157), (4638,994), "copper", (3,4,2)),
)

AREA_NAMES = {
    "fujian_area": ("闽东", "闽侯"),
    "minnan_area": ("闽南", "泉州"),
    "west_fujian_area": ("闽西", "汀州"),
}


def mask(values: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    return np.all(values == np.asarray(colour, dtype=np.uint8), axis=2)


def replace_named_block(text: str, name: str, replacement: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    depth = 0
    for index in range(text.find("{", match.start()), len(text)):
        if text[index] == "{": depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[:match.start()] + replacement.rstrip() + text[index+1:]
    raise ValueError(f"Unclosed block {name}")


def append_ids(text: str, block_name: str, ids: list[int], comment: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(block_name)}\s*=\s*\{{", text)
    if not match: raise ValueError(f"Missing block {block_name}")
    depth = 0
    for index in range(text.find("{", match.start()), len(text)):
        if text[index] == "{": depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                insertion = "\n        " + " ".join(map(str, ids)) + f" # {comment}\n"
                return text[:index].rstrip() + insertion + text[index:]
    raise ValueError(f"Unclosed block {block_name}")


def apply_geometry() -> dict[int, tuple[int, int]]:
    original = np.array(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    draft = np.array(Image.open(DRAFT).convert("RGB"), dtype=np.uint8)
    if original.shape != draft.shape: raise ValueError("Draft dimensions differ")
    xiamen_before = original.copy()[mask(original, (135,45,225))]
    changed = 0; centres = {}
    for province in P:
        province_mask = mask(draft, province.draft_colour)
        if not province_mask.any(): raise ValueError(f"Empty draft province: {province.chinese}")
        before = original[province_mask].copy(); original[province_mask] = province.colour
        changed += int(np.count_nonzero(np.any(before != original[province_mask], axis=1)))
        ys, xs = np.where(province_mask); sx, sy = province.seed
        nearest = int(np.argmin((xs-sx)**2 + (ys-sy)**2))
        centres[province.province_id] = (int(xs[nearest]), 2048-int(ys[nearest]))
    # User-authored Xiamen geometry and RGB are immutable.
    xiamen_after = original[mask(original, (135,45,225))]
    if len(xiamen_before) != 29 or len(xiamen_after) != 29 or not np.array_equal(xiamen_before, xiamen_after):
        raise AssertionError("Xiamen pixel preservation failed")
    Image.fromarray(original, mode="RGB").save(MAP / "provinces.bmp", format="BMP")
    print(f"FUJIAN_GEOMETRY_APPLIED:{changed};XIAMEN_PIXELS:29")
    return centres


def update_definition() -> None:
    path = MAP / "definition.csv"; lines = path.read_text(encoding="cp1252").splitlines()
    by_id = {p.province_id:p for p in P}; found=set(); output=[]
    for line in lines:
        head=line.split(";",1)[0]
        if head.isdigit() and int(head) in by_id:
            p=by_id[int(head)]; r,g,b=p.colour
            output.append(f"{p.province_id};{r};{g};{b};{p.english};x"); found.add(p.province_id)
        else: output.append(line)
    for p in P:
        if p.province_id not in found:
            r,g,b=p.colour; output.append(f"{p.province_id};{r};{g};{b};{p.english};x")
    path.write_text("\n".join(output)+"\n",encoding="cp1252")


def update_areas_region() -> None:
    path=MAP/"area.txt"; text=path.read_text(encoding="cp1252")
    for area in AREA_NAMES:
        ids=[p.province_id for p in P if p.area==area]
        text=replace_named_block(text,area,f"{area} = {{ # Fujian 13-province refinement\n    {' '.join(map(str,ids))}\n}}")
    path.write_text(text,encoding="cp1252")
    path=MAP/"region.txt"; text=path.read_text(encoding="cp1252")
    start=text.index("south_china_region = {"); end=text.index("xinan_region",start); block=text[start:end]
    if "minnan_area" not in block: block=block.replace("        fujian_area\n","        fujian_area\n        minnan_area\n")
    path.write_text(text[:start]+block+text[end:],encoding="cp1252")


def history(p: Province) -> str:
    cores=["MNG","MIN"]
    lines=[f"# {p.province_id} - {p.english}","","owner = MNG","controller = MNG",*(f"add_core = {c}" for c in cores),
           "culture = gdd_min","religion = confucianism",f'capital = "{p.english}"',f"trade_goods = {p.goods}",
           f"base_tax = {p.development[0]}",f"base_production = {p.development[1]}",f"base_manpower = {p.development[2]}","is_city = yes"]
    if p.cot: lines.append(f"center_of_trade = {p.cot}")
    if p.fort: lines.append("fort_15th = yes")
    lines += ["discovered_by = chinese","discovered_by = nomad_group","","1519.1.1 = { discovered_by = POR }",
              "1646.10.1 = { owner = QNG controller = QNG add_core = QNG }",
              "1662.4.1 = { owner = CZH controller = CZH add_core = CZH }",
              "1681.10.1 = { owner = QNG controller = QNG add_core = QNG }"]
    return "\n".join(lines)+"\n"


def update_histories() -> None:
    directory=MOD/"history/provinces"
    for p in P:
        desired=directory/f"{p.province_id} - {p.english}.txt"
        for old in directory.glob(f"{p.province_id} - *.txt"):
            if old != desired: old.unlink()
        desired.write_text(history(p),encoding="utf-8")


def position_block(p: Province, x: int, y: int) -> str:
    points=" ".join([f"{x:.3f} {y:.3f}"]*6+["0.000 0.000"])
    return f"""#{p.english} - Fujian 13-province refinement
{p.province_id}={{
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


def update_positions(centres: dict[int,tuple[int,int]]) -> None:
    path=MAP/"positions.txt"; text=path.read_text(encoding="cp1252")
    text=re.sub(r"(?m)^#.* - Fujian 13-province refinement\n","",text)
    for p in P:
        # Keep the user's existing Xiamen placement along with its pixels.
        if p.province_id == 4958: continue
        x,y=centres[p.province_id]; text=replace_named_block(text,str(p.province_id),position_block(p,x,y))
    path.write_text(text,encoding="cp1252")


def update_memberships() -> None:
    new_ids=[p.province_id for p in P if p.province_id>=5096]; marker="B19 Fujian 13-province refinement"
    for filename,block_name in (("continent.txt","asia"),("climate.txt","normal_monsoon")):
        path=MAP/filename; text=path.read_text(encoding="cp1252")
        if marker not in text: path.write_text(append_ids(text,block_name,new_ids,marker),encoding="cp1252")
    node_path=MOD/"common/tradenodes/00_tradenodes.txt"; text=node_path.read_text(encoding="cp1252")
    start=text.index("canton={"); depth=0; end=None
    for i in range(text.find("{",start),len(text)):
        if text[i]=="{":depth+=1
        elif text[i]=="}":
            depth-=1
            if depth==0:end=i+1;break
    node=text[start:end]
    if marker not in node: node=append_ids(node,"members",new_ids,marker); node_path.write_text(text[:start]+node+text[end:],encoding="cp1252")
    company_path=MOD/"common/trade_companies/00_trade_companies.txt"; text=company_path.read_text(encoding="cp1252")
    start=text.index("trade_company_east_china = {"); depth=0; end=None
    for i in range(text.find("{",start),len(text)):
        if text[i]=="{": depth+=1
        elif text[i]=="}":
            depth-=1
            if depth==0: end=i+1; break
    if end is None: raise ValueError("Unclosed trade_company_east_china")
    block=text[start:end]
    if marker not in block: block=append_ids(block,"provinces",new_ids,marker); company_path.write_text(text[:start]+block+text[end:],encoding="cp1252")
    path=MAP/"default.map"; text=path.read_text(encoding="cp1252"); text=re.sub(r"(?m)^max_provinces\s*=\s*\d+","max_provinces = 5101",text); path.write_text(text,encoding="cp1252")


def update_localisation() -> None:
    lines=["l_english:"]
    for p in P: lines += [f' PROV{p.province_id}:0 "{p.chinese}"',f' PROV_ADJ{p.province_id}:0 "{p.chinese}"']
    lines.append("")
    for area,(display,capital) in AREA_NAMES.items(): lines += [f' {area}:0 "{display}"',f' {area}_name:0 "{capital}"',f' {area}_adj:0 "{display}"']
    source=MOD/"localisation_source/gdd_b19_fujian_map_readable_utf8.txt"; source.write_text("\n".join(lines)+"\n",encoding="utf-8")
    sys.path.insert(0,str(ROOT/"tools")); from encode_eu4_chinese_localisation import encode_file
    encode_file(source,MOD/"localisation/gdd_b19_fujian_map_l_english.yml")


def main() -> None:
    centres=apply_geometry(); update_definition(); update_areas_region(); update_histories(); update_positions(centres); update_memberships(); update_localisation()
    print("FUJIAN_13_PROVINCE_REFINEMENT_APPLIED")


if __name__ == "__main__": main()
