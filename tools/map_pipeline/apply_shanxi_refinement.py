#!/usr/bin/env python3
"""Apply the reviewed 20-province Shanxi draft and five mountain barriers."""

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
DRAFT = ROOT / "planning/shanxi_20_mountain_draft.bmp"
PREVIEW = ROOT / "docs/map/previews/B23_shanxi_20_formal.png"


@dataclass(frozen=True)
class Province:
    province_id: int
    chinese: str
    english: str
    area: str | None
    draft_colour: tuple[int, int, int]
    colour: tuple[int, int, int]
    goods: str | None
    development: tuple[int, int, int]
    cot: int = 0
    fort: bool = False


P = (
    Province(697,"大同","Datong","yanmen_area",(218,88,72),(227,146,128),"iron",(5,5,3),1,True),
    Province(5242,"右玉","Youyu","yanmen_area",(236,160,55),(236,160,55),"livestock",(2,3,2)),
    Province(5243,"朔州","Shuozhou","yanmen_area",(226,200,66),(226,200,66),"grain",(3,4,2)),
    Province(2177,"宁武","Ningwu","yanmen_area",(137,191,64),(89,162,208),"livestock",(2,3,3),0,True),
    Province(5244,"代州","Daizhou","yanmen_area",(65,172,104),(65,172,104),"livestock",(3,3,2),0,True),
    Province(693,"太原","Taiyuan","shanxi_area",(58,164,160),(227,138,192),"cloth",(8,8,4),2,True),
    Province(5245,"忻州","Xinzhou","shanxi_area",(62,144,197),(62,144,197),"grain",(3,4,2)),
    Province(5246,"平定","Pingding","shanxi_area",(89,112,203),(89,112,203),"iron",(3,5,2)),
    Province(5247,"辽州","Liaozhou","shanxi_area",(137,91,198),(137,91,198),"iron",(2,4,2)),
    Province(5248,"汾州","Fenzhou","shanxi_area",(193,120,74),(193,120,74),"wine",(4,5,2)),
    Province(2178,"潞安","Luan","shangdang_area",(63,126,95),(90,172,96),"iron",(5,5,3)),
    Province(5251,"沁州","Qinzhou","shangdang_area",(75,135,174),(75,135,174),"grain",(3,3,2)),
    Province(5252,"泽州","Zezhou","shangdang_area",(111,90,160),(111,90,160),"iron",(3,6,2)),
    Province(5249,"绛州","Jiangzhou","shangdang_area",(201,116,92),(201,116,92),"grain",(3,3,2)),
    Province(5250,"曲沃","Quwo","shangdang_area",(224,84,111),(224,84,111),"cloth",(4,3,2)),
    Province(5255,"离石","Lishi","hedong_area",(185,82,175),(185,82,175),"livestock",(2,3,3)),
    Province(5256,"隰州","Xizhou","hedong_area",(215,85,130),(215,85,130),"livestock",(2,3,3)),
    Province(694,"平阳","Pingyang","hedong_area",(106,153,74),(99,140,255),"cloth",(5,6,3)),
    Province(5253,"解州","Jiezhou","hedong_area",(173,81,86),(173,81,86),"salt",(3,6,2)),
    Province(5254,"蒲州","Puzhou","hedong_area",(211,139,69),(211,139,69),"grain",(3,4,2)),
    Province(5257,"恒五山","Heng-Wutai Mountains",None,(124,124,134),(124,124,134),None,(0,0,0)),
    Province(5258,"太行北山","North Taihang Mountains",None,(82,82,92),(82,82,92),None,(0,0,0)),
    Province(5259,"太行南山","South Taihang Mountains",None,(72,72,82),(72,72,82),None,(0,0,0)),
    Province(5260,"吕梁山","Luliang Mountains",None,(102,96,108),(102,96,108),None,(0,0,0)),
    Province(5261,"中条山","Zhongtiao Mountains",None,(118,105,92),(118,105,92),None,(0,0,0)),
)

AREA_NAMES = {
    "yanmen_area": ("雁门", "大同"),
    "shanxi_area": ("晋阳", "太原"),
    "shangdang_area": ("上党", "潞安"),
    "hedong_area": ("河东", "平阳"),
}


def mask(values: np.ndarray, colour: tuple[int,int,int]) -> np.ndarray:
    return np.all(values == np.asarray(colour,dtype=np.uint8),axis=2)


def block_bounds(text: str, name: str) -> tuple[int,int] | None:
    match=re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{",text)
    if not match:return None
    depth=0
    for i in range(text.find("{",match.start()),len(text)):
        if text[i]=="{":depth+=1
        elif text[i]=="}":
            depth-=1
            if depth==0:return match.start(),i+1
    raise ValueError(f"Unclosed block {name}")


def replace_block(text: str,name: str,replacement: str) -> str:
    bounds=block_bounds(text,name)
    if bounds is None:return text.rstrip()+"\n\n"+replacement.rstrip()+"\n"
    return text[:bounds[0]]+replacement.rstrip()+text[bounds[1]:]


def remove_all_blocks(text: str,name: str) -> str:
    while (bounds:=block_bounds(text,name)) is not None:
        text=text[:bounds[0]]+text[bounds[1]:].lstrip("\n")
    return text


def append_ids(text: str,name: str,ids: list[int],comment: str) -> str:
    bounds=block_bounds(text,name)
    if bounds is None:raise ValueError(f"Missing block {name}")
    block=text[bounds[0]:bounds[1]]
    pos=block.rfind("}")
    insertion="\n    "+" ".join(map(str,ids))+f" # {comment}\n"
    block=block[:pos].rstrip()+insertion+block[pos:]
    return text[:bounds[0]]+block+text[bounds[1]:]


def apply_geometry() -> tuple[np.ndarray,dict[int,tuple[int,int]]]:
    base=np.array(Image.open(MAP/"provinces.bmp").convert("RGB"),dtype=np.uint8)
    draft=np.array(Image.open(DRAFT).convert("RGB"),dtype=np.uint8)
    if base.shape!=draft.shape:raise ValueError("Shanxi draft dimensions differ")
    centres={};changed=0;draft_union=np.zeros(base.shape[:2],dtype=bool)
    for province in P:
        province_mask=mask(draft,province.draft_colour)
        if not province_mask.any():raise ValueError(f"Empty draft province: {province.chinese}")
        draft_union |= province_mask
        before=base[province_mask].copy();base[province_mask]=province.colour
        changed+=int(np.count_nonzero(np.any(before!=base[province_mask],axis=1)))
        if province.area:
            ys,xs=np.where(province_mask);centres[province.province_id]=(int(np.median(xs)),2048-int(np.median(ys)))
    # Copy the draft's neighbour-colour backfill for pieces of the old
    # five-province outline that lie outside the new workshop-derived border.
    managed=np.zeros(base.shape[:2],dtype=bool)
    for province in P:
        managed |= mask(base,province.colour)
    cleanup=managed & ~draft_union
    cleanup_before=base[cleanup].copy();base[cleanup]=draft[cleanup]
    cleanup_changed=int(np.count_nonzero(np.any(cleanup_before!=base[cleanup],axis=1)))
    Image.fromarray(base,mode="RGB").save(MAP/"provinces.bmp",format="BMP")
    print(f"SHANXI_GEOMETRY_APPLIED:{changed};OLD_BORDER_RETURNED:{cleanup_changed}")
    return base,centres


def update_definition() -> None:
    path=MAP/"definition.csv";lines=path.read_text(encoding="cp1252").splitlines();by_id={p.province_id:p for p in P};found=set();out=[]
    for line in lines:
        head=line.split(";",1)[0]
        if head.isdigit() and int(head) in by_id:
            p=by_id[int(head)];r,g,b=p.colour;out.append(f"{p.province_id};{r};{g};{b};{p.english};x");found.add(p.province_id)
        else:out.append(line)
    for p in P:
        if p.province_id not in found:
            r,g,b=p.colour;out.append(f"{p.province_id};{r};{g};{b};{p.english};x")
    path.write_text("\n".join(out)+"\n",encoding="cp1252")


def update_areas_region() -> None:
    path=MAP/"area.txt";text=path.read_text(encoding="cp1252")
    for area in AREA_NAMES:text=remove_all_blocks(text,area)
    for area in AREA_NAMES:
        ids=[p.province_id for p in P if p.area==area]
        if len(ids)!=5:raise AssertionError(f"{area} does not contain five provinces")
        text=text.rstrip()+f"\n\n{area} = {{ # Shanxi 20-province refinement\n    {' '.join(map(str,ids))}\n}}\n"
    path.write_text(text,encoding="cp1252")
    path=MAP/"region.txt";text=path.read_text(encoding="cp1252");start=text.index("north_china_region = {");end=text.index("central_asia_region",start) if "central_asia_region" in text[start:] else len(text);block=text[start:end]
    for area in ("yanmen_area","shangdang_area","hedong_area"):
        if re.search(rf"(?m)^\s*{area}\s*$",block) is None:block=block.replace("        shanxi_area\n",f"        shanxi_area\n        {area}\n",1)
    path.write_text(text[:start]+block+text[end:],encoding="cp1252")


def history_text(p: Province) -> str:
    lines=[f"# {p.province_id} - {p.english}","","owner = MNG","controller = MNG","add_core = MNG","culture = zhili","religion = confucianism",f'capital = "{p.english}"',f"trade_goods = {p.goods}",f"base_tax = {p.development[0]}",f"base_production = {p.development[1]}",f"base_manpower = {p.development[2]}","is_city = yes"]
    if p.cot:lines.append(f"center_of_trade = {p.cot}")
    if p.fort:lines.append("fort_15th = yes")
    lines += ["discovered_by = chinese","discovered_by = nomad_group"]
    return "\n".join(lines)+"\n"


def update_histories() -> None:
    directory=MOD/"history/provinces"
    for p in P:
        for old in directory.glob(f"{p.province_id} - *.txt"):old.unlink()
        if p.area:(directory/f"{p.province_id} - {p.english}.txt").write_text(history_text(p),encoding="utf-8")


def position_block(p: Province,x: int,y: int) -> str:
    pts=" ".join([f"{x:.3f} {y:.3f}"]*6+["0.000 0.000"])
    return f"""#{p.english} - Shanxi 20-province refinement
{p.province_id}={{
    position={{
        {pts}
    }}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 1.000 0.000 0.000 0.000 0.000
    }}
}}"""


def update_positions(centres: dict[int,tuple[int,int]]) -> None:
    path=MAP/"positions.txt";text=path.read_text(encoding="cp1252");text=re.sub(r"(?m)^#.* - Shanxi 20-province refinement\n","",text)
    for p in P:
        if not p.area:continue
        text=replace_block(text,str(p.province_id),position_block(p,*centres[p.province_id]))
    path.write_text(text,encoding="cp1252")


def add_to_top(path: Path,top: str,nested: str,ids: list[int],marker: str) -> None:
    text=path.read_text(encoding="cp1252");bounds=block_bounds(text,top)
    if bounds is None:raise ValueError(f"Missing {top}")
    block=text[bounds[0]:bounds[1]]
    block=re.sub(rf"(?m)^\s*.*# {re.escape(marker)}\n?","",block)
    block=append_ids(block,nested,ids,marker)
    path.write_text(text[:bounds[0]]+block+text[bounds[1]:],encoding="cp1252")


def add_to_terrain(text: str,terrain: str,ids: list[int],marker: str) -> str:
    bounds=block_bounds(text,terrain)
    if bounds is None:raise ValueError(f"Missing terrain {terrain}")
    block=text[bounds[0]:bounds[1]];block=re.sub(rf"(?m)^\s*.*# {re.escape(marker)}\n?","",block);block=append_ids(block,"terrain_override",ids,marker)
    return text[:bounds[0]]+block+text[bounds[1]:]


def update_memberships() -> None:
    land_new=[p.province_id for p in P if p.area and p.province_id>=5242]
    mountains=[p.province_id for p in P if not p.area]
    all_new=land_new+mountains;marker="B23 Shanxi 20-province refinement"
    path=MAP/"continent.txt";text=path.read_text(encoding="cp1252");text=re.sub(rf"(?m)^\s*.*# {re.escape(marker)}\n?","",text);text=append_ids(text,"asia",all_new,marker);path.write_text(text,encoding="cp1252")
    path=MAP/"climate.txt";text=path.read_text(encoding="cp1252");text=re.sub(rf"(?m)^\s*.*# {re.escape(marker)}(?: impassable)?\n?","",text);text=append_ids(text,"normal_monsoon",land_new,marker);text=append_ids(text,"impassable",mountains,marker+" impassable");path.write_text(text,encoding="cp1252")
    path=MAP/"terrain.txt";text=path.read_text(encoding="cp1252");text=add_to_terrain(text,"highlands",[5242,5244,5246,5247,5251,5252,5255,5256],marker+" highlands");text=add_to_terrain(text,"farmlands",[5243,5245,5248,5249,5250,5253,5254],marker+" farmlands");path.write_text(text,encoding="cp1252")
    add_to_top(MOD/"common/tradenodes/00_tradenodes.txt","beijing","members",land_new,marker)
    add_to_top(MOD/"common/trade_companies/00_trade_companies.txt","trade_company_north_china","provinces",land_new,marker)
    path=MAP/"default.map";text=path.read_text(encoding="cp1252");current=int(re.search(r"(?m)^max_provinces\s*=\s*(\d+)",text).group(1));text=re.sub(r"(?m)^max_provinces\s*=\s*\d+",f"max_provinces = {max(current,5262)}",text);path.write_text(text,encoding="cp1252")


def update_localisation() -> None:
    lines=["l_english:"]
    for p in P:lines += [f' PROV{p.province_id}:0 "{p.chinese}"',f' PROV_ADJ{p.province_id}:0 "{p.chinese}"']
    for area,(display,capital) in AREA_NAMES.items():lines += [f' {area}:0 "{display}"',f' {area}_name:0 "{capital}"',f' {area}_adj:0 "{display}"']
    source=MOD/"localisation_source/gdd_b23_shanxi_map_readable_utf8.txt";source.write_text("\n".join(lines)+"\n",encoding="utf-8");sys.path.insert(0,str(ROOT/"tools"));from encode_eu4_chinese_localisation import encode_file;encode_file(source,MOD/"localisation/gdd_b23_shanxi_map_l_english.yml")


def render_preview(bitmap: np.ndarray) -> None:
    crop=Image.fromarray(bitmap[675:845,4480:4635],mode="RGB");crop.resize((930,1020),Image.Resampling.NEAREST).save(PREVIEW)


def main() -> None:
    bitmap,centres=apply_geometry();update_definition();update_areas_region();update_histories();update_positions(centres);update_memberships();update_localisation();render_preview(bitmap)
    print("SHANXI_20_PROVINCE_REFINEMENT_APPLIED")


if __name__=="__main__":main()
