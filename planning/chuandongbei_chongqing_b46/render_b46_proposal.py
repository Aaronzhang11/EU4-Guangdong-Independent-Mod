#!/usr/bin/env python3
"""Render a non-canonical B46 second-refinement proposal.

The script reads the current canonical provinces.bmp, subdivides only the
reviewed parent masks in memory, and writes preview PNGs.  It never writes any
game-loaded map file.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import csv

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/chuandongbei_chongqing_b46"

PARENT_IDS = {5081, 2169, 5082, 4211, 680, 5026, 5027, 4987}
UNCHANGED_IDS = {5080, 5028}
TARGET_IDS = PARENT_IDS | UNCHANGED_IDS


@dataclass(frozen=True)
class Cell:
    province_id: int
    name: str
    parent_id: int
    seed_x: float
    seed_y: float
    development: int
    polity: str
    area: str
    new: bool = False


# Normalised seeds are measured inside each current parent province bounding box.
# They are planning geometry only; the formal implementation would freeze and
# audit the reviewed pixel mask before assigning permanent colours.
CELLS = (
    Cell(5080, "绵州", 5080, .50, .50, 12, "蜀", "剑阆"),
    Cell(5081, "剑州", 5081, .38, .70, 4, "苴", "剑阆"),
    Cell(5329, "昭化", 5081, .60, .22, 4, "苴", "剑阆", True),
    Cell(2169, "阆中", 2169, .28, .58, 6, "巴", "剑阆"),
    Cell(5330, "巴州", 2169, .78, .38, 4, "宕渠", "巴渠", True),
    Cell(5082, "顺庆", 5082, .28, .70, 6, "巴", "巴渠"),
    Cell(5331, "蓬州", 5082, .70, .25, 5, "巴", "巴渠", True),
    Cell(4211, "达州", 4211, .62, .27, 4, "宕渠", "巴渠"),
    Cell(5332, "渠州", 4211, .34, .76, 4, "宕渠", "巴渠", True),
    Cell(5026, "合州", 5026, .66, .27, 6, "巴", "巴渝"),
    Cell(5333, "昌州", 5026, .25, .76, 4, "巴", "巴渝", True),
    Cell(680, "重庆", 680, .63, .30, 11, "巴", "巴渝"),
    Cell(5334, "江津", 680, .27, .78, 8, "巴", "巴渝", True),
    Cell(5027, "涪州", 5027, .55, .20, 4, "枳", "涪陵"),
    Cell(5335, "南川", 5027, .20, .66, 3, "枳", "涪陵", True),
    Cell(5336, "彭水", 5027, .78, .78, 3, "枳", "涪陵", True),
    Cell(4987, "万州", 4987, .58, .48, 4, "宕渠", "峡江"),
    Cell(5337, "忠州", 4987, .22, .78, 3, "枳", "涪陵", True),
    Cell(5338, "开州", 4987, .30, .14, 3, "宕渠", "峡江", True),
    Cell(5028, "夔州", 5028, .50, .50, 8, "巴氐", "峡江"),
)

POLITY_COLORS = {
    "蜀": (223, 146, 46),
    "苴": (164, 117, 54),
    "巴": (53, 131, 181),
    "宕渠": (69, 151, 108),
    "枳": (162, 91, 151),
    "巴氐": (126, 90, 72),
}
AREA_COLORS = {
    "剑阆": (218, 158, 67),
    "巴渠": (94, 157, 117),
    "巴渝": (75, 132, 187),
    "涪陵": (164, 102, 163),
    "峡江": (93, 104, 170),
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size, index=1 if bold else 0)
    return ImageFont.load_default()


def definitions() -> tuple[dict[tuple[int, int, int], int], dict[int, tuple[int, int, int]]]:
    rgb_to_id: dict[tuple[int, int, int], int] = {}
    id_to_rgb: dict[int, tuple[int, int, int]] = {}
    with (MAP / "definition.csv").open(encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if len(row) < 4 or not row[0].isdigit():
                continue
            province_id = int(row[0])
            rgb = tuple(map(int, row[1:4]))
            rgb_to_id[rgb] = province_id
            id_to_rgb[province_id] = rgb
    return rgb_to_id, id_to_rgb


def largest_component(mask: np.ndarray) -> np.ndarray:
    seen = np.zeros(mask.shape, dtype=bool)
    best: list[tuple[int, int]] = []
    height, width = mask.shape
    for sy, sx in zip(*np.where(mask), strict=True):
        if seen[sy, sx]:
            continue
        queue = [(int(sy), int(sx))]
        seen[sy, sx] = True
        component: list[tuple[int, int]] = []
        while queue:
            y, x = queue.pop()
            component.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        if len(component) > len(best):
            best = component
    output = np.zeros(mask.shape, dtype=bool)
    for y, x in best:
        output[y, x] = True
    return output


def nearest_mask_point(mask: np.ndarray, target_x: float, target_y: float) -> tuple[int, int]:
    ys, xs = np.where(mask)
    index = np.argmin((xs - target_x) ** 2 + (ys - target_y) ** 2)
    return int(xs[index]), int(ys[index])


def split_parent(parent_mask: np.ndarray, children: list[Cell]) -> dict[int, np.ndarray]:
    ys, xs = np.where(parent_mask)
    min_x, max_x = int(xs.min()), int(xs.max())
    min_y, max_y = int(ys.min()), int(ys.max())
    width = max(1, max_x - min_x)
    height = max(1, max_y - min_y)
    seeds = []
    for cell in children:
        tx = min_x + cell.seed_x * width
        ty = min_y + cell.seed_y * height
        seeds.append(nearest_mask_point(parent_mask, tx, ty))
    distance = np.stack([
        ((xs - sx) / width) ** 2 + ((ys - sy) / height) ** 2
        for sx, sy in seeds
    ])
    choices = np.argmin(distance, axis=0)
    result: dict[int, np.ndarray] = {}
    for index, cell in enumerate(children):
        mask = np.zeros(parent_mask.shape, dtype=bool)
        mask[ys[choices == index], xs[choices == index]] = True
        result[cell.province_id] = largest_component(mask)

    # Any concavity crumbs are assigned to the neighbouring child with the
    # longest shared edge, preserving the complete parent mask.
    assigned = np.zeros(parent_mask.shape, dtype=bool)
    for mask in result.values():
        assigned |= mask
    leftovers = parent_mask & ~assigned
    while leftovers.any():
        progress = False
        for province_id, mask in result.items():
            neighbours = np.zeros(mask.shape, dtype=bool)
            neighbours[1:] |= mask[:-1]
            neighbours[:-1] |= mask[1:]
            neighbours[:, 1:] |= mask[:, :-1]
            neighbours[:, :-1] |= mask[:, 1:]
            take = leftovers & neighbours
            if take.any():
                result[province_id] |= take
                leftovers &= ~take
                progress = True
        if not progress:
            break
    if leftovers.any():
        raise RuntimeError("Unable to assign all planning pixels")
    return result


def build_cells() -> tuple[np.ndarray, dict[int, np.ndarray], tuple[int, int, int, int]]:
    _, id_to_rgb = definitions()
    values = np.array(Image.open(MAP / "provinces.bmp").convert("RGB"), dtype=np.uint8)
    masks: dict[int, np.ndarray] = {}
    for parent_id in sorted(TARGET_IDS):
        rgb = np.asarray(id_to_rgb[parent_id], dtype=np.uint8)
        parent_mask = np.all(values == rgb, axis=2)
        children = [cell for cell in CELLS if cell.parent_id == parent_id]
        if len(children) == 1:
            masks[children[0].province_id] = largest_component(parent_mask)
        else:
            masks.update(split_parent(parent_mask, children))
    union = np.zeros(values.shape[:2], dtype=bool)
    for mask in masks.values():
        union |= mask
    ys, xs = np.where(union)
    box = (int(xs.min()) - 5, int(ys.min()) - 5, int(xs.max()) + 6, int(ys.max()) + 6)
    return values, masks, box


def border(mask: np.ndarray) -> np.ndarray:
    inside = mask.copy()
    eroded = mask.copy()
    eroded[1:] &= mask[:-1]
    eroded[:-1] &= mask[1:]
    eroded[:, 1:] &= mask[:, :-1]
    eroded[:, :-1] &= mask[:, 1:]
    return inside & ~eroded


def component_count(mask: np.ndarray) -> int:
    seen = np.zeros(mask.shape, dtype=bool)
    count = 0
    height, width = mask.shape
    for sy, sx in zip(*np.where(mask), strict=True):
        if seen[sy, sx]:
            continue
        count += 1
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        while stack:
            y, x = stack.pop()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
    return count


def audit_groups(masks: dict[int, np.ndarray], attribute: str) -> dict[str, int]:
    by_id = {cell.province_id: cell for cell in CELLS}
    shape = next(iter(masks.values())).shape
    unions: dict[str, np.ndarray] = {}
    for province_id, mask in masks.items():
        key = getattr(by_id[province_id], attribute)
        unions.setdefault(key, np.zeros(shape, dtype=bool))
        unions[key] |= mask
    return {key: component_count(mask) for key, mask in unions.items()}


def label_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    cx, cy = float(xs.mean()), float(ys.mean())
    index = np.argmin((xs - cx) ** 2 + (ys - cy) ** 2)
    return int(xs[index]), int(ys[index])


def render_panel(masks: dict[int, np.ndarray], box: tuple[int, int, int, int], mode: str) -> Image.Image:
    left, top, right, bottom = box
    scale = 7
    canvas = np.full((bottom - top, right - left, 3), (230, 226, 215), dtype=np.uint8)
    by_id = {cell.province_id: cell for cell in CELLS}
    palette = POLITY_COLORS if mode == "polity" else AREA_COLORS
    for province_id, full_mask in masks.items():
        mask = full_mask[top:bottom, left:right]
        cell = by_id[province_id]
        key = cell.polity if mode == "polity" else cell.area
        canvas[mask] = palette[key]
    for full_mask in masks.values():
        mask = full_mask[top:bottom, left:right]
        canvas[border(mask)] = (250, 248, 240)
    image = Image.fromarray(canvas).resize(
        ((right - left) * scale, (bottom - top) * scale), Image.Resampling.NEAREST
    )
    draw = ImageDraw.Draw(image)
    label_font = font(18, True)
    small_font = font(13)
    for province_id, full_mask in masks.items():
        local = full_mask[top:bottom, left:right]
        x, y = label_point(local)
        x, y = x * scale, y * scale
        cell = by_id[province_id]
        title = ("★" if cell.new else "") + cell.name
        sub = f"{cell.development}发展"
        title_box = draw.textbbox((0, 0), title, font=label_font)
        sub_box = draw.textbbox((0, 0), sub, font=small_font)
        width = max(title_box[2], sub_box[2]) + 8
        height = title_box[3] + sub_box[3] + 8
        rect = (x - width // 2, y - height // 2, x + width // 2, y + height // 2)
        draw.rounded_rectangle(rect, radius=4, fill=(250, 247, 238), outline=(45, 45, 45), width=1)
        draw.text((x - title_box[2] // 2, rect[1] + 2), title, font=label_font, fill=(25, 25, 25))
        draw.text((x - sub_box[2] // 2, rect[1] + title_box[3] + 3), sub, font=small_font, fill=(75, 75, 75))
    return image


def compose(panel: Image.Image, mode: str, filename: str) -> None:
    palette = POLITY_COLORS if mode == "polity" else AREA_COLORS
    title = "川东北—重庆第二轮细化：国家方案" if mode == "polity" else "川东北—重庆第二轮细化：区域方案"
    subtitle = "当前10省 → 方案20省；★为新增省份；总发展度保持不变"
    margin = 34
    legend_width = 390
    canvas = Image.new("RGB", (panel.width + legend_width + margin * 3, panel.height + 150), (247, 244, 236))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 20), title, font=font(30, True), fill=(35, 35, 35))
    draw.text((margin, 62), subtitle, font=font(17), fill=(90, 90, 90))
    canvas.paste(panel, (margin, 105))
    x = margin * 2 + panel.width
    draw.rounded_rectangle((x, 105, x + legend_width, panel.height + 105), radius=14, fill=(252, 250, 245), outline=(190, 184, 170))
    draw.text((x + 24, 127), "国家归属" if mode == "polity" else "Area 分组", font=font(24, True), fill=(40, 40, 40))
    y = 176
    by_id = {cell.province_id: cell for cell in CELLS}
    for key, color in palette.items():
        members = [cell.name for cell in CELLS if (cell.polity if mode == "polity" else cell.area) == key]
        dev = sum(cell.development for cell in CELLS if (cell.polity if mode == "polity" else cell.area) == key)
        draw.rounded_rectangle((x + 24, y, x + 48, y + 24), radius=4, fill=color)
        draw.text((x + 60, y - 2), f"{key}  {dev}发展", font=font(18, True), fill=(40, 40, 40))
        y += 30
        text = "、".join(members)
        draw.multiline_text((x + 60, y), text, font=font(14), fill=(85, 85, 85), spacing=4)
        y += 42 if len(text) < 17 else 62
    y = max(y + 10, panel.height + 105 - 150)
    draw.line((x + 24, y, x + legend_width - 24, y), fill=(205, 200, 188), width=1)
    y += 17
    notes = [
        "• 只拆现有大省，不抬区域总发展度",
        "• 巴保留嘉陵江—重庆主轴，但不再吞并整个川东北",
        "• 新增宕渠、枳两个小国，形成山地缓冲",
        "• 夔州继续归巴氐，剑州—昭化归苴",
    ]
    for note in notes:
        draw.text((x + 24, y), note, font=font(14), fill=(70, 70, 70))
        y += 28
    canvas.save(OUT / filename)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _, masks, box = build_cells()
    compose(render_panel(masks, box, "polity"), "polity", "b46_country_preview.png")
    compose(render_panel(masks, box, "area"), "area", "b46_area_preview.png")
    province_components = {province_id: component_count(mask) for province_id, mask in masks.items()}
    area_components = audit_groups(masks, "area")
    polity_components = audit_groups(masks, "polity")
    if set(province_components.values()) != {1}:
        raise RuntimeError(f"Fragmented proposed province: {province_components}")
    if set(area_components.values()) != {1}:
        raise RuntimeError(f"Fragmented proposed Area: {area_components}")
    if set(polity_components.values()) != {1}:
        raise RuntimeError(f"Fragmented proposed polity: {polity_components}")
    print(f"Rendered {len(masks)} provinces; new={sum(cell.new for cell in CELLS)}")
    print(f"Target development={sum(cell.development for cell in CELLS)}")
    print(f"Area components={area_components}")
    print(f"Polity components={polity_components}")
    print(f"Pixel counts={{{', '.join(f'{pid}: {int(mask.sum())}' for pid, mask in sorted(masks.items()))}}}")


if __name__ == "__main__":
    main()
