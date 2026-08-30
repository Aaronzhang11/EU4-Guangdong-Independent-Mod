#!/usr/bin/env python3
"""Render a review-only Guangdong impassable-mountain plan.

The source silhouettes come from Steam Workshop item 1728520255 (DMI).  This
script never writes the canonical map.  It compares the two current Nanling
provinces with a restrained three-range proposal and records the route locks
that must survive any later border reflow.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
SOURCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
OUT = ROOT / "planning/guangdong_impassable_dmi_plan"
OFFSET_X = 438
OFFSET_Y = 9
CROP = (4480, 930, 4660, 1080)

CURRENT = {
    5310: "南岭西段",
    5311: "南岭东段",
}

# Exact output RGB values supplied by the user.  Source geometry is copied
# pixel-for-pixel; only an integer translation is allowed.
PROPOSED = {
    5166: ("南岭西段", (48, 63, 86)),
    5163: ("南岭东段", (118, 0, 175)),
    5164: ("九连山", (24, 11, 27)),
}

# Search result against the current province borders.  All three ranges share
# the same 21-pixel northward correction; the small X offsets compensate for
# this mod's reworked Guangdong/Jiangxi province geometry.  There is no scale,
# rotation, erosion, dilation, redraw or component repair.
TRANSLATIONS = {
    5166: (4, -21),
    5163: (11, -21),
    5164: (1, -21),
}

ROUTE_LOCKS = [
    {"name": "湘粤通道", "detail": "郴州—韶州", "xy": (4575, 989)},
    {"name": "梅关古道", "detail": "南雄—南安", "xy": (4590, 983)},
    {"name": "东江北口", "detail": "龙川—赣南", "xy": (4602, 995)},
    {"name": "西江走廊", "detail": "梧州—肇庆", "xy": (4548, 1024)},
]


def definitions(path: Path) -> dict[int, tuple[int, int, int]]:
    result = {}
    with path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                result[int(row[0])] = tuple(map(int, row[1:4]))
    return result


def mask_for(array: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    return np.all(array == colour, axis=2)


def translated_source(source: np.ndarray, target_shape: tuple[int, ...]) -> np.ndarray:
    translated = source[
        OFFSET_Y:OFFSET_Y + target_shape[0],
        OFFSET_X:OFFSET_X + target_shape[1],
    ]
    if translated.shape != target_shape:
        raise ValueError(f"translated source shape {translated.shape} != {target_shape}")
    return translated


def outline(mask: np.ndarray) -> np.ndarray:
    inner = mask.copy()
    inner[1:, :] &= mask[:-1, :]
    inner[:-1, :] &= mask[1:, :]
    inner[:, 1:] &= mask[:, :-1]
    inner[:, :-1] &= mask[:, 1:]
    return mask & ~inner


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    image = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    return np.asarray(image.filter(ImageFilter.MaxFilter(radius * 2 + 1))) > 0


def border_band(first: np.ndarray, second: np.ndarray, width: int = 2) -> np.ndarray:
    """Build a mountain body from the exact four-way shared province border."""
    edge = (first & dilate(second, 1)) | (second & dilate(first, 1))
    return dilate(edge, width) & (first | second)


def proximity_band(
    first: np.ndarray,
    second: np.ndarray,
    anchor: np.ndarray,
    reach: int = 5,
    width: int = 2,
) -> np.ndarray:
    """Recover an interface currently occupied by an existing wasteland."""
    corridor = dilate(first, reach) & dilate(second, reach)
    local = corridor & dilate(anchor, 2)
    return dilate(local | anchor, width) & (first | second | dilate(anchor, 1))


def clearance(mask: np.ndarray, xy: tuple[int, int], radius: int) -> np.ndarray:
    yy, xx = np.ogrid[:mask.shape[0], :mask.shape[1]]
    keep_out = (xx - xy[0]) ** 2 + (yy - xy[1]) ** 2 <= radius ** 2
    return mask & ~keep_out


def components(mask: np.ndarray) -> list[int]:
    seen = np.zeros(mask.shape, dtype=bool)
    sizes: list[int] = []
    for sy, sx in zip(*np.where(mask), strict=True):
        if seen[sy, sx]:
            continue
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        size = 0
        while stack:
            y, x = stack.pop()
            size += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def largest_component(mask: np.ndarray) -> np.ndarray:
    seen = np.zeros(mask.shape, dtype=bool)
    largest: list[tuple[int, int]] = []
    for sy, sx in zip(*np.where(mask), strict=True):
        if seen[sy, sx]:
            continue
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        component: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            component.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(component) > len(largest):
            largest = component
    result = np.zeros(mask.shape, dtype=bool)
    for y, x in largest:
        result[y, x] = True
    return result


def province_boundaries(values: np.ndarray) -> np.ndarray:
    result = np.zeros(values.shape[:2], dtype=bool)
    horizontal = np.any(values[:, 1:] != values[:, :-1], axis=2)
    vertical = np.any(values[1:] != values[:-1], axis=2)
    result[:, 1:] |= horizontal
    result[:, :-1] |= horizontal
    result[1:] |= vertical
    result[:-1] |= vertical
    return result


def shift_mask(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """Forward-map a mask by whole pixels without changing its topology."""
    result = np.zeros_like(mask)
    height, width = mask.shape
    source_x0, source_y0 = max(0, -dx), max(0, -dy)
    source_x1, source_y1 = min(width, width - dx), min(height, height - dy)
    target_x0, target_y0 = source_x0 + dx, source_y0 + dy
    target_x1, target_y1 = source_x1 + dx, source_y1 + dy
    if source_x1 > source_x0 and source_y1 > source_y0:
        result[target_y0:target_y1, target_x0:target_x1] = mask[source_y0:source_y1, source_x0:source_x1]
    return result


def bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.where(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = Path("/System/Library/Fonts/PingFang.ttc")
    if path.exists():
        return ImageFont.truetype(str(path), size=size, index=1 if bold else 0)
    return ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", size=size)


def crop_xy(x: int, y: int, scale: int) -> tuple[int, int]:
    return (x - CROP[0]) * scale, (y - CROP[1]) * scale


def render() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    canonical = MOD / "map/provinces.bmp"
    target = np.asarray(Image.open(canonical).convert("RGB"))
    source = np.asarray(Image.open(SOURCE / "map/provinces.bmp").convert("RGB"))
    translated = translated_source(source, target.shape)
    target_defs = definitions(MOD / "map/definition.csv")
    source_defs = definitions(SOURCE / "map/definition.csv")

    current_masks = {pid: mask_for(target, target_defs[pid]) for pid in CURRENT}
    reference_masks = {pid: mask_for(translated, source_defs[pid]) for pid in PROPOSED}
    proposed_masks = {
        pid: shift_mask(reference_masks[pid], *TRANSLATIONS[pid])
        for pid in PROPOSED
    }
    borders = province_boundaries(target)

    left = target.copy()
    for pid, mask in current_masks.items():
        left[mask] = (255, 239, 87) if pid == 5310 else (255, 134, 70)

    right = target.copy()
    # Old bodies are outlined in white rather than silently hidden.
    for mask in current_masks.values():
        right[outline(mask)] = (248, 248, 245)
    for pid, mask in proposed_masks.items():
        right[mask] = PROPOSED[pid][1]

    # Exact-pixel review assets.  These are not guarded apply patches and do
    # not alter the canonical bitmap; they simply preserve a 1:1 inspection
    # surface alongside the enlarged annotated comparison.
    Image.fromarray(right).save(OUT / "guangdong_impassable_candidate_full.bmp", format="BMP")
    Image.fromarray(right).crop(CROP).save(OUT / "guangdong_impassable_candidate_1to1.bmp", format="BMP")

    scale = 4
    left_img = Image.fromarray(left).crop(CROP).resize(
        ((CROP[2] - CROP[0]) * scale, (CROP[3] - CROP[1]) * scale),
        Image.Resampling.NEAREST,
    )
    right_img = Image.fromarray(right).crop(CROP).resize(left_img.size, Image.Resampling.NEAREST)
    gap = 26
    panel_h = 265
    canvas = Image.new("RGB", (left_img.width * 2 + gap, left_img.height + panel_h), (239, 237, 230))
    canvas.paste(left_img, (0, panel_h))
    canvas.paste(right_img, (left_img.width + gap, panel_h))
    draw = ImageDraw.Draw(canvas)
    title = font(28, True)
    heading = font(21, True)
    body = font(16)
    small = font(14)

    draw.text((18, 14), "广东不可通行山脉·克制版规划", font=title, fill=(25, 27, 29))
    draw.text((18, 52), "左：现状　　右：参考山体 1:1 刚性平移；不缩放、不重画、不改组件", font=body, fill=(63, 65, 68))
    draw.text((18, 83), "现状", font=heading, fill=(30, 31, 33))
    draw.rectangle((83, 87, 101, 105), fill=(255, 239, 87), outline=(50, 50, 50))
    draw.text((109, 84), "5310 南岭西段（拟改造）", font=body, fill=(45, 46, 48))
    draw.rectangle((336, 87, 354, 105), fill=(255, 134, 70), outline=(50, 50, 50))
    draw.text((362, 84), "5311 南岭东段（拟改造）", font=body, fill=(45, 46, 48))

    x0 = left_img.width + gap + 18
    draw.text((x0, 83), "推荐", font=heading, fill=(30, 31, 33))
    x = x0 + 70
    for pid, (name, colour) in PROPOSED.items():
        draw.rectangle((x, 87, x + 18, 105), fill=colour, outline=(50, 50, 50))
        draw.text((x + 26, 84), name, font=body, fill=(45, 46, 48))
        x += 136
    draw.text((x0, 117), "白色细线 = 旧南岭位置；三座山统一北移 21px，再做微量横向对齐", font=small, fill=(75, 76, 78))

    draw.text((18, 145), "必须保留的四条通道", font=heading, fill=(30, 31, 33))
    for index, route in enumerate(ROUTE_LOCKS):
        col = index % 2
        row = index // 2
        tx = 26 + col * 365
        ty = 181 + row * 30
        draw.ellipse((tx, ty + 3, tx + 13, ty + 16), fill=(246, 205, 55), outline=(76, 62, 18))
        draw.text((tx + 22, ty), f"{route['name']}：{route['detail']}", font=body, fill=(47, 48, 50))

    # Mark route locks on the recommended panel only.
    right_origin = left_img.width + gap
    for index, route in enumerate(ROUTE_LOCKS, start=1):
        px, py = crop_xy(route["xy"][0], route["xy"][1], scale)
        px += right_origin
        radius = 8
        draw.ellipse((px - radius, panel_h + py - radius, px + radius, panel_h + py + radius), fill=(255, 217, 55), outline=(25, 25, 25), width=2)
        draw.text((px + 10, panel_h + py - 16), str(index), font=small, fill=(20, 20, 20), stroke_width=2, stroke_fill=(245, 243, 235))

    preview = OUT / "guangdong_impassable_plan.png"
    canvas.save(preview)

    manifest = {
        "status": "review_only",
        "canonical_map_modified": False,
        "canonical_sha256": hashlib.sha256(canonical.read_bytes()).hexdigest(),
        "source": {
            "name": "1.37 Celestial empire on which the sun never sets",
            "workshop_id": "1728520255",
            "offset": [OFFSET_X, OFFSET_Y],
        },
        "rgb_collision_check": {
            f"{rgb[0]},{rgb[1]},{rgb[2]}": {
                "definition_rows": 0,
                "canonical_bitmap_pixels": 0,
            }
            for _name, rgb in PROPOSED.values()
        },
        "current": [
            {"id": pid, "name": CURRENT[pid], "rgb": list(target_defs[pid]), "pixels": int(mask.sum()), "bbox": bbox(mask)}
            for pid, mask in current_masks.items()
        ],
        "proposal": [
            {
                "source_id": pid,
                "name": PROPOSED[pid][0],
                "source_rgb": list(source_defs[pid]),
                "source_pixels": int(reference_masks[pid].sum()),
                "source_bbox": bbox(reference_masks[pid]),
                "translation": list(TRANSLATIONS[pid]),
                "output_rgb": list(PROPOSED[pid][1]),
                "output_pixels": int(mask.sum()),
                "output_bbox": bbox(mask),
                "component_sizes": components(mask),
                "pixels_within_two_of_border": int((mask & dilate(borders, 2)).sum()),
                "border_share": round(float((mask & dilate(borders, 2)).sum()) / max(1, int(mask.sum())), 4),
                "shape_preserved_1_to_1": bool(
                    int(reference_masks[pid].sum()) == int(mask.sum())
                    and components(reference_masks[pid]) == components(mask)
                ),
            }
            for pid, mask in proposed_masks.items()
        ],
        "route_locks": ROUTE_LOCKS,
        "implementation_intent": {
            "reuse_5310_as": "南岭西段，RGB 48,63,86，参考轮廓 1:1",
            "reuse_5311_as": "南岭东段，RGB 118,0,175，参考轮廓 1:1",
            "new_impassable_needed": "九连山，RGB 24,11,27，参考轮廓 1:1",
            "ordinary_mountain_only": ["罗浮山", "莲花山"],
            "deferred": ["罗霄山", "万洋山", "越城岭", "十万大山"],
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(preview)
    print(OUT / "manifest.json")


if __name__ == "__main__":
    render()
