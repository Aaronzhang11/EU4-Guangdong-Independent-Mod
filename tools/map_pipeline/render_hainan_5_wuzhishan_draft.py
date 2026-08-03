#!/usr/bin/env python3
"""Render a formal-base Hainan five-province and Wuzhishan draft."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
FULL_OUTPUT = ROOT / "planning/hainan_5_wuzhishan_formal_base_draft.bmp"
CROP_OUTPUT = ROOT / "planning/hainan_5_wuzhishan_crop.bmp"
PREVIEW_OUTPUT = ROOT / "docs/map/previews/B27_hainan_5_wuzhishan_draft.png"


@dataclass(frozen=True)
class Cell:
    name: str
    english: str
    colour: tuple[int, int, int]
    goods: str
    development: tuple[int, int, int]
    note: str


CELLS = (
    Cell("琼州", "Qiongzhou", (239,174,66), "粮食", (3,2,2), "北岸府城与琼州海峡门户"),
    Cell("儋州", "Danzhou", (196,91,74), "盐", (2,2,2), "西北海岸盐场与港湾"),
    Cell("昌化", "Changhua", (84,156,103), "热带木材", (2,2,1), "西南沿海林产与黎峒边缘"),
    Cell("崖州", "Yazhou", (59,141,183), "鱼类", (2,2,2), "南端港口与南海航路"),
    Cell("万州", "Wanzhou", (155,113,184), "香料", (2,2,2), "东岸季风港与热带作物"),
)
MOUNTAIN_NAME = "五指山"
MOUNTAIN_COLOUR = (92,88,84)


def definitions(path: Path) -> dict[int, tuple[int, int, int]]:
    output = {}
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if fields[0].isdigit():
            output[int(fields[0])] = tuple(map(int, fields[1:4]))
    return output


def coast_distance(mask: np.ndarray) -> np.ndarray:
    distance = np.full(mask.shape, 999, dtype=np.int16)
    queue: deque[tuple[int, int]] = deque()
    height, width = mask.shape
    for y, x in zip(*np.where(mask), strict=True):
        if any(not (0 <= y + dy < height and 0 <= x + dx < width)
               or not mask[y + dy, x + dx]
               for dy, dx in ((1,0),(-1,0),(0,1),(0,-1))):
            distance[y, x] = 1
            queue.append((int(y), int(x)))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = y + dy, x + dx
            if (0 <= ny < height and 0 <= nx < width and mask[ny, nx]
                    and distance[ny, nx] > distance[y, x] + 1):
                distance[ny, nx] = distance[y, x] + 1
                queue.append((ny, nx))
    return distance


def connected(mask: np.ndarray) -> bool:
    points = list(zip(*np.where(mask), strict=True))
    if not points:
        return False
    remaining = set((int(y),int(x)) for y,x in points)
    stack = [remaining.pop()]
    while stack:
        y,x = stack.pop()
        for point in ((y+1,x),(y-1,x),(y,x+1),(y,x-1)):
            if point in remaining:
                remaining.remove(point)
                stack.append(point)
    return not remaining


def components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    remaining = set((int(y),int(x)) for y,x in zip(*np.where(mask),strict=True))
    output: list[list[tuple[int,int]]] = []
    while remaining:
        stack=[remaining.pop()];component=[]
        while stack:
            y,x=stack.pop();component.append((y,x))
            for point in ((y+1,x),(y-1,x),(y,x+1),(y,x-1)):
                if point in remaining:
                    remaining.remove(point);stack.append(point)
        output.append(component)
    return output


def label_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    x, y = int(np.median(xs)), int(np.median(ys))
    nearest = int(np.argmin((xs-x)**2 + (ys-y)**2))
    return int(xs[nearest]), int(ys[nearest])


def main() -> None:
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB"))
    defs = definitions(MAP / "definition.csv")
    # Vanilla Hainan is split between Kiungchow (666) and Ngaichow (2160).
    # Their union, not province 666 alone, is the authoritative island mask.
    island = (np.all(current == defs[666], axis=2)
              | np.all(current == defs[2160], axis=2))
    if int(island.sum()) != 760:
        raise ValueError(f"Expected the two-province formal Hainan mask (760 pixels), found {island.sum()}")

    distance = coast_distance(island)
    # At this map scale distance ten produces a compact central ridge. It is
    # fully landlocked and large enough to remain legible without swallowing
    # the five coastal jurisdictions.
    mountain_candidate = island & (distance >= 10)
    main_ridge = max(components(mountain_candidate), key=len)
    mountain = np.zeros(island.shape, dtype=bool)
    for y,x in main_ridge:
        mountain[y,x] = True
    my, mx = np.where(mountain)
    centre_y, centre_x = float(my.mean()), float(mx.mean())
    labels = np.full(island.shape, -1, dtype=np.int8)
    for y, x in zip(*np.where(island & ~mountain), strict=True):
        angle = math.degrees(math.atan2(-(y-centre_y), x-centre_x))
        # Unequal angular spans compensate for Hainan's broad northern half,
        # keeping the five coastal provinces close in pixel area.
        if 50 <= angle < 126:
            label = 0  # Qiongzhou, northern coast
        elif angle >= 126 or angle < -150:
            label = 1  # Danzhou, northwest and west
        elif -150 <= angle < -76:
            label = 2  # Changhua, southwest
        elif -76 <= angle < 16:
            label = 3  # Yazhou, south
        else:
            label = 4  # Wanzhou, east
        labels[y, x] = label

    # At this tiny scale an angular boundary can leave a one-pixel splinter.
    # Return such splinters to the neighbouring coastal province with which
    # they share the longest edge; the five principal shapes remain intact.
    for index in range(len(CELLS)):
        groups=components(labels==index)
        if len(groups)<=1:
            continue
        keep=max(groups,key=len)
        for group in groups:
            if group is keep:
                continue
            neighbours=[]
            for y,x in group:
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny,nx=y+dy,x+dx
                    if 0<=ny<labels.shape[0] and 0<=nx<labels.shape[1] and labels[ny,nx]>=0 and labels[ny,nx]!=index:
                        neighbours.append(int(labels[ny,nx]))
            if not neighbours:
                raise ValueError(f"Cannot absorb fragment of {CELLS[index].name}")
            replacement=Counter(neighbours).most_common(1)[0][0]
            for y,x in group:
                labels[y,x]=replacement

    output = current.copy()
    masks = []
    for index, cell in enumerate(CELLS):
        cell_mask = labels == index
        if not connected(cell_mask):
            raise ValueError(f"Disconnected planned province: {cell.name}")
        masks.append(cell_mask)
        output[cell_mask] = cell.colour
    if not connected(mountain):
        raise ValueError("Wuzhishan is disconnected")
    # A distance-six core can never touch the coast, checked explicitly so a
    # future coastline edit cannot silently turn the mountain into a shoreline.
    if np.any(mountain & (distance == 1)):
        raise ValueError("Wuzhishan touches the coast")
    output[mountain] = MOUNTAIN_COLOUR

    FULL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(output, mode="RGB").save(FULL_OUTPUT, format="BMP")
    ys, xs = np.where(island)
    pad = 8
    x0, x1 = int(xs.min())-pad, int(xs.max())+pad+1
    y0, y1 = int(ys.min())-pad, int(ys.max())+pad+1
    crop = output[y0:y1, x0:x1]
    Image.fromarray(crop, mode="RGB").save(CROP_OUTPUT, format="BMP")

    scale = 20
    shown = Image.fromarray(crop).resize((crop.shape[1]*scale,crop.shape[0]*scale),Image.Resampling.NEAREST)
    canvas = Image.new("RGB",(shown.width+720,max(shown.height+100,900)),(247,245,239))
    canvas.paste(shown,(30,70))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path,30)
    label = ImageFont.truetype(font_path,16)
    body = ImageFont.truetype(font_path,15)
    small = ImageFont.truetype(font_path,13)
    draw.text((30,20),"海南五省与五指山 · 正式底图内分割草案",font=title,fill=(32,36,38))
    for cell, cell_mask in zip(CELLS,masks,strict=True):
        x,y=label_point(cell_mask);px=30+(x-x0)*scale;py=70+(y-y0)*scale
        box=draw.textbbox((px,py),cell.name,font=label,anchor="mm")
        draw.rounded_rectangle((box[0]-4,box[1]-3,box[2]+4,box[3]+3),radius=3,fill=(253,251,245),outline=(40,43,45))
        draw.text((px,py),cell.name,font=label,fill=(22,25,27),anchor="mm")
    x,y=label_point(mountain);px=30+(x-x0)*scale;py=70+(y-y0)*scale
    box=draw.textbbox((px,py),MOUNTAIN_NAME,font=label,anchor="mm")
    draw.rounded_rectangle((box[0]-4,box[1]-3,box[2]+4,box[3]+3),radius=3,fill=(245,242,235),outline=(30,30,30))
    draw.text((px,py),MOUNTAIN_NAME,font=label,fill=(20,20,20),anchor="mm")

    panel_x=shown.width+65
    draw.rounded_rectangle((panel_x-22,70,canvas.width-25,canvas.height-30),radius=16,fill=(253,252,248),outline=(195,192,184),width=2)
    draw.text((panel_x,92),"规划结构",font=ImageFont.truetype(font_path,21),fill=(35,39,41))
    y=136
    for cell in CELLS:
        draw.rounded_rectangle((panel_x,y,panel_x+24,y+24),radius=3,fill=cell.colour)
        draw.text((panel_x+35,y),cell.name,font=body,fill=(35,39,41))
        draw.text((panel_x+95,y+1),f"{cell.goods} · {sum(cell.development)}发展度",font=small,fill=(73,75,72))
        draw.text((panel_x+260,y+1),cell.note,font=small,fill=(73,75,72))
        y+=48
    draw.rounded_rectangle((panel_x,y,panel_x+24,y+24),radius=3,fill=MOUNTAIN_COLOUR)
    draw.text((panel_x+35,y),"五指山",font=body,fill=(35,39,41))
    draw.text((panel_x+95,y+1),"不可通行 · 0发展度",font=small,fill=(73,75,72));y+=55
    draw.line((panel_x,y,canvas.width-50,y),fill=(205,201,193),width=2);y+=24
    for line in (
        "• 五个沿海省份组成独立的海南区域",
        "• 五指山完全位于岛内，不接触海岸",
        "• 五省均可沿海岸相互连通，中央不可直接横穿",
        "• 五省合计30发展度；全岛不设置贸易中心",
        "• 商品全部使用原版：粮食、盐、热带木材、鱼类、香料",
        "• 本图仅为规划预览，未覆盖正式 provinces.bmp",
    ):
        draw.text((panel_x,y),line,font=small,fill=(66,69,67));y+=31
    canvas.save(PREVIEW_OUTPUT)
    counts={cell.name:int(mask.sum()) for cell,mask in zip(CELLS,masks,strict=True)}
    print(f"HAINAN_DRAFT:5; WUZHISHAN:{int(mountain.sum())}; DEVELOPMENT:30; PIXELS:{counts}")
    print(FULL_OUTPUT);print(CROP_OUTPUT);print(PREVIEW_OUTPUT)


if __name__ == "__main__":
    main()
