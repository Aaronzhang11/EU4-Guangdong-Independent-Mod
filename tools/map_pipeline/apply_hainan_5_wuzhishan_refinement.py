#!/usr/bin/env python3
"""Apply the reviewed five-province Hainan and Wuzhishan draft."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import apply_gansu_ningxia_refinement as common


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
DRAFT = ROOT / "planning/hainan_5_wuzhishan_formal_base_draft.bmp"
BACKUP = ROOT / "planning/pre_hainan_5_wuzhishan_provinces.bmp"
PREVIEW = ROOT / "docs/map/previews/B27_hainan_5_wuzhishan_formal.png"
MARKER = "B27 Hainan five-province refinement"


@dataclass(frozen=True)
class Province:
    province_id: int
    chinese: str
    english: str
    colour: tuple[int,int,int]
    goods: str | None
    development: tuple[int,int,int]


P = (
    Province(666,"琼州","Qiongzhou",(239,174,66),"grain",(3,2,2)),
    Province(5301,"儋州","Danzhou",(196,91,74),"salt",(2,2,2)),
    Province(5302,"昌化","Changhua",(84,156,103),"tropical_wood",(2,2,1)),
    Province(2160,"崖州","Yazhou",(59,141,183),"fish",(2,2,2)),
    Province(5303,"万州","Wanzhou",(155,113,184),"spices",(2,2,2)),
    Province(5304,"五指山","Wuzhishan",(92,88,84),None,(0,0,0)),
)
LAND = tuple(province for province in P if province.goods is not None)
MOUNTAIN = next(province for province in P if province.goods is None)


def definitions() -> dict[int,tuple[int,int,int]]:
    output={}
    for line in (MAP/"definition.csv").read_text(encoding="cp1252").splitlines():
        fields=line.split(";")
        if fields[0].isdigit():output[int(fields[0])]=tuple(map(int,fields[1:4]))
    return output


def actual_point(mask: np.ndarray) -> tuple[int,int]:
    ys,xs=np.where(mask);x,y=int(np.median(xs)),int(np.median(ys));nearest=int(np.argmin((xs-x)**2+(ys-y)**2))
    return int(xs[nearest]),int(ys[nearest])


def apply_geometry() -> tuple[np.ndarray,dict[int,tuple[int,int]]]:
    if not BACKUP.exists():shutil.copy2(MAP/"provinces.bmp",BACKUP)
    base=np.asarray(Image.open(MAP/"provinces.bmp").convert("RGB"));draft=np.asarray(Image.open(DRAFT).convert("RGB"))
    if base.shape!=draft.shape:raise ValueError("Hainan draft dimensions differ")
    defs=definitions();already=all(defs.get(p.province_id)==p.colour for p in P)
    old=np.zeros(base.shape[:2],dtype=bool)
    if not already:
        for province_id in (666,2160):old|=np.all(base==defs[province_id],axis=2)
    union=np.zeros(base.shape[:2],dtype=bool);centres={};output=base.copy()
    for province in P:
        mask=np.all(draft==province.colour,axis=2)
        if not mask.any():raise ValueError(f"Empty Hainan cell: {province.chinese}")
        union|=mask;output[mask]=province.colour
        if province.goods:
            x,y=actual_point(mask);centres[province.province_id]=(x,output.shape[0]-y)
    if old.any() and not np.array_equal(old,union):
        raise ValueError("Draft does not exactly cover the two formal Hainan provinces")
    Image.fromarray(output,mode="RGB").save(MAP/"provinces.bmp",format="BMP")
    return output,centres


def update_definition() -> None:
    path=MAP/"definition.csv";records={p.province_id:p for p in P};lines=path.read_text(encoding="cp1252").splitlines();out=[];seen=set()
    for line in lines:
        head=line.split(";",1)[0]
        if head.isdigit() and int(head) in records:
            p=records[int(head)];r,g,b=p.colour;out.append(f"{p.province_id};{r};{g};{b};{p.english};x");seen.add(p.province_id)
        else:out.append(line)
    for p in P:
        if p.province_id not in seen:
            r,g,b=p.colour;out.append(f"{p.province_id};{r};{g};{b};{p.english};x")
    path.write_text("\n".join(out)+"\n",encoding="cp1252")


def update_areas_region() -> None:
    path=MAP/"area.txt";text=path.read_text(encoding="cp1252")
    bounds=common.block_bounds(text,"west_guangdong_area");block=text[bounds[0]:bounds[1]]
    clean="\n".join(line.split("#")[0] for line in block.splitlines());ids=[int(i) for i in re.findall(r"\b\d+\b",clean) if int(i) not in (666,2160)]
    text=common.replace_block(text,"west_guangdong_area",f"west_guangdong_area = {{\n    {' '.join(map(str,ids))}\n}}")
    text=common.replace_block(text,"hainan_area",f"hainan_area = {{ # {MARKER}\n    666 5301 5302 2160 5303\n}}")
    path.write_text(text,encoding="cp1252")
    path=MAP/"region.txt";text=path.read_text(encoding="cp1252");bounds=common.block_bounds(text,"south_china_region");block=text[bounds[0]:bounds[1]]
    if re.search(r"(?m)^\s*hainan_area\s*$",block) is None:block=block.replace("        west_guangdong_area\n","        west_guangdong_area\n        hainan_area\n",1)
    path.write_text(text[:bounds[0]]+block+text[bounds[1]:],encoding="cp1252")


def history_text(p: Province) -> str:
    tax,production,manpower=p.development
    return "\n".join([f"# {p.province_id} - {p.english}","","owner = MNG","controller = MNG","add_core = MNG","culture = chimin","religion = confucianism",f'capital = "{p.english}"',f"trade_goods = {p.goods}",f"base_tax = {tax}",f"base_production = {production}",f"base_manpower = {manpower}","is_city = yes","discovered_by = chinese","discovered_by = indian","discovered_by = muslim","discovered_by = nomad_group"]) + "\n"


def update_histories() -> None:
    directory=MOD/"history/provinces"
    for p in P:
        for old in directory.glob(f"{p.province_id} - *.txt"):old.unlink()
        if p.goods:(directory/f"{p.province_id} - {p.english}.txt").write_text(history_text(p),encoding="utf-8")


def position_block(p: Province,x: int,y: int) -> str:
    points=" ".join([f"{x:.3f} {y:.3f}"]*6+["0.000 0.000"])
    return f"""#{p.english} - {MARKER}
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
    path=MAP/"positions.txt";text=path.read_text(encoding="cp1252");text=re.sub(rf"(?m)^#.* - {re.escape(MARKER)}\n","",text)
    for p in LAND:text=common.replace_block(text,str(p.province_id),position_block(p,*centres[p.province_id]))
    path.write_text(text,encoding="cp1252")


def update_memberships() -> None:
    new_all=[5301,5302,5303,5304];new_land=[5301,5302,5303]
    path=MAP/"continent.txt";text=common.append_ids(path.read_text(encoding="cp1252"),"asia",new_all,MARKER);path.write_text(text,encoding="cp1252")
    path=MAP/"climate.txt";text=path.read_text(encoding="cp1252");text=common.append_ids(text,"tropical",new_all,MARKER);text=common.append_ids(text,"normal_monsoon",new_all,MARKER);text=common.append_ids(text,"impassable",[5304],MARKER+" impassable");path.write_text(text,encoding="cp1252")
    path=MAP/"terrain.txt";text=path.read_text(encoding="cp1252");text=common.append_nested_ids(text,"jungle","terrain_override",new_land,MARKER+" jungle");text=common.append_nested_ids(text,"mountain","terrain_override",[5304],MARKER+" mountain");path.write_text(text,encoding="cp1252")
    path=MOD/"common/tradenodes/00_tradenodes.txt";text=common.append_nested_ids(path.read_text(encoding="cp1252"),"canton","members",new_land,MARKER);path.write_text(text,encoding="cp1252")
    path=MOD/"common/trade_companies/00_trade_companies.txt";text=common.append_nested_ids(path.read_text(encoding="cp1252"),"trade_company_south_china","provinces",new_land,MARKER);path.write_text(text,encoding="cp1252")
    path=MAP/"default.map";text=path.read_text(encoding="cp1252");current=int(re.search(r"(?m)^max_provinces\s*=\s*(\d+)",text).group(1));text=re.sub(r"(?m)^max_provinces\s*=\s*\d+",f"max_provinces = {max(current,5305)}",text);path.write_text(text,encoding="cp1252")


def update_localisation() -> None:
    lines=["l_english:"]
    for p in P:lines += [f' PROV{p.province_id}:0 "{p.chinese}"',f' PROV_ADJ{p.province_id}:0 "{p.chinese}"']
    lines += [' hainan_area:0 "海南"',' hainan_area_name:0 "琼州"',' hainan_area_adj:0 "海南"']
    source=MOD/"localisation_source/gdd_b27_hainan_map_readable_utf8.txt";source.write_text("\n".join(lines)+"\n",encoding="utf-8");sys.path.insert(0,str(ROOT/"tools"));from encode_eu4_chinese_localisation import encode_file;encode_file(source,MOD/"localisation/gdd_b27_hainan_map_l_english.yml")


def render_preview(bitmap: np.ndarray) -> None:
    crop=bitmap[1065:1115,4492:4548];shown=Image.fromarray(crop).resize((896,800),Image.Resampling.NEAREST);canvas=Image.new("RGB",(1280,860),(247,245,239));canvas.paste(shown,(20,50));draw=ImageDraw.Draw(canvas);font="/System/Library/Fonts/STHeiti Medium.ttc";draw.text((20,12),"海南五省与五指山 · 正式实装",font=ImageFont.truetype(font,27),fill=(30,34,36));x,y=945,80
    for p in LAND:draw.text((x,y),f"{p.chinese} · {sum(p.development)}发展度",font=ImageFont.truetype(font,15),fill=(38,41,43));y+=42
    draw.text((x,y),"五指山 · 不可通行",font=ImageFont.truetype(font,15),fill=(38,41,43));y+=55;draw.text((x,y),"海南区域：30发展度",font=ImageFont.truetype(font,15),fill=(38,41,43));y+=36;draw.text((x,y),"贸易中心：0",font=ImageFont.truetype(font,15),fill=(38,41,43));canvas.save(PREVIEW)


def main() -> None:
    bitmap,centres=apply_geometry();update_definition();update_areas_region();update_histories();update_positions(centres);update_memberships();update_localisation();render_preview(bitmap);print("HAINAN_5_PROVINCE_WUZHISHAN_APPLIED")


if __name__=="__main__":main()
