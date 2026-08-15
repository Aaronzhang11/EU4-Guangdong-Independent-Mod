#!/usr/bin/env python3
"""Render the non-canonical B47 Jingxiang–southern Henan proposal.

The current thirteen province masks are the locked exterior. County GeoJSON
guides only their internal subdivisions. Installed workshop maps are rendered
as density references but none of their pixels are copied into the proposal.
All outputs stay in this planning directory; no game-loaded file is touched.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
import csv
import hashlib
import json
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = Path(__file__).resolve().parent
GEO_DIR = OUT / "reference_geojson"
HUBEI_URL = "https://geo.datav.aliyun.com/areas_v3/bound/420000_full_district.json"
HENAN_URL = "https://geo.datav.aliyun.com/areas_v3/bound/410000_full_district.json"
REVIEWED_BMP = OUT / "b47_geojson_reviewed_provinces.bmp"
REVIEW_PNG = OUT / "b47_geojson_review.png"
REFERENCE_PNG = OUT / "b47_reference_comparison.png"
MANIFEST = OUT / "preview_manifest.json"

WORKSHOP = Path("/Users/xinanyapiao/Library/Application Support/Steam/steamapps/workshop/content/236850")
REFERENCES = (
    ("大明日不落", WORKSHOP / "1728520255"),
    ("岁在甲子", WORKSHOP / "3400977776"),
    ("风云世纪两千年", WORKSHOP / "2935149060"),
)

PARENT_IDS = (5008, 2171, 681, 2172, 5015, 5010, 5013, 5014, 687, 5053, 5054, 5055, 2175)
NEW_RGB = {
    5341: (210, 87, 145),
    5342: (77, 172, 204),
    5343: (188, 151, 62),
    5344: (92, 189, 108),
    5345: (133, 83, 198),
    5346: (218, 111, 67),
    5347: (68, 123, 190),
    5348: (172, 76, 102),
    5349: (112, 169, 73),
    5350: (201, 124, 183),
}


@dataclass(frozen=True)
class Cell:
    province_id: int
    name: str
    parent_id: int
    development: int
    polity: str
    area_key: str
    area_name: str
    culture: str
    new: bool = False


CELLS = (
    Cell(5008, "郧", 5008, 4, "SHE", "hanshang_area", "鄢庸", "gdd_chu"),
    Cell(5341, "房州", 5008, 4, "SHE", "hanshang_area", "鄢庸", "gdd_chu", True),
    Cell(2171, "襄阳", 2171, 11, "LUO", "hanshang_area", "鄢庸", "gdd_zhongyuan"),
    Cell(5342, "宜城", 2171, 6, "LUO", "hanshang_area", "鄢庸", "gdd_zhongyuan", True),
    Cell(5010, "安陆", 5010, 4, "QVN", "yunmeng_jingmen_area", "江汉", "gdd_chu"),
    Cell(5343, "荆门", 5010, 4, "QVN", "yunmeng_jingmen_area", "江汉", "gdd_chu", True),
    Cell(5015, "沔阳", 5015, 3, "ZHU", "yunmeng_jingmen_area", "江汉", "gdd_chu"),
    Cell(5344, "监利", 5015, 3, "ZHU", "yunmeng_jingmen_area", "江汉", "gdd_chu", True),
    Cell(2172, "荆州", 2172, 9, "CHC", "jingyi_area", "荆郢", "gdd_chu"),
    Cell(5345, "枝江", 2172, 5, "CHC", "jingyi_area", "荆郢", "gdd_chu", True),
    Cell(5014, "公安", 5014, 9, "CHC", "jingyi_area", "荆郢", "gdd_chu"),
    Cell(681, "夷陵", 681, 7, "SHE", "yigui_area", "夷陵", "gdd_chu"),
    Cell(5346, "归州", 681, 4, "SHE", "yigui_area", "夷陵", "gdd_chu", True),
    Cell(5013, "施州", 5013, 6, "BD2", "jingyi_area", "荆郢", "gdd_diqiang"),
    Cell(687, "南阳", 687, 10, "GON", "wandeng_area", "申邓", "gdd_zhongyuan"),
    Cell(5347, "方城", 687, 5, "GON", "wandeng_area", "申邓", "gdd_zhongyuan", True),
    Cell(5055, "邓州", 5055, 6, "GON", "wandeng_area", "申邓", "gdd_zhongyuan"),
    Cell(5348, "内乡", 5055, 4, "GON", "wandeng_area", "申邓", "gdd_zhongyuan", True),
    Cell(5053, "汝州", 5053, 8, "CZH", "rucai_area", "汝蔡", "gdd_zhongyuan"),
    Cell(5054, "汝宁", 5054, 8, "CAI", "rucai_area", "汝蔡", "gdd_zhongyuan"),
    Cell(5349, "息州", 5054, 4, "CAI", "rucai_area", "汝蔡", "gdd_zhongyuan", True),
    Cell(2175, "信阳", 2175, 5, "SUI", "dean_qihuang_area", "随黄", "gdd_chu"),
    Cell(5350, "光州", 2175, 4, "SUI", "dean_qihuang_area", "随黄", "gdd_chu", True),
)
CELL_BY_ID = {cell.province_id: cell for cell in CELLS}
CELL_BY_NAME = {cell.name: cell for cell in CELLS}

POLITY_NAMES = {"SHE": "申", "LUO": "罗", "CHC": "楚", "QVN": "权", "ZHU": "州", "BD2": "巴氐", "GON": "共", "CZH": "周", "CAI": "蔡", "SUI": "随"}
POLITY_COLORS = {
    "SHE": (176, 109, 70), "LUO": (60, 143, 132), "CHC": (135, 78, 153),
    "QVN": (178, 138, 75), "ZHU": (130, 96, 142),
    "BD2": (126, 91, 72), "GON": (70, 111, 174), "CZH": (202, 155, 55),
    "CAI": (91, 149, 78), "SUI": (75, 132, 181),
}
AREA_COLORS = {
    "鄢庸": (202, 139, 66), "江汉": (66, 148, 158), "荆郢": (139, 83, 155),
    "夷陵": (91, 143, 95), "申邓": (177, 91, 82), "汝蔡": (187, 154, 66),
    "随黄": (76, 121, 175),
}

# County-level modern geometry is used as a boundary language. Historical
# names and groupings remain the design authority.
FEATURE_GROUPS = {
    "郧": ((420300, "茅箭区"), (420300, "张湾区"), (420300, "郧阳区"), (420300, "郧西县"), (420300, "丹江口市")),
    "房州": ((420300, "竹山县"), (420300, "竹溪县"), (420300, "房县")),
    "襄阳": ((420600, "襄城区"), (420600, "樊城区"), (420600, "襄州区"), (420600, "谷城县"), (420600, "老河口市"), (420600, "枣阳市")),
    "宜城": ((420600, "南漳县"), (420600, "保康县"), (420600, "宜城市")),
    "安陆": ((420900, "孝南区"), (420900, "孝昌县"), (420900, "大悟县"), (420900, "云梦县"), (420900, "应城市"), (420900, "安陆市")),
    "荆门": ((420800, "东宝区"), (420800, "掇刀区"), (420800, "钟祥市"), (420800, "京山市")),
    "沔阳": ((420000, "仙桃市"), (420000, "潜江市"), (420000, "天门市"), (420900, "汉川市"), (420800, "沙洋县")),
    "监利": ((421000, "监利市"), (421000, "洪湖市")),
    "荆州": ((421000, "沙市区"), (421000, "荆州区"), (421000, "江陵县")),
    "枝江": ((420500, "远安县"), (420500, "当阳市"), (420500, "宜都市"), (420500, "枝江市")),
    "公安": ((421000, "公安县"), (421000, "石首市"), (421000, "松滋市")),
    "夷陵": ((420500, "西陵区"), (420500, "伍家岗区"), (420500, "点军区"), (420500, "猇亭区"), (420500, "夷陵区"), (420500, "长阳土家族自治县"), (420500, "五峰土家族自治县")),
    "归州": ((420500, "兴山县"), (420500, "秭归县"), (422800, "巴东县")),
    "施州": ((422800, "恩施市"), (422800, "利川市"), (422800, "建始县"), (422800, "宣恩县"), (422800, "咸丰县"), (422800, "来凤县"), (422800, "鹤峰县")),
    "南阳": ((411300, "宛城区"), (411300, "卧龙区"), (411300, "社旗县"), (411300, "唐河县"), (411300, "新野县"), (411300, "桐柏县")),
    "方城": ((411300, "南召县"), (411300, "方城县")),
    "邓州": ((411300, "邓州市"),),
    "内乡": ((411300, "西峡县"), (411300, "镇平县"), (411300, "内乡县"), (411300, "淅川县")),
    "汝州": ((410400, "新华区"), (410400, "卫东区"), (410400, "石龙区"), (410400, "湛河区"), (410400, "宝丰县"), (410400, "叶县"), (410400, "鲁山县"), (410400, "郏县"), (410400, "舞钢市"), (410400, "汝州市")),
    "汝宁": ((411700, "驿城区"), (411700, "西平县"), (411700, "上蔡县"), (411700, "平舆县"), (411700, "正阳县"), (411700, "确山县"), (411700, "泌阳县"), (411700, "汝南县"), (411700, "遂平县"), (411700, "新蔡县")),
    "息州": ((411500, "淮滨县"), (411500, "息县")),
    "信阳": ((411500, "浉河区"), (411500, "平桥区"), (411500, "罗山县")),
    "光州": ((411500, "光山县"), (411500, "新县"), (411500, "商城县"), (411500, "固始县"), (411500, "潢川县")),
}
FEATURE_TARGET = {feature: name for name, features in FEATURE_GROUPS.items() for feature in features}
if len(FEATURE_TARGET) != sum(len(features) for features in FEATURE_GROUPS.values()):
    raise ValueError("A GeoJSON feature is assigned to more than one historical cell")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size, index=1 if bold else 0)
    return ImageFont.load_default()


def definitions(root: Path = MAP) -> tuple[dict[int, tuple[int, int, int]], dict[tuple[int, int, int], int], dict[int, str]]:
    id_to_rgb: dict[int, tuple[int, int, int]] = {}
    rgb_to_id: dict[tuple[int, int, int], int] = {}
    names: dict[int, str] = {}
    with (root / "definition.csv").open(encoding="cp1252", errors="replace") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if len(row) < 5 or not row[0].isdigit():
                continue
            province_id = int(row[0])
            rgb = tuple(map(int, row[1:4]))
            id_to_rgb[province_id] = rgb
            rgb_to_id[rgb] = province_id
            names[province_id] = row[4]
    return id_to_rgb, rgb_to_id, names


def load_geojson(url: str, filename: str) -> dict[str, object]:
    GEO_DIR.mkdir(parents=True, exist_ok=True)
    path = GEO_DIR / filename
    if not path.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "EU4-Guangdong-Independent-Mod/B47-preview"})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
        json.loads(payload.decode("utf-8"))
        path.write_bytes(payload)
    return json.loads(path.read_text(encoding="utf-8"))


def polygons(geometry: dict[str, object]) -> list[list[list[list[float]]]]:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    raise ValueError(f"Unsupported GeoJSON geometry: {geometry['type']}")


def component_masks(mask: np.ndarray) -> list[np.ndarray]:
    seen = np.zeros(mask.shape, dtype=bool)
    result: list[np.ndarray] = []
    height, width = mask.shape
    for sy, sx in zip(*np.where(mask), strict=True):
        if seen[sy, sx]:
            continue
        points: list[tuple[int, int]] = []
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        while stack:
            y, x = stack.pop()
            points.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        part = np.zeros(mask.shape, dtype=bool)
        for y, x in points:
            part[y, x] = True
        result.append(part)
    return sorted(result, key=lambda value: int(value.sum()), reverse=True)


def largest_component(mask: np.ndarray) -> np.ndarray:
    values = component_masks(mask)
    return values[0] if values else np.zeros(mask.shape, dtype=bool)


def border(mask: np.ndarray) -> np.ndarray:
    eroded = mask.copy()
    eroded[1:] &= mask[:-1]
    eroded[:-1] &= mask[1:]
    eroded[:, 1:] &= mask[:, :-1]
    eroded[:, :-1] &= mask[:, 1:]
    return mask & ~eroded


def nearest_mask_point(mask: np.ndarray, x: float, y: float) -> tuple[int, int]:
    ys, xs = np.where(mask)
    index = int(np.argmin((xs - x) ** 2 + (ys - y) ** 2))
    return int(xs[index]), int(ys[index])


def build_cells() -> tuple[np.ndarray, dict[int, np.ndarray], np.ndarray, tuple[int, int, int, int], dict[str, object]]:
    id_to_rgb, _, _ = definitions()
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    parent_masks = {province_id: np.all(current == np.asarray(id_to_rgb[province_id], dtype=np.uint8), axis=2) for province_id in PARENT_IDS}
    editable = np.zeros(current.shape[:2], dtype=bool)
    for mask in parent_masks.values():
        editable |= mask
    ys, xs = np.where(editable)
    target_box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)

    features = load_geojson(HUBEI_URL, "420000_full_district.json")["features"] + load_geojson(HENAN_URL, "410000_full_district.json")["features"]
    selected: list[dict[str, object]] = []
    centers: dict[str, list[tuple[float, float]]] = {cell.name: [] for cell in CELLS}
    all_points: list[tuple[float, float]] = []
    for feature in features:
        props = feature["properties"]
        parent_code = int((props.get("parent") or {}).get("adcode", 0))
        key = (parent_code, props["name"])
        target = FEATURE_TARGET.get(key)
        if target is None:
            continue
        selected.append(feature)
        center = props.get("centroid") or props.get("center")
        if center:
            centers[target].append((float(center[0]), float(center[1])))
        for polygon in polygons(feature["geometry"]):
            all_points.extend((float(point[0]), float(point[1])) for point in polygon[0])
    if len(selected) != len(FEATURE_TARGET):
        found = {(int((f["properties"].get("parent") or {}).get("adcode", 0)), f["properties"]["name"]) for f in selected}
        raise ValueError(f"Missing GeoJSON features: {sorted(set(FEATURE_TARGET) - found)}")

    lon_min = min(point[0] for point in all_points)
    lon_max = max(point[0] for point in all_points)
    lat_min = min(point[1] for point in all_points)
    lat_max = max(point[1] for point in all_points)
    x_min, y_min, x_max, y_max = target_box

    def project(point: tuple[float, float] | list[float]) -> tuple[int, int]:
        lon, lat = float(point[0]), float(point[1])
        x = x_min + (lon - lon_min) / (lon_max - lon_min) * (x_max - x_min - 1)
        y = y_min + (lat_max - lat) / (lat_max - lat_min) * (y_max - y_min - 1)
        return round(x), round(y)

    labels_image = Image.new("I", (current.shape[1], current.shape[0]), 0)
    draw = ImageDraw.Draw(labels_image)
    for feature in selected:
        props = feature["properties"]
        key = (int((props.get("parent") or {}).get("adcode", 0)), props["name"])
        target_id = CELL_BY_NAME[FEATURE_TARGET[key]].province_id
        for polygon in polygons(feature["geometry"]):
            exterior = [project(point) for point in polygon[0]]
            if len(exterior) >= 3:
                draw.polygon(exterior, fill=target_id)
    labels = np.asarray(labels_image, dtype=np.int32).copy()

    masks: dict[int, np.ndarray] = {}
    for parent_id, parent_mask in parent_masks.items():
        children = [cell for cell in CELLS if cell.parent_id == parent_id]
        child_ids = {cell.province_id for cell in children}
        local = np.where(parent_mask & np.isin(labels, list(child_ids)), labels, 0)
        for child in children:
            if np.any(local == child.province_id):
                continue
            points = centers[child.name]
            if points:
                px = sum(project(point)[0] for point in points) / len(points)
                py = sum(project(point)[1] for point in points) / len(points)
            else:
                py_values, px_values = np.where(parent_mask)
                px, py = float(px_values.mean()), float(py_values.mean())
            available = parent_mask & (local == 0)
            sx, sy = nearest_mask_point(available if available.any() else parent_mask, px, py)
            local[sy, sx] = child.province_id

        frontier = deque((int(y), int(x)) for y, x in zip(*np.where(parent_mask & (local > 0)), strict=True))
        while frontier:
            y, x = frontier.popleft()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < current.shape[0] and 0 <= nx < current.shape[1] and parent_mask[ny, nx] and local[ny, nx] == 0:
                    local[ny, nx] = local[y, x]
                    frontier.append((ny, nx))

        kept: dict[int, np.ndarray] = {child.province_id: largest_component(parent_mask & (local == child.province_id)) for child in children}
        if any(not mask.any() for mask in kept.values()):
            raise ValueError(f"Parent {parent_id} produced an empty child")
        clean_labels = np.zeros(local.shape, dtype=np.int32)
        frontier.clear()
        for province_id, mask in kept.items():
            clean_labels[mask] = province_id
            frontier.extend((int(y), int(x)) for y, x in zip(*np.where(mask), strict=True))
        while frontier:
            y, x = frontier.popleft()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < current.shape[0] and 0 <= nx < current.shape[1] and parent_mask[ny, nx] and clean_labels[ny, nx] == 0:
                    clean_labels[ny, nx] = clean_labels[y, x]
                    frontier.append((ny, nx))
        if np.any(parent_mask & (clean_labels == 0)):
            raise ValueError(f"Parent {parent_id} contains an unassigned component")
        for child in children:
            mask = parent_mask & (clean_labels == child.province_id)
            if len(component_masks(mask)) != 1:
                raise ValueError(f"{child.name} is not four-way connected")
            masks[child.province_id] = mask

    covered = np.zeros(editable.shape, dtype=bool)
    for mask in masks.values():
        if np.any(covered & mask):
            raise ValueError("Proposed provinces overlap")
        covered |= mask
    if not np.array_equal(covered, editable):
        raise ValueError("Proposed cells do not exactly cover the locked parent mask")
    box = (max(0, target_box[0] - 7), max(0, target_box[1] - 7), min(current.shape[1], target_box[2] + 7), min(current.shape[0], target_box[3] + 7))
    metadata = {"geojson_feature_count": len(selected), "geojson_bounds": [lon_min, lat_min, lon_max, lat_max]}
    return current, masks, editable, box, metadata


def label_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    cx, cy = float(xs.mean()), float(ys.mean())
    index = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
    return int(xs[index]), int(ys[index])


def group_edge(labels: np.ndarray) -> np.ndarray:
    edge = np.zeros(labels.shape, dtype=bool)
    edge[1:] |= (labels[1:] != labels[:-1]) & (labels[1:] > 0) & (labels[:-1] > 0)
    edge[:-1] |= (labels[:-1] != labels[1:]) & (labels[:-1] > 0) & (labels[1:] > 0)
    edge[:, 1:] |= (labels[:, 1:] != labels[:, :-1]) & (labels[:, 1:] > 0) & (labels[:, :-1] > 0)
    edge[:, :-1] |= (labels[:, :-1] != labels[:, 1:]) & (labels[:, :-1] > 0) & (labels[:, 1:] > 0)
    return edge


def render_map(masks: dict[int, np.ndarray], box: tuple[int, int, int, int], mode: str) -> Image.Image:
    left, top, right, bottom = box
    scale = 8
    heightmap = np.asarray(Image.open(MAP / "heightmap.bmp").convert("L"), dtype=np.float32)[top:bottom, left:right]
    rivers = np.asarray(Image.open(MAP / "rivers.bmp").convert("L"), dtype=np.uint8)[top:bottom, left:right]
    relief = np.clip(0.86 + heightmap / 620.0, 0.82, 1.17)
    canvas = np.zeros((*heightmap.shape, 3), dtype=np.float32)
    canvas[:] = np.asarray((207, 202, 187), dtype=np.float32) * relief[:, :, None]
    province_labels = np.zeros(heightmap.shape, dtype=np.int32)
    group_labels = np.zeros(heightmap.shape, dtype=np.int16)
    groups = list(POLITY_COLORS if mode == "polity" else AREA_COLORS)
    for province_id, full_mask in masks.items():
        cell = CELL_BY_ID[province_id]
        local = full_mask[top:bottom, left:right]
        key = cell.polity if mode == "polity" else cell.area_name
        palette = POLITY_COLORS if mode == "polity" else AREA_COLORS
        color = np.asarray(palette[key], dtype=np.float32)
        canvas[local] = np.clip(color[None, :] * relief[local, None], 0, 255)
        province_labels[local] = province_id
        group_labels[local] = groups.index(key) + 1
    province_edges = np.zeros(heightmap.shape, dtype=bool)
    for full_mask in masks.values():
        province_edges |= border(full_mask[top:bottom, left:right])
    canvas[province_edges] = (247, 242, 226)
    canvas[group_edge(group_labels)] = (48, 47, 43)
    canvas[(rivers != 255) & (province_labels > 0)] = (67, 171, 207)
    image = Image.fromarray(canvas.astype(np.uint8)).resize((canvas.shape[1] * scale, canvas.shape[0] * scale), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    occupied: list[tuple[int, int, int, int]] = []
    label_font = font(14, True)
    for province_id, full_mask in sorted(masks.items(), key=lambda item: CELL_BY_ID[item[0]].development, reverse=True):
        local = full_mask[top:bottom, left:right]
        px, py = label_point(local)
        anchor = (px * scale, py * scale)
        cell = CELL_BY_ID[province_id]
        text = f"{'★' if cell.new else ''}{cell.name} {cell.development}"
        bbox = draw.textbbox((0, 0), text, font=label_font)
        width, height = bbox[2] + 10, bbox[3] + 8
        offsets = ((0, 0), (0, -26), (0, 26), (34, 0), (-34, 0), (34, -25), (-34, -25), (34, 25), (-34, 25), (0, -50), (0, 50))
        chosen = None
        for dx, dy in offsets:
            candidate = (anchor[0] + dx - width // 2, anchor[1] + dy - height // 2, anchor[0] + dx + width // 2, anchor[1] + dy + height // 2)
            if not any(not (candidate[2] < old[0] or candidate[0] > old[2] or candidate[3] < old[1] or candidate[1] > old[3]) for old in occupied):
                chosen = candidate
                break
        if chosen is None:
            chosen = candidate
        occupied.append(chosen)
        center = ((chosen[0] + chosen[2]) // 2, (chosen[1] + chosen[3]) // 2)
        if abs(center[0] - anchor[0]) + abs(center[1] - anchor[1]) > 18:
            draw.line((anchor, center), fill=(43, 42, 39), width=2)
        draw.rounded_rectangle(chosen, radius=5, fill=(248, 244, 231), outline=(44, 43, 40), width=1)
        draw.text((chosen[0] + 5, chosen[1] + 3), text, font=label_font, fill=(28, 28, 26))
    return image


def totals(attribute: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for cell in CELLS:
        key = getattr(cell, attribute)
        result[key] = result.get(key, 0) + cell.development
    return result


def compose_review(
    country: Image.Image,
    area: Image.Image,
    *,
    title: str = "B47 荆襄—豫南二次细化 · GeoJSON正式预览",
    subtitle: str = "当前13省 → 方案23省｜新增10省｜总发展度133守恒｜★为新增｜河流与地形只作视觉引导",
    output: Path = REVIEW_PNG,
) -> None:
    margin, gap, header, footer = 34, 28, 118, 245
    width = country.width + area.width + margin * 2 + gap
    height = max(country.height, area.height) + header + footer
    canvas = Image.new("RGB", (width, height), (244, 239, 228))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 18), title, font=font(31, True), fill=(36, 35, 32))
    draw.text((margin, 62), subtitle, font=font(16), fill=(82, 78, 69))
    canvas.paste(country, (margin, header))
    canvas.paste(area, (margin + country.width + gap, header))
    draw.rounded_rectangle((margin + 12, header + 12, margin + 175, header + 48), radius=8, fill=(248, 244, 232), outline=(72, 68, 61))
    draw.text((margin + 27, header + 17), "国家与文化", font=font(17, True), fill=(42, 40, 36))
    second_x = margin + country.width + gap
    draw.rounded_rectangle((second_x + 12, header + 12, second_x + 175, header + 48), radius=8, fill=(248, 244, 232), outline=(72, 68, 61))
    draw.text((second_x + 32, header + 17), "春秋 Area", font=font(17, True), fill=(42, 40, 36))

    y = header + max(country.height, area.height) + 24
    area_totals = totals("area_name")
    card_gap = 12
    card_width = (width - margin * 2 - card_gap * 6) // 7
    for index, (name, color) in enumerate(AREA_COLORS.items()):
        x = margin + index * (card_width + card_gap)
        draw.rounded_rectangle((x, y, x + card_width, y + 105), radius=10, fill=(250, 247, 238), outline=(190, 181, 163))
        draw.rounded_rectangle((x + 12, y + 13, x + 38, y + 39), radius=5, fill=color)
        draw.text((x + 48, y + 10), f"{name} · {area_totals[name]}", font=font(17, True), fill=(42, 40, 36))
        members = "、".join(cell.name for cell in CELLS if cell.area_name == name)
        draw.text((x + 12, y + 50), members, font=font(12), fill=(78, 74, 66))
    polity_line = "　".join(f"{POLITY_NAMES[tag]} {value}" for tag, value in totals("polity").items())
    draw.text((margin, y + 127), "区内国家发展度：" + polity_line, font=font(15, True), fill=(55, 52, 47))
    draw.text((margin, y + 162), "边界方法：县级 GeoJSON 定方位；大明日不落、岁在甲子、风云世纪两千年只校准密度与边界节奏，不复制其省份像素。", font=font(14), fill=(86, 80, 70))
    canvas.save(output)


def color_for(province_id: int) -> tuple[int, int, int]:
    digest = hashlib.sha256(str(province_id).encode()).digest()
    return tuple(68 + byte % 145 for byte in digest[:3])


def reference_panel(title: str, root: Path) -> tuple[Image.Image, int]:
    id_to_rgb, rgb_to_id, names = definitions(root / "map")
    values = np.asarray(Image.open(root / "map/provinces.bmp").convert("RGB"), dtype=np.uint8)
    centers: list[tuple[float, float]] = []
    for province_id in (681, 2171, 2175):
        rgb = id_to_rgb.get(province_id)
        if rgb is None:
            continue
        ys, xs = np.where(np.all(values == np.asarray(rgb, dtype=np.uint8), axis=2))
        if len(xs):
            centers.append((float(xs.mean()), float(ys.mean())))
    if len(centers) != 3:
        raise ValueError(f"{title} lacks shared Jingxiang anchors")
    sx, sy = values.shape[1] / 5632, values.shape[0] / 2048
    left = max(0, round(min(x for x, _ in centers) - 45 * sx))
    right = min(values.shape[1], round(max(x for x, _ in centers) + 58 * sx))
    top = max(0, round(min(y for _, y in centers) - 38 * sy))
    bottom = min(values.shape[0], round(max(y for _, y in centers) + 58 * sy))
    crop = values[top:bottom, left:right]
    output = np.full(crop.shape, (204, 200, 189), dtype=np.uint8)
    province_ids: list[int] = []
    for rgb in np.unique(crop.reshape(-1, 3), axis=0):
        key = tuple(int(value) for value in rgb)
        province_id = rgb_to_id.get(key)
        if province_id is None:
            continue
        mask = np.all(crop == rgb, axis=2)
        if int(mask.sum()) < max(8, round(14 * sx * sy)):
            continue
        province_ids.append(province_id)
        output[mask] = color_for(province_id)
        output[border(mask)] = (247, 243, 230)
    image = Image.fromarray(output).resize((470, 330), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 12, 245, 48), radius=7, fill=(248, 244, 232), outline=(55, 53, 49))
    draw.text((24, 18), f"{title} · 约{len(set(province_ids))}块", font=font(16, True), fill=(36, 35, 32))
    return image, len(set(province_ids))


def planned_reference_panel(masks: dict[int, np.ndarray], box: tuple[int, int, int, int]) -> Image.Image:
    left, top, right, bottom = box
    shape = (bottom - top, right - left)
    output = np.full((*shape, 3), (204, 200, 189), dtype=np.uint8)
    for province_id, full_mask in masks.items():
        mask = full_mask[top:bottom, left:right]
        output[mask] = color_for(province_id)
        output[border(mask)] = (247, 243, 230)
    image = Image.fromarray(output).resize((470, 330), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 12, 264, 48), radius=7, fill=(248, 244, 232), outline=(55, 53, 49))
    draw.text((24, 18), "本案 B47 · 23省", font=font(16, True), fill=(36, 35, 32))
    return image


def compose_references(masks: dict[int, np.ndarray], box: tuple[int, int, int, int]) -> dict[str, int]:
    panels: list[tuple[str, Image.Image]] = []
    counts: dict[str, int] = {}
    for title, root in REFERENCES:
        panel, count = reference_panel(title, root)
        panels.append((title, panel))
        counts[title] = count
    panels.append(("B47", planned_reference_panel(masks, box)))
    width = 34 * 2 + 470 * 4 + 22 * 3
    canvas = Image.new("RGB", (width, 470), (244, 239, 228))
    draw = ImageDraw.Draw(canvas)
    draw.text((34, 18), "荆襄—豫南：三款参考模组与 B47 密度对照", font=font(29, True), fill=(36, 35, 32))
    draw.text((34, 58), "共同锚点裁图，仅比较块度、方向和边界节奏；参考块数含少量邻区，不作省份一一映射。", font=font(15), fill=(82, 78, 69))
    for index, (_, panel) in enumerate(panels):
        canvas.paste(panel, (34 + index * 492, 103))
    canvas.save(REFERENCE_PNG)
    return counts


def write_reviewed_bmp(current: np.ndarray, masks: dict[int, np.ndarray]) -> int:
    id_to_rgb, _, _ = definitions()
    reviewed = current.copy()
    for province_id, mask in masks.items():
        reviewed[mask] = NEW_RGB[province_id] if province_id in NEW_RGB else id_to_rgb[province_id]
    changed = int(np.count_nonzero(np.any(reviewed != current, axis=2)))
    Image.fromarray(reviewed, mode="RGB").save(REVIEWED_BMP, format="BMP")
    return changed


def main() -> None:
    if len(CELLS) != 23 or len([cell for cell in CELLS if cell.new]) != 10:
        raise ValueError("B47 preview must remain a 13-to-23 split")
    if sum(cell.development for cell in CELLS) != 133:
        raise ValueError("B47 preview development must remain 133")
    id_to_rgb, _, _ = definitions()
    if any(province_id in id_to_rgb for province_id in NEW_RGB):
        raise ValueError("A provisional B47 ID is already defined")
    collisions = {rgb: province_id for province_id, rgb in id_to_rgb.items() if rgb in set(NEW_RGB.values())}
    if collisions:
        raise ValueError(f"B47 RGB collision: {collisions}")

    current, masks, editable, box, metadata = build_cells()
    changed = write_reviewed_bmp(current, masks)
    country = render_map(masks, box, "polity")
    area = render_map(masks, box, "area")
    compose_review(country, area)
    reference_counts = compose_references(masks, box)

    editable_count = int(editable.sum())
    covered = np.zeros(editable.shape, dtype=bool)
    for mask in masks.values():
        covered |= mask
    exterior = int(np.count_nonzero(covered & ~editable))
    manifest = {
        "batch": "B47_jingxiang_yunan_geojson_preview",
        "status": "review_only_not_game_loaded",
        "canonical_map_modified": False,
        "parent_ids": list(PARENT_IDS),
        "provisional_new_ids": sorted(NEW_RGB),
        "max_provinces_if_applied": 5351,
        "new_rgb": {str(key): list(value) for key, value in NEW_RGB.items()},
        "editable_pixel_count": editable_count,
        "covered_pixel_count": int(covered.sum()),
        "changed_preview_pixels": changed,
        "changed_pixels_outside_editable_mask": exterior,
        "development_total": sum(cell.development for cell in CELLS),
        "connectivity_policy": {
            "jingyi_area": "strictly river-separated; gameplay-connected by existing 2172-5013 crossing through navigable river 5037",
            "other_areas": "strictly land-connected in the reviewed preview",
            "new_synthetic_crossings": 0,
        },
        "province_pixel_counts": {str(key): int(mask.sum()) for key, mask in masks.items()},
        "cells": [asdict(cell) for cell in CELLS],
        "geojson": {
            "sources": [HUBEI_URL, HENAN_URL],
            **metadata,
        },
        "workshop_density_references": reference_counts,
        "workshop_roots": {title: str(path) for title, path in REFERENCES},
        "outputs": [str(REVIEWED_BMP), str(REVIEW_PNG), str(REFERENCE_PNG)],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B47_PREVIEW PASS cells={len(CELLS)} new=10 dev=133 editable={editable_count} changed={changed} exterior={exterior}")
    print(REVIEW_PNG)
    print(REFERENCE_PNG)


if __name__ == "__main__":
    main()
