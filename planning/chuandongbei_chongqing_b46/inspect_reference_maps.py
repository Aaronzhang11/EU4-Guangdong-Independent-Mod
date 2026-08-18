#!/usr/bin/env python3
"""Compare installed workshop maps over the B46 planning mask.

This is a read-only planning aid.  It never copies reference pixels into the
mod and writes only a labelled comparison PNG in this planning directory.
"""

from __future__ import annotations

from pathlib import Path
import csv
import hashlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render_b46_proposal as proposal


ROOT = Path(__file__).resolve().parents[2]
WORKSHOP = Path("/Users/xinanyapiao/Library/Application Support/Steam/steamapps/workshop/content/236850")
OUTPUT = Path(__file__).resolve().parent / "b46_reference_comparison.png"
REFERENCES = (
    ("天朝日不落", WORKSHOP / "1728520255"),
    ("岁在甲子", WORKSHOP / "3400977776"),
    ("风云世纪两千年", WORKSHOP / "2935149060"),
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return proposal.font(size, bold)


def read_definitions(path: Path) -> tuple[dict[tuple[int, int, int], int], dict[int, str]]:
    rgb_to_id: dict[tuple[int, int, int], int] = {}
    names: dict[int, str] = {}
    with path.open(encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if len(row) < 5 or not row[0].isdigit():
                continue
            province_id = int(row[0])
            rgb_to_id[tuple(map(int, row[1:4]))] = province_id
            names[province_id] = row[4]
    return rgb_to_id, names


def color_for(province_id: int) -> tuple[int, int, int]:
    digest = hashlib.sha256(str(province_id).encode()).digest()
    return tuple(65 + byte % 155 for byte in digest[:3])


def label_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    cx, cy = float(xs.mean()), float(ys.mean())
    index = np.argmin((xs - cx) ** 2 + (ys - cy) ** 2)
    return int(xs[index]), int(ys[index])


def history_names(root: Path) -> dict[int, str]:
    result: dict[int, str] = {}
    directory = root / "history/provinces"
    if not directory.exists():
        return result
    for path in directory.iterdir():
        prefix = path.name.split("-", 1)[0].strip()
        if prefix.isdigit():
            label = path.stem.split("-", 1)[1].strip() if "-" in path.stem else path.stem
            result[int(prefix)] = label
    return result


def anchor_box(values: np.ndarray, id_to_rgb: dict[int, tuple[int, int, int]]) -> tuple[int, int, int, int]:
    centers: list[tuple[float, float]] = []
    for province_id in (679, 680, 2169, 4211):
        rgb = id_to_rgb.get(province_id)
        if rgb is None:
            continue
        ys, xs = np.where(np.all(values == np.asarray(rgb, dtype=np.uint8), axis=2))
        if len(xs):
            centers.append((float(xs.mean()), float(ys.mean())))
    if len(centers) < 3:
        raise ValueError("Reference map is missing the Sichuan anchor provinces")
    scale_x = values.shape[1] / 5632
    scale_y = values.shape[0] / 2048
    left = max(0, round(min(x for x, _ in centers) - 24 * scale_x))
    right = min(values.shape[1], round(max(x for x, _ in centers) + 28 * scale_x))
    top = max(0, round(min(y for _, y in centers) - 22 * scale_y))
    bottom = min(values.shape[0], round(max(y for _, y in centers) + 28 * scale_y))
    return left, top, right, bottom


def render_reference(
    title: str,
    root: Path,
) -> tuple[Image.Image, list[tuple[int, str, int]]]:
    values = np.array(Image.open(root / "map/provinces.bmp").convert("RGB"), dtype=np.uint8)
    rgb_to_id, names = read_definitions(root / "map/definition.csv")
    id_to_rgb = {province_id: rgb for rgb, province_id in rgb_to_id.items()}
    names.update(history_names(root))
    box = anchor_box(values, id_to_rgb)
    left, top, right, bottom = box
    scale = 4
    crop_h, crop_w = bottom - top, right - left
    source_crop = values[top:bottom, left:right]
    canvas = np.full((crop_h, crop_w, 3), (226, 223, 215), dtype=np.uint8)
    records: list[tuple[int, str, int]] = []
    masks: dict[int, np.ndarray] = {}
    unique_colors = np.unique(source_crop.reshape(-1, 3), axis=0)
    for color in unique_colors:
        rgb = tuple(int(value) for value in color)
        province_id = rgb_to_id.get(rgb)
        if province_id is None:
            continue
        local = np.all(source_crop == color, axis=2)
        pixels = int(local.sum())
        if pixels < 18:
            continue
        masks[province_id] = local
        records.append((province_id, names.get(province_id, "?"), pixels))
        canvas[local] = color_for(province_id)
    union = np.zeros((crop_h, crop_w), dtype=bool)
    for local in masks.values():
        union |= local
        canvas[proposal.border(local)] = (250, 248, 241)
    canvas[~union] = (185, 183, 177)
    image = Image.fromarray(canvas).resize((crop_w * scale, crop_h * scale), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    for province_id, local in masks.items():
        x, y = label_point(local)
        x, y = x * scale, y * scale
        label = names.get(province_id, str(province_id))
        if len(label) > 14:
            label = str(province_id)
        bbox = draw.textbbox((0, 0), label, font=font(11, True))
        rect = (x - bbox[2] // 2 - 2, y - bbox[3] // 2 - 1, x + bbox[2] // 2 + 2, y + bbox[3] // 2 + 1)
        draw.rectangle(rect, fill=(250, 247, 239), outline=(50, 50, 50))
        draw.text((x - bbox[2] // 2, y - bbox[3] // 2), label, font=font(11, True), fill=(20, 20, 20))
    records.sort(key=lambda record: record[0])
    return image, records


def main() -> None:
    panels: list[tuple[str, Image.Image, list[tuple[int, str, int]]]] = []
    for title, root in REFERENCES:
        panel, records = render_reference(title, root)
        panels.append((title, panel, records))

    panel_width = max(panel.width for _, panel, _ in panels)
    panel_height = max(panel.height for _, panel, _ in panels)
    canvas = Image.new("RGB", (panel_width * 3 + 80, panel_height + 200), (247, 244, 236))
    draw = ImageDraw.Draw(canvas)
    draw.text((30, 18), "川东北—重庆：三款参考模组同坐标边界比较", font=font(30, True), fill=(35, 35, 35))
    draw.text((30, 61), "以成都、重庆、阆中、达州为共同锚点裁图；用于比较密度和边界语言，不直接移植像素", font=font(16), fill=(85, 85, 85))
    for index, (title, panel, records) in enumerate(panels):
        x = 20 + index * panel_width
        draw.text((x + 10, 101), f"{title} · {len(records)}块", font=font(22, True), fill=(40, 40, 40))
        canvas.paste(panel, (x, 140))
        names = "、".join(name for _, name, pixels in records if pixels >= 25)
        if names:
            draw.text((x + 10, panel_height + 150), names[:68], font=font(13), fill=(80, 80, 80))
    canvas.save(OUTPUT)
    for title, _, records in panels:
        print(title, len(records), records)


if __name__ == "__main__":
    main()
