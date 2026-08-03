#!/usr/bin/env python3
"""Render a non-canonical 26-province Yunnan county-GeoJSON draft."""

from __future__ import annotations

from collections import deque
import csv
import json
from pathlib import Path
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
URL = "https://geo.datav.aliyun.com/areas_v3/bound/530000_full_district.json"
FULL_OUTPUT = ROOT / "planning/yunnan_26_province_draft.bmp"
CROP_OUTPUT = ROOT / "planning/yunnan_26_province_crop.bmp"
REVIEW_OUTPUT = ROOT / "docs/map/previews/B20_yunnan_26_geojson_draft.png"
CROP = (4315, 900, 4485, 1070)
SOURCE_IDS = (660, 661, 662, 663, 675, 2165, 2166, 2167)


PROVINCES = (
    ("滇西北", "德钦", (199, 104, 151), (4357, 927)),
    ("滇西北", "独克宗", (150, 193, 55), (4376, 932)),
    ("滇西北", "丽江", (61, 171, 211), (4384, 949)),
    ("滇西北", "剑川", (232, 192, 56), (4374, 966)),
    ("滇西北", "泸水", (218, 108, 54), (4347, 967)),
    ("滇西", "大理", (232, 154, 55), (4376, 985)),
    ("滇西", "保山", (202, 168, 74), (4354, 996)),
    ("滇西", "德宏", (74, 159, 125), (4343, 1012)),
    ("滇中", "楚雄", (221, 107, 52), (4396, 987)),
    ("滇中", "昆明", (238, 224, 204), (4413, 990)),
    ("滇中", "玉溪", (239, 194, 127), (4415, 1005)),
    ("滇中", "东川", (206, 55, 43), (4417, 968)),
    ("滇东", "昭通", (244, 182, 62), (4440, 938)),
    ("滇东", "镇雄", (107, 156, 51), (4457, 953)),
    ("滇东", "宣威", (25, 130, 90), (4445, 968)),
    ("滇东", "曲靖", (80, 78, 115), (4440, 986)),
    ("滇西南", "临沧", (145, 202, 55), (4376, 1017)),
    ("滇西南", "耿马", (231, 40, 37), (4359, 1021)),
    ("滇西南", "思茅", (226, 168, 151), (4392, 1031)),
    ("滇西南", "镇沅", (73, 172, 207), (4396, 1019)),
    ("滇西南", "勐连", (112, 218, 194), (4374, 1038)),
    ("滇南", "版纳", (246, 151, 27), (4387, 1047)),
    ("滇南", "勐腊", (57, 88, 139), (4401, 1048)),
    ("滇南", "蒙自", (36, 133, 156), (4425, 1018)),
    ("滇南", "红河", (241, 224, 45), (4415, 1032)),
    ("滇南", "文山", (143, 209, 24), (4450, 1020)),
)
NAME_TO_INDEX = {name:index for index,(_area,name,_colour,_seed) in enumerate(PROVINCES)}

PARENT_TARGET = {
    530100:"昆明", 530300:"曲靖", 530400:"玉溪", 530500:"保山",
    530600:"昭通", 530700:"丽江", 530800:"思茅", 530900:"临沧",
    532300:"楚雄", 532500:"蒙自", 532600:"文山", 532800:"版纳",
    532900:"大理", 533100:"德宏", 533300:"泸水", 533400:"独克宗",
}
COUNTY_TARGET = {
    # Dêqên and the old Zhongdian/Deqen frontier.
    "德钦县":"德钦", "维西傈僳族自治县":"德钦", "香格里拉市":"独克宗",
    # Jianchuan corridor north of Erhai.
    "剑川县":"剑川", "洱源县":"剑川", "鹤庆县":"剑川",
    # Kunming basin versus Dongchuan/Wumeng copper mountains.
    "东川区":"东川", "禄劝彝族苗族自治县":"东川", "寻甸回族彝族自治县":"东川",
    # Qujing basin and the Xuanwei corridor.
    "宣威市":"宣威", "富源县":"宣威", "会泽县":"宣威",
    # Zhaotong basin versus the eastern Zhenxiong highlands.
    "镇雄县":"镇雄", "彝良县":"镇雄", "威信县":"镇雄", "盐津县":"镇雄", "大关县":"镇雄",
    # Lincang and the Wa frontier.
    "耿马傣族佤族自治县":"耿马", "镇康县":"耿马", "沧源佤族自治县":"耿马",
    # Simao, Zhenyuan and Menglian sub-basins.
    "镇沅彝族哈尼族拉祜族自治县":"镇沅", "江城哈尼族彝族自治县":"镇沅",
    "孟连傣族拉祜族佤族自治县":"勐连", "澜沧拉祜族自治县":"勐连", "西盟佤族自治县":"勐连",
    # Xishuangbanna split along the Lancang river and Mengla mountains.
    "勐腊县":"勐腊", "景洪市":"版纳", "勐海县":"版纳",
    # Red River north/south banks and the Mengzi basin.
    "元阳县":"红河", "红河县":"红河", "金平苗族瑶族傣族自治县":"红河",
    "绿春县":"红河", "河口瑶族自治县":"红河",
}

AREA_COLOURS = {
    "滇西北":(112,105,184), "滇西":(208,139,60), "滇中":(199,92,66),
    "滇东":(68,143,98), "滇西南":(73,161,151), "滇南":(61,132,183),
}


def font(size:int,bold:bool=False):
    for path in (Path("/System/Library/Fonts/PingFang.ttc"),Path("/System/Library/Fonts/STHeiti Medium.ttc")):
        if path.exists(): return ImageFont.truetype(str(path),size=size,index=1 if path.name=="PingFang.ttc" and bold else 0)
    return ImageFont.load_default()


def definitions():
    c2i={}
    with (MOD/"map/definition.csv").open(encoding="cp1252",newline="") as h:
        for row in csv.reader(h,delimiter=";"):
            if row and row[0].isdigit(): c2i[tuple(map(int,row[1:4]))]=int(row[0])
    return c2i


def polygons(geometry):
    if geometry["type"]=="Polygon": return [geometry["coordinates"]]
    if geometry["type"]=="MultiPolygon": return geometry["coordinates"]
    raise ValueError(geometry["type"])


def fill(labels,allowed):
    q=deque((int(y),int(x)) for y,x in zip(*np.where(allowed&(labels>=0)),strict=True))
    while q:
        y,x=q.popleft()
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=y+dy,x+dx
            if 0<=ny<labels.shape[0] and 0<=nx<labels.shape[1] and allowed[ny,nx] and labels[ny,nx]<0:
                labels[ny,nx]=labels[y,x];q.append((ny,nx))


def absorb_flecks(labels,allowed,maximum=2):
    for label in range(len(PROVINCES)):
        m=allowed&(labels==label);seen=np.zeros(m.shape,bool)
        for sy,sx in zip(*np.where(m),strict=True):
            if seen[sy,sx]:continue
            stack=[(int(sy),int(sx))];seen[sy,sx]=1;comp=[]
            while stack:
                y,x=stack.pop();comp.append((y,x))
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny,nx=y+dy,x+dx
                    if 0<=ny<m.shape[0] and 0<=nx<m.shape[1] and m[ny,nx] and not seen[ny,nx]:seen[ny,nx]=1;stack.append((ny,nx))
            if len(comp)>maximum:continue
            near=[]
            for y,x in comp:
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny,nx=y+dy,x+dx
                    if 0<=ny<m.shape[0] and 0<=nx<m.shape[1] and allowed[ny,nx] and labels[ny,nx]>=0 and labels[ny,nx]!=label:near.append(int(labels[ny,nx]))
            if near:
                repl=max(set(near),key=near.count)
                for y,x in comp:labels[y,x]=repl


def snap(label_mask,seed):
    x,y=seed
    if label_mask[y,x]:return x,y
    yy,xx=np.where(label_mask);i=int(np.argmin((xx-x)**2+(yy-y)**2));return int(xx[i]),int(yy[i])


def main():
    c2i=definitions();original=np.array(Image.open(MOD/"map/provinces.bmp").convert("RGB"),dtype=np.uint8)
    height=np.array(Image.open(MOD/"map/heightmap.bmp").convert("L"),dtype=np.uint8)
    rivers=np.array(Image.open(MOD/"map/rivers.bmp"),dtype=np.uint8)
    lookup=np.full(1<<24,-1,np.int32)
    for c,pid in c2i.items():lookup[(c[0]<<16)|(c[1]<<8)|c[2]]=pid
    packed=(original[:,:,0].astype(np.int32)<<16)|(original[:,:,1].astype(np.int32)<<8)|original[:,:,2].astype(np.int32)
    ids=lookup[packed];outline=np.isin(ids,SOURCE_IDS)
    with urllib.request.urlopen(URL,timeout=30) as response:data=json.load(response)
    points=[]
    for feature in data["features"]:
        for poly in polygons(feature["geometry"]):points.extend((float(p[0]),float(p[1])) for p in poly[0])
    lon0,lon1=min(p[0] for p in points),max(p[0] for p in points);lat0,lat1=min(p[1] for p in points),max(p[1] for p in points)
    yy,xx=np.where(outline);xmin,xmax,ymin,ymax=int(xx.min()),int(xx.max()),int(yy.min()),int(yy.max())
    def project(point):
        lon,lat=float(point[0]),float(point[1]);return round(xmin+(lon-lon0)/(lon1-lon0)*(xmax-xmin)),round(ymin+(lat1-lat)/(lat1-lat0)*(ymax-ymin))
    raster=Image.new("I",(original.shape[1],original.shape[0]),color=-1);draw=ImageDraw.Draw(raster)
    for feature in data["features"]:
        props=feature["properties"];name=props["name"];parent=int(props["parent"]["adcode"]);target=COUNTY_TARGET.get(name,PARENT_TARGET[parent]);label=NAME_TO_INDEX[target]
        for poly in polygons(feature["geometry"]):
            exterior=[project(p) for p in poly[0]]
            if len(exterior)>=3:draw.polygon(exterior,fill=label)
    labels=np.asarray(raster,dtype=np.int16).copy();labels[~outline]=-1;fill(labels,outline);absorb_flecks(labels,outline)
    draft=original.copy()
    for i,(_a,_n,c,_s) in enumerate(PROVINCES):draft[labels==i]=c
    FULL_OUTPUT.parent.mkdir(parents=True,exist_ok=True);REVIEW_OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(draft).save(FULL_OUTPUT,format="BMP");Image.fromarray(draft).crop(CROP).save(CROP_OUTPUT,format="BMP")

    left,top,right,bottom=CROP;lc=labels[top:bottom,left:right];ic=ids[top:bottom,left:right];rc=rivers[top:bottom,left:right];hc=height[top:bottom,left:right]
    review=np.full((*lc.shape,3),(220,218,210),dtype=np.uint8)
    for area in AREA_COLOURS:
        indexes=[i for i,(a,_n,_c,_s) in enumerate(PROVINCES) if a==area]
        for j,index in enumerate(indexes):
            base=AREA_COLOURS[area];factor=.82+.09*(j%5);review[lc==index]=tuple(min(238,round(v*factor+8*(j//5))) for v in base)
    review[(rc!=255)&(lc>=0)]=(66,148,202)
    h=hc.astype(np.int16);ridge=np.zeros(h.shape,np.int16);ridge[1:]=np.maximum(ridge[1:],np.abs(h[1:]-h[:-1]));ridge[:,1:]=np.maximum(ridge[:,1:],np.abs(h[:,1:]-h[:,:-1]));review[(ridge>=13)&(lc>=0)&(rc==255)]=(143,103,68)
    scale=6;enlarged=np.repeat(np.repeat(review,scale,axis=0),scale,axis=1);el=np.repeat(np.repeat(lc,scale,axis=0),scale,axis=1);boundary=np.zeros(el.shape,bool);boundary[1:]|=(el[1:]>=0)&(el[:-1]>=0)&(el[1:]!=el[:-1]);boundary[:,1:]|=(el[:,1:]>=0)&(el[:,:-1]>=0)&(el[:,1:]!=el[:,:-1]);enlarged[boundary]=(248,246,238)
    canvas=Image.new("RGB",(1960,1120),(247,245,239));origin=(35,75);canvas.paste(Image.fromarray(enlarged),origin);draw=ImageDraw.Draw(canvas)
    draw.text((35,20),"云南二十六省 · 县级GeoJSON辅助草图",fill=(38,42,43),font=font(31,True));draw.text((760,29),"蓝色为河流 · 棕色为山脊",fill=(92,94,91),font=font(16))
    lf=font(14,True)
    for i,(_area,name,_colour,seed) in enumerate(PROVINCES):
        x,y=snap(labels==i,seed);px=origin[0]+(x-left)*scale;py=origin[1]+(y-top)*scale;box=draw.textbbox((px,py),name,font=lf,anchor="mm");box=(box[0]-3,box[1]-2,box[2]+3,box[3]+2);draw.rounded_rectangle(box,radius=3,fill=(253,251,245),outline=(58,62,63));draw.text((px,py),name,fill=(30,34,36),font=lf,anchor="mm")
    panel=1090;draw.rounded_rectangle((1070,75,1925,1080),radius=18,fill=(253,252,248),outline=(196,194,187),width=2);draw.text((panel,100),"六个区域",fill=(40,44,45),font=font(25,True));y=150
    for area in AREA_COLOURS:
        names=" · ".join(n for a,n,_c,_s in PROVINCES if a==area);draw.rounded_rectangle((panel,y,panel+25,y+25),radius=4,fill=AREA_COLOURS[area]);draw.text((panel+38,y-1),area,fill=(43,47,48),font=font(18,True));draw.text((panel+125,y+2),names,fill=(83,85,82),font=font(15));y+=58
    draw.line((panel,520,1895,520),fill=(207,203,194),width=2);draw.text((panel,545),"县级组合依据",fill=(43,47,48),font=font(21,True))
    notes=("• 德钦＋维西为德钦；香格里拉为独克宗","• 剑川、洱源、鹤庆构成剑川走廊","• 东川、禄劝、寻甸沿金沙江—乌蒙高地成省","• 宣威统合宣威、富源、会泽；镇雄统合乌蒙东缘","• 镇沅与镇雄分别位于普洱北部和昭通东部","• 红河按元江—红河谷南北两侧拆为蒙自、红河","• 景洪—勐海为版纳，勐腊单列南部边境省","• 仅输出草图，不覆盖正式 provinces.bmp")
    y=590
    for note in notes:draw.text((panel,y),note,fill=(71,73,70),font=font(15));y+=43
    canvas.save(REVIEW_OUTPUT)
    counts={n:int(np.count_nonzero(labels==i)) for i,(_a,n,_c,_s) in enumerate(PROVINCES)};print(FULL_OUTPUT);print(CROP_OUTPUT);print(REVIEW_OUTPUT);print(counts)


if __name__=="__main__":main()
