#!/usr/bin/env python3
"""Render a five-province Tianshui–Minzhou draft without touching the formal map."""

from __future__ import annotations

import csv
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/tianshui_five_province"

TIANSHUI_SOURCE = 2180
MINZHOU_SOURCE = 5291
LINTAO_SOURCE = 5294
CROP = (4398, 780, 4482, 860)

# Preview-only RGB values. They are deliberately absent from definition.csv.
GONGCHANG_RGB = (236, 149, 48)
WUDU_RGB = (111, 76, 190)


def definitions() -> dict[int, tuple[int, int, int]]:
    result = {}
    with (MAP / "definition.csv").open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[int(row[0])] = tuple(map(int, row[1:4]))
    return result


def component_count(mask: np.ndarray) -> int:
    points = {tuple(map(int, point)) for point in np.argwhere(mask)}
    count = 0
    while points:
        count += 1
        queue = [points.pop()]
        while queue:
            y, x = queue.pop()
            for neighbour in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if neighbour in points:
                    points.remove(neighbour)
                    queue.append(neighbour)
    return count


def safe_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    target_x, target_y = float(xs.mean()), float(ys.mean())
    border = np.zeros_like(mask)
    border[1:] |= mask[1:] & ~mask[:-1]
    border[:-1] |= mask[:-1] & ~mask[1:]
    border[:, 1:] |= mask[:, 1:] & ~mask[:, :-1]
    border[:, :-1] |= mask[:, :-1] & ~mask[:, 1:]
    candidates = np.column_stack(np.where(mask & ~border))
    if not len(candidates):
        candidates = np.column_stack((ys, xs))
    distances = (candidates[:, 1] - target_x) ** 2 + (candidates[:, 0] - target_y) ** 2
    y, x = candidates[int(np.argmin(distances))]
    return int(x), int(y)


def boundary(mask: np.ndarray) -> np.ndarray:
    result = np.zeros_like(mask)
    result[1:] |= mask[1:] != mask[:-1]
    result[:-1] |= mask[:-1] != mask[1:]
    result[:, 1:] |= mask[:, 1:] != mask[:, :-1]
    result[:, :-1] |= mask[:, :-1] != mask[:, 1:]
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    colours = definitions()
    if GONGCHANG_RGB in colours.values() or WUDU_RGB in colours.values():
        raise ValueError("Preview RGB collides with definition.csv")

    source = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    if np.any(np.all(source == GONGCHANG_RGB, axis=2)) or np.any(np.all(source == WUDU_RGB, axis=2)):
        raise ValueError("Preview RGB already occurs in provinces.bmp")

    tianshui_source = np.all(source == colours[TIANSHUI_SOURCE], axis=2)
    minzhou = np.all(source == colours[MINZHOU_SOURCE], axis=2)
    lintao = np.all(source == colours[LINTAO_SOURCE], axis=2)
    yy, xx = np.indices(tianshui_source.shape)

    # Follow the photographed guide: a sloping Tianshui/Gongchang boundary,
    # then a compact southeastern Wudu cut from the lower Tianshui body.
    tianshui = tianshui_source & (yy <= 828 + 0.35 * (xx - 4445))
    lower = tianshui_source & ~tianshui
    wudu = lower & (xx >= 4454 - 0.10 * (yy - 836))
    gongchang = lower & ~wudu

    masks = {
        "临洮": lintao,
        "岷州": minzhou,
        "天水": tianshui,
        "巩昌": gongchang,
        "武都": wudu,
    }
    for name, mask in masks.items():
        if not mask.any() or component_count(mask) != 1:
            raise ValueError(f"{name} is empty or disconnected")
    if np.any((tianshui.astype(int) + gongchang + wudu) != tianshui_source.astype(int)):
        raise ValueError("Tianshui partition does not exactly cover its source province")

    draft = source.copy()
    draft[gongchang] = GONGCHANG_RGB
    draft[wudu] = WUDU_RGB
    changed = np.any(draft != source, axis=2)
    if np.any(changed & ~tianshui_source):
        raise ValueError("Draft changes pixels outside the Tianshui source province")

    full_path = OUT / "tianshui_five_province_full_draft.bmp"
    crop_path = OUT / "tianshui_five_province_crop.bmp"
    Image.fromarray(draft).save(full_path, format="BMP")
    x0, y0, x1, y1 = CROP
    crop = draft[y0:y1, x0:x1].copy()
    Image.fromarray(crop).save(crop_path, format="BMP")

    # Annotated viewing copy; the BMPs above remain exact province-colour drafts.
    packed = (
        (crop[:, :, 0].astype(np.uint32) << 16)
        | (crop[:, :, 1].astype(np.uint32) << 8)
        | crop[:, :, 2].astype(np.uint32)
    )
    shown = crop.copy()
    shown[boundary(packed)] = (35, 36, 38)
    scale = 8
    map_image = Image.fromarray(shown).resize(
        (shown.shape[1] * scale, shown.shape[0] * scale), Image.Resampling.NEAREST
    )
    canvas = Image.new("RGB", (map_image.width + 430, map_image.height), (244, 242, 235))
    canvas.paste(map_image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 27)
    label = ImageFont.truetype(font_path, 21)
    body = ImageFont.truetype(font_path, 17)
    small = ImageFont.truetype(font_path, 14)

    for name, mask in masks.items():
        local = mask[y0:y1, x0:x1]
        px, py = safe_point(local)
        text_box = draw.textbbox((0, 0), name, font=label)
        tx = px * scale - (text_box[2] - text_box[0]) // 2
        ty = py * scale - (text_box[3] - text_box[1]) // 2
        draw.text((tx + 2, ty + 2), name, font=label, fill=(250, 248, 240))
        draw.text((tx, ty), name, font=label, fill=(25, 25, 27))

    panel_x = map_image.width + 24
    draw.text((panel_x, 24), "天水—岷州五省草案", font=title, fill=(27, 28, 30))
    draw.text((panel_x, 70), "依照手绘红框；保持外围逐像素不变", font=small, fill=(69, 70, 72))
    legend = [
        ("临洮", colours[LINTAO_SOURCE]),
        ("岷州", colours[MINZHOU_SOURCE]),
        ("天水", colours[TIANSHUI_SOURCE]),
        ("巩昌", GONGCHANG_RGB),
        ("武都", WUDU_RGB),
    ]
    y = 118
    for name, colour in legend:
        draw.rectangle((panel_x, y, panel_x + 30, y + 22), fill=colour, outline=(35, 35, 35))
        draw.text((panel_x + 44, y - 1), f"{name}  {int(masks[name].sum())} 像素", font=body, fill=(38, 39, 41))
        y += 44
    draw.text((panel_x, 365), "拆分逻辑", font=title, fill=(27, 28, 30))
    draw.text((panel_x, 414), "天水 → 天水、巩昌、武都", font=body, fill=(45, 46, 48))
    draw.text((panel_x, 450), "岷州侧 → 岷州、临洮", font=body, fill=(45, 46, 48))
    draw.text((panel_x, 510), f"草案改色：{int(changed.sum())} 像素", font=body, fill=(45, 92, 57))
    draw.text((panel_x, 546), "正式 provinces.bmp：0 像素改动", font=body, fill=(45, 92, 57))
    draw.text((panel_x, 590), "未分配正式 ID、历史、区域或本地化。", font=small, fill=(91, 69, 43))
    annotated_path = OUT / "tianshui_five_province_annotated.png"
    canvas.save(annotated_path)

    report = {
        "status": "preview_only",
        "source_bitmap": str(MAP / "provinces.bmp"),
        "full_draft": str(full_path),
        "crop_draft": str(crop_path),
        "annotated": str(annotated_path),
        "editable_source_id": TIANSHUI_SOURCE,
        "province_pixels": {name: int(mask.sum()) for name, mask in masks.items()},
        "changed_pixels": int(changed.sum()),
        "changed_outside_editable_mask": int(np.sum(changed & ~tianshui_source)),
        "components": {name: component_count(mask) for name, mask in masks.items()},
        "preview_rgb": {
            "巩昌": list(GONGCHANG_RGB),
            "武都": list(WUDU_RGB),
        },
    }
    (OUT / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
