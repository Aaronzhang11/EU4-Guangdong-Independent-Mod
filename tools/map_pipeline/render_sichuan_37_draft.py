#!/usr/bin/env python3
"""Create a non-canonical 36-province Sichuan planning BMP and review plate."""

from __future__ import annotations

import colorsys
import csv
import heapq
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
FULL_OUTPUT = ROOT / "planning/sichuan_36_province_draft.bmp"
CROP_OUTPUT = ROOT / "planning/sichuan_36_province_crop.bmp"
REVIEW_OUTPUT = ROOT / "docs/map/previews/B17_sichuan_36_draft.png"
CROP = (4295, 805, 4540, 985)


@dataclass(frozen=True)
class DraftProvince:
    name: str
    seed: tuple[int, int]
    goods: str
    development: str
    note: str = ""


GROUPS: dict[str, dict[str, object]] = {
    "成都": {
        "source": (679, 4212),
        "provinces": (
            DraftProvince("成都", (4449, 888), "丝绸", "10/11/4", "二级商埠"),
            DraftProvince("灌州", (4428, 881), "谷物", "4/4/2"),
            DraftProvince("邛州", (4417, 899), "茶叶", "4/4/2"),
            DraftProvince("眉州", (4438, 902), "布匹", "5/5/2"),
        ),
    },
    "嘉雅": {
        "source": (679, 4212),
        "provinces": (
            DraftProvince("嘉州", (4446, 916), "茶叶", "5/5/2"),
            DraftProvince("雅州", (4427, 916), "茶叶", "4/5/2"),
            DraftProvince("黎州", (4409, 913), "牲畜", "2/2/2"),
        ),
    },
    "川北": {
        "source": (2169, 4211),
        "provinces": (
            DraftProvince("绵州", (4447, 875), "布匹", "5/5/2"),
            DraftProvince("剑州", (4451, 858), "铁矿", "3/3/2", "要塞"),
            DraftProvince("阆中", (4467, 869), "谷物", "4/4/2"),
            DraftProvince("顺庆", (4475, 886), "谷物", "4/5/2"),
            DraftProvince("达州", (4498, 875), "牲畜", "3/3/2"),
        ),
    },
    "川南": {
        "source": (4213,),
        "provinces": (
            DraftProvince("资州", (4455, 912), "盐", "4/5/2"),
            DraftProvince("富顺", (4448, 919), "盐", "3/6/2"),
            DraftProvince("叙州", (4437, 929), "谷物", "4/4/2"),
            DraftProvince("泸州", (4454, 929), "谷物", "4/4/2"),
        ),
    },
    "巴东": {
        "source": (680, 5026, 5027, 4987, 5028),
        "fixed": (680, 5026, 5027, 4987, 5028),
        "provinces": (
            DraftProvince("重庆", (4462, 911), "布匹", "8/9/3", "二级商埠"),
            DraftProvince("合州", (4474, 900), "谷物", "4/4/2"),
            DraftProvince("涪州", (4491, 921), "纸张", "4/4/2"),
            DraftProvince("万州", (4497, 896), "茶叶", "3/4/2"),
            DraftProvince("夔州", (4515, 883), "船具", "3/3/2", "要塞"),
        ),
    },
    "松茂": {
        "source": (2170,),
        "provinces": (
            DraftProvince("松州", (4428, 847), "牲畜", "3/3/3", "一级商埠、要塞"),
            DraftProvince("茂州", (4434, 863), "牲畜", "2/2/2"),
            DraftProvince("汶川", (4428, 873), "羊毛", "2/2/2"),
            DraftProvince("南坪", (4434, 834), "牲畜", "2/2/2", "九寨沟；邓至国"),
        ),
    },
    "阿坝": {
        "source": (2170,),
        "provinces": (
            DraftProvince("马尔康", (4406, 860), "茶叶", "2/3/2"),
            DraftProvince("金川", (4407, 872), "铜矿", "2/2/2"),
            DraftProvince("阿坝", (4404, 842), "羊毛", "2/2/3"),
            DraftProvince("若尔盖", (4418, 836), "牲畜", "1/2/3"),
        ),
    },
    "甘孜": {
        "source": (678, 2133, 2135),
        "include_markam_east": True,
        "provinces": (
            DraftProvince("康定", (4393, 906), "茶叶", "3/4/2", "打箭炉；一级商埠、自由市候选"),
            DraftProvince("德格", (4367, 861), "纸张", "3/4/2", "包含甘孜地块"),
            DraftProvince("壤塘", (4386, 850), "羊毛", "1/2/2"),
            DraftProvince("理塘", (4368, 917), "牲畜", "2/3/2", "包含巴塘"),
        ),
    },
    "凉山": {
        "source": (675, 2748),
        "provinces": (
            DraftProvince("嶲州", (4420, 943), "谷物", "4/4/3", "越西＋西昌；要塞"),
            DraftProvince("会理", (4438, 960), "铜矿", "3/4/2", "会理＋雷波"),
            DraftProvince("盐源", (4397, 958), "盐", "2/2/2"),
        ),
    },
}

MACROS = (
    (("成都", "嘉雅", "川北", "川南", "巴东"), (679, 4212, 2169, 4211, 4213, 680, 5026, 5027, 4987, 5028), False),
    (("松茂", "阿坝", "甘孜", "凉山"), (2170, 678, 2133, 2135, 2748), False),
)

AREA_BASE = {
    "成都": (222, 153, 62), "嘉雅": (204, 113, 61), "川北": (104, 160, 92),
    "川南": (67, 155, 135), "巴东": (60, 126, 168), "松茂": (112, 151, 201),
    "阿坝": (122, 102, 180), "甘孜": (153, 94, 171), "凉山": (190, 92, 119),
}

WESTERN_AREAS = ("松茂", "阿坝", "甘孜", "凉山")
BASIN_AREAS = ("成都", "嘉雅", "川北", "川南", "巴东")
BASIN_GEOJSON = (
    "https://geo.datav.aliyun.com/areas_v3/bound/510000_full_district.json",
    "https://geo.datav.aliyun.com/areas_v3/bound/500000_full.json",
)
WESTERN_GEOJSON = (
    "https://geo.datav.aliyun.com/areas_v3/bound/513200_full.json",
    "https://geo.datav.aliyun.com/areas_v3/bound/513300_full.json",
    "https://geo.datav.aliyun.com/areas_v3/bound/513400_full.json",
)
COUNTY_TARGET = {
    "马尔康市": "马尔康", "黑水县": "马尔康",
    "金川县": "金川", "小金县": "金川",
    "阿坝县": "阿坝", "红原县": "阿坝", "若尔盖县": "若尔盖",
    "松潘县": "松州", "九寨沟县": "南坪", "茂县": "茂州",
    "汶川县": "汶川", "理县": "汶川", "壤塘县": "壤塘",
    "康定市": "康定", "泸定县": "康定", "丹巴县": "康定",
    "九龙县": "康定", "道孚县": "康定",
    "炉霍县": "德格", "甘孜县": "德格", "德格县": "德格",
    "白玉县": "德格", "石渠县": "德格", "色达县": "德格",
    "雅江县": "理塘", "新龙县": "理塘", "理塘县": "理塘",
    "巴塘县": "理塘", "乡城县": "理塘", "稻城县": "理塘", "得荣县": "理塘",
    "西昌市": "嶲州", "德昌县": "嶲州", "昭觉县": "嶲州",
    "喜德县": "嶲州", "冕宁县": "嶲州", "越西县": "嶲州",
    "甘洛县": "嶲州", "美姑县": "嶲州",
    "会理市": "会理", "会东县": "会理", "宁南县": "会理",
    "普格县": "会理", "布拖县": "会理", "金阳县": "会理", "雷波县": "会理",
    "盐源县": "盐源", "木里藏族自治县": "盐源",
}

SICHUAN_PARENT_TARGET = {
    510100: "成都", 511400: "眉州", 511100: "嘉州", 511800: "雅州",
    510600: "绵州", 510700: "绵州", 510800: "剑州", 510900: "顺庆",
    511300: "顺庆", 511600: "顺庆", 511700: "达州", 511900: "达州",
    512000: "资州", 511000: "资州", 510300: "富顺", 511500: "叙州", 510500: "泸州",
}
SICHUAN_COUNTY_TARGET = {
    "都江堰市": "灌州", "彭州市": "灌州",
    "邛崃市": "邛州", "大邑县": "邛州", "蒲江县": "邛州",
    "汉源县": "黎州", "石棉县": "黎州",
    "阆中市": "阆中", "南部县": "阆中", "仪陇县": "阆中",
}
CHONGQING_TARGET = {
    "渝中区": "重庆", "大渡口区": "重庆", "江北区": "重庆", "沙坪坝区": "重庆",
    "九龙坡区": "重庆", "南岸区": "重庆", "北碚区": "重庆", "渝北区": "重庆",
    "巴南区": "重庆", "綦江区": "重庆", "江津区": "重庆", "永川区": "重庆",
    "璧山区": "重庆", "荣昌区": "重庆",
    "合川区": "合州", "大足区": "合州", "铜梁区": "合州", "潼南区": "合州",
    "涪陵区": "涪州", "长寿区": "涪州", "南川区": "涪州", "武隆区": "涪州",
    "黔江区": "涪州", "秀山土家族苗族自治县": "涪州",
    "酉阳土家族苗族自治县": "涪州", "彭水苗族土家族自治县": "涪州",
    "万州区": "万州", "开州区": "万州", "梁平区": "万州", "城口县": "万州",
    "垫江县": "万州", "忠县": "万州",
    "云阳县": "夔州", "奉节县": "夔州", "巫山县": "夔州", "巫溪县": "夔州",
    "丰都县": "夔州", "石柱土家族自治县": "夔州",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc") if bold
        else Path("/System/Library/Fonts/STHeiti Light.ttc"),
    )
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size, index=1 if path.name == "PingFang.ttc" and bold else 0)
    return ImageFont.load_default()


def definition() -> tuple[dict[tuple[int, int, int], int], dict[int, tuple[int, int, int]]]:
    colour_to_id: dict[tuple[int, int, int], int] = {}
    id_to_colour: dict[int, tuple[int, int, int]] = {}
    with (MOD / "map/definition.csv").open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                province_id = int(row[0])
                colour = tuple(int(value) for value in row[1:4])
                colour_to_id[colour] = province_id
                id_to_colour[province_id] = colour
    return colour_to_id, id_to_colour


def snap_seed(mask: np.ndarray, seed: tuple[int, int]) -> tuple[int, int]:
    x, y = seed
    if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] and mask[y, x]:
        return x, y
    yy, xx = np.where(mask)
    index = np.argmin((xx - x) ** 2 + (yy - y) ** 2)
    return int(xx[index]), int(yy[index])


def watershed(
    mask: np.ndarray,
    seeds: tuple[tuple[int, int], ...],
    height: np.ndarray,
    rivers: np.ndarray,
) -> np.ndarray:
    labels = np.full(mask.shape, -1, dtype=np.int16)
    distance = np.full(mask.shape, np.inf, dtype=np.float64)
    queue: list[tuple[float, int, int, int]] = []
    for label, seed in enumerate(seeds):
        x, y = snap_seed(mask, seed)
        labels[y, x] = label
        distance[y, x] = 0
        heapq.heappush(queue, (0.0, label, x, y))

    height_limit, width_limit = mask.shape
    while queue:
        current, label, x, y = heapq.heappop(queue)
        if current != distance[y, x] or labels[y, x] != label:
            continue
        for delta_x, delta_y in (
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ):
            next_x, next_y = x + delta_x, y + delta_y
            if not (0 <= next_x < width_limit and 0 <= next_y < height_limit and mask[next_y, next_x]):
                continue
            diagonal = 1.41421356237 if delta_x and delta_y else 1.0
            ridge = abs(int(height[next_y, next_x]) - int(height[y, x])) / 11.0
            river_barrier = 5.5 if rivers[next_y, next_x] != 255 or rivers[y, x] != 255 else 0.0
            smooth_warp = (
                np.sin(next_x * 0.31 + label * 0.73)
                + np.sin(next_y * 0.27 - label * 0.49)
                + np.sin((next_x + next_y) * 0.13 + label)
            ) * 0.13
            candidate = current + diagonal + ridge + river_barrier + smooth_warp
            if candidate < distance[next_y, next_x]:
                distance[next_y, next_x] = candidate
                labels[next_y, next_x] = label
                heapq.heappush(queue, (candidate, label, next_x, next_y))
    return labels


def balanced_warped_voronoi(
    mask: np.ndarray,
    seeds: tuple[tuple[int, int], ...],
) -> np.ndarray:
    """Make compact, similarly sized cells while retaining gently curved borders."""
    yy, xx = np.where(mask)
    warped_x = xx + 2.8 * np.sin(yy * 0.29) + 1.4 * np.sin((xx + yy) * 0.16)
    warped_y = yy + 2.2 * np.sin(xx * 0.25) + 1.2 * np.sin((xx - yy) * 0.18)
    seed_x = np.asarray([seed[0] for seed in seeds], dtype=np.float64)
    seed_y = np.asarray([seed[1] for seed in seeds], dtype=np.float64)
    warped_seed_x = seed_x + 2.8 * np.sin(seed_y * 0.29) + 1.4 * np.sin((seed_x + seed_y) * 0.16)
    warped_seed_y = seed_y + 2.2 * np.sin(seed_x * 0.25) + 1.2 * np.sin((seed_x - seed_y) * 0.18)
    distance = (
        (warped_x[:, None] - warped_seed_x[None, :]) ** 2
        + 1.08 * (warped_y[:, None] - warped_seed_y[None, :]) ** 2
    )
    weights = np.zeros(len(seeds), dtype=np.float64)
    target = len(xx) / len(seeds)
    labels_at_pixels = np.zeros(len(xx), dtype=np.int16)
    for iteration in range(180):
        labels_at_pixels = np.argmin(distance + weights[None, :], axis=1).astype(np.int16)
        counts = np.bincount(labels_at_pixels, minlength=len(seeds))
        if np.max(np.abs(counts - target)) <= max(3, target * 0.035):
            break
        learning_rate = 3.2 if iteration < 80 else 1.4
        weights += learning_rate * (counts - target) / target
        weights -= weights.mean()
    labels = np.full(mask.shape, -1, dtype=np.int16)
    labels[yy, xx] = labels_at_pixels
    return labels


def geometry_polygons(geometry: dict[str, object]) -> list[list[list[list[float]]]]:
    coordinates = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        return [coordinates]
    if geometry["type"] == "MultiPolygon":
        return coordinates
    raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def mountain_balanced_partition(
    allowed_mask: np.ndarray,
    base_labels: np.ndarray,
    label_indices: tuple[int, ...],
    provinces: tuple[DraftProvince, ...],
    height: np.ndarray,
    rivers: np.ndarray,
) -> np.ndarray:
    """Balance province sizes using mountain- and river-aware geodesic cells."""
    yy, xx = np.where(allowed_mask)
    y_min, y_max = int(yy.min()), int(yy.max())
    x_min, x_max = int(xx.min()), int(xx.max())
    submask = allowed_mask[y_min:y_max + 1, x_min:x_max + 1]
    subheight = height[y_min:y_max + 1, x_min:x_max + 1]
    subrivers = rivers[y_min:y_max + 1, x_min:x_max + 1]
    local_y, local_x = np.where(submask)
    distance_matrix = np.full((len(local_x), len(label_indices)), np.inf, dtype=np.float64)

    for column, label_index in enumerate(label_indices):
        seed_x, seed_y = snap_seed(allowed_mask, provinces[label_index].seed)
        seed_x -= x_min
        seed_y -= y_min
        distance = np.full(submask.shape, np.inf, dtype=np.float64)
        distance[seed_y, seed_x] = 0.0
        queue: list[tuple[float, int, int]] = [(0.0, seed_x, seed_y)]
        while queue:
            current, x, y = heapq.heappop(queue)
            if current != distance[y, x]:
                continue
            for delta_x, delta_y in (
                (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (1, -1), (-1, 1), (-1, -1),
            ):
                next_x, next_y = x + delta_x, y + delta_y
                if not (
                    0 <= next_x < submask.shape[1]
                    and 0 <= next_y < submask.shape[0]
                    and submask[next_y, next_x]
                ):
                    continue
                diagonal = 1.41421356237 if delta_x and delta_y else 1.0
                slope = abs(int(subheight[next_y, next_x]) - int(subheight[y, x])) / 3.8
                river_barrier = 5.0 if subrivers[next_y, next_x] != 255 or subrivers[y, x] != 255 else 0.0
                candidate = current + diagonal + slope + river_barrier
                if candidate < distance[next_y, next_x]:
                    distance[next_y, next_x] = candidate
                    heapq.heappush(queue, (candidate, next_x, next_y))
        distance_matrix[:, column] = distance[local_y, local_x]

    base_at_pixels = base_labels[y_min:y_max + 1, x_min:x_max + 1][local_y, local_x]
    for column, label_index in enumerate(label_indices):
        distance_matrix[:, column] += np.where(base_at_pixels == label_index, 0.0, 7.0)
    current_counts = np.asarray(
        [np.count_nonzero(base_at_pixels == label_index) for label_index in label_indices],
        dtype=np.float64,
    )
    equal_target = len(local_x) / len(label_indices)
    targets = equal_target * 0.88 + current_counts * 0.12
    targets *= len(local_x) / targets.sum()
    weights = np.zeros(len(label_indices), dtype=np.float64)
    selected = np.zeros(len(local_x), dtype=np.int16)
    for iteration in range(420):
        selected = np.argmin(distance_matrix + weights[None, :], axis=1).astype(np.int16)
        counts = np.bincount(selected, minlength=len(label_indices))
        if np.max(np.abs(counts - targets) / targets) < 0.065:
            break
        rate = 3.0 if iteration < 220 else 1.4
        weights += rate * (counts - targets) / targets
        weights -= weights.mean()

    result = base_labels.copy()
    mapped = np.asarray(label_indices, dtype=np.int16)[selected]
    subresult = result[y_min:y_max + 1, x_min:x_max + 1]
    subresult[local_y, local_x] = mapped
    return result


def basin_geojson_partition(
    mask: np.ndarray,
    provinces: tuple[DraftProvince, ...],
) -> np.ndarray:
    selected_features: list[tuple[dict[str, object], str]] = []
    with urllib.request.urlopen(BASIN_GEOJSON[0], timeout=30) as response:
        sichuan_features = json.load(response)["features"]
    for feature in sichuan_features:
        properties = feature["properties"]
        parent_code = int(properties["parent"]["adcode"])
        if parent_code not in SICHUAN_PARENT_TARGET:
            continue
        county_name = properties["name"]
        target = SICHUAN_COUNTY_TARGET.get(county_name, SICHUAN_PARENT_TARGET[parent_code])
        selected_features.append((feature, target))
    with urllib.request.urlopen(BASIN_GEOJSON[1], timeout=30) as response:
        chongqing_features = json.load(response)["features"]
    for feature in chongqing_features:
        county_name = feature["properties"]["name"]
        selected_features.append((feature, CHONGQING_TARGET[county_name]))

    all_points: list[tuple[float, float]] = []
    for feature, _target in selected_features:
        for polygon in geometry_polygons(feature["geometry"]):
            all_points.extend((float(point[0]), float(point[1])) for point in polygon[0])
    longitudes = [point[0] for point in all_points]
    latitudes = [point[1] for point in all_points]
    lon_min, lon_max = min(longitudes), max(longitudes)
    lat_min, lat_max = min(latitudes), max(latitudes)
    yy, xx = np.where(mask)
    x_min, x_max = int(xx.min()), int(xx.max())
    y_min, y_max = int(yy.min()), int(yy.max())

    def project(point: list[float]) -> tuple[int, int]:
        lon, lat = float(point[0]), float(point[1])
        x = x_min + (lon - lon_min) / (lon_max - lon_min) * (x_max - x_min)
        y = y_min + (lat_max - lat) / (lat_max - lat_min) * (y_max - y_min)
        return round(x), round(y)

    label_by_name = {province.name: index for index, province in enumerate(provinces)}
    raster = Image.new("I", (mask.shape[1], mask.shape[0]), color=-1)
    draw = ImageDraw.Draw(raster)
    for feature, target in selected_features:
        label = label_by_name[target]
        for polygon in geometry_polygons(feature["geometry"]):
            exterior = [project(point) for point in polygon[0]]
            if len(exterior) >= 3:
                draw.polygon(exterior, fill=label)
    labels = np.asarray(raster, dtype=np.int16).copy()
    labels[~mask] = -1

    frontier = [(int(x), int(y)) for y, x in zip(*np.where(mask & (labels >= 0)), strict=True)]
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


def western_geojson_partition(
    mask: np.ndarray,
    provinces: tuple[DraftProvince, ...],
    id_map: np.ndarray,
    height: np.ndarray,
    rivers: np.ndarray,
) -> np.ndarray:
    features: list[dict[str, object]] = []
    for url in WESTERN_GEOJSON:
        with urllib.request.urlopen(url, timeout=30) as response:
            features.extend(json.load(response)["features"])
    all_points: list[tuple[float, float]] = []
    for feature in features:
        for polygon in geometry_polygons(feature["geometry"]):
            all_points.extend((float(point[0]), float(point[1])) for point in polygon[0])
    longitudes = [point[0] for point in all_points]
    latitudes = [point[1] for point in all_points]
    lon_min, lon_max = min(longitudes), max(longitudes)
    lat_min, lat_max = min(latitudes), max(latitudes)
    yy, xx = np.where(mask)
    x_min, x_max = int(xx.min()), int(xx.max())
    y_min, y_max = int(yy.min()), int(yy.max())

    def project(point: list[float]) -> tuple[int, int]:
        lon, lat = float(point[0]), float(point[1])
        x = x_min + (lon - lon_min) / (lon_max - lon_min) * (x_max - x_min)
        y = y_min + (lat_max - lat) / (lat_max - lat_min) * (y_max - y_min)
        return round(x), round(y)

    label_by_name = {province.name: index for index, province in enumerate(provinces)}
    raster = Image.new("I", (mask.shape[1], mask.shape[0]), color=-1)
    draw = ImageDraw.Draw(raster)
    for feature in features:
        county_name = feature["properties"]["name"]
        target_name = COUNTY_TARGET[county_name]
        label = label_by_name[target_name]
        for polygon in geometry_polygons(feature["geometry"]):
            exterior = [project(point) for point in polygon[0]]
            if len(exterior) >= 3:
                draw.polygon(exterior, fill=label)
    labels = np.asarray(raster, dtype=np.int16).copy()
    labels[~mask] = -1

    frontier = [(int(x), int(y)) for y, x in zip(*np.where(mask & (labels >= 0)), strict=True)]
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

    name_to_index = {province.name: index for index, province in enumerate(provinces)}
    aba_labels = tuple(name_to_index[name] for name in ("松州", "茂州", "汶川", "南坪", "马尔康", "金川", "阿坝", "若尔盖"))
    ganzi_labels = tuple(name_to_index[name] for name in ("康定", "德格", "壤塘", "理塘"))
    liangshan_labels = tuple(name_to_index[name] for name in ("嶲州", "会理", "盐源"))
    aba_mask = id_map == 2170
    x_grid = np.broadcast_to(np.arange(id_map.shape[1]), id_map.shape)
    ganzi_mask = np.isin(id_map, (678, 2133, 2135)) | ((id_map == 2132) & (x_grid >= 4344))
    liangshan_mask = id_map == 2748
    labels = mountain_balanced_partition(aba_mask, labels, aba_labels, provinces, height, rivers)
    labels = mountain_balanced_partition(ganzi_mask, labels, ganzi_labels, provinces, height, rivers)
    labels = mountain_balanced_partition(liangshan_mask, labels, liangshan_labels, provinces, height, rivers)
    return labels


def distinct_colours(count: int, forbidden: set[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    result: list[tuple[int, int, int]] = []
    index = 0
    while len(result) < count:
        hue = (0.071 + index * 0.61803398875) % 1.0
        saturation = 0.58 + (index % 3) * 0.07
        value = 0.78 + (index % 2) * 0.10
        colour = tuple(round(value * 255) for value in colorsys.hsv_to_rgb(hue, saturation, value))
        if colour not in forbidden and colour not in result:
            result.append(colour)
        index += 1
    return result


def area_shades(base: tuple[int, int, int], count: int) -> list[tuple[int, int, int]]:
    shades = []
    for index in range(count):
        factor = 0.82 + 0.10 * (index % 4)
        offset = 10 * (index // 4)
        shades.append(tuple(min(238, round(channel * factor + offset)) for channel in base))
    return shades


def main() -> None:
    colour_to_id, id_to_colour = definition()
    original = np.asarray(Image.open(MOD / "map/provinces.bmp").convert("RGB"))
    height = np.asarray(Image.open(MOD / "map/heightmap.bmp").convert("L"))
    rivers = np.asarray(Image.open(MOD / "map/rivers.bmp"))
    lookup = np.full(1 << 24, -1, dtype=np.int32)
    for colour, province_id in colour_to_id.items():
        lookup[(colour[0] << 16) | (colour[1] << 8) | colour[2]] = province_id
    packed = (
        original[:, :, 0].astype(np.int32) << 16
        | original[:, :, 1].astype(np.int32) << 8
        | original[:, :, 2].astype(np.int32)
    )
    id_map = lookup[packed]

    draft = original.copy()
    assigned = np.full(id_map.shape, -1, dtype=np.int16)
    province_records: list[tuple[str, DraftProvince, int]] = []
    total = sum(len(group["provinces"]) for group in GROUPS.values())
    colours = distinct_colours(total, set(colour_to_id))
    for area, group in GROUPS.items():
        for province in group["provinces"]:
            province_records.append((area, province, len(province_records)))

    record_index = {
        (area, province.name): index
        for index, (area, province, _colour_index) in enumerate(province_records)
    }

    for areas, source_ids, fixed in MACROS:
        provinces = tuple(
            province
            for area in areas
            for province in GROUPS[area]["provinces"]
        )
        mask = np.isin(id_map, source_ids)
        if "甘孜" in areas:
            x_grid = np.broadcast_to(np.arange(id_map.shape[1]), id_map.shape)
            mask |= (id_map == 2132) & (x_grid >= 4344)
        if fixed:
            local_labels = np.full(id_map.shape, -1, dtype=np.int16)
            for local_index, province_id in enumerate(source_ids):
                local_labels[id_map == province_id] = local_index
        elif areas == ("成都", "嘉雅"):
            local_labels = balanced_warped_voronoi(mask, tuple(p.seed for p in provinces))
        elif areas == BASIN_AREAS:
            local_labels = basin_geojson_partition(mask, provinces)
        elif areas == WESTERN_AREAS:
            local_labels = western_geojson_partition(mask, provinces, id_map, height, rivers)
        else:
            local_labels = watershed(mask, tuple(p.seed for p in provinces), height, rivers)
        for local_index, province in enumerate(provinces):
            province_mask = mask & (local_labels == local_index)
            area = next(area for area in areas if province in GROUPS[area]["provinces"])
            index = record_index[(area, province.name)]
            draft[province_mask] = colours[index]
            assigned[province_mask] = index

    FULL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(draft).save(FULL_OUTPUT)
    Image.fromarray(draft).crop(CROP).save(CROP_OUTPUT)

    left, top, right, bottom = CROP
    assigned_crop = assigned[top:bottom, left:right]
    id_crop = id_map[top:bottom, left:right]
    river_crop = rivers[top:bottom, left:right]
    height_crop = height[top:bottom, left:right]
    review = np.full((*assigned_crop.shape, 3), (218, 216, 207), dtype=np.uint8)
    water_ids = tuple(range(5032, 5045)) + (1655, 1896, 1897)
    review[np.isin(id_crop, water_ids)] = (87, 164, 205)

    for area in GROUPS:
        indexes = [index for index, record in enumerate(province_records) if record[0] == area]
        for shade, record_index in zip(area_shades(AREA_BASE[area], len(indexes)), indexes, strict=True):
            review[assigned_crop == record_index] = shade
    visible_river = (river_crop != 255) & (assigned_crop >= 0)
    review[visible_river] = (67, 144, 196)
    ridge_strength = np.zeros(height_crop.shape, dtype=np.int16)
    height_int = height_crop.astype(np.int16)
    ridge_strength[1:] = np.maximum(ridge_strength[1:], np.abs(height_int[1:] - height_int[:-1]))
    ridge_strength[:-1] = np.maximum(ridge_strength[:-1], np.abs(height_int[:-1] - height_int[1:]))
    ridge_strength[:, 1:] = np.maximum(ridge_strength[:, 1:], np.abs(height_int[:, 1:] - height_int[:, :-1]))
    ridge_strength[:, :-1] = np.maximum(ridge_strength[:, :-1], np.abs(height_int[:, :-1] - height_int[:, 1:]))
    visible_ridge = (ridge_strength >= 12) & (assigned_crop >= 0) & ~visible_river
    review[visible_ridge] = (143, 105, 70)

    scope = assigned_crop >= 0
    scale = 4
    enlarged = np.repeat(np.repeat(review, scale, axis=0), scale, axis=1)
    enlarged_labels = np.repeat(np.repeat(assigned_crop, scale, axis=0), scale, axis=1)
    thin_boundary = np.zeros(enlarged_labels.shape, dtype=bool)
    thin_boundary[1:, :] |= (
        (enlarged_labels[1:, :] >= 0)
        & (enlarged_labels[:-1, :] >= 0)
        & (enlarged_labels[1:, :] != enlarged_labels[:-1, :])
    )
    thin_boundary[:, 1:] |= (
        (enlarged_labels[:, 1:] >= 0)
        & (enlarged_labels[:, :-1] >= 0)
        & (enlarged_labels[:, 1:] != enlarged_labels[:, :-1])
    )
    enlarged[thin_boundary] = (247, 244, 235)
    map_image = Image.fromarray(enlarged)
    canvas = Image.new("RGB", (1750, 890), (246, 244, 237))
    map_origin = (35, 88)
    canvas.paste(map_image, map_origin)
    draw = ImageDraw.Draw(canvas)
    draw.text((35, 25), "四川三十六省 · 县级GeoJSON辅助草图", fill=(37, 42, 44), font=font(31, True))
    draw.text((730, 33), "灰色为未改动省份；蓝线为河流，棕线为高程山脊", fill=(101, 104, 103), font=font(16))

    label_font = font(14, True)
    tiny_font = font(9)
    for record_index, (area, province, _colour_index) in enumerate(province_records):
        mask = assigned == record_index
        seed_x, seed_y = snap_seed(mask, province.seed)
        px = map_origin[0] + (seed_x - left) * scale
        py = map_origin[1] + (seed_y - top) * scale
        box = draw.textbbox((px, py), province.name, font=label_font, anchor="mm")
        box = (box[0] - 3, box[1] - 1, box[2] + 3, box[3] + 1)
        draw.rounded_rectangle(box, radius=3, fill=(255, 253, 246), outline=(54, 59, 61), width=1)
        draw.text((px, py), province.name, fill=(31, 35, 37), font=label_font, anchor="mm")
        if province.note:
            draw.text((px, box[3] + 2), "★", fill=(126, 72, 31), font=tiny_font, anchor="ma")

    legend_x = 1045
    draw.rounded_rectangle((1020, 88, 1715, 850), radius=18, fill=(255, 253, 247), outline=(208, 204, 193), width=2)
    draw.text((legend_x, 110), "九个区域", fill=(40, 45, 47), font=font(25, True))
    y = 155
    for area, group in GROUPS.items():
        draw.rounded_rectangle((legend_x, y, legend_x + 25, y + 25), radius=4, fill=AREA_BASE[area])
        draw.text((legend_x + 38, y + 12), area, fill=(38, 43, 45), font=font(19, True), anchor="lm")
        names = " · ".join(province.name for province in group["provinces"])
        draw.text((legend_x + 98, y + 13), names, fill=(76, 78, 77), font=font(14), anchor="lm")
        y += 52

    draw.line((legend_x, 638, 1684, 638), fill=(216, 211, 198), width=2)
    draw.text((legend_x, 664), "草图重点", fill=(40, 45, 47), font=font(22, True))
    notes = (
        "• 马尔康拆出金川；松州北侧新增南坪（九寨沟）",
        "• 甘孜压缩为康定、德格、壤塘、理塘四省",
        "• 凉山压缩为嶲州、会理、盐源三省",
        "• 成都、重庆为二级商埠；松州、康定为一级",
        "• 三州边界由现代县级GeoJSON投影后合并",
        "• 这是规划色块，不占用正式省份ID，也不修改模组地图",
    )
    y = 708
    for note in notes:
        draw.text((legend_x, y), note, fill=(64, 67, 66), font=font(15))
        y += 29

    REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(REVIEW_OUTPUT)
    print(FULL_OUTPUT)
    print(CROP_OUTPUT)
    print(REVIEW_OUTPUT)


if __name__ == "__main__":
    main()
