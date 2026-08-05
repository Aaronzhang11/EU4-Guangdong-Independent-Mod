#!/usr/bin/env python3
"""Render a review-only GeoJSON-guided Tianshui/Gongchang refinement."""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/longyou"
URL = "https://geo.datav.aliyun.com/areas_v3/bound/620000_full_district.json"

QINZHOU = 2180
GONGCHANG = 5291
QINGSHUI = 5305
TONGWEI = 5306

NEW_COLOURS = {
    QINGSHUI: (47, 187, 209),
    TONGWEI: (207, 109, 43),
}

TIANSHUI_NAMES = {
    "秦州区", "麦积区", "清水县", "秦安县", "甘谷县", "武山县", "张家川回族自治县"
}
QINGSHUI_NAMES = {"清水县", "张家川回族自治县"}
DINGXI_NAMES = {"安定区", "通渭县", "陇西县", "渭源县", "临洮县", "漳县", "岷县"}
TONGWEI_NAMES = {"安定区", "通渭县"}


def definitions(path: Path):
    result = {}
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 5 and fields[0].isdigit():
            result[int(fields[0])] = (tuple(map(int, fields[1:4])), fields[4])
    return result


def polygon_rings(geometry):
    coordinates = geometry["coordinates"]
    polygons = coordinates if geometry["type"] == "MultiPolygon" else [coordinates]
    for polygon in polygons:
        if polygon:
            yield polygon[0]


def projected_group(parent_mask, features, all_names, target_names):
    selected = [f for f in features if f["properties"].get("name") in all_names]
    if not selected:
        raise ValueError(f"GeoJSON lacks features for {sorted(all_names)}")
    coordinates = [point for feature in selected for ring in polygon_rings(feature["geometry"]) for point in ring]
    lon0 = min(point[0] for point in coordinates)
    lon1 = max(point[0] for point in coordinates)
    lat0 = min(point[1] for point in coordinates)
    lat1 = max(point[1] for point in coordinates)
    yy, xx = np.where(parent_mask)
    x0, x1, y0, y1 = int(xx.min()), int(xx.max()), int(yy.min()), int(yy.max())

    canvas = Image.new("1", (parent_mask.shape[1], parent_mask.shape[0]))
    draw = ImageDraw.Draw(canvas)
    for feature in selected:
        if feature["properties"].get("name") not in target_names:
            continue
        for ring in polygon_rings(feature["geometry"]):
            points = [
                (
                    x0 + (point[0] - lon0) / (lon1 - lon0) * max(1, x1 - x0),
                    y0 + (lat1 - point[1]) / (lat1 - lat0) * max(1, y1 - y0),
                )
                for point in ring
            ]
            draw.polygon(points, fill=1)
    return np.asarray(canvas, dtype=bool) & parent_mask


def components(mask):
    seen = np.zeros(mask.shape, dtype=bool)
    groups = []
    for sy, sx in zip(*np.where(mask)):
        if seen[sy, sx]:
            continue
        cells = []
        queue = deque([(int(sy), int(sx))])
        seen[sy, sx] = True
        while queue:
            y, x = queue.popleft()
            cells.append((y, x))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if (0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1]
                        and mask[ny, nx] and not seen[ny, nx]):
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        groups.append(cells)
    return sorted(groups, key=len, reverse=True)


def clean_partition(parent, new):
    new_groups = components(new)
    if not new_groups:
        raise ValueError("Projected GeoJSON produced an empty province")
    cleaned_new = np.zeros(parent.shape, dtype=bool)
    yy, xx = zip(*new_groups[0])
    cleaned_new[np.array(yy), np.array(xx)] = True
    old = parent & ~cleaned_new
    old_groups = components(old)
    if not old_groups:
        raise ValueError("Projected GeoJSON consumed the entire parent")
    cleaned_old = np.zeros(parent.shape, dtype=bool)
    yy, xx = zip(*old_groups[0])
    cleaned_old[np.array(yy), np.array(xx)] = True
    # Any tiny parent fragments belong to the new province.  A second pass
    # ensures both final provinces are single four-way components.
    cleaned_new = parent & ~cleaned_old
    new_groups = components(cleaned_new)
    if len(new_groups) != 1:
        keep = np.zeros(parent.shape, dtype=bool)
        yy, xx = zip(*new_groups[0])
        keep[np.array(yy), np.array(xx)] = True
        cleaned_new = keep
        cleaned_old = parent & ~cleaned_new
    return cleaned_old, cleaned_new


def font(size, bold=False):
    paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in paths:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size, index=1 if bold else 0)
            except OSError:
                return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def label_point(mask):
    yy, xx = np.where(mask)
    centre = np.array([yy.mean(), xx.mean()])
    points = np.column_stack((yy, xx))
    y, x = points[np.argmin(np.sum((points - centre) ** 2, axis=1))]
    return int(x), int(y)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    defs = definitions(MAP / "definition.csv")
    used_colours = {colour for colour, _ in defs.values()}
    for province_id, colour in NEW_COLOURS.items():
        if colour in used_colours:
            raise ValueError(f"RGB {colour} for {province_id} is already used")

    with urllib.request.urlopen(URL, timeout=30) as response:
        geojson = json.load(response)
    features = geojson["features"]
    selected_features = [
        feature for feature in features
        if feature["properties"].get("name") in (TIANSHUI_NAMES | DINGXI_NAMES)
    ]
    (OUT / "gansu_selected_counties_geojson.json").write_text(
        json.dumps({"type": "FeatureCollection", "features": selected_features}, ensure_ascii=False),
        encoding="utf-8",
    )

    source = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    qinzhou_mask = np.all(source == defs[QINZHOU][0], axis=2)
    gongchang_mask = np.all(source == defs[GONGCHANG][0], axis=2)
    qingshui_hint = projected_group(
        qinzhou_mask, features, TIANSHUI_NAMES, QINGSHUI_NAMES
    )
    tongwei_hint = projected_group(
        gongchang_mask, features, DINGXI_NAMES, TONGWEI_NAMES
    )
    qinzhou_keep, qingshui_mask = clean_partition(qinzhou_mask, qingshui_hint)
    gongchang_keep, tongwei_mask = clean_partition(gongchang_mask, tongwei_hint)

    draft = source.copy()
    draft[qingshui_mask] = NEW_COLOURS[QINGSHUI]
    draft[tongwei_mask] = NEW_COLOURS[TONGWEI]
    Image.fromarray(draft).save(
        OUT / "tianshui_gongchang_geojson_7_full_draft.bmp", format="BMP"
    )

    context_ids = [2180, 2181, 2183, 5276, 5277, 5278, 5289, 5290, 5291, 699, 5293, 5294]
    context = qingshui_mask | tongwei_mask
    for province_id in context_ids:
        context |= np.all(source == defs[province_id][0], axis=2)
    yy, xx = np.where(context)
    pad = 8
    x0, x1 = max(0, int(xx.min()) - pad), min(source.shape[1], int(xx.max()) + pad + 1)
    y0, y1 = max(0, int(yy.min()) - pad), min(source.shape[0], int(yy.max()) + pad + 1)
    crop = draft[y0:y1, x0:x1]
    Image.fromarray(crop).save(OUT / "tianshui_gongchang_geojson_7_draft.bmp", format="BMP")
    Image.fromarray(crop).resize(
        (crop.shape[1] * 7, crop.shape[0] * 7), Image.Resampling.NEAREST
    ).save(OUT / "tianshui_gongchang_geojson_7_raw.png")

    scale = 7
    map_image = Image.fromarray(crop).resize(
        (crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST
    )
    canvas = Image.new("RGB", (map_image.width + 510, max(map_image.height, 720)), (248, 246, 239))
    canvas.paste(map_image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    title = font(28, True)
    body = font(18)
    small = font(15)
    draw.text((map_image.width + 28, 22), "秦州—巩昌细化草案", fill=(28, 30, 31), font=title)
    draw.text((map_image.width + 28, 64), "GeoJSON引导；现有外边界锁定", fill=(76, 77, 75), font=small)

    label_masks = {
        1: ("秦州", qinzhou_keep),
        2: ("清水", qingshui_mask),
        3: ("秦安", np.all(source == defs[5276][0], axis=2)),
        4: ("巩昌", gongchang_keep),
        5: ("通渭", tongwei_mask),
    }
    for number, (name, mask) in label_masks.items():
        x, y = label_point(mask)
        px, py = (x - x0) * scale + 2, (y - y0) * scale + 2
        draw.ellipse((px - 13, py - 13, px + 13, py + 13), fill=(250, 250, 246), outline=(35, 35, 35), width=2)
        draw.text((px - 6, py - 12), str(number), fill=(20, 20, 20), font=body)
        draw.text((map_image.width + 32, 112 + number * 34), f"{number:02d}  {name}", fill=(35, 35, 35), font=body)

    draw.text((map_image.width + 28, 326), "新区域：陇右", fill=(50, 50, 50), font=body)
    draw.text((map_image.width + 28, 362), "清水 · 秦安 · 巩昌 · 通渭", fill=(50, 50, 50), font=small)
    draw.text((map_image.width + 28, 416), "区域调整", fill=(50, 50, 50), font=body)
    draw.text((map_image.width + 28, 452), "秦州、静宁归陇东；洮州、岷州、阶州留陇南", fill=(65, 65, 65), font=small)
    draw.text((map_image.width + 28, 510), "历史依据", fill=(50, 50, 50), font=body)
    draw.text((map_image.width + 28, 546), "明秦州领秦安、清水；巩昌府治陇西，辖通渭", fill=(65, 65, 65), font=small)
    draw.text((map_image.width + 28, 600), "仅预览：未写入正式 provinces.bmp", fill=(130, 45, 40), font=small)
    canvas.save(OUT / "tianshui_gongchang_geojson_7_annotated.png")

    report = {
        "formal_map_changed": False,
        "new_provinces": {
            str(QINGSHUI): {"name": "清水", "rgb": NEW_COLOURS[QINGSHUI], "pixels": int(qingshui_mask.sum())},
            str(TONGWEI): {"name": "通渭", "rgb": NEW_COLOURS[TONGWEI], "pixels": int(tongwei_mask.sum())},
        },
        "retained_pixels": {
            str(QINZHOU): int(qinzhou_keep.sum()),
            str(GONGCHANG): int(gongchang_keep.sum()),
        },
        "area_plan": {
            "longyou_area": [2181, 5276, 5278, 5305],
            "xi_shaanxi_area": [2180, 5277, 5291, 5306],
            "longnan_area": [2183, 5289, 5290],
        },
    }
    (OUT / "draft_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
