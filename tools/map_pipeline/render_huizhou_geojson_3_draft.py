#!/usr/bin/env python3
"""Render a review-only three-province split of Guangdong Huizhou (2157)."""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
OUT = ROOT / "planning/huizhou"
GEOJSON = ROOT / "planning/guangdong/440000_full.json"
PARENT_COLOUR = (65, 52, 224)  # 2157 Waichow / 惠州
UNITS = [
    ("惠州", (65, 52, 224), (4596, 1017), "府城、归善与东江下游"),
    ("河源", (41, 163, 188), (4603, 1005), "东江中游与河源盆地"),
    ("龙川", (202, 132, 60), (4612, 998), "龙川、和平与东北山口"),
]


def nearest(mask, x, y):
    if mask[y, x]:
        return x, y
    yy, xx = np.where(mask)
    i = np.argmin((xx - x) ** 2 + (yy - y) ** 2)
    return int(xx[i]), int(yy[i])


def geojson_centres():
    data = json.loads(GEOJSON.read_text())
    wanted = {"惠州市", "河源市"}
    return {
        feature["properties"]["name"]: feature["properties"]["center"]
        for feature in data["features"] if feature["properties"]["name"] in wanted
    }


def split_connected(mask):
    """Four-way geodesic growth produces three compact connected provinces."""
    owner = np.full(mask.shape, -1, dtype=np.int8)
    distance = np.full(mask.shape, 32767, dtype=np.int16)
    queue = deque()
    for label, (_name, _colour, seed, _note) in enumerate(UNITS):
        x, y = nearest(mask, *seed)
        owner[y, x] = label
        distance[y, x] = 0
        queue.append((x, y, label))
    while queue:
        x, y, label = queue.popleft()
        nd = int(distance[y, x]) + 1
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0]
                    and mask[ny, nx] and nd < distance[ny, nx]):
                distance[ny, nx] = nd
                owner[ny, nx] = label
                queue.append((nx, ny, label))
    return owner


def font(size):
    for candidate in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    current = np.asarray(Image.open(MOD / "map/provinces.bmp").convert("RGB"))
    parent = np.all(current == PARENT_COLOUR, axis=2)
    if int(parent.sum()) != 790:
        raise ValueError(f"Unexpected Huizhou parent size: {int(parent.sum())}")

    centres = geojson_centres()
    if set(centres) != {"惠州市", "河源市"}:
        raise ValueError("Guangdong GeoJSON lacks Huizhou or Heyuan")

    labels = split_connected(parent)
    draft = current.copy()
    for i, (_name, colour, _seed, _note) in enumerate(UNITS):
        draft[labels == i] = colour
    if not np.array_equal(draft[~parent], current[~parent]):
        raise ValueError("Draft changed pixels outside current Huizhou")
    Image.fromarray(draft).save(OUT / "huizhou_geojson_3_full_draft.bmp", format="BMP")

    yy, xx = np.where(parent)
    pad = 10
    x0, x1 = int(xx.min()) - pad, int(xx.max()) + pad + 1
    y0, y1 = int(yy.min()) - pad, int(yy.max()) + pad + 1
    crop = draft[y0:y1, x0:x1]
    Image.fromarray(crop).save(OUT / "huizhou_geojson_3_draft.bmp", format="BMP")
    scale = 12
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(OUT / "huizhou_geojson_3_raw.png")

    local_parent = parent[y0:y1, x0:x1]
    boundary = np.zeros(local_parent.shape, dtype=bool)
    boundary[1:] |= local_parent[1:] & np.any(crop[1:] != crop[:-1], axis=2)
    boundary[:, 1:] |= local_parent[:, 1:] & np.any(crop[:, 1:] != crop[:, :-1], axis=2)
    shown = np.asarray(raw).copy()
    shown[np.repeat(np.repeat(boundary, scale, axis=0), scale, axis=1)] = (32, 32, 32)
    map_image = Image.fromarray(shown)

    sidebar = 560
    canvas = Image.new("RGB", (map_image.width + sidebar, max(map_image.height, 650)), (248, 247, 243))
    canvas.paste(map_image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    lx = map_image.width + 25
    draw.text((lx, 22), "惠州三省 · GeoJSON引导草案", fill=(24, 24, 24), font=font(27))
    draw.text((lx, 62), "锁定现有惠州外框；东莞、香港、陆丰不动", fill=(75, 75, 75), font=font(15))
    for i, (name, colour, _seed, note) in enumerate(UNITS):
        ty = 118 + i * 105
        draw.rectangle((lx, ty + 3, lx + 28, ty + 31), fill=colour, outline=(35, 35, 35))
        size = int(np.count_nonzero(labels == i))
        draw.text((lx + 42, ty), f"{i + 1:02d} {name} · {size}像素", fill=(25, 25, 25), font=font(20))
        draw.text((lx + 42, ty + 38), note, fill=(75, 75, 75), font=font(15))
        py, px = np.where(labels == i)
        cx = int((np.median(px) - x0) * scale)
        cy = int((np.median(py) - y0) * scale)
        draw.text((cx, cy), str(i + 1), anchor="mm", fill=(10, 10, 10),
                  stroke_width=3, stroke_fill=(255, 255, 255), font=font(20))
    draw.text((lx, 460), "参考：现代惠州、河源 GeoJSON 城址与范围", fill=(75, 75, 75), font=font(15))
    draw.text((lx, 490), "龙川按东江上游与历史县治另拆", fill=(75, 75, 75), font=font(15))
    draw.text((lx, 540), "仅为预览，未写入正式 provinces.bmp", fill=(75, 75, 75), font=font(15))
    canvas.save(OUT / "huizhou_geojson_3_annotated.png")

    sizes = {name: int(np.count_nonzero(labels == i)) for i, (name, *_rest) in enumerate(UNITS)}
    print(f"HUIZHOU_DRAFT; OUTSIDE_CHANGED:0; SIZES:{sizes}; GEOJSON:{centres}")


if __name__ == "__main__":
    main()
