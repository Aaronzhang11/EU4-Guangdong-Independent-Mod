#!/usr/bin/env python3
"""Render Liaoning with a restrained mid-Qing Shengjing outer boundary."""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import render_liaoning_vanilla_geojson_12_draft as base


def block_ids(text: str, key: str):
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        return set()
    start = text.find("{", match.start())
    depth = 0
    for end in range(start, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                body = re.sub(r"#.*", "", text[start + 1:end])
                return {int(value) for value in re.findall(r"\b\d+\b", body)}
    raise ValueError(f"Unclosed block {key}")


def land_mask(vanilla):
    defs = base.definitions(base.VANILLA / "map/definition.csv")
    reverse = {colour: pid for pid, colour in defs.items()}
    text = (base.VANILLA / "map/default.map").read_text(encoding="latin-1")
    water = block_ids(text, "sea_starts") | block_ids(text, "lakes")
    packed = ((vanilla[:, :, 0].astype(np.uint32) << 16)
              | (vanilla[:, :, 1].astype(np.uint32) << 8)
              | vanilla[:, :, 2].astype(np.uint32))
    water_keys = np.array([(r << 16) | (g << 8) | b for colour, pid in reverse.items()
                           if pid in water for r, g, b in [colour]], dtype=np.uint32)
    return ~np.isin(packed, water_keys)


def qing_outline(vanilla, original):
    """Add the Shengjing paddock/Willow-Palisade shoulder without making a mega-region."""
    yy, xx = np.where(original)
    x0, x1, y0, y1 = xx.min(), xx.max(), yy.min(), yy.max()
    shape = Image.new("1", (original.shape[1], original.shape[0]), 0)
    draw = ImageDraw.Draw(shape)

    # The northern shoulder represents Kaiyuan-Changtu and the Shengjing paddock.
    draw.polygon([
        (x0 + 27, y0 + 10), (x0 + 31, y0 - 2), (x0 + 44, y0 - 10),
        (x0 + 61, y0 - 13), (x0 + 79, y0 - 9), (x1 + 6, y0 + 5),
        (x1 + 9, y0 + 24), (x1 + 5, y0 + 42), (x1 - 3, y0 + 48),
        (x1 - 10, y0 + 31), (x0 + 61, y0 + 9), (x0 + 42, y0 + 16),
    ], fill=1)

    # A modest north-western pasture bulge; the Liaoxi corridor itself stays fixed.
    draw.polygon([
        (x0 + 10, y0 + 24), (x0 + 7, y0 + 10), (x0 + 16, y0 + 1),
        (x0 + 31, y0 + 2), (x0 + 38, y0 + 15), (x0 + 30, y0 + 28),
    ], fill=1)

    historical = np.asarray(shape, dtype=bool)
    # "稍微参考" means a restrained shoulder, not annexing the whole polygon.
    # Limit the historical envelope to a four-pixel outward movement from the
    # vanilla border, preserving EU4's recognizable scale and coastline.
    source = Image.fromarray((original.astype(np.uint8) * 255), mode="L")
    dilated = np.asarray(source.filter(ImageFilter.MaxFilter(9))) > 0
    extension = historical & dilated & land_mask(vanilla)
    return original | extension


def main():
    base.OUT.mkdir(parents=True, exist_ok=True)
    current = np.asarray(Image.open(base.CURRENT_MAP).convert("RGB"))
    vanilla = np.asarray(Image.open(base.VANILLA / "map/provinces.bmp").convert("RGB"))
    vanilla_defs = base.definitions(base.VANILLA / "map/definition.csv")
    original = base.packed_mask(vanilla, [vanilla_defs[i] for i in base.VANILLA_IDS])
    region = qing_outline(vanilla, original)
    yy, xx = np.where(region)
    x0, x1, y0, y1 = xx.min(), xx.max(), yy.min(), yy.max()

    # Keep the modern projection tied to the original EU4 Liaoning box, so only
    # the outer historical shoulder changes and the reviewed internal layout stays stable.
    oy, ox = np.where(original)
    original_box = (ox.min(), oy.min(), ox.max(), oy.max())
    features = base.load_features()
    geo_box = base.bounds(features)
    seeds = []
    for province in base.PROVINCES:
        name, lon, lat, *rest = province
        x, y = base.snap(region, *base.project(lon, lat, geo_box, original_box))
        seeds.append((name, x, y, *rest))
    colours = base.palette(len(base.PROVINCES))

    # Preserve every internal pixel from the accepted GeoJSON draft. Only grow
    # its edge colours into the newly added Qing shoulder.
    reviewed = np.asarray(Image.open(base.OUT / "liaoning_vanilla_geojson_12_full_draft.bmp").convert("RGB"))
    draft = current.copy()
    draft[original] = reviewed[original]
    assigned = original.copy()
    queue = deque((int(x), int(y)) for y, x in zip(*np.where(original)))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < region.shape[1] and 0 <= ny < region.shape[0]
                    and region[ny, nx] and not assigned[ny, nx]):
                draft[ny, nx] = draft[y, x]
                assigned[ny, nx] = True
                queue.append((nx, ny))
    if np.any(region & ~assigned):
        raise ValueError("Qing boundary extension is not connected to vanilla Liaoning")
    assert np.array_equal(draft[original], reviewed[original])
    assert np.array_equal(draft[~region], current[~region])
    Image.fromarray(draft).save(base.OUT / "liaoning_qing_outer_geojson_12_full_draft.bmp", format="BMP")

    pad = 7
    cx0, cy0 = max(0, x0 - pad), max(0, y0 - pad)
    cx1, cy1 = min(current.shape[1] - 1, x1 + pad), min(current.shape[0] - 1, y1 + pad)
    crop = draft[cy0:cy1 + 1, cx0:cx1 + 1]
    Image.fromarray(crop).save(base.OUT / "liaoning_qing_outer_geojson_12_draft.bmp", format="BMP")
    scale = 8
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(base.OUT / "liaoning_qing_outer_geojson_12_raw.png")

    local_region = region[cy0:cy1 + 1, cx0:cx1 + 1]
    boundary = np.zeros(local_region.shape, dtype=bool)
    boundary[1:] |= local_region[1:] & np.any(crop[1:] != crop[:-1], axis=2)
    boundary[:, 1:] |= local_region[:, 1:] & np.any(crop[:, 1:] != crop[:, :-1], axis=2)
    shown = np.asarray(raw).copy()
    shown[np.repeat(np.repeat(boundary, scale, 0), scale, 1)] = (35, 35, 35)
    map_img = Image.fromarray(shown)

    sidebar = 600
    canvas = Image.new("RGB", (map_img.width + sidebar, max(map_img.height, 850)), (248, 247, 243))
    canvas.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    title, body, small = base.font(29, True), base.font(19), base.font(15)
    lx = map_img.width + 24
    draw.text((lx, 20), "辽宁十二省 · 清代盛京外界草案", fill=(22, 22, 22), font=title)
    draw.text((lx, 60), "内部方案不变；北界参考柳条边与盛京围场折中线", fill=(75, 75, 75), font=small)

    total = [0, 0, 0]
    for i, ((name, sx, sy, area, goods, dev, cot), colour) in enumerate(zip(seeds, colours)):
        px, py = (sx - cx0) * scale, (sy - cy0) * scale
        draw.text((px, py), str(i + 1), fill=(15, 15, 15), stroke_width=3,
                  stroke_fill=(255, 255, 255), font=body, anchor="mm")
        col, row = i // 6, i % 6
        tx, ty = lx + col * 285, 105 + row * 55
        draw.rectangle((tx, ty + 4, tx + 22, ty + 26), fill=colour, outline=(40, 40, 40))
        cot_text = f" · 贸{cot}" if cot else ""
        draw.text((tx + 31, ty), f"{i + 1:02d} {name} · {area}", fill=(25, 25, 25), font=body)
        draw.text((tx + 31, ty + 26), f"{dev[0]}/{dev[1]}/{dev[2]}  {base.GOODS_CN[goods]}{cot_text}",
                  fill=(80, 80, 80), font=small)
        total = [a + b for a, b in zip(total, dev)]

    added = int(np.count_nonzero(region & ~original))
    y = 470
    draw.text((lx, y), f"盛京外界扩展：+{added}像素；十二省均保留", fill=(30, 30, 30), font=body)
    draw.text((lx, y + 38), "北：开原—昌图肩部；东北：盛京围场西缘", fill=(60, 60, 60), font=small)
    draw.text((lx, y + 68), "西：辽西走廊不变；东南：鸭绿江与海岸不动", fill=(60, 60, 60), font=small)
    draw.text((lx, y + 108), "这是中期清代折中方案，不采用晚清奉天省直线", fill=(60, 60, 60), font=small)
    draw.text((lx, y + 148), "仅为预览，未写入正式 provinces.bmp", fill=(60, 60, 60), font=small)
    canvas.save(base.OUT / "liaoning_qing_outer_geojson_12_annotated.png")
    print(f"LIAONING_QING_OUTER; ORIGINAL:{int(original.sum())}; ADDED:{added}; TOTAL:{int(region.sum())}")


if __name__ == "__main__":
    main()
