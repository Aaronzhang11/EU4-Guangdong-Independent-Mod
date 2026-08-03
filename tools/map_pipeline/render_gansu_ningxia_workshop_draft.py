#!/usr/bin/env python3
"""Render a review-only Gansu and Ningxia draft from workshop 1728520255."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
SOURCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
FULL_OUTPUT = ROOT / "planning/gansu_ningxia_23_formal_base_draft.bmp"
CROP_OUTPUT = ROOT / "planning/gansu_ningxia_23_formal_base_crop.bmp"
REVIEW_OUTPUT = ROOT / "docs/map/previews/B26_gansu_ningxia_23_draft.png"

# The workshop canvas is the same projection, with 423 columns and 11 rows
# preceding the current mod's retained map extent. No resampling is needed.
SOURCE_X_OFFSET = 423
SOURCE_Y_OFFSET = 11


@dataclass(frozen=True)
class Cell:
    area: str
    name: str
    source_id: int
    goods: str
    development: int
    note: str


CELLS = (
    Cell("宁夏", "宁夏", 698, "盐", 11, "银川平原与区域集市"),
    Cell("宁夏", "中卫", 5285, "牲畜", 6, "黄河渡口与河套西门"),
    Cell("宁夏", "灵州", 5286, "粮食", 9, "黄河灌溉与东南门户"),
    Cell("宁夏", "松山", 5284, "牲畜", 5, "贺兰山南口军镇"),
    Cell("陇南", "秦州", 2180, "粮食", 11, "渭水上游、陇右都会"),
    Cell("陇南", "洮州", 2183, "牲畜", 7, "洮河谷地与番汉互市"),
    Cell("陇南", "阶州", 5279, "牲畜", 5, "白龙江谷地"),
    Cell("陇南", "岷州", 5280, "牲畜", 6, "岷山北麓商道"),
    Cell("陇南", "巩昌", 5281, "粮食", 8, "渭河—漳河盆地"),
    Cell("陇中", "西宁", 2184, "盐", 10, "河湟都会与茶马集市"),
    Cell("陇中", "兰州", 699, "铜", 13, "黄河枢纽、二级贸易中心"),
    Cell("陇中", "碾伯", 5288, "粮食", 6, "湟水谷地农牧交界"),
    Cell("陇中", "河州", 5287, "牲畜", 7, "黄河上游渡口与茶马互市"),
    Cell("陇中", "狄道", 5283, "粮食", 7, "洮河中游与陇中南门"),
    Cell("河西", "武威", 708, "牲畜", 10, "凉州都会与走廊东门"),
    Cell("河西", "靖远", 2182, "粮食", 6, "黄河峡谷；替代重复的凉州名"),
    Cell("河西", "永昌", 5289, "羊毛", 6, "祁连北麓牧业"),
    Cell("河西", "张掖", 5290, "粮食", 10, "黑河绿洲、一级贸易中心"),
    Cell("河西", "嘉峪", 5291, "铁矿", 6, "肃州东关与长城节点"),
    Cell("瓜沙", "玉门", 707, "宝石", 7, "走廊西端关市"),
    Cell("瓜沙", "瓜州", 5292, "羊毛", 5, "疏勒河绿洲"),
    Cell("瓜沙", "苦峪", 5293, "牲畜", 5, "安西通道与军镇"),
    Cell("瓜沙", "沙州", 5294, "丝绸", 8, "敦煌绿洲与西域商路"),
)

def definitions(path: Path) -> dict[int, tuple[int, int, int]]:
    result: dict[int, tuple[int, int, int]] = {}
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if fields[0].isdigit():
            result[int(fields[0])] = tuple(map(int, fields[1:4]))
    return result


def mask_for(bitmap: np.ndarray, colours: list[tuple[int, int, int]]) -> np.ndarray:
    packed = ((bitmap[:, :, 0].astype(np.uint32) << 16)
              | (bitmap[:, :, 1].astype(np.uint32) << 8)
              | bitmap[:, :, 2].astype(np.uint32))
    keys = np.asarray([(r << 16) | (g << 8) | b for r, g, b in colours], dtype=np.uint32)
    return np.isin(packed, keys)


def palette(count: int, forbidden: set[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    colours: list[tuple[int, int, int]] = []
    seed = 0
    while len(colours) < count:
        colour = ((47 + seed * 83) % 246 + 5,
                  (91 + seed * 137) % 246 + 5,
                  (163 + seed * 191) % 246 + 5)
        if colour not in forbidden and colour not in colours:
            colours.append(colour)
        seed += 1
    return colours


def fill_retired(bitmap: np.ndarray, retired: np.ndarray, forbidden: np.ndarray) -> np.ndarray:
    output = bitmap.copy()
    pending = retired.copy()
    queue: deque[tuple[int, int]] = deque()
    height, width = retired.shape
    for y, x in zip(*np.where(retired), strict=True):
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and not forbidden[ny, nx]:
                output[y, x] = bitmap[ny, nx]
                pending[y, x] = False
                queue.append((int(y), int(x)))
                break
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and pending[ny, nx]:
                output[ny, nx] = output[y, x]
                pending[ny, nx] = False
                queue.append((ny, nx))
    if pending.any():
        raise ValueError("Could not return all superseded Gansu pixels")
    return output


def label_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    x, y = int(np.median(xs)), int(np.median(ys))
    nearest = int(np.argmin((xs - x) ** 2 + (ys - y) ** 2))
    return int(xs[nearest]), int(ys[nearest])


def largest_component(mask: np.ndarray) -> np.ndarray:
    seen = np.zeros(mask.shape, dtype=bool)
    best: list[tuple[int, int]] = []
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
                if (0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1]
                        and mask[ny, nx] and not seen[ny, nx]):
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(component) > len(best):
            best = component
    result = np.zeros(mask.shape, dtype=bool)
    for y, x in best:
        result[y, x] = True
    return result


def main() -> None:
    source_defs = definitions(SOURCE / "map/definition.csv")
    current_defs = definitions(MOD / "map/definition.csv")
    source = np.asarray(Image.open(SOURCE / "map/provinces.bmp").convert("RGB"))
    current = np.asarray(Image.open(MOD / "map/provinces.bmp").convert("RGB"))
    translated = source[
        SOURCE_Y_OFFSET:SOURCE_Y_OFFSET + current.shape[0],
        SOURCE_X_OFFSET:SOURCE_X_OFFSET + current.shape[1],
    ]

    forbidden = set(current_defs.values()) | set(source_defs.values())
    colours = palette(len(CELLS), forbidden)
    # The current formal Gansu outline is absolute authority. Workshop pixels
    # are used only as subdivision seeds inside these eight existing cells;
    # no proposed colour is allowed to cross the current outer border.
    formal_ids = (698, 699, 2180, 2183, 707, 708, 2182, 2184)
    planned = mask_for(current, [current_defs[i] for i in formal_ids])
    labels = np.full(planned.shape, -1, dtype=np.int16)
    for index, cell in enumerate(CELLS):
        source_seed = np.all(translated == source_defs[cell.source_id], axis=2) & planned
        source_seed = largest_component(source_seed)
        if not source_seed.any():
            raise ValueError(f"Source cell does not touch formal Gansu: {cell.name}")
        labels[source_seed] = index

    # Grow the workshop-derived seeds through every remaining formal Gansu
    # pixel. This retains the current coastline/border pixel-for-pixel while
    # adapting the internal source boundaries to the current outline.
    queue: deque[tuple[int, int]] = deque(
        (int(y), int(x)) for y, x in zip(*np.where(labels >= 0), strict=True)
    )
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if (0 <= ny < labels.shape[0] and 0 <= nx < labels.shape[1]
                    and planned[ny, nx] and labels[ny, nx] == -1):
                labels[ny, nx] = labels[y, x]
                queue.append((ny, nx))
    if np.any(planned & (labels < 0)):
        raise ValueError("Formal Gansu mask contains an unreachable component")
    cell_masks = [labels == index for index in range(len(CELLS))]

    output = current.copy()
    for colour, cell_mask in zip(colours, cell_masks, strict=True):
        output[cell_mask] = colour

    FULL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(output, mode="RGB").save(FULL_OUTPUT, format="BMP")

    ys, xs = np.where(planned)
    pad = 12
    x0, x1 = max(0, int(xs.min()) - pad), min(output.shape[1], int(xs.max()) + pad + 1)
    y0, y1 = max(0, int(ys.min()) - pad), min(output.shape[0], int(ys.max()) + pad + 1)
    crop_array = output[y0:y1, x0:x1]
    Image.fromarray(crop_array, mode="RGB").save(CROP_OUTPUT, format="BMP")

    scale = 4
    map_panel = Image.fromarray(crop_array).resize(
        (crop_array.shape[1] * scale, crop_array.shape[0] * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (map_panel.width + 760, max(map_panel.height + 100, 1120)), (247, 245, 239))
    canvas.paste(map_panel, (30, 72))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 30)
    section = ImageFont.truetype(font_path, 20)
    body = ImageFont.truetype(font_path, 15)
    small = ImageFont.truetype(font_path, 13)
    draw.text((30, 20), "甘肃—宁夏二十三省 · 正式 provinces.bmp 内分割草案", font=title, fill=(34, 38, 40))

    for colour, cell, cell_mask in zip(colours, CELLS, cell_masks, strict=True):
        x, y = label_point(cell_mask)
        px, py = 30 + (x - x0) * scale, 72 + (y - y0) * scale
        box = draw.textbbox((px, py), cell.name, font=small, anchor="mm")
        draw.rounded_rectangle((box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2),
                               radius=3, fill=(253, 251, 245), outline=(43, 47, 49))
        draw.text((px, py), cell.name, font=small, fill=(25, 28, 30), anchor="mm")

    panel_x = map_panel.width + 55
    draw.rounded_rectangle((panel_x - 20, 72, canvas.width - 25, 1085), radius=16,
                           fill=(253, 252, 248), outline=(195, 192, 184), width=2)
    draw.text((panel_x, 94), "五个区域", font=section, fill=(35, 39, 41))
    y = 134
    for area in ("宁夏", "陇南", "陇中", "河西", "瓜沙"):
        members = [cell for cell in CELLS if cell.area == area]
        draw.text((panel_x, y), area, font=body, fill=(35, 39, 41))
        draw.text((panel_x + 58, y), " · ".join(cell.name for cell in members), font=small, fill=(70, 72, 69))
        y += 39
    draw.line((panel_x, y + 3, canvas.width - 50, y + 3), fill=(205, 201, 193), width=2)
    y += 24
    draw.text((panel_x, y), "经济建议", font=section, fill=(35, 39, 41)); y += 36
    for line in (
        "• 总发展度建议 174：宁夏31、陇南37、陇中43、河西38、瓜沙25",
        "• 核心贸易中心：兰州（二级）与张掖（一级）",
        "• 西宁、宁夏保留区域性集市，不再额外堆贸易中心",
        "• 商品仅用原版：粮食、牲畜、羊毛、盐、铜、铁、宝石、丝绸",
        "• 不新增不可通行省份或特殊地形机制",
        "• 正式甘宁外边界逐像素锁定，区域外不作任何覆盖",
        "• 武威与凉州同城，故源图东侧‘凉州’按位置改为靖远",
        "• 本图仅作规划预览，未写入正式 provinces.bmp",
    ):
        draw.text((panel_x, y), line, font=small, fill=(66, 69, 67)); y += 31
    canvas.save(REVIEW_OUTPUT)

    for cell, cell_mask in zip(CELLS, cell_masks, strict=True):
        if not cell_mask.any():
            raise ValueError(f"Empty planned province: {cell.name}")
    print(f"PLAYABLE:{len(CELLS)}; DEVELOPMENT:{sum(c.development for c in CELLS)}; MOUNTAINS:0")
    print(FULL_OUTPUT)
    print(CROP_OUTPUT)
    print(REVIEW_OUTPUT)


if __name__ == "__main__":
    main()
