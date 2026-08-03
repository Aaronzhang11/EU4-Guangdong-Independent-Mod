#!/usr/bin/env python3
"""Render a non-canonical Shanxi draft from workshop 1728520255 geometry."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
SOURCE = Path("/Users/xinanyapiao/Library/Application Support/Steam/steamapps/workshop/content/236850/1728520255")
FULL_OUTPUT = ROOT / "planning/shanxi_20_mountain_draft.bmp"
CROP_OUTPUT = ROOT / "planning/shanxi_20_mountain_crop.bmp"
REVIEW_OUTPUT = ROOT / "docs/map/previews/B23_shanxi_20_mountain_draft.png"
CROP = (4480, 675, 4635, 845)


@dataclass(frozen=True)
class Cell:
    area: str
    chinese: str
    source_ids: tuple[int, ...]
    colour: tuple[int, int, int]
    goods: str
    note: str


CELLS = (
    Cell("晋北", "大同", (697,), (218,88,72), "铁矿", "北方军镇、边市"),
    Cell("晋北", "右玉", (5253,), (236,160,55), "牲畜", "杀虎口通道"),
    Cell("晋北", "朔州", (5254,), (226,200,66), "粮食", "桑干河上游"),
    Cell("晋北", "宁武", (2177,), (137,191,64), "牲畜", "宁武关军镇"),
    Cell("晋北", "代州", (5252,5256), (65,172,104), "马匹", "雁门关—滹沱河谷；吸收蔚州草图块"),
    Cell("晋中", "太原", (693,), (58,164,160), "布匹", "晋阳盆地、二级贸易中心"),
    Cell("晋中", "忻州", (5255,), (62,144,197), "粮食", "忻定盆地"),
    Cell("晋中", "平定", (5257,), (89,112,203), "铁矿", "娘子关门户"),
    Cell("晋中", "辽州", (5261,), (137,91,198), "铁矿", "太行西麓谷地"),
    Cell("吕梁", "离石", (5258,), (185,82,175), "牲畜", "吕梁山西麓"),
    Cell("吕梁", "隰州", (5259,), (215,85,130), "牲畜", "黄河东岸山地"),
    Cell("吕梁", "汾州", (5260,), (193,120,74), "酒", "汾河中游商埠"),
    Cell("河东", "平阳", (694,), (106,153,74), "布匹", "临汾盆地北部与河东都会"),
    Cell("河东", "绛州", (), (201,116,92), "粮食", "汾水下游西岸与故绛走廊"),
    Cell("河东", "曲沃", (), (224,84,111), "布匹", "古晋都邑与汾水下游节点"),
    Cell("河东", "潞安", (2178,), (63,126,95), "铁矿", "上党盆地"),
    Cell("河东", "沁州", (5262,), (75,135,174), "布匹", "沁河谷地"),
    Cell("河东", "泽州", (5263,), (111,90,160), "煤炭", "太行南端矿业"),
    Cell("河东", "解州", (5264,), (173,81,86), "盐", "运城盆地与解盐池"),
    Cell("河东", "蒲州", (), (211,139,69), "粮食", "黄河蒲津渡与关中通道"),
)

MOUNTAINS = (
    Cell("山脉", "恒五山", (5177,), (124,124,134), "不可通行", "恒山—五台山核心，雁门通口保留"),
    Cell("山脉", "太行北山", (5178,), (82,82,92), "不可通行", "北段山脊，娘子关留口"),
    Cell("山脉", "太行南山", (5179,), (72,72,82), "不可通行", "南段山脊，壶关、天井关留口"),
    Cell("山脉", "吕梁山", (5181,), (102,96,108), "不可通行", "晋中与黄河东岸间的山脊"),
    Cell("山脉", "中条山", (5180,), (118,105,92), "不可通行", "河东盆地南缘，轵关陉留口"),
)


def definitions(path: Path) -> tuple[dict[int, tuple[int, int, int]], dict[tuple[int, int, int], int]]:
    by_id: dict[int, tuple[int, int, int]] = {}
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        fields = line.split(";")
        if fields[0].isdigit():
            by_id[int(fields[0])] = tuple(map(int, fields[1:4]))
    return by_id, {colour: province_id for province_id, colour in by_id.items()}


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
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx] = True
                    stack.append((ny,nx))
        if len(component) > len(best):
            best = component
    output = np.zeros(mask.shape, dtype=bool)
    for y, x in best:
        output[y, x] = True
    return output


def main() -> None:
    source_defs, source_reverse = definitions(SOURCE / "map/definition.csv")
    current_defs, _current_reverse = definitions(MOD / "map/definition.csv")
    source = np.array(Image.open(SOURCE / "map/provinces.bmp").convert("RGB"), dtype=np.uint8)
    current = np.array(Image.open(MOD / "map/provinces.bmp").convert("RGB"), dtype=np.uint8)

    # Geographical alignment between the source's 6400x2560 canvas and this
    # mod's 5632x2048 canvas. The target mask comes from the source Shanxi
    # outline itself, so the draft can also correct the current five-province
    # outer border instead of clipping Zezhou and Hedong at that old boundary.
    yy, xx = np.mgrid[675:845, 4480:4635]
    yy = yy.ravel(); xx = xx.ravel()
    source_x = np.rint(4956 + (xx - 4529) * (82 / 72)).astype(int)
    source_y = np.rint(yy + 1).astype(int)
    sampled = source[source_y, source_x]
    sampled_ids = np.array([source_reverse.get(tuple(map(int, colour)), -1) for colour in sampled], dtype=int)

    labels = np.full(current.shape[:2], -1, dtype=np.int16)
    cell_by_source = {source_id: index for index, cell in enumerate(CELLS) for source_id in cell.source_ids}
    mountain_by_source = {source_id: len(CELLS) + index for index, cell in enumerate(MOUNTAINS) for source_id in cell.source_ids}
    for y, x, source_id in zip(yy, xx, sampled_ids, strict=True):
        if source_id in cell_by_source:
            labels[y, x] = cell_by_source[source_id]
        elif source_id in mountain_by_source:
            labels[y, x] = mountain_by_source[source_id]

    # The political map needs a denser southern Jin theatre than the source
    # mod. Split Pingyang into Pingyang/Jiangzhou/Quwo and the old Hedong block
    # into Jiezhou/Puzhou, following the lower Fen and Yellow River directions.
    by_name = {cell.chinese:index for index,cell in enumerate(CELLS)}
    pingyang_mask = labels == by_name["平阳"]
    py_y, py_x = np.where(pingyang_mask)
    py_mid_y = float(np.quantile(py_y, 0.47))
    py_mid_x = float(np.quantile(py_x, 0.50))
    lower = pingyang_mask & (np.indices(labels.shape)[0] > py_mid_y)
    labels[lower & (np.indices(labels.shape)[1] <= py_mid_x)] = by_name["绛州"]
    labels[lower & (np.indices(labels.shape)[1] > py_mid_x)] = by_name["曲沃"]

    jie_mask = labels == by_name["解州"]
    jie_y, jie_x = np.where(jie_mask)
    split_x = float(np.quantile(jie_x, 0.44))
    # A slight south-east tilt follows the salt-lake basin rather than making
    # a ruler-straight vertical border.
    jie_y_mid = float(np.median(jie_y))
    grid_y, grid_x = np.indices(labels.shape)
    puzhou = jie_mask & (grid_x < split_x + 0.18 * (grid_y - jie_y_mid))
    labels[puzhou] = by_name["蒲州"]

    # A source wasteland ID can contain detached raster fragments. EU4
    # province colours must be contiguous, so keep the principal ridge and
    # return minor fragments to the nearest playable province.
    target = labels >= 0
    for index in range(len(CELLS), len(CELLS) + len(MOUNTAINS)):
        core = largest_component(labels == index)
        labels[(labels == index) & ~core] = -1
    queue: deque[tuple[int, int]] = deque()
    for y, x in zip(*np.where((labels >= 0) & (labels < len(CELLS))), strict=True):
        queue.append((int(y), int(x)))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < labels.shape[0] and 0 <= nx < labels.shape[1] and target[ny,nx] and labels[ny,nx] == -1:
                labels[ny,nx] = labels[y,x]
                queue.append((ny,nx))

    all_cells = CELLS + MOUNTAINS
    output = current.copy()
    # The source outline is narrower than the old five-province Shanxi in a
    # few places. Return every superseded Shanxi pixel outside the new outline
    # to the adjacent non-Shanxi province, otherwise retained RGBs become
    # detached flying enclaves after formalisation.
    managed_ids = {693,694,697,2177,2178,*range(5242,5262)}
    old_shanxi = np.zeros(current.shape[:2],dtype=bool)
    for province_id in managed_ids:
        if province_id in current_defs:
            old_shanxi |= np.all(current == np.asarray(current_defs[province_id],dtype=np.uint8),axis=2)
    clear = old_shanxi & ~target
    pending = clear.copy()
    queue.clear()
    for y,x in zip(*np.where(clear),strict=True):
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=y+dy,x+dx
            if 0<=ny<pending.shape[0] and 0<=nx<pending.shape[1] and not clear[ny,nx] and not target[ny,nx]:
                output[y,x]=output[ny,nx];pending[y,x]=False;queue.append((int(y),int(x)));break
    while queue:
        y,x=queue.popleft()
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=y+dy,x+dx
            if 0<=ny<pending.shape[0] and 0<=nx<pending.shape[1] and pending[ny,nx]:
                output[ny,nx]=output[y,x];pending[ny,nx]=False;queue.append((ny,nx))
    if pending.any():
        raise ValueError("Could not return all superseded Shanxi pixels")
    for index, cell in enumerate(all_cells):
        if not np.any(labels == index):
            raise ValueError(f"Draft cell is empty: {cell.chinese}")
        output[labels == index] = cell.colour
    FULL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(output, mode="RGB").save(FULL_OUTPUT, format="BMP")

    left, top, right, bottom = CROP
    crop = Image.fromarray(output[top:bottom, left:right], mode="RGB")
    crop.save(CROP_OUTPUT, format="BMP")
    scale = 6
    map_panel = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (1840, 1110), (247,245,239))
    canvas.paste(map_panel, (30,70))
    draw = ImageDraw.Draw(canvas)
    font_path = Path("/System/Library/Fonts/STHeiti Medium.ttc")
    title_font = ImageFont.truetype(str(font_path), 30)
    label_font = ImageFont.truetype(str(font_path), 14)
    small_font = ImageFont.truetype(str(font_path), 13)
    draw.text((30,20), "山西二十省与四大山系 · 世界观政治图修订草图", font=title_font, fill=(35,39,41))

    for index, cell in enumerate(all_cells):
        cell_mask = labels == index
        ys, xs = np.where(cell_mask)
        x = int(np.median(xs)); y = int(np.median(ys))
        # Snap median to an actual pixel of the cell.
        nearest = int(np.argmin((xs-x)**2 + (ys-y)**2)); x=int(xs[nearest]); y=int(ys[nearest])
        px = 30 + (x-left)*scale; py = 70 + (y-top)*scale
        box = draw.textbbox((px,py), cell.chinese, font=label_font, anchor="mm")
        draw.rounded_rectangle((box[0]-3,box[1]-2,box[2]+3,box[3]+2), radius=3, fill=(252,250,244), outline=(45,48,50))
        draw.text((px,py), cell.chinese, font=label_font, fill=(24,27,29), anchor="mm")

    panel_x = 990
    draw.rounded_rectangle((970,70,1810,1080), radius=16, fill=(253,252,248), outline=(195,192,184), width=2)
    draw.text((panel_x,92), "规划结构", font=ImageFont.truetype(str(font_path),22), fill=(38,42,44))
    y = 135
    for area in ("晋北","晋中","吕梁","河东"):
        names = " · ".join(cell.chinese for cell in CELLS if cell.area == area)
        draw.text((panel_x,y), area, font=label_font, fill=(35,39,41))
        draw.text((panel_x+65,y), names, font=small_font, fill=(72,74,71))
        y += 42
    draw.line((panel_x,y+5,1785,y+5), fill=(204,201,193), width=2); y += 28
    draw.text((panel_x,y), "不可通行山脉", font=ImageFont.truetype(str(font_path),19), fill=(38,42,44)); y += 36
    for cell in MOUNTAINS:
        draw.rounded_rectangle((panel_x,y,panel_x+23,y+23), radius=3, fill=cell.colour)
        draw.text((panel_x+34,y), cell.chinese, font=label_font, fill=(40,43,45))
        draw.text((panel_x+120,y+1), cell.note, font=small_font, fill=(82,83,79))
        y += 43
    draw.line((panel_x,y+5,1785,y+5), fill=(204,201,193), width=2); y += 28
    draw.text((panel_x,y), "经济与节点建议", font=ImageFont.truetype(str(font_path),19), fill=(38,42,44)); y += 35
    notes = (
        "• 太原：布匹，二级贸易中心与要塞",
        "• 大同：铁矿，一级边贸与九边军镇",
        "• 解州：盐；泽州、平定、潞安表现煤铁矿业",
        "• 曲沃、绛州强化河东南部的都邑与交通层次",
        "• 全省建议总发展度约112，不可通行山脉为0",
        "• 蔚州、宣化不纳入山西，避免侵入燕赵舞台",
        "• 山脉保留关隘通道，不形成整条无出口石墙",
        "• 本图仅为草图，不覆盖正式 provinces.bmp",
    )
    for note in notes:
        draw.text((panel_x,y), note, font=small_font, fill=(70,72,69)); y += 31
    canvas.save(REVIEW_OUTPUT)

    counts = {cell.chinese: int(np.count_nonzero(labels == index)) for index,cell in enumerate(all_cells)}
    print(FULL_OUTPUT)
    print(CROP_OUTPUT)
    print(REVIEW_OUTPUT)
    print(counts)


if __name__ == "__main__":
    main()
