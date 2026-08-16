#!/usr/bin/env python3
"""Render the GeoJSON-guided B46 v2 proposal without touching canonical files."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import csv
import json
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

import render_b46_proposal as v1


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = Path(__file__).resolve().parent
REVIEWED_BMP = OUT / "b46_reviewed_provinces.bmp"
SICHUAN_URL = "https://geo.datav.aliyun.com/areas_v3/bound/510000_full_district.json"
CHONGQING_URL = "https://geo.datav.aliyun.com/areas_v3/bound/500000_full.json"

BASIN_IDS = {
    679, 5075, 5076, 5077, 4212, 5078, 5079,
    5080, 5081, 2169, 5082, 4211,
    5083, 5084, 5085, 4213,
    680, 5026, 5027, 4987, 5028,
}
TARGET_PARENT_IDS = {5080, 5081, 2169, 5082, 4211, 680, 5026, 5027, 4987, 5028}


@dataclass(frozen=True)
class Cell:
    province_id: int
    name: str
    development: int
    polity: str
    area: str
    culture: str
    new: bool = False


CELLS = (
    Cell(5080, "绵州", 12, "蜀", "剑阆", "巴蜀"),
    Cell(5081, "剑州", 4, "苴", "剑阆", "巴蜀"),
    Cell(5329, "昭化", 4, "苴", "剑阆", "巴蜀", True),
    Cell(2169, "阆中", 7, "巴", "剑阆", "巴蜀"),
    Cell(5330, "蓬州", 4, "巴", "巴渠", "巴蜀", True),
    Cell(5331, "遂州", 4, "蜀", "剑阆", "巴蜀", True),
    Cell(5332, "巴州", 3, "宕渠", "巴渠", "巴蜀", True),
    Cell(5082, "顺庆", 5, "巴", "巴渠", "巴蜀"),
    Cell(4211, "达州", 3, "宕渠", "巴渠", "巴蜀"),
    Cell(5333, "渠州", 3, "宕渠", "巴渠", "巴蜀", True),
    Cell(5026, "合州", 5, "巴", "巴渝", "巴蜀"),
    Cell(5334, "昌州", 4, "巴", "巴渝", "巴蜀", True),
    Cell(680, "重庆", 11, "巴", "巴渝", "巴蜀"),
    Cell(5335, "江津", 6, "巴", "巴渝", "巴蜀", True),
    Cell(5027, "涪州", 4, "枳", "涪陵", "苗"),
    Cell(5336, "南川", 3, "枳", "涪陵", "苗", True),
    Cell(5337, "彭水", 3, "枳", "涪陵", "苗", True),
    Cell(4987, "万州", 5, "宕渠", "峡江", "巴蜀"),
    Cell(5338, "忠州", 4, "枳", "涪陵", "巴蜀", True),
    Cell(5339, "开州", 3, "宕渠", "峡江", "巴蜀", True),
    Cell(5028, "夔州", 6, "巴氐", "峡江", "氐羌"),
    Cell(5340, "石砫", 3, "枳", "涪陵", "苗", True),
)
CELL_BY_NAME = {cell.name: cell for cell in CELLS}
CELL_BY_ID = {cell.province_id: cell for cell in CELLS}
PERMANENT_RGB = {
    5329: (184, 165, 77), 5330: (155, 76, 224), 5331: (48, 184, 80),
    5332: (224, 94, 101), 5333: (62, 104, 184), 5334: (164, 224, 58),
    5335: (184, 77, 176), 5336: (76, 224, 192), 5337: (184, 114, 48),
    5338: (120, 94, 224), 5339: (74, 184, 62), 5340: (224, 58, 123),
}

POLITY_COLORS = {
    "蜀": (220, 145, 42), "苴": (173, 120, 52), "巴": (45, 126, 178),
    "宕渠": (59, 145, 105), "枳": (154, 84, 148), "巴氐": (125, 84, 70),
}
AREA_COLORS = {
    "剑阆": (218, 156, 61), "巴渠": (86, 154, 113), "巴渝": (64, 127, 183),
    "涪陵": (158, 92, 155), "峡江": (90, 102, 168),
}

SICHUAN_CITY_DEFAULT = {
    510600: "绵州", 510700: "绵州", 510800: "昭化",
    510900: "遂州", 511300: "顺庆", 511600: "渠州",
    511700: "达州", 511900: "巴州",
}
SICHUAN_COUNTY_TARGET = {
    "剑阁县": "剑州", "苍溪县": "剑州",
    "阆中市": "阆中", "南部县": "阆中", "仪陇县": "阆中",
    "蓬安县": "蓬州", "营山县": "蓬州",
    "大竹县": "渠州", "渠县": "渠州",
}
CHONGQING_TARGET = {
    "渝中区": "重庆", "大渡口区": "重庆", "江北区": "重庆", "沙坪坝区": "重庆",
    "九龙坡区": "重庆", "南岸区": "重庆", "北碚区": "重庆", "渝北区": "重庆",
    "巴南区": "重庆",
    "江津区": "江津", "綦江区": "江津", "永川区": "江津",
    "璧山区": "昌州", "荣昌区": "昌州", "大足区": "昌州", "铜梁区": "昌州", "潼南区": "昌州",
    "合川区": "合州",
    "涪陵区": "涪州", "长寿区": "涪州",
    "南川区": "南川", "武隆区": "南川",
    "黔江区": "彭水", "秀山土家族苗族自治县": "彭水", "酉阳土家族苗族自治县": "彭水",
    "彭水苗族土家族自治县": "彭水",
    "万州区": "万州", "梁平区": "万州", "垫江县": "万州",
    "开州区": "开州", "城口县": "开州",
    "忠县": "忠州", "丰都县": "忠州",
    "云阳县": "夔州", "奉节县": "夔州", "巫山县": "夔州", "巫溪县": "夔州",
    "石柱土家族自治县": "石砫",
}


def definitions() -> dict[int, tuple[int, int, int]]:
    result: dict[int, tuple[int, int, int]] = {}
    with (MAP / "definition.csv").open(encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if len(row) >= 4 and row[0].isdigit():
                result[int(row[0])] = tuple(map(int, row[1:4]))
    return result


def geometry_polygons(geometry: dict[str, object]) -> list[list[list[list[float]]]]:
    coordinates = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        return [coordinates]
    if geometry["type"] == "MultiPolygon":
        return coordinates
    raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def fetch_features() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    with urllib.request.urlopen(SICHUAN_URL, timeout=30) as response:
        sichuan = json.load(response)["features"]
    with urllib.request.urlopen(CHONGQING_URL, timeout=30) as response:
        chongqing = json.load(response)["features"]
    return sichuan, chongqing


def province_mask(values: np.ndarray, rgb: tuple[int, int, int]) -> np.ndarray:
    return np.all(values == np.asarray(rgb, dtype=np.uint8), axis=2)


def build_geojson_cells() -> tuple[dict[int, np.ndarray], tuple[int, int, int, int], np.ndarray]:
    id_to_rgb = definitions()
    values = np.array(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    basin_mask = np.zeros(values.shape[:2], dtype=bool)
    target_mask = np.zeros(values.shape[:2], dtype=bool)
    for province_id in BASIN_IDS:
        basin_mask |= province_mask(values, id_to_rgb[province_id])
    for province_id in TARGET_PARENT_IDS:
        target_mask |= province_mask(values, id_to_rgb[province_id])

    sichuan, chongqing = fetch_features()
    selected_sichuan: list[dict[str, object]] = []
    for feature in sichuan:
        properties = feature["properties"]
        parent = properties.get("parent") or {}
        parent_code = int(parent.get("adcode", 0))
        if parent_code in {
            510100, 511400, 511100, 511800, 510600, 510700, 510800, 510900,
            511300, 511600, 511700, 511900, 512000, 511000, 510300, 511500, 510500,
        }:
            selected_sichuan.append(feature)

    all_features = selected_sichuan + chongqing
    points: list[tuple[float, float]] = []
    for feature in all_features:
        for polygon in geometry_polygons(feature["geometry"]):
            points.extend((float(point[0]), float(point[1])) for point in polygon[0])
    lon_min = min(point[0] for point in points)
    lon_max = max(point[0] for point in points)
    lat_min = min(point[1] for point in points)
    lat_max = max(point[1] for point in points)
    ys, xs = np.where(basin_mask)
    x_min, x_max = int(xs.min()), int(xs.max())
    y_min, y_max = int(ys.min()), int(ys.max())

    def project(point: list[float]) -> tuple[int, int]:
        lon, lat = float(point[0]), float(point[1])
        x = x_min + (lon - lon_min) / (lon_max - lon_min) * (x_max - x_min)
        y = y_min + (lat_max - lat) / (lat_max - lat_min) * (y_max - y_min)
        return round(x), round(y)

    labels = Image.new("I", (values.shape[1], values.shape[0]), color=0)
    draw = ImageDraw.Draw(labels)
    for feature in selected_sichuan:
        properties = feature["properties"]
        county = properties["name"]
        parent_code = int(properties["parent"]["adcode"])
        target = SICHUAN_COUNTY_TARGET.get(county, SICHUAN_CITY_DEFAULT.get(parent_code))
        if target is None:
            continue
        target_id = CELL_BY_NAME[target].province_id
        for polygon in geometry_polygons(feature["geometry"]):
            exterior = [project(point) for point in polygon[0]]
            if len(exterior) >= 3:
                draw.polygon(exterior, fill=target_id)
    for feature in chongqing:
        county = feature["properties"]["name"]
        target = CHONGQING_TARGET.get(county)
        if target is None:
            continue
        target_id = CELL_BY_NAME[target].province_id
        for polygon in geometry_polygons(feature["geometry"]):
            exterior = [project(point) for point in polygon[0]]
            if len(exterior) >= 3:
                draw.polygon(exterior, fill=target_id)

    label_values = np.asarray(labels, dtype=np.int32).copy()
    label_values[~target_mask] = 0
    frontier = deque((int(x), int(y)) for y, x in zip(*np.where(target_mask & (label_values > 0)), strict=True))
    while frontier:
        x, y = frontier.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < values.shape[1] and 0 <= ny < values.shape[0] and target_mask[ny, nx] and label_values[ny, nx] == 0:
                label_values[ny, nx] = label_values[y, x]
                frontier.append((nx, ny))

    # Keep the largest component of each proposed province, then let surviving
    # neighbours absorb rare raster crumbs.  This produces exact four-way cells.
    masks: dict[int, np.ndarray] = {}
    for cell in CELLS:
        raw = label_values == cell.province_id
        if not raw.any():
            raise RuntimeError(f"GeoJSON produced no pixels for {cell.name}")
        masks[cell.province_id] = v1.largest_component(raw)
    assigned = np.zeros(target_mask.shape, dtype=bool)
    for mask in masks.values():
        assigned |= mask
    leftovers = target_mask & ~assigned
    while leftovers.any():
        progress = False
        for province_id, mask in masks.items():
            adjacent = np.zeros(mask.shape, dtype=bool)
            adjacent[1:] |= mask[:-1]
            adjacent[:-1] |= mask[1:]
            adjacent[:, 1:] |= mask[:, :-1]
            adjacent[:, :-1] |= mask[:, 1:]
            take = leftovers & adjacent
            if take.any():
                masks[province_id] |= take
                leftovers &= ~take
                progress = True
        if not progress:
            raise RuntimeError("Unable to absorb GeoJSON raster crumbs")

    ys, xs = np.where(target_mask)
    box = (int(xs.min()) - 5, int(ys.min()) - 5, int(xs.max()) + 6, int(ys.max()) + 6)
    return masks, box, target_mask


def label_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    cx, cy = float(xs.mean()), float(ys.mean())
    index = np.argmin((xs - cx) ** 2 + (ys - cy) ** 2)
    return int(xs[index]), int(ys[index])


def render_panel(masks: dict[int, np.ndarray], box: tuple[int, int, int, int], mode: str) -> Image.Image:
    left, top, right, bottom = box
    scale = 8
    heightmap = np.array(Image.open(MAP / "heightmap.bmp").convert("L"), dtype=np.float32)
    rivers = np.array(Image.open(MAP / "rivers.bmp").convert("L"), dtype=np.uint8)
    crop_shape = (bottom - top, right - left)
    canvas = np.full((*crop_shape, 3), (225, 222, 212), dtype=np.float32)
    palette = POLITY_COLORS if mode == "polity" else AREA_COLORS
    for province_id, full_mask in masks.items():
        mask = full_mask[top:bottom, left:right]
        cell = CELL_BY_ID[province_id]
        key = cell.polity if mode == "polity" else cell.area
        base = np.asarray(palette[key], dtype=np.float32)
        relief = (heightmap[top:bottom, left:right] - 110.0) / 255.0
        shade = np.clip(1.0 + relief * 0.34, 0.78, 1.14)
        colored = np.clip(base[None, None, :] * shade[:, :, None], 0, 255)
        canvas[mask] = colored[mask]
    for full_mask in masks.values():
        local = full_mask[top:bottom, left:right]
        canvas[v1.border(local)] = (251, 247, 237)
    union = np.zeros(crop_shape, dtype=bool)
    for full_mask in masks.values():
        union |= full_mask[top:bottom, left:right]
    river_mask = (rivers[top:bottom, left:right] != 255) & union
    canvas[river_mask] = (70, 171, 210)
    image = Image.fromarray(canvas.astype(np.uint8)).resize(
        (crop_shape[1] * scale, crop_shape[0] * scale), Image.Resampling.NEAREST
    )
    draw = ImageDraw.Draw(image)
    occupied: list[tuple[int, int, int, int]] = []
    name_font = v1.font(16, True)
    for province_id, full_mask in sorted(masks.items()):
        local = full_mask[top:bottom, left:right]
        x, y = label_point(local)
        anchor = (x * scale, y * scale)
        cell = CELL_BY_ID[province_id]
        text = ("★" if cell.new else "") + cell.name
        bbox = draw.textbbox((0, 0), text, font=name_font)
        width, height = bbox[2] + 8, bbox[3] + 6
        offsets = ((0, 0), (0, -24), (22, 0), (-22, 0), (0, 24), (28, -22), (-28, -22), (28, 22), (-28, 22))
        chosen = None
        for dx, dy in offsets:
            candidate = (anchor[0] + dx - width // 2, anchor[1] + dy - height // 2,
                         anchor[0] + dx + width // 2, anchor[1] + dy + height // 2)
            if not any(not (candidate[2] < old[0] or candidate[0] > old[2] or candidate[3] < old[1] or candidate[1] > old[3]) for old in occupied):
                chosen = candidate
                break
        if chosen is None:
            chosen = candidate
        occupied.append(chosen)
        center = ((chosen[0] + chosen[2]) // 2, (chosen[1] + chosen[3]) // 2)
        if abs(center[0] - anchor[0]) + abs(center[1] - anchor[1]) > 12:
            draw.line((anchor, center), fill=(55, 55, 55), width=1)
        draw.rounded_rectangle(chosen, radius=4, fill=(250, 247, 238), outline=(45, 45, 45))
        draw.text((chosen[0] + 4, chosen[1] + 2), text, font=name_font, fill=(25, 25, 25))
    return image


def compose(panel: Image.Image, mode: str, filename: str) -> None:
    palette = POLITY_COLORS if mode == "polity" else AREA_COLORS
    title = "川东北—重庆二次细化 · GeoJSON国家图" if mode == "polity" else "川东北—重庆二次细化 · GeoJSON区域图"
    subtitle = "县级GeoJSON定边，叠加高度与河流纹理；当前10省 → 方案22省；★为新增省"
    margin, legend_width = 34, 420
    canvas = Image.new("RGB", (panel.width + legend_width + margin * 3, panel.height + 150), (247, 244, 236))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 18), title, font=v1.font(30, True), fill=(35, 35, 35))
    draw.text((margin, 60), subtitle, font=v1.font(16), fill=(85, 85, 85))
    canvas.paste(panel, (margin, 105))
    x = margin * 2 + panel.width
    draw.rounded_rectangle((x, 105, x + legend_width, panel.height + 105), radius=14, fill=(252, 250, 245), outline=(190, 184, 170))
    draw.text((x + 24, 126), "国家与文化" if mode == "polity" else "Area 与发展度", font=v1.font(23, True), fill=(40, 40, 40))
    y = 172
    for key, color in palette.items():
        cells = [cell for cell in CELLS if (cell.polity if mode == "polity" else cell.area) == key]
        dev = sum(cell.development for cell in cells)
        draw.rounded_rectangle((x + 24, y, x + 48, y + 24), radius=4, fill=color)
        draw.text((x + 60, y - 2), f"{key} · {dev}发展", font=v1.font(17, True), fill=(40, 40, 40))
        y += 29
        members = "、".join(cell.name for cell in cells)
        draw.text((x + 60, y), members, font=v1.font(13), fill=(80, 80, 80))
        y += 42 if len(members) < 17 else 58
        if mode == "polity":
            cultures = " / ".join(dict.fromkeys(cell.culture for cell in cells))
            draw.text((x + 60, y - 16), f"文化：{cultures}", font=v1.font(12), fill=(104, 91, 76))
    note_y = panel.height + 105 - 135
    draw.line((x + 24, note_y, x + legend_width - 24, note_y), fill=(205, 200, 188))
    notes = (
        "县界来源：阿里云 DataV 行政区 GeoJSON",
        "外框锁定当前川北＋巴东10省，不侵入邻区",
        "区域总发展度106不变；巴在本区降至42发展",
        "参考三款模组的密度与山河语言，不复制像素",
    )
    for index, note in enumerate(notes):
        draw.text((x + 24, note_y + 15 + index * 25), "• " + note, font=v1.font(13), fill=(70, 70, 70))
    canvas.save(OUT / filename)


def write_reviewed_bmp(masks: dict[int, np.ndarray]) -> None:
    values = np.array(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    id_to_rgb = definitions()
    for province_id, mask in masks.items():
        colour = PERMANENT_RGB[province_id] if province_id in PERMANENT_RGB else id_to_rgb[province_id]
        values[mask] = colour
    Image.fromarray(values, mode="RGB").save(REVIEWED_BMP, format="BMP")


def main() -> None:
    masks, box, target_mask = build_geojson_cells()
    for province_id, mask in masks.items():
        count = v1.component_count(mask)
        if count != 1:
            raise RuntimeError(f"{CELL_BY_ID[province_id].name} has {count} components")
    area_components = v1.audit_groups(masks, "area") if False else None
    # v1's audit helper is tied to the v1 Cell table; build the v2 unions here.
    for attribute in ("area", "polity"):
        groups: dict[str, np.ndarray] = {}
        for province_id, mask in masks.items():
            key = getattr(CELL_BY_ID[province_id], attribute)
            groups.setdefault(key, np.zeros(target_mask.shape, dtype=bool))
            groups[key] |= mask
        counts = {key: v1.component_count(mask) for key, mask in groups.items()}
        if set(counts.values()) != {1}:
            raise RuntimeError(f"Disconnected {attribute}: {counts}")
        print(attribute, counts)
    if sum(cell.development for cell in CELLS) != 106:
        raise RuntimeError("Development total drifted")
    write_reviewed_bmp(masks)
    compose(render_panel(masks, box, "polity"), "polity", "b46_geojson_country_preview.png")
    compose(render_panel(masks, box, "area"), "area", "b46_geojson_area_preview.png")
    print("province_pixels", {CELL_BY_ID[pid].name: int(mask.sum()) for pid, mask in masks.items()})
    print("development", sum(cell.development for cell in CELLS))


if __name__ == "__main__":
    main()
