#!/usr/bin/env python3
"""Render a review-only ten-province Liaoning draft from workshop geometry."""

from __future__ import annotations

from collections import Counter, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
SOURCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
OUT = ROOT / "planning/liaoning"

# The workshop map uses the same North-China projection with this fixed margin.
# Liaoning needs its own best-fit translation. The Hebei transplant offset
# displaced the peninsula eastward and pushed Jiuliancheng over the Yalu.
SOURCE_X_OFFSET = 454
SOURCE_Y_OFFSET = 5

# id: Chinese, English, area, goods, tax/production/manpower, centre of trade
PROVINCES = {
    726: ("沈阳", "Shenyang", "辽东", "cloth", (4, 4, 3), 1),
    5204: ("辽阳", "Liaoyang", "辽东", "iron", (5, 5, 5), 0),
    5205: ("铁岭", "Tieling", "辽东", "livestock", (2, 3, 3), 0),
    5206: ("辽河套", "Liaohetao", "辽西", "grain", (3, 3, 2), 0),
    2112: ("九连城", "Jiuliancheng", "辽东", "fur", (2, 2, 3), 0),
    704: ("宁远", "Ningyuan", "辽西", "salt", (3, 2, 3), 0),
    5207: ("广宁", "Guangning", "辽西", "livestock", (4, 3, 3), 0),
    5209: ("锦州", "Jinzhou", "辽西", "salt", (3, 4, 3), 0),
    4652: ("海城", "Haicheng", "辽东", "grain", (3, 3, 2), 0),
    2113: ("盖州", "Gaizhou", "辽东", "fish", (3, 3, 3), 0),
}
SOURCE_IDS = set(PROVINCES)
OLD_IDS = {704, 726, 2112, 2113, 4652}
GOODS_CN = {
    "cloth": "布匹", "iron": "铁矿", "livestock": "牲畜", "grain": "谷物",
    "fur": "毛皮", "salt": "盐", "fish": "鱼类",
}


def definitions(path: Path):
    by_id = {}
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 5 and fields[0].isdigit():
            by_id[int(fields[0])] = (tuple(map(int, fields[1:4])), fields[4])
    return by_id


def colour_mask(bitmap: np.ndarray, colours):
    packed = ((bitmap[:, :, 0].astype(np.uint32) << 16)
              | (bitmap[:, :, 1].astype(np.uint32) << 8)
              | bitmap[:, :, 2].astype(np.uint32))
    keys = np.array([(r << 16) | (g << 8) | b for r, g, b in colours], dtype=np.uint32)
    return np.isin(packed, keys)


def fill_retired(result: np.ndarray, retired: np.ndarray, protected: np.ndarray):
    """Return old Liaoning pixels outside the imported outline to neighbours."""
    h, w = retired.shape
    queue = deque()
    assigned = np.zeros(retired.shape, dtype=bool)
    for y, x in zip(*np.where(retired)):
        neighbours = []
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not retired[ny, nx]:
                neighbours.append(tuple(result[ny, nx]))
        if neighbours:
            result[y, x] = Counter(neighbours).most_common(1)[0][0]
            assigned[y, x] = True
            queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and retired[ny, nx] and not assigned[ny, nx]:
                result[ny, nx] = result[y, x]
                assigned[ny, nx] = True
                queue.append((nx, ny))
    if np.any(retired & ~assigned):
        raise ValueError("Could not return all superseded Liaoning pixels")


def fill_original_outline(result: np.ndarray, original: np.ndarray, imported: np.ndarray):
    """Grow only imported Liaoning colours through uncovered vanilla pixels."""
    assigned = imported & original
    queue = deque((int(x), int(y)) for y, x in zip(*np.where(assigned)))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < original.shape[1] and 0 <= ny < original.shape[0]
                    and original[ny, nx] and not assigned[ny, nx]):
                result[ny, nx] = result[y, x]
                assigned[ny, nx] = True
                queue.append((nx, ny))
    if np.any(original & ~assigned):
        raise ValueError("Could not fill the original Liaoning outline")


def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    source = np.asarray(Image.open(SOURCE / "map/provinces.bmp").convert("RGB"))
    current_defs = definitions(MAP / "definition.csv")
    source_defs = definitions(SOURCE / "map/definition.csv")

    old_mask = colour_mask(base, [current_defs[i][0] for i in OLD_IDS])
    result = base.copy()
    imported = np.zeros(old_mask.shape, dtype=bool)

    # Preserve every workshop internal province shape. Gaizhou follows the
    # vanilla peninsula coast, while Jiuliancheng is clipped to the Yalu's west bank.
    for pid in SOURCE_IDS:
        colour = source_defs[pid][0]
        ys, xs = np.where(np.all(source == colour, axis=2))
        for sy, sx in zip(ys, xs):
            tx, ty = int(sx - SOURCE_X_OFFSET), int(sy - SOURCE_Y_OFFSET)
            if not (0 <= tx < base.shape[1] and 0 <= ty < base.shape[0]):
                continue
            if pid in {2112, 2113} and not old_mask[ty, tx]:
                continue
            result[ty, tx] = colour
            imported[ty, tx] = True

    fill_original_outline(result, old_mask, imported)
    changed = np.any(result != base, axis=2)
    Image.fromarray(result).save(OUT / "liaoning_workshop_10_corrected_full_draft.bmp", format="BMP")

    display_mask = old_mask | imported | changed
    yy, xx = np.where(display_mask)
    margin = 12
    x0, x1 = max(0, xx.min() - margin), min(base.shape[1], xx.max() + margin + 1)
    y0, y1 = max(0, yy.min() - margin), min(base.shape[0], yy.max() + margin + 1)
    crop = Image.fromarray(result[y0:y1, x0:x1])
    scale = 8
    shown = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)
    shown.save(OUT / "liaoning_workshop_10_corrected_draft.bmp", format="BMP")
    shown.save(OUT / "liaoning_workshop_10_corrected_raw.png")

    sidebar = 600
    canvas = Image.new("RGB", (shown.width + sidebar, max(shown.height, 830)), (248, 247, 243))
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    title, body, small = font(30, True), font(20), font(16)
    lx = shown.width + 25
    draw.text((lx, 20), "辽宁十省 · 大明日不落几何修正版", fill=(24, 24, 24), font=title)
    draw.text((lx, 60), "八省原形保留；盖州顺半岛；九连城止于鸭绿江", fill=(75, 75, 75), font=small)

    # Province labels and trade-centre stars.
    label_offsets = {704: (-10, 8), 5209: (-8, 3), 5207: (-8, -5), 5206: (-18, -5),
                     726: (-4, 3), 5204: (3, 4), 5205: (0, -5), 4652: (-8, 4),
                     2113: (-5, 7), 2112: (5, 3)}
    row_y = 100
    total_dev = 0
    for pid, data in PROVINCES.items():
        chinese, _, area, goods, dev, cot = data
        colour = source_defs[pid][0]
        mask = np.all(result == colour, axis=2)
        py, px = np.where(mask)
        cx = int((px.mean() - x0) * scale)
        cy = int((py.mean() - y0) * scale)
        ox, oy = label_offsets.get(pid, (0, 0))
        label = chinese + ("★" if cot else "")
        draw.text((cx + ox, cy + oy), label, anchor="mm", fill=(255, 255, 255),
                  stroke_width=2, stroke_fill=(35, 35, 35), font=small)

        draw.rectangle((lx, row_y + 4, lx + 18, row_y + 22), fill=colour, outline=(45, 45, 45))
        dev_total = sum(dev)
        total_dev += dev_total
        cot_text = f"；贸{cot}" if cot else ""
        draw.text((lx + 28, row_y),
                  f"{chinese}  {dev[0]}/{dev[1]}/{dev[2]}={dev_total}  {GOODS_CN[goods]}{cot_text}",
                  fill=(35, 35, 35), font=body)
        row_y += 43

    row_y += 12
    draw.text((lx, row_y), f"总发展度：{total_dev}（税32／产32／兵30）", fill=(30, 30, 30), font=body)
    draw.text((lx, row_y + 38), "贸易中心：仅沈阳Ⅰ", fill=(30, 30, 30), font=body)
    draw.text((lx, row_y + 78), "★ 表示贸易中心；商品均取自原版 EU4", fill=(75, 75, 75), font=small)
    draw.text((lx, row_y + 108), "仅为预览，未写入正式 provinces.bmp", fill=(75, 75, 75), font=small)
    canvas.save(OUT / "liaoning_workshop_10_corrected_annotated.png")
    print(f"LIAONING_DRAFT; PROVINCES:{len(PROVINCES)}; DEV:{total_dev}; CHANGED:{int(changed.sum())}")


if __name__ == "__main__":
    main()
