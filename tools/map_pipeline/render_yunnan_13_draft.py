#!/usr/bin/env python3
"""Render a non-canonical thirteen-province Yunnan draft from modern divisions."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import render_sichuan_37_draft as shared


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
FULL_OUTPUT = ROOT / "planning/yunnan_13_province_draft.bmp"
CROP_OUTPUT = ROOT / "planning/yunnan_13_province_crop.bmp"
REVIEW_OUTPUT = ROOT / "docs/map/previews/B18_yunnan_13_draft.png"
CROP = (4318, 900, 4470, 1070)
GEOJSON_URL = "https://geo.datav.aliyun.com/areas_v3/bound/530000_full.json"


@dataclass(frozen=True)
class Province:
    name: str
    seed: tuple[int, int]
    area: str
    modern_basis: str
    size_weight: float = 1.0


PROVINCES = (
    Province("昆明", (4410, 988), "滇中", "昆明＋玉溪", 1.15),
    Province("曲靖", (4431, 978), "滇中", "曲靖", 1.00),
    Province("昭通", (4430, 946), "滇中", "昭通", 0.82),
    Province("楚雄", (4392, 985), "滇中", "楚雄", 1.08),
    Province("大理", (4372, 982), "滇西", "大理", 1.00),
    Province("丽江", (4375, 945), "滇西", "丽江＋迪庆", 1.10),
    Province("怒江", (4348, 958), "滇西", "怒江", 0.80),
    Province("保山", (4354, 994), "滇西", "保山＋德宏", 1.12),
    Province("临沧", (4375, 1014), "滇南", "临沧", 0.94),
    Province("普洱", (4394, 1025), "滇南", "普洱", 1.12),
    Province("西双版纳", (4382, 1045), "滇南", "西双版纳", 0.78),
    Province("红河", (4418, 1020), "滇东", "红河", 1.05),
    Province("文山", (4440, 1010), "滇东", "文山", 1.04),
)

AREA_BASE = {
    "滇中": (219, 145, 57),
    "滇西": (119, 103, 180),
    "滇南": (61, 158, 126),
    "滇东": (64, 135, 183),
}

FEATURE_TARGET = {
    "昆明市": "昆明", "玉溪市": "昆明", "曲靖市": "曲靖", "昭通市": "昭通",
    "楚雄彝族自治州": "楚雄", "大理白族自治州": "大理",
    "丽江市": "丽江", "迪庆藏族自治州": "丽江",
    "怒江傈僳族自治州": "怒江", "保山市": "保山",
    "德宏傣族景颇族自治州": "保山", "临沧市": "临沧", "普洱市": "普洱",
    "西双版纳傣族自治州": "西双版纳", "红河哈尼族彝族自治州": "红河",
    "文山壮族苗族自治州": "文山",
}


def snap(mask: np.ndarray, seed: tuple[int, int]) -> tuple[int, int]:
    x, y = seed
    if mask[y, x]:
        return seed
    yy, xx = np.where(mask)
    index = np.argmin((xx - x) ** 2 + (yy - y) ** 2)
    return int(xx[index]), int(yy[index])


def geometry_polygons(geometry: dict[str, object]) -> list[list[list[float]]]:
    coordinates = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        return [coordinates]
    if geometry["type"] == "MultiPolygon":
        return coordinates
    raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def modern_partition(mask: np.ndarray) -> np.ndarray:
    with urllib.request.urlopen(GEOJSON_URL, timeout=30) as response:
        geojson = json.load(response)
    coordinates: list[tuple[float, float]] = []
    for feature in geojson["features"]:
        for rings in geometry_polygons(feature["geometry"]):
            coordinates.extend((float(point[0]), float(point[1])) for point in rings[0])
    longitude = [point[0] for point in coordinates]
    latitude = [point[1] for point in coordinates]
    lon_min, lon_max = min(longitude), max(longitude)
    lat_min, lat_max = min(latitude), max(latitude)
    yy, xx = np.where(mask)
    x_min, x_max = int(xx.min()), int(xx.max())
    y_min, y_max = int(yy.min()), int(yy.max())

    def project(point: list[float]) -> tuple[int, int]:
        lon, lat = float(point[0]), float(point[1])
        x = x_min + (lon - lon_min) / (lon_max - lon_min) * (x_max - x_min)
        y = y_min + (lat_max - lat) / (lat_max - lat_min) * (y_max - y_min)
        return round(x), round(y)

    raster = Image.new("I", (mask.shape[1], mask.shape[0]), color=-1)
    draw = ImageDraw.Draw(raster)
    name_to_index = {province.name: index for index, province in enumerate(PROVINCES)}
    for feature in geojson["features"]:
        feature_name = feature["properties"]["name"]
        target_name = FEATURE_TARGET[feature_name]
        label = name_to_index[target_name]
        for rings in geometry_polygons(feature["geometry"]):
            exterior = [project(point) for point in rings[0]]
            if len(exterior) >= 3:
                draw.polygon(exterior, fill=label)
    labels = np.asarray(raster, dtype=np.int16).copy()
    labels[~mask] = -1

    # Extend the projected polygons only into outline pixels left uncovered by
    # the difference between the modern boundary and EU4's existing Yunnan mask.
    frontier: list[tuple[int, int]] = [
        (int(x), int(y)) for y, x in zip(*np.where(mask & (labels >= 0)), strict=True)
    ]
    head = 0
    while head < len(frontier):
        x, y = frontier[head]
        head += 1
        for next_x, next_y in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (
                0 <= next_x < mask.shape[1]
                and 0 <= next_y < mask.shape[0]
                and mask[next_y, next_x]
                and labels[next_y, next_x] < 0
            ):
                labels[next_y, next_x] = labels[y, x]
                frontier.append((next_x, next_y))
    return labels


def main() -> None:
    colour_to_id, _id_to_colour = shared.definition()
    original = np.asarray(Image.open(MOD / "map/provinces.bmp").convert("RGB"))
    lookup = np.full(1 << 24, -1, dtype=np.int32)
    for colour, province_id in colour_to_id.items():
        lookup[(colour[0] << 16) | (colour[1] << 8) | colour[2]] = province_id
    packed = (
        original[:, :, 0].astype(np.int32) << 16
        | original[:, :, 1].astype(np.int32) << 8
        | original[:, :, 2].astype(np.int32)
    )
    id_map = lookup[packed]
    # Province 675 is currently named Liangshan in history, but its geometry is
    # the Wumeng/Zhaotong projection north of the modern Yunnan outline.
    yunnan_mask = np.isin(id_map, (660, 661, 662, 663, 675, 2165, 2166, 2167))
    labels = modern_partition(yunnan_mask)

    colours = shared.distinct_colours(len(PROVINCES), set(colour_to_id))
    draft = original.copy()
    for index, colour in enumerate(colours):
        draft[labels == index] = colour
    FULL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(draft).save(FULL_OUTPUT)
    Image.fromarray(draft).crop(CROP).save(CROP_OUTPUT)

    left, top, right, bottom = CROP
    label_crop = labels[top:bottom, left:right]
    id_crop = id_map[top:bottom, left:right]
    rivers = np.asarray(Image.open(MOD / "map/rivers.bmp"))[top:bottom, left:right]
    review = np.full((*label_crop.shape, 3), (218, 216, 207), dtype=np.uint8)
    water_ids = tuple(range(5032, 5045)) + (1655, 1896, 1897)
    review[np.isin(id_crop, water_ids)] = (87, 164, 205)
    for area in AREA_BASE:
        indexes = [index for index, province in enumerate(PROVINCES) if province.area == area]
        shades = shared.area_shades(AREA_BASE[area], len(indexes))
        for index, shade in zip(indexes, shades, strict=True):
            review[label_crop == index] = shade
    review[(rivers != 255) & (label_crop >= 0)] = (63, 142, 194)

    scale = 5
    enlarged = np.repeat(np.repeat(review, scale, axis=0), scale, axis=1)
    enlarged_labels = np.repeat(np.repeat(label_crop, scale, axis=0), scale, axis=1)
    boundary = np.zeros(enlarged_labels.shape, dtype=bool)
    boundary[1:] |= (
        (enlarged_labels[1:] >= 0)
        & (enlarged_labels[:-1] >= 0)
        & (enlarged_labels[1:] != enlarged_labels[:-1])
    )
    boundary[:, 1:] |= (
        (enlarged_labels[:, 1:] >= 0)
        & (enlarged_labels[:, :-1] >= 0)
        & (enlarged_labels[:, 1:] != enlarged_labels[:, :-1])
    )
    enlarged[boundary] = (247, 244, 235)
    map_image = Image.fromarray(enlarged)

    canvas = Image.new("RGB", (1510, 930), (246, 244, 237))
    origin = (35, 70)
    canvas.paste(map_image, origin)
    draw = ImageDraw.Draw(canvas)
    draw.text((35, 20), "云南十三省 · 现代州市真实边界草图", fill=(38, 43, 45), font=shared.font(30, True))
    draw.text((610, 27), "蓝线为现有河流参考", fill=(101, 104, 103), font=shared.font(16))

    label_font = shared.font(15, True)
    for index, province in enumerate(PROVINCES):
        seed_x, seed_y = snap(labels == index, province.seed)
        x = origin[0] + (seed_x - left) * scale
        y = origin[1] + (seed_y - top) * scale
        box = draw.textbbox((x, y), province.name, font=label_font, anchor="mm")
        box = (box[0] - 4, box[1] - 2, box[2] + 4, box[3] + 2)
        draw.rounded_rectangle(box, radius=4, fill=(255, 253, 246), outline=(52, 57, 59), width=1)
        draw.text((x, y), province.name, fill=(31, 35, 37), font=label_font, anchor="mm")

    legend_x = 830
    draw.rounded_rectangle((805, 70, 1475, 890), radius=18, fill=(255, 253, 247), outline=(208, 204, 193), width=2)
    draw.text((legend_x, 95), "十三省方案", fill=(40, 45, 47), font=shared.font(25, True))
    y = 142
    for area in AREA_BASE:
        draw.rounded_rectangle((legend_x, y, legend_x + 26, y + 26), radius=4, fill=AREA_BASE[area])
        draw.text((legend_x + 40, y + 13), area, fill=(38, 43, 45), font=shared.font(19, True), anchor="lm")
        names = " · ".join(province.name for province in PROVINCES if province.area == area)
        draw.text((legend_x + 105, y + 13), names, fill=(76, 78, 77), font=shared.font(15), anchor="lm")
        y += 56

    draw.line((legend_x, 375, 1445, 375), fill=(216, 211, 198), width=2)
    draw.text((legend_x, 403), "从现代十六州市合并为十三省", fill=(40, 45, 47), font=shared.font(22, True))
    merges = (
        "• 昆明：昆明市＋玉溪市",
        "• 丽江：丽江市＋迪庆州",
        "• 保山：保山市＋德宏州",
        "• 怒江、红河、文山、西双版纳仍独立",
    )
    y = 452
    for line in merges:
        draw.text((legend_x, y), line, fill=(64, 67, 66), font=shared.font(16))
        y += 39

    draw.line((legend_x, 626, 1445, 626), fill=(216, 211, 198), width=2)
    draw.text((legend_x, 654), "边界骨架", fill=(40, 45, 47), font=shared.font(22, True))
    notes = (
        "金沙江：昭通—丽江北缘与川滇边界",
        "怒江、澜沧江：滇西纵向省界",
        "哀牢山—红河谷：滇中与滇南分界",
        "南盘江：曲靖、昆明与红河方向的转折",
        "州市轮廓来自现代市级GeoJSON，并适配EU4云南外框",
        "本图仅为规划BMP，不修改正式 provinces.bmp",
    )
    y = 704
    for line in notes:
        draw.text((legend_x, y), "• " + line, fill=(64, 67, 66), font=shared.font(15))
        y += 34

    REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(REVIEW_OUTPUT)
    print(FULL_OUTPUT)
    print(CROP_OUTPUT)
    print(REVIEW_OUTPUT)


if __name__ == "__main__":
    main()
