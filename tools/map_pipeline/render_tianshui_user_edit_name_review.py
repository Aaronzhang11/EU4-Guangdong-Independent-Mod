#!/usr/bin/env python3
"""Label the user's current Tianshui bitmap edit without changing the map."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/tianshui_user_edit_review"
CROP = (4402, 788, 4478, 858)

TARGETS = (
    ("临洮", (171, 163, 193), "新色，待分配正式 ID"),
    ("岷州", (224, 208, 220), "现 ID 5291，游戏名仍为巩昌"),
    ("天水", (138, 152, 194), "现 ID 2180，游戏名仍为秦州"),
    ("巩昌", (219, 0, 220), "新色，待分配正式 ID"),
    ("武都", (0, 211, 220), "新色，待分配正式 ID"),
)


def safe_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError("Cannot label an empty mask")
    target_x, target_y = float(xs.mean()), float(ys.mean())
    border = np.zeros_like(mask)
    border[1:] |= mask[1:] & ~mask[:-1]
    border[:-1] |= mask[:-1] & ~mask[1:]
    border[:, 1:] |= mask[:, 1:] & ~mask[:, :-1]
    border[:, :-1] |= mask[:, :-1] & ~mask[:, 1:]
    candidates = np.column_stack(np.where(mask & ~border))
    if not len(candidates):
        candidates = np.column_stack((ys, xs))
    distance = (candidates[:, 1] - target_x) ** 2 + (candidates[:, 0] - target_y) ** 2
    y, x = candidates[int(np.argmin(distance))]
    return int(x), int(y)


def boundary(values: np.ndarray) -> np.ndarray:
    result = np.zeros(values.shape, dtype=bool)
    result[1:] |= values[1:] != values[:-1]
    result[:-1] |= values[:-1] != values[1:]
    result[:, 1:] |= values[:, 1:] != values[:, :-1]
    result[:, :-1] |= values[:, :-1] != values[:, 1:]
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source_path = MAP / "provinces.bmp"
    bitmap = np.asarray(Image.open(source_path).convert("RGB"), dtype=np.uint8)
    x0, y0, x1, y1 = CROP
    crop = bitmap[y0:y1, x0:x1].copy()
    Image.fromarray(crop).save(OUT / "tianshui_user_edit_raw_crop.bmp", format="BMP")

    masks = {
        name: np.all(bitmap == rgb, axis=2)
        for name, rgb, _status in TARGETS
    }
    missing = [name for name, mask in masks.items() if not mask.any()]
    if missing:
        raise ValueError(f"Missing target colours: {missing}")

    packed = (
        (crop[:, :, 0].astype(np.uint32) << 16)
        | (crop[:, :, 1].astype(np.uint32) << 8)
        | crop[:, :, 2].astype(np.uint32)
    )
    shown = crop.copy()
    shown[boundary(packed)] = (34, 35, 37)
    scale = 8
    map_image = Image.fromarray(shown).resize(
        (shown.shape[1] * scale, shown.shape[0] * scale),
        Image.Resampling.NEAREST,
    )
    panel_width = 510
    canvas = Image.new("RGB", (map_image.width + panel_width, map_image.height), (244, 242, 235))
    canvas.paste(map_image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 26)
    label = ImageFont.truetype(font_path, 21)
    body = ImageFont.truetype(font_path, 16)
    small = ImageFont.truetype(font_path, 13)

    for name, _rgb, _status in TARGETS:
        local = masks[name][y0:y1, x0:x1]
        px, py = safe_point(local)
        box = draw.textbbox((0, 0), name, font=label)
        tx = px * scale - (box[2] - box[0]) // 2
        ty = py * scale - (box[3] - box[1]) // 2
        draw.text((tx + 2, ty + 2), name, font=label, fill=(250, 248, 240))
        draw.text((tx, ty), name, font=label, fill=(24, 25, 27))

    panel_x = map_image.width + 22
    draw.text((panel_x, 22), "当前 BMP 名称对应检查", font=title, fill=(27, 28, 30))
    draw.text((panel_x, 64), "左图直接读取你修改后的 provinces.bmp", font=small, fill=(69, 70, 72))
    y = 104
    report_targets = []
    for name, rgb, status in TARGETS:
        pixels = int(masks[name].sum())
        draw.rectangle((panel_x, y, panel_x + 30, y + 22), fill=rgb, outline=(35, 35, 35))
        draw.text((panel_x + 42, y - 1), f"{name} · {pixels} 像素", font=body, fill=(36, 37, 39))
        draw.text((panel_x + 42, y + 23), status, font=small, fill=(87, 68, 44))
        report_targets.append({"name": name, "rgb": list(rgb), "pixels": pixels, "status": status})
        y += 76

    draw.text((panel_x, 492), "注意：武都色包含 1 个原宁羌像素。", font=small, fill=(145, 53, 46))
    draw.text((panel_x, 520), "本图未修改正式地图，也未写入定义与本地化。", font=small, fill=(47, 91, 58))

    png_path = OUT / "tianshui_user_edit_named_review.png"
    bmp_path = OUT / "tianshui_user_edit_named_review.bmp"
    canvas.save(png_path)
    canvas.save(bmp_path, format="BMP")
    report = {
        "status": "review_only",
        "source": str(source_path),
        "crop": list(CROP),
        "targets": report_targets,
        "known_pixel_provenance_issue": {
            "name": "武都",
            "pixels_from_head_ningqiang": 1,
        },
        "outputs": {
            "annotated_bmp": str(bmp_path),
            "annotated_png": str(png_path),
            "raw_crop_bmp": str(OUT / "tianshui_user_edit_raw_crop.bmp"),
        },
    }
    (OUT / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
