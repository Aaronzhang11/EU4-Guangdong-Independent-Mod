#!/usr/bin/env python3
"""Render a review-only 12-province Liaoning draft inside the vanilla EU4 outline."""

from __future__ import annotations

import colorsys
import heapq
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
CURRENT_MAP = MOD / "map/provinces.bmp"
VANILLA = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "common/Europa Universalis IV"
)
OUT = ROOT / "planning/liaoning"
GEO_DIR = OUT / "geojson_cities"
VANILLA_IDS = [704, 726, 2112, 2113, 4652]

# Historical seat, longitude/latitude, area, vanilla trade good, development, CoT.
PROVINCES = [
    ("宁远", 120.73, 40.62, "辽西", "salt", (2, 2, 2), 0),
    ("锦州", 121.13, 41.10, "辽西", "salt", (3, 3, 3), 0),
    ("义州", 121.24, 41.54, "辽西", "grain", (2, 2, 3), 0),
    ("广宁", 121.80, 41.60, "辽西", "livestock", (4, 3, 3), 1),
    ("沈阳", 123.43, 41.80, "辽中", "cloth", (4, 4, 3), 0),
    ("铁岭", 123.84, 42.29, "辽中", "livestock", (2, 3, 3), 0),
    ("辽阳", 123.18, 41.27, "辽中", "iron", (5, 5, 4), 2),
    ("海州", 122.75, 40.85, "辽中", "grain", (3, 3, 2), 0),
    ("盖州", 122.35, 40.40, "辽南", "fish", (3, 3, 3), 1),
    ("复州", 121.98, 39.63, "辽南", "fish", (2, 3, 2), 0),
    ("金州", 121.72, 39.10, "辽南", "naval_supplies", (3, 3, 2), 1),
    ("九连城", 124.39, 40.13, "辽东", "fur", (2, 2, 3), 0),
]
GOODS_CN = {
    "salt": "盐", "grain": "谷物", "livestock": "牲畜", "cloth": "布匹",
    "iron": "铁矿", "fish": "鱼类", "naval_supplies": "船材", "fur": "毛皮",
}


def definitions(path: Path):
    result = {}
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 5 and fields[0].isdigit():
            result[int(fields[0])] = tuple(map(int, fields[1:4]))
    return result


def packed_mask(bitmap, colours):
    packed = ((bitmap[:, :, 0].astype(np.uint32) << 16)
              | (bitmap[:, :, 1].astype(np.uint32) << 8)
              | bitmap[:, :, 2].astype(np.uint32))
    keys = np.array([(r << 16) | (g << 8) | b for r, g, b in colours], dtype=np.uint32)
    return np.isin(packed, keys)


def rings(geometry):
    if geometry["type"] == "Polygon":
        yield from geometry["coordinates"]
    else:
        for polygon in geometry["coordinates"]:
            yield from polygon


def load_features():
    features = []
    for path in sorted(GEO_DIR.glob("*_full.json")):
        features.extend(json.loads(path.read_text())["features"])
    return features


def bounds(features):
    points = [p for feature in features for ring in rings(feature["geometry"]) for p in ring]
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def project(lon, lat, geo_box, pixel_box):
    min_lon, min_lat, max_lon, max_lat = geo_box
    x0, y0, x1, y1 = pixel_box
    x = x0 + (lon - min_lon) / (max_lon - min_lon) * (x1 - x0)
    y = y0 + (max_lat - lat) / (max_lat - min_lat) * (y1 - y0)
    return int(round(x)), int(round(y))


def snap(mask, x, y):
    if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] and mask[y, x]:
        return x, y
    yy, xx = np.where(mask)
    pos = np.argmin((xx - x) ** 2 + (yy - y) ** 2)
    return int(xx[pos]), int(yy[pos])


def raster_guide(features, geo_box, pixel_box, mask):
    image = Image.new("I", (mask.shape[1], mask.shape[0]), 0)
    draw = ImageDraw.Draw(image)
    for zone, feature in enumerate(features, start=1):
        for ring in rings(feature["geometry"]):
            polygon = [project(p[0], p[1], geo_box, pixel_box) for p in ring]
            if len(polygon) >= 3:
                draw.polygon(polygon, fill=zone)
    guide = np.asarray(image).copy()
    guide[~mask] = -1
    return guide


def raster_barriers(geo_box, pixel_box, mask):
    """Soft guides for the Liao River and the two major mountain belts."""
    image = Image.new("1", (mask.shape[1], mask.shape[0]), 0)
    draw = ImageDraw.Draw(image)
    lines = [
        # Lower Liao River.
        [(123.35, 42.45), (123.25, 41.95), (123.05, 41.45), (122.85, 40.95), (122.35, 40.65)],
        # Yiwulü Mountains, separating the Liaoxi corridor from the central plain.
        [(121.95, 42.35), (121.85, 41.90), (121.72, 41.45), (121.65, 41.05)],
        # Liaodong uplands, used only as a gentle internal guide.
        [(124.15, 42.05), (123.90, 41.55), (123.65, 41.05), (123.45, 40.55)],
    ]
    for line in lines:
        draw.line([project(lon, lat, geo_box, pixel_box) for lon, lat in line], fill=1, width=1)
    barrier = np.asarray(image, dtype=bool).copy()
    barrier[~mask] = False
    return barrier


def partition(mask, guide, barrier, seeds):
    owner = np.full(mask.shape, -1, dtype=np.int16)
    distance = np.full(mask.shape, np.inf)
    queue = []
    # Small bonuses keep major historical centres from becoming tiny Voronoi cells.
    bonuses = {"辽阳": 42, "沈阳": 28, "义州": 35, "广宁": 20,
               "锦州": 12, "盖州": 10, "金州": 20}
    for i, (name, x, y, *_rest) in enumerate(seeds):
        start = -bonuses.get(name, 0)
        owner[y, x] = i
        distance[y, x] = start
        heapq.heappush(queue, (start, i, x, y))
    moves = [(-1, 0, 10), (1, 0, 10), (0, -1, 10), (0, 1, 10),
             (-1, -1, 14), (-1, 1, 14), (1, -1, 14), (1, 1, 14)]
    while queue:
        cost, source, x, y = heapq.heappop(queue)
        if cost != distance[y, x] or owner[y, x] != source:
            continue
        for dx, dy, step in moves:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0] and mask[ny, nx]):
                continue
            county_cross = guide[y, x] > 0 and guide[ny, nx] > 0 and guide[y, x] != guide[ny, nx]
            ridge_cross = barrier[y, x] != barrier[ny, nx] and (barrier[y, x] or barrier[ny, nx])
            new = cost + step + (34 if county_cross else 0) + (20 if ridge_cross else 0)
            if new < distance[ny, nx]:
                distance[ny, nx] = new
                owner[ny, nx] = source
                heapq.heappush(queue, (new, source, nx, ny))
    return owner


def palette(count):
    used = set(definitions(MOD / "map/definition.csv").values())
    result, i = [], 0
    while len(result) < count:
        hue = (0.03 + i * 0.61803398875) % 1.0
        sat = 0.52 + 0.08 * (i % 3)
        val = 0.72 + 0.07 * (i % 2)
        colour = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(hue, sat, val))
        if colour not in used and colour not in result:
            result.append(colour)
        i += 1
    return result


def font(size, bold=False):
    candidates = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    current = np.asarray(Image.open(CURRENT_MAP).convert("RGB"))
    vanilla = np.asarray(Image.open(VANILLA / "map/provinces.bmp").convert("RGB"))
    vanilla_defs = definitions(VANILLA / "map/definition.csv")
    region = packed_mask(vanilla, [vanilla_defs[i] for i in VANILLA_IDS])
    y0, x0 = np.min(np.argwhere(region), axis=0)
    y1, x1 = np.max(np.argwhere(region), axis=0)

    features = load_features()
    geo_box = bounds(features)
    pixel_box = (x0, y0, x1, y1)
    seeds = []
    for province in PROVINCES:
        name, lon, lat, *rest = province
        x, y = snap(region, *project(lon, lat, geo_box, pixel_box))
        seeds.append((name, x, y, *rest))
    guide = raster_guide(features, geo_box, pixel_box, region)
    barrier = raster_barriers(geo_box, pixel_box, region)
    owner = partition(region, guide, barrier, seeds)
    colours = palette(len(PROVINCES))

    draft = current.copy()
    for i, colour in enumerate(colours):
        draft[owner == i] = colour
    assert np.array_equal(draft[~region], current[~region])
    Image.fromarray(draft).save(OUT / "liaoning_vanilla_geojson_12_full_draft.bmp", format="BMP")

    pad = 7
    cx0, cy0 = max(0, x0 - pad), max(0, y0 - pad)
    cx1, cy1 = min(current.shape[1] - 1, x1 + pad), min(current.shape[0] - 1, y1 + pad)
    crop = draft[cy0:cy1 + 1, cx0:cx1 + 1]
    Image.fromarray(crop).save(OUT / "liaoning_vanilla_geojson_12_draft.bmp", format="BMP")
    scale = 9
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(OUT / "liaoning_vanilla_geojson_12_raw.png")

    local_region = region[cy0:cy1 + 1, cx0:cx1 + 1]
    boundary = np.zeros(local_region.shape, dtype=bool)
    boundary[1:] |= local_region[1:] & np.any(crop[1:] != crop[:-1], axis=2)
    boundary[:, 1:] |= local_region[:, 1:] & np.any(crop[:, 1:] != crop[:, :-1], axis=2)
    shown = np.asarray(raw).copy()
    shown[np.repeat(np.repeat(boundary, scale, 0), scale, 1)] = (35, 35, 35)
    map_img = Image.fromarray(shown)

    sidebar = 590
    canvas = Image.new("RGB", (map_img.width + sidebar, max(map_img.height, 850)), (248, 247, 243))
    canvas.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    title, body, small = font(29, True), font(19), font(15)
    lx = map_img.width + 24
    draw.text((lx, 20), "辽宁十二省 · 原版外框 GeoJSON 草案", fill=(22, 22, 22), font=title)
    draw.text((lx, 60), "原版外边界锁定；县界、辽河与山地共同引导", fill=(75, 75, 75), font=small)

    total = [0, 0, 0]
    for i, ((name, sx, sy, area, goods, dev, cot), colour) in enumerate(zip(seeds, colours)):
        px, py = (sx - cx0) * scale, (sy - cy0) * scale
        draw.text((px, py), str(i + 1), fill=(15, 15, 15), stroke_width=3,
                  stroke_fill=(255, 255, 255), font=body, anchor="mm")
        col, row = i // 6, i % 6
        tx, ty = lx + col * 280, 105 + row * 55
        draw.rectangle((tx, ty + 4, tx + 22, ty + 26), fill=colour, outline=(40, 40, 40))
        cot_text = f" · 贸{cot}" if cot else ""
        draw.text((tx + 31, ty), f"{i + 1:02d} {name} · {area}", fill=(25, 25, 25), font=body)
        draw.text((tx + 31, ty + 26), f"{dev[0]}/{dev[1]}/{dev[2]}  {GOODS_CN[goods]}{cot_text}",
                  fill=(80, 80, 80), font=small)
        total = [a + b for a, b in zip(total, dev)]

    y = 470
    draw.text((lx, y), f"总发展度 {sum(total)}：税{total[0]}／产{total[1]}／兵{total[2]}", fill=(30, 30, 30), font=body)
    draw.text((lx, y + 38), "贸易中心：辽阳Ⅱ、广宁Ⅰ、盖州Ⅰ、金州Ⅰ", fill=(30, 30, 30), font=body)
    draw.text((lx, y + 78), "辽西：宁远、锦州、义州、广宁", fill=(65, 65, 65), font=small)
    draw.text((lx, y + 106), "辽中：沈阳、铁岭、辽阳、海州", fill=(65, 65, 65), font=small)
    draw.text((lx, y + 134), "辽南：盖州、复州、金州；辽东：九连城", fill=(65, 65, 65), font=small)
    draw.text((lx, y + 180), "辽宁外部边界改动：0像素", fill=(65, 65, 65), font=small)
    draw.text((lx, y + 208), "仅为预览，未写入正式 provinces.bmp", fill=(65, 65, 65), font=small)
    canvas.save(OUT / "liaoning_vanilla_geojson_12_annotated.png")

    sizes = [int(np.count_nonzero(owner == i)) for i in range(len(PROVINCES))]
    print(f"LIAONING_VANILLA_GEOJSON; PROVINCES:12; PIXELS:{int(region.sum())}; DEV:{sum(total)}; OUTSIDE:0")
    print("SIZES", dict(zip((p[0] for p in PROVINCES), sizes)))


if __name__ == "__main__":
    main()
