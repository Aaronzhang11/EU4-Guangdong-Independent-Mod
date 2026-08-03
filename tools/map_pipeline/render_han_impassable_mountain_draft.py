#!/usr/bin/env python3
"""Render a non-destructive Han-region impassable-mountain candidate bitmap."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/han_mountains"
FULL_BMP = OUT / "han_impassable_mountains_candidate_full_draft.bmp"
CROP_BMP = OUT / "han_impassable_mountains_candidate_crop.bmp"
ANNOTATED = OUT / "han_impassable_mountains_candidate_annotated.png"
CROP = (4300, 650, 4780, 1060)

# Broken segments intentionally preserve major historical passes. Coordinates
# are on the formal 5632x2048 EU4 bitmap and only serve this review draft.
CANDIDATES = (
    ("燕山", (176, 176, 184), 8, (((4598, 716), (4618, 708), (4627, 708)),
                                   ((4636, 710), (4650, 715), (4665, 723)))),
    ("大别山", (134, 139, 150), 7, (((4582, 867), (4594, 871), (4603, 873)),
                                     ((4611, 876), (4621, 880), (4630, 884)))),
    ("巫山", (91, 94, 108), 7, (((4482, 894), (4489, 901), (4494, 906)),
                                 ((4499, 911), (4505, 918), (4510, 922)))),
    ("武陵—雪峰山", (113, 103, 123), 8,
     (((4494, 918), (4503, 927), (4511, 936)),
      ((4517, 943), (4524, 951), (4530, 958)),
      ((4535, 964), (4540, 971), (4544, 978)))),
    ("武夷山", (128, 111, 94), 7, (((4647, 922), (4650, 935), (4650, 944)),
                                    ((4648, 952), (4643, 966), (4636, 980)))),
    ("南岭", (157, 128, 91), 8, (((4519, 986), (4532, 989), (4542, 990)),
                                  ((4549, 991), (4560, 993), (4570, 993)),
                                  ((4578, 993), (4589, 992), (4599, 990)),
                                  ((4607, 988), (4617, 985), (4626, 981)))),
    ("罗霄山（可选）", (202, 148, 73), 6,
     (((4587, 924), (4589, 935), (4591, 945)),
      ((4594, 952), (4596, 962), (4597, 972)))),
)

EXISTING_IDS = (5029, 5175, 5176, 5183, 5187, 5257, 5258, 5259, 5260, 5261, 5304)


def brace_block(text: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"Missing block {name}")
    start = text.index("{", match.start())
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:index]
    raise ValueError(f"Unclosed block {name}")


def definitions() -> dict[int, tuple[int, int, int]]:
    result = {}
    with (MAP / "definition.csv").open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[int(row[0])] = tuple(map(int, row[1:4]))
    return result


def line_mask(size: tuple[int, int], segments, width: int) -> np.ndarray:
    layer = Image.new("1", size, 0)
    draw = ImageDraw.Draw(layer)
    for segment in segments:
        draw.line(segment, fill=1, width=width, joint="curve")
    return np.asarray(layer, dtype=bool)


def render() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    result = base.copy()
    defs = definitions()

    default = (MAP / "default.map").read_text(encoding="cp1252")
    sea_body = re.sub(r"#.*", "", brace_block(default, "sea_starts"))
    sea_ids = [int(value) for value in re.findall(r"\b\d+\b", sea_body)]
    sea_colors = {defs[province_id] for province_id in sea_ids if province_id in defs}

    for _, color, width, segments in CANDIDATES:
        mask = line_mask((base.shape[1], base.shape[0]), segments, width)
        yy, xx = np.nonzero(mask)
        for y, x in zip(yy, xx):
            if tuple(base[y, x]) in sea_colors:
                mask[y, x] = False
        result[mask] = color

    Image.fromarray(result).save(FULL_BMP, format="BMP")
    crop = Image.fromarray(result).crop(CROP)
    crop.save(CROP_BMP, format="BMP")

    display = np.asarray(crop).copy()
    x0, y0, _, _ = CROP
    existing_colors = [defs[province_id] for province_id in EXISTING_IDS if province_id in defs]
    for color in existing_colors:
        display[np.all(display == color, axis=2)] = (66, 68, 72)

    scale = 2
    map_image = Image.fromarray(display).resize(
        (display.shape[1] * scale, display.shape[0] * scale), Image.Resampling.NEAREST
    )
    canvas = Image.new("RGB", (map_image.width + 520, max(map_image.height, 900)), (244, 242, 236))
    canvas.paste(map_image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 15)
    label = ImageFont.truetype(font_path, 16)
    panel_x = map_image.width + 24
    draw.text((panel_x, 24), "汉地战略山脉候选", font=title, fill=(32, 34, 36))
    draw.text((panel_x, 68), "灰黑：已经实装；彩灰：建议新增", font=small, fill=(75, 76, 78))
    draw.text((panel_x, 93), "橙色：可选，容易造成过度分割", font=small, fill=(75, 76, 78))

    y = 142
    notes = {
        "燕山": "强化华北北缘，保留古北口等通道",
        "大别山": "分隔淮西、鄂东与豫南，保留三条山口",
        "巫山": "强化三峡东口，不封死长江航路",
        "武陵—雪峰山": "限制湘西直穿，保留沅水与辰州通道",
        "武夷山": "分隔赣闽，保留铅山、杉关等通道",
        "南岭": "形成岭南北墙，保留桂湘、韶关、梅关通道",
        "罗霄山（可选）": "可强化湘赣边界，但不建议整段封死",
    }
    for index, (name, color, _, segments) in enumerate(CANDIDATES, 1):
        draw.rectangle((panel_x, y + 4, panel_x + 24, y + 28), fill=color, outline=(45, 45, 45))
        draw.text((panel_x + 36, y), f"{index}. {name}", font=body, fill=(35, 36, 38))
        draw.text((panel_x + 36, y + 28), notes[name], font=small, fill=(70, 71, 73))
        first = segments[0][0]
        mx = int((first[0] - x0) * scale)
        my = int((first[1] - y0) * scale)
        draw.ellipse((mx - 14, my - 14, mx + 14, my + 14), fill=(242, 239, 228), outline=(35, 35, 35), width=2)
        text = str(index)
        box = draw.textbbox((0, 0), text, font=label)
        draw.text((mx - (box[2] - box[0]) / 2, my - (box[3] - box[1]) / 2 - 2), text,
                  font=label, fill=(25, 25, 25))
        y += 78
    draw.text((panel_x, y + 8), "断开的山带代表预留山口，并非绘制遗漏。", font=small, fill=(60, 61, 63))
    draw.text((panel_x, y + 36), "本图只用于选址，不可直接作为游戏地图。", font=small, fill=(60, 61, 63))
    canvas.save(ANNOTATED)

    print(FULL_BMP)
    print(CROP_BMP)
    print(ANNOTATED)


if __name__ == "__main__":
    render()
