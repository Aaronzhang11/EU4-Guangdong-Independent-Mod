#!/usr/bin/env python3
"""Render the implemented B16 Anhui geometry as a readable review plate."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
OUTPUT = ROOT / "docs/map/previews/B16_anhui_review.png"

CROP = (4588, 815, 4691, 931)
SCALE = 7
MAP_ORIGIN = (34, 72)

AREAS = {
    "淮颍": (5058, 2144, 5059, 2143),
    "江淮": (5060, 1838, 5061, 5063, 5064),
    "皖江": (686, 5065, 5066, 5062),
    "徽宁": (2147, 2146, 5067, 5068),
}

AREA_COLOURS = {
    "淮颍": ((239, 180, 65), (247, 200, 88), (220, 146, 53), (244, 166, 82)),
    "江淮": ((91, 176, 119), (68, 158, 116), (112, 190, 137), (64, 143, 98), (137, 195, 116)),
    "皖江": ((221, 117, 66), (202, 91, 59), (235, 139, 58), (214, 153, 72)),
    "徽宁": ((137, 102, 190), (112, 82, 166), (160, 117, 202), (126, 117, 190)),
}

NAMES = {
    5058: "亳州", 2144: "颍州", 5059: "寿州", 2143: "凤阳",
    5060: "六安", 1838: "庐州", 5061: "巢湖", 5063: "滁州", 5064: "和州",
    686: "安庆", 5065: "池州", 5066: "芜湖", 5062: "无为",
    2147: "徽州", 2146: "宁国", 5067: "太平", 5068: "广德",
}

LABELS = {
    5058: (4617, 839), 2144: (4612, 848), 5059: (4620, 860), 2143: (4634, 837),
    5060: (4618, 877), 1838: (4630, 873), 5061: (4644, 870), 5063: (4655, 850),
    5064: (4634, 855), 686: (4617, 890), 5065: (4630, 890), 5066: (4657, 882),
    5062: (4640, 880), 2147: (4648, 907), 2146: (4658, 892), 5067: (4642, 897),
    5068: (4668, 885),
}

DETAILS = {
    "淮颍": "亳州 · 颍州 · 寿州 · 凤阳",
    "江淮": "六安 · 庐州 · 巢湖 · 滁州 · 和州",
    "皖江": "安庆 · 池州 · 芜湖 · 无为",
    "徽宁": "徽州 · 宁国 · 太平 · 广德",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size, index=1 if bold else 0)
    return ImageFont.load_default()


def definition_colours() -> dict[tuple[int, int, int], int]:
    result: dict[tuple[int, int, int], int] = {}
    with (MOD / "map/definition.csv").open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[tuple(int(value) for value in row[1:4])] = int(row[0])
    return result


def main() -> None:
    colour_to_id = definition_colours()
    source = np.asarray(Image.open(MOD / "map/provinces.bmp").convert("RGB"))
    left, top, right, bottom = CROP
    source = source[top:bottom, left:right]
    id_map = np.full(source.shape[:2], -1, dtype=np.int32)
    for colour, province_id in colour_to_id.items():
        mask = np.all(source == colour, axis=2)
        id_map[mask] = province_id

    rendered = np.full_like(source, (219, 218, 211))
    water = np.isin(id_map, tuple(range(5032, 5045)) + (1655, 1896, 1897))
    rendered[water] = (92, 170, 211)
    for area, province_ids in AREAS.items():
        for province_id, colour in zip(province_ids, AREA_COLOURS[area], strict=True):
            rendered[id_map == province_id] = colour

    province_ids = tuple(NAMES)
    anhui = np.isin(id_map, province_ids)
    boundary = np.zeros_like(anhui)
    boundary[1:, :] |= anhui[1:, :] & (id_map[1:, :] != id_map[:-1, :])
    boundary[:-1, :] |= anhui[:-1, :] & (id_map[:-1, :] != id_map[1:, :])
    boundary[:, 1:] |= anhui[:, 1:] & (id_map[:, 1:] != id_map[:, :-1])
    boundary[:, :-1] |= anhui[:, :-1] & (id_map[:, :-1] != id_map[:, 1:])
    rendered[boundary] = (247, 245, 236)

    map_image = Image.fromarray(rendered).resize(
        (rendered.shape[1] * SCALE, rendered.shape[0] * SCALE),
        Image.Resampling.NEAREST,
    )
    canvas = Image.new("RGB", (1320, 930), (246, 244, 237))
    canvas.paste(map_image, MAP_ORIGIN)
    draw = ImageDraw.Draw(canvas)
    draw.text((34, 24), "安徽十七省 · B16 正式像素审图", fill=(38, 43, 47), font=font(30, True))
    draw.text((780, 25), "基于当前 provinces.bmp", fill=(103, 106, 106), font=font(17))

    label_font = font(17, True)
    id_font = font(11)
    for province_id, (x, y) in LABELS.items():
        px = MAP_ORIGIN[0] + (x - left) * SCALE
        py = MAP_ORIGIN[1] + (y - top) * SCALE
        name = NAMES[province_id]
        box = draw.textbbox((px, py), name, font=label_font, anchor="mm")
        box = (box[0] - 4, box[1] - 2, box[2] + 4, box[3] + 2)
        draw.rounded_rectangle(box, radius=4, fill=(255, 253, 246), outline=(53, 58, 60), width=1)
        draw.text((px, py), name, fill=(35, 39, 41), font=label_font, anchor="mm")
        draw.text((px, box[3] + 2), str(province_id), fill=(52, 56, 58), font=id_font, anchor="ma")

    legend_x = 790
    draw.rounded_rectangle((760, 74, 1285, 890), radius=18, fill=(255, 253, 247), outline=(208, 205, 194), width=2)
    draw.text((legend_x, 99), "四个区域", fill=(42, 47, 49), font=font(25, True))
    y = 145
    for area in AREAS:
        draw.rounded_rectangle((legend_x, y, legend_x + 28, y + 28), radius=5, fill=AREA_COLOURS[area][1])
        draw.text((legend_x + 42, y + 13), area, fill=(36, 41, 43), font=font(22, True), anchor="lm")
        draw.text((legend_x + 112, y + 14), DETAILS[area], fill=(79, 81, 80), font=font(16), anchor="lm")
        y += 62

    draw.line((legend_x, 407, 1252, 407), fill=(216, 211, 198), width=2)
    draw.text((legend_x, 435), "设计结果", fill=(42, 47, 49), font=font(25, True))
    notes = (
        "• 17省，区域规模为 4 / 5 / 4 / 4",
        "• 总发展度 160（税58 / 产65 / 兵37）",
        "• 芜湖：二级贸易中心，预留自由市",
        "• 寿州：一级贸易中心与淮河要塞",
        "• 巢湖164像素；无为116像素，均为连通省份",
        "• 蓝色为已接入的长江、淮河可通行水面",
    )
    y = 482
    for note in notes:
        draw.text((legend_x, y), note, fill=(64, 67, 67), font=font(17))
        y += 46

    draw.line((legend_x, 772, 1252, 772), fill=(216, 211, 198), width=2)
    draw.text((legend_x, 798), "边界原则", fill=(42, 47, 49), font=font(21, True))
    draw.text((legend_x, 838), "淮河—江淮丘陵—长江—皖南山地逐层展开，", fill=(72, 75, 75), font=font(16))
    draw.text((legend_x, 867), "巢湖从无为中独立，保留两岸和河道玩法。", fill=(72, 75, 75), font=font(16))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
