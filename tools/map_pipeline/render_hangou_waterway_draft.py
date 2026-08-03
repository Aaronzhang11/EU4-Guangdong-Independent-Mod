#!/usr/bin/env python3
"""Render a four-segment Hangou waterway preview on the current bitmap."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "guangdong_independent_practice/map/provinces.bmp"
OUT = ROOT / "planning/hangou"

SEGMENTS = [
    ("邗沟", (29, 106, 158), [
        (4659, 843), (4660, 844), (4661, 845), (4662, 846),
        (4663, 846), (4664, 848), (4665, 850), (4666, 852),
        (4666, 853), (4666, 855), (4667, 857),
        (4667, 858), (4667, 860), (4667, 861),
    ]),
]

CROP = (4638, 818, 4692, 883)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGB")
    draft = source.copy()
    for _, colour, points in SEGMENTS:
        layer = Image.new("1", source.size, 0)
        ImageDraw.Draw(layer).line(points, fill=1, width=2)
        draft.paste(colour, mask=layer)

    draft.save(OUT / "hangou_single_full_draft.bmp")
    crop = draft.crop(CROP)
    crop.save(OUT / "hangou_single_draft.bmp")
    scale = 12
    raw = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)
    raw.save(OUT / "hangou_single_raw.png")

    # Add black outlines only around the proposed waterway and number each reach.
    local = np.asarray(crop)
    route_colours = {colour for _, colour, _ in SEGMENTS}
    route = np.zeros(local.shape[:2], dtype=bool)
    for colour in route_colours:
        route |= np.all(local == colour, axis=2)
    boundary = np.zeros(route.shape, dtype=bool)
    boundary[1:] |= route[1:] & ~route[:-1]
    boundary[:-1] |= route[:-1] & ~route[1:]
    boundary[:, 1:] |= route[:, 1:] & ~route[:, :-1]
    boundary[:, :-1] |= route[:, :-1] & ~route[:, 1:]
    shown = np.asarray(raw).copy()
    shown[np.repeat(np.repeat(boundary, scale, 0), scale, 1)] = (25, 25, 25)
    map_img = Image.fromarray(shown)

    canvas = Image.new("RGB", (map_img.width + 430, max(map_img.height, 780)), "white")
    canvas.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 22)
    small = ImageFont.truetype(font_path, 17)
    number = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 18)
    lx = map_img.width + 24
    draw.text((lx, 24), "邗沟可航水道草案", fill=(20, 20, 20), font=title)
    draw.text((lx, 66), "洪泽湖—高邮—扬州—长江下游", fill=(75, 75, 75), font=small)
    for i, (name, colour, points) in enumerate(SEGMENTS, start=1):
        ty = 120 + (i - 1) * 62
        draw.rectangle((lx, ty + 3, lx + 31, ty + 34), fill=colour, outline=(30, 30, 30))
        draw.text((lx + 45, ty), f"{i:02d}  {name}", fill=(20, 20, 20), font=body)
        px = (points[len(points) // 2][0] - CROP[0]) * scale
        py = (points[len(points) // 2][1] - CROP[1]) * scale
        draw.text((px, py), str(i), fill="black", font=number, stroke_width=3, stroke_fill="white")
    draw.text((lx, 405), "既有水面", fill=(35, 35, 35), font=body)
    draw.text((lx, 448), "洪泽湖：1896", fill=(75, 75, 75), font=small)
    draw.text((lx, 477), "长江下游：5033", fill=(75, 75, 75), font=small)
    draw.text((lx, 530), "沿岸节点", fill=(35, 35, 35), font=body)
    draw.text((lx, 573), "高邮：5021　扬州：685", fill=(75, 75, 75), font=small)
    draw.text((lx, 635), "未写入正式 provinces.bmp", fill=(75, 75, 75), font=small)
    canvas.save(OUT / "hangou_single_annotated.png")
    print("HANGOU_DRAFT:1")


if __name__ == "__main__":
    main()
