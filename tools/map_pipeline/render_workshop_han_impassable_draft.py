#!/usr/bin/env python3
"""Overlay the 1728520255 workshop mod's exact Han mountain geometry as a draft."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
SOURCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
OUT = ROOT / "planning/han_mountains/workshop_transplant"
SOURCE_X_OFFSET = 438
SOURCE_Y_OFFSET = 9
CROP = (4300, 680, 4730, 1060)

NAMES = {
    5146: "中央山脉", 5147: "大凉山", 5152: "泰山", 5154: "天目山",
    5155: "仙霞岭", 5156: "浙闽丘陵", 5157: "杉岭", 5158: "武夷山",
    5159: "幕阜山", 5160: "九岭山", 5161: "罗霄山", 5162: "万洋山",
    5163: "大庾岭", 5164: "九连山", 5165: "雪峰山", 5166: "萌渚岭",
    5167: "十万大山", 5168: "哀牢山", 5169: "苗岭", 5170: "越城岭",
    5171: "大娄山", 5172: "巫山", 5173: "桐柏山", 5174: "大洪山",
    5175: "大巴山", 5176: "岷山", 5177: "恒山", 5178: "太行山北段",
    5179: "太行山南段", 5180: "中条山", 5181: "吕梁山", 5182: "伏牛山",
    5183: "秦岭", 5187: "陇山", 5237: "大别山",
}

GROUPS = {
    "北方山系": (5177, 5178, 5179, 5180, 5181, 5182, 5183, 5187),
    "长江中游": (5159, 5160, 5173, 5174, 5237),
    "东南山系": (5154, 5155, 5156, 5157, 5158, 5161, 5162, 5163, 5164),
    "西南山系": (5147, 5165, 5166, 5167, 5168, 5169, 5170, 5171, 5172, 5175, 5176),
    "山东与台湾": (5152, 5146),
}

GROUP_COLORS = {
    "北方山系": (65, 67, 72),
    "长江中游": (91, 93, 99),
    "东南山系": (121, 112, 101),
    "西南山系": (103, 93, 111),
    "山东与台湾": (126, 126, 132),
}


def definitions(path: Path) -> dict[int, tuple[int, int, int]]:
    result = {}
    with path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[int(row[0])] = tuple(map(int, row[1:4]))
    return result


def mask_for(values: np.ndarray, colors) -> np.ndarray:
    packed = (
        (values[:, :, 0].astype(np.uint32) << 16)
        | (values[:, :, 1].astype(np.uint32) << 8)
        | values[:, :, 2].astype(np.uint32)
    )
    keys = np.array(
        [(red << 16) | (green << 8) | blue for red, green, blue in colors],
        dtype=np.uint32,
    )
    return np.isin(packed, keys)


def render() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    target = np.asarray(Image.open(MOD / "map/provinces.bmp").convert("RGB"))
    source = np.asarray(Image.open(SOURCE / "map/provinces.bmp").convert("RGB"))
    source_defs = definitions(SOURCE / "map/definition.csv")
    translated = source[
        SOURCE_Y_OFFSET:SOURCE_Y_OFFSET + target.shape[0],
        SOURCE_X_OFFSET:SOURCE_X_OFFSET + target.shape[1],
    ]
    if translated.shape != target.shape:
        raise ValueError(f"Translated workshop map is {translated.shape}, expected {target.shape}")

    selected_ids = tuple(NAMES)
    selected_colors = [source_defs[province_id] for province_id in selected_ids]
    selected = mask_for(translated, selected_colors)

    # Full draft copies the source pixels verbatim. This is review geometry, not
    # a playable map: target IDs and definitions are deliberately not changed.
    full = target.copy()
    full[selected] = translated[selected]
    full_path = OUT / "workshop_han_mountains_full_draft.bmp"
    Image.fromarray(full).save(full_path, format="BMP")
    crop_path = OUT / "workshop_han_mountains_crop_draft.bmp"
    Image.fromarray(full).crop(CROP).save(crop_path, format="BMP")

    # The annotated review recolors only the transplanted source masks by
    # geographic group so the source's dense random province palette remains legible.
    review = target.copy()
    for group, province_ids in GROUPS.items():
        colors = [source_defs[province_id] for province_id in province_ids]
        review[mask_for(translated, colors)] = GROUP_COLORS[group]
    crop = Image.fromarray(review).crop(CROP)
    scale = 2
    shown = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 610, max(shown.height, 900)), (244, 242, 236))
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 15)
    number_font = ImageFont.truetype(font_path, 16)
    panel_x = shown.width + 24
    draw.text((panel_x, 22), "大明日不落山脉移植草图", font=title, fill=(30, 31, 33))
    draw.text((panel_x, 65), "源图像素原样平移：X−438，Y−9；没有缩放", font=small, fill=(69, 70, 72))
    draw.text((panel_x, 90), "仅排除源模组的“长城”不可通行地块", font=small, fill=(69, 70, 72))

    markers = {
        "北方山系": (4560, 792), "长江中游": (4592, 912),
        "东南山系": (4648, 968), "西南山系": (4490, 934),
        "山东与台湾": (4660, 794),
    }
    y = 136
    for index, (group, province_ids) in enumerate(GROUPS.items(), 1):
        color = GROUP_COLORS[group]
        draw.rectangle((panel_x, y + 4, panel_x + 24, y + 28), fill=color, outline=(35, 35, 35))
        draw.text((panel_x + 36, y), f"{index}. {group}", font=body, fill=(32, 33, 35))
        names = "、".join(NAMES[province_id] for province_id in province_ids)
        # Wrap long Chinese name lists by character count.
        lines, current = [], ""
        for part in names.split("、"):
            candidate = part if not current else current + "、" + part
            if len(candidate) > 25:
                lines.append(current)
                current = part
            else:
                current = candidate
        if current:
            lines.append(current)
        for offset, line in enumerate(lines):
            draw.text((panel_x + 36, y + 29 + offset * 22), line, font=small, fill=(70, 71, 73))

        mx, my = markers[group]
        px, py = (mx - CROP[0]) * scale, (my - CROP[1]) * scale
        draw.ellipse((px - 14, py - 14, px + 14, py + 14), fill=(242, 239, 228), outline=(28, 28, 28), width=2)
        number = str(index)
        bounds = draw.textbbox((0, 0), number, font=number_font)
        draw.text((px - (bounds[2] - bounds[0]) / 2, py - (bounds[3] - bounds[1]) / 2 - 2),
                  number, font=number_font, fill=(22, 22, 22))
        y += 64 + 22 * len(lines)

    draw.text((panel_x, 820), "深色地块即源模组原始不可通行山脉轮廓。", font=small, fill=(61, 62, 64))
    draw.text((panel_x, 847), "本草图未修改正式 provinces.bmp。", font=small, fill=(61, 62, 64))
    annotated = OUT / "workshop_han_mountains_annotated.png"
    canvas.save(annotated)

    print(f"SOURCE_MOUNTAINS:{len(selected_ids)}; PIXELS:{int(selected.sum())}")
    print(full_path)
    print(crop_path)
    print(annotated)


if __name__ == "__main__":
    render()
