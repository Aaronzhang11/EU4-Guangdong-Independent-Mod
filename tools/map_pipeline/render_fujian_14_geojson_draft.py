#!/usr/bin/env python3
"""Render a non-canonical 13-province Fujian GeoJSON planning draft."""

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
GEOJSON_URL = "https://geo.datav.aliyun.com/areas_v3/bound/350000_full_district.json"
FULL_OUTPUT = ROOT / "planning/fujian_13_province_draft.bmp"
CROP_OUTPUT = ROOT / "planning/fujian_13_province_crop.bmp"
REVIEW_OUTPUT = ROOT / "docs/map/previews/B19_fujian_13_geojson_draft.png"
CROP = (4595, 915, 4705, 1030)
FUJIAN_SOURCE_IDS = (669, 1829, 2152, 2153, 4952, 4953, 4957, 4958)
XIAMEN_ID = 4958


PROVINCES = (
    ("闽东", "闽侯", (230, 137, 66)),
    ("闽东", "福宁", (80, 156, 200)),
    ("闽东", "福清", (220, 184, 69)),
    ("闽东", "兴化", (77, 170, 118)),
    ("闽南", "泉州", (201, 92, 78)),
    ("闽南", "永春", (151, 103, 190)),
    ("闽南", "厦门", (135, 45, 225)),  # exact canonical RGB and pixels
    ("闽南", "漳州", (69, 157, 151)),
    ("闽西", "建宁", (105, 145, 76)),
    ("闽西", "邵武", (198, 137, 57)),
    ("闽西", "延平", (83, 111, 176)),
    ("闽西", "汀州", (176, 78, 103)),
    ("闽西", "龙岩", (113, 163, 157)),
)
NAME_TO_INDEX = {name: index for index, (_area, name, _colour) in enumerate(PROVINCES)}

PARENT_TARGET = {
    350100: "闽侯", 350300: "兴化", 350400: "延平", 350500: "泉州",
    350600: "漳州", 350700: "建宁", 350800: "龙岩", 350900: "福宁",
}
COUNTY_TARGET = {
    # Fuzhou's lower Min river and southern maritime approaches.
    "长乐区": "福清", "永泰县": "福清", "平潭县": "福清", "福清市": "福清",
    # Inland Quanzhou follows the Jin and Daiyun mountain corridors.
    "安溪县": "永春", "永春县": "永春", "德化县": "永春", "南安市": "永春",
    # Jiulong estuary and southern Zhangzhou coast.
    "云霄县": "漳州", "漳浦县": "漳州", "诏安县": "漳州", "东山县": "漳州",
    "平和县": "漳州", "龙海区": "漳州",
    # Northern Fujian historical prefectures and the Futun river basin.
    "光泽县": "邵武", "邵武市": "邵武", "泰宁县": "邵武", "建宁县": "邵武",
    "延平区": "延平", "建阳区": "延平", "顺昌县": "延平",
    "三元区": "延平", "大田县": "延平", "尤溪县": "延平", "沙县区": "延平",
    "将乐县": "延平", "永安市": "延平",
    "浦城县": "建宁", "松溪县": "建宁", "政和县": "建宁", "武夷山市": "建宁", "建瓯市": "建宁",
    # Tingzhou retains the upper Ting river; Longyan takes the Jiulong headwaters.
    "明溪县": "汀州", "清流县": "汀州", "宁化县": "汀州",
    "长汀县": "汀州", "武平县": "汀州", "连城县": "汀州",
    "新罗区": "龙岩", "永定区": "龙岩", "上杭县": "龙岩", "漳平市": "龙岩",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (Path("/System/Library/Fonts/PingFang.ttc"), Path("/System/Library/Fonts/STHeiti Medium.ttc"))
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size, index=1 if path.name == "PingFang.ttc" and bold else 0)
    return ImageFont.load_default()


def definitions() -> tuple[dict[tuple[int, int, int], int], dict[int, tuple[int, int, int]]]:
    colour_to_id, id_to_colour = {}, {}
    with (MOD / "map/definition.csv").open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                pid = int(row[0]); colour = tuple(map(int, row[1:4]))
                colour_to_id[colour] = pid; id_to_colour[pid] = colour
    return colour_to_id, id_to_colour


def polygons(geometry: dict) -> list:
    if geometry["type"] == "Polygon": return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon": return geometry["coordinates"]
    raise ValueError(geometry["type"])


def load_geojson() -> dict:
    with urllib.request.urlopen(GEOJSON_URL, timeout=30) as response:
        return json.load(response)


def fill_unassigned(labels: np.ndarray, mask: np.ndarray) -> None:
    queue = deque((int(y), int(x)) for y, x in zip(*np.where(mask & (labels >= 0)), strict=True))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and labels[ny, nx] < 0:
                labels[ny, nx] = labels[y, x]
                queue.append((ny, nx))


def absorb_flecks(labels: np.ndarray, mask: np.ndarray, maximum: int = 2) -> None:
    height, width = labels.shape
    for label in range(len(PROVINCES)):
        province_mask = mask & (labels == label)
        seen = np.zeros(mask.shape, dtype=bool)
        for sy, sx in zip(*np.where(province_mask), strict=True):
            if seen[sy, sx]: continue
            stack = [(int(sy), int(sx))]; seen[sy, sx] = True; component = []
            while stack:
                y, x = stack.pop(); component.append((y, x))
                for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny, nx = y+dy, x+dx
                    if 0 <= ny < height and 0 <= nx < width and province_mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx] = True; stack.append((ny,nx))
            if len(component) > maximum: continue
            neighbours = []
            for y, x in component:
                for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny, nx = y+dy, x+dx
                    if 0 <= ny < height and 0 <= nx < width and mask[ny,nx] and labels[ny,nx] >= 0 and labels[ny,nx] != label:
                        neighbours.append(int(labels[ny,nx]))
            if neighbours:
                replacement = max(set(neighbours), key=neighbours.count)
                for y, x in component: labels[y, x] = replacement


def main() -> None:
    colour_to_id, id_to_colour = definitions()
    original = np.array(Image.open(MOD / "map/provinces.bmp").convert("RGB"), dtype=np.uint8)
    heightmap = np.array(Image.open(MOD / "map/heightmap.bmp").convert("L"), dtype=np.uint8)
    rivers = np.array(Image.open(MOD / "map/rivers.bmp"), dtype=np.uint8)
    lookup = np.full(1 << 24, -1, dtype=np.int32)
    for colour, pid in colour_to_id.items(): lookup[(colour[0] << 16) | (colour[1] << 8) | colour[2]] = pid
    packed = (original[:,:,0].astype(np.int32) << 16) | (original[:,:,1].astype(np.int32) << 8) | original[:,:,2].astype(np.int32)
    id_map = lookup[packed]
    fujian_mask = np.isin(id_map, FUJIAN_SOURCE_IDS)
    xiamen_mask = id_map == XIAMEN_ID
    editable_mask = fujian_mask & ~xiamen_mask

    data = load_geojson()
    features = [f for f in data["features"] if int(f["properties"]["parent"]["adcode"]) != 350200]
    points = []
    for feature in data["features"]:
        for polygon in polygons(feature["geometry"]): points.extend((float(p[0]), float(p[1])) for p in polygon[0])
    lon_min, lon_max = min(p[0] for p in points), max(p[0] for p in points)
    lat_min, lat_max = min(p[1] for p in points), max(p[1] for p in points)
    ys, xs = np.where(fujian_mask)
    x_min, x_max, y_min, y_max = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())

    def project(point) -> tuple[int, int]:
        lon, lat = float(point[0]), float(point[1])
        x = x_min + (lon-lon_min)/(lon_max-lon_min)*(x_max-x_min)
        y = y_min + (lat_max-lat)/(lat_max-lat_min)*(y_max-y_min)
        return round(x), round(y)

    raster = Image.new("I", (original.shape[1], original.shape[0]), color=-1)
    draw = ImageDraw.Draw(raster)
    for feature in features:
        props = feature["properties"]; county = props["name"]; parent = int(props["parent"]["adcode"])
        target = COUNTY_TARGET.get(county, PARENT_TARGET[parent]); label = NAME_TO_INDEX[target]
        for polygon in polygons(feature["geometry"]):
            exterior = [project(point) for point in polygon[0]]
            if len(exterior) >= 3: draw.polygon(exterior, fill=label)
    labels = np.asarray(raster, dtype=np.int16).copy(); labels[~editable_mask] = -1
    fill_unassigned(labels, editable_mask); absorb_flecks(labels, editable_mask)
    labels[xiamen_mask] = NAME_TO_INDEX["厦门"]

    draft = original.copy()
    for index, (_area, _name, colour) in enumerate(PROVINCES): draft[fujian_mask & (labels == index)] = colour
    # Exact preservation guard for the hand-painted Xiamen province.
    draft[xiamen_mask] = original[xiamen_mask]
    if not np.array_equal(draft[xiamen_mask], original[xiamen_mask]): raise AssertionError("Xiamen geometry changed")
    FULL_OUTPUT.parent.mkdir(parents=True, exist_ok=True); REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(draft).save(FULL_OUTPUT, format="BMP")
    Image.fromarray(draft).crop(CROP).save(CROP_OUTPUT, format="BMP")

    left, top, right, bottom = CROP
    crop_labels = labels[top:bottom, left:right]
    crop_ids = id_map[top:bottom, left:right]
    crop_rivers = rivers[top:bottom, left:right]
    crop_height = heightmap[top:bottom, left:right]
    review = np.full((*crop_labels.shape, 3), (220, 218, 210), dtype=np.uint8)
    for index, (_area, _name, colour) in enumerate(PROVINCES): review[crop_labels == index] = colour
    review[(crop_rivers != 255) & (crop_labels >= 0)] = (70, 149, 202)
    h = crop_height.astype(np.int16); ridge = np.zeros(h.shape, dtype=np.int16)
    ridge[1:] = np.maximum(ridge[1:], np.abs(h[1:]-h[:-1])); ridge[:,1:] = np.maximum(ridge[:,1:], np.abs(h[:,1:]-h[:,:-1]))
    review[(ridge >= 13) & (crop_labels >= 0) & (crop_rivers == 255)] = (143, 103, 68)

    scale = 6
    enlarged = np.repeat(np.repeat(review, scale, axis=0), scale, axis=1)
    elabels = np.repeat(np.repeat(crop_labels, scale, axis=0), scale, axis=1)
    boundary = np.zeros(elabels.shape, dtype=bool)
    boundary[1:] |= (elabels[1:] >= 0) & (elabels[:-1] >= 0) & (elabels[1:] != elabels[:-1])
    boundary[:,1:] |= (elabels[:,1:] >= 0) & (elabels[:,:-1] >= 0) & (elabels[:,1:] != elabels[:,:-1])
    enlarged[boundary] = (248, 246, 238)
    map_image = Image.fromarray(enlarged)
    canvas = Image.new("RGB", (1500, 850), (247, 245, 239)); origin = (35, 100); canvas.paste(map_image, origin)
    draw = ImageDraw.Draw(canvas)
    draw.text((35, 27), "福建十三省 · 县级GeoJSON辅助草图", fill=(38,42,43), font=font(31, True))
    draw.text((700, 35), "蓝色为河流 · 棕色为山脊 · 厦门保持原像素与RGB", fill=(92,94,91), font=font(16))
    for index, (_area, name, _colour) in enumerate(PROVINCES):
        yy, xx = np.where(crop_labels == index)
        if len(xx) == 0: continue
        x, y = int(np.median(xx))*scale+origin[0], int(np.median(yy))*scale+origin[1]
        box = draw.textbbox((0,0), name, font=font(15, True)); w=box[2]-box[0]; htxt=box[3]-box[1]
        draw.rectangle((x-w//2-3,y-htxt//2-2,x+w//2+3,y+htxt//2+2),fill=(248,246,239),outline=(74,76,73))
        draw.text((x-w//2,y-htxt//2-1),name,fill=(33,38,40),font=font(15,True))

    panel_x = 735
    draw.rounded_rectangle((715,90,1470,815),radius=18,fill=(253,252,248),outline=(196,194,187),width=2)
    draw.text((panel_x,115),"三个区域",fill=(40,44,45),font=font(26,True))
    area_colours = {"闽东":(230,137,66),"闽南":(201,92,78),"闽西":(105,145,76)}
    y=165
    for area in ("闽东","闽南","闽西"):
        names=" · ".join(name for a,name,_c in PROVINCES if a==area)
        draw.rounded_rectangle((panel_x,y,panel_x+26,y+26),radius=4,fill=area_colours[area])
        draw.text((panel_x+40,y-1),area,fill=(44,48,48),font=font(20,True))
        draw.text((panel_x+112,y+2),names,fill=(90,91,88),font=font(16))
        y+=62
    draw.line((panel_x,365,1445,365),fill=(205,202,193),width=2)
    draw.text((panel_x,390),"规划原则",fill=(44,48,48),font=font(22,True))
    notes=(
        "• 福宁沿闽东北海岸与鹫峰山脉展开",
        "• 福清控制闽江口南岸、福清湾与平潭方向",
        "• 泉州—永春按沿海港区与戴云山腹地分开",
        "• 漳州统合九龙江流域与闽南沿海诸县",
        "• 建宁、邵武、延平依建溪—富屯溪水系划界",
        "• 汀州沿汀江上游；龙岩沿九龙江上游",
        "• 厦门沿用正式地图的29个手绘像素",
        "• 这是规划草图，不覆盖正式 provinces.bmp",
    )
    y=435
    for note in notes: draw.text((panel_x,y),note,fill=(72,73,71),font=font(16)); y+=39
    canvas.save(REVIEW_OUTPUT)
    counts={name:int(np.count_nonzero(labels==index)) for index,(_a,name,_c) in enumerate(PROVINCES)}
    print(FULL_OUTPUT); print(CROP_OUTPUT); print(REVIEW_OUTPUT); print(counts)


if __name__ == "__main__": main()
