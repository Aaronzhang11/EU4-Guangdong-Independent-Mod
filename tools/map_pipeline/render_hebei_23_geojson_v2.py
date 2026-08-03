#!/usr/bin/env python3
"""Render the balanced, smoothed V2 of the 23-province Hebei preview."""

from __future__ import annotations

from collections import Counter, deque
import heapq
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render_hebei_23_geojson_draft as base


TARGET_SIZES = np.array([
    350, 250, 300, 220,       # Xuanzhen
    850, 800, 450,            # Yanbei
    220, 220, 50,             # Yongping; Shanhaiguan is deliberately tiny
    180, 180, 250, 300,       # Baohe
    170, 220, 160, 100,       # Heng-Zhao
    130, 130, 110, 110, 142,  # Jinan
], dtype=np.int32)


def distance_fields(mask: np.ndarray, guide: np.ndarray, seeds):
    """GeoJSON-guided graph distances from every historical seat."""
    height, width = mask.shape
    fields = np.full((len(seeds), height, width), np.inf, dtype=np.float32)
    moves = [(-1, 0, 10), (1, 0, 10), (0, -1, 10), (0, 1, 10),
             (-1, -1, 14), (-1, 1, 14), (1, -1, 14), (1, 1, 14)]
    for source, (_, sx, sy, _) in enumerate(seeds):
        queue = [(0.0, sx, sy)]
        fields[source, sy, sx] = 0.0
        while queue:
            cost, x, y = heapq.heappop(queue)
            if cost != fields[source, y, x]:
                continue
            for dx, dy, step in moves:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < height and mask[ny, nx]):
                    continue
                crossing = guide[y, x] > 0 and guide[ny, nx] > 0 and guide[y, x] != guide[ny, nx]
                new = cost + step + (22 if crossing else 0)
                if new < fields[source, ny, nx]:
                    fields[source, ny, nx] = new
                    heapq.heappush(queue, (new, nx, ny))
    return fields


def balanced_owner(fields: np.ndarray, mask: np.ndarray, targets: np.ndarray):
    """Solve an additively weighted geodesic Voronoi diagram."""
    biases = np.zeros(fields.shape[0], dtype=np.float32)
    owner = np.full(mask.shape, -1, dtype=np.int16)
    for iteration in range(1200):
        scores = fields + biases[:, None, None]
        owner[mask] = np.argmin(scores[:, mask], axis=0)
        counts = np.bincount(owner[mask], minlength=len(targets))
        error = counts - targets
        if np.max(np.abs(error)) <= 3:
            break
        rate = max(1.2, 9.0 * (1.0 - iteration / 1400.0))
        biases += rate * np.log((counts + 1.0) / (targets + 1.0))
        biases -= biases.mean()
    return owner, fields + biases[:, None, None]


def components(owner: np.ndarray, province: int):
    target = owner == province
    seen = np.zeros(target.shape, dtype=bool)
    result = []
    for sy, sx in zip(*np.nonzero(target)):
        if seen[sy, sx]:
            continue
        queue = deque([(sx, sy)])
        seen[sy, sx] = True
        comp = []
        while queue:
            x, y = queue.popleft()
            comp.append((x, y))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < target.shape[1] and 0 <= ny < target.shape[0] and target[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((nx, ny))
        result.append(comp)
    return result


def repair_connectivity(owner: np.ndarray, scores: np.ndarray, seeds, protected: np.ndarray, closed=frozenset()):
    """Move detached components to their best bordering province."""
    for _ in range(8):
        changed = False
        for province, (_, sx, sy, _) in enumerate(seeds):
            comps = components(owner, province)
            if len(comps) <= 1:
                continue
            keep = next((comp for comp in comps if (sx, sy) in comp), max(comps, key=len))
            keep_set = set(keep)
            for comp in comps:
                if comp is keep or comp == keep or any((x, y) in keep_set for x, y in comp):
                    continue
                for x, y in comp:
                    if protected[y, x]:
                        continue
                    candidates = []
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < owner.shape[1] and 0 <= ny < owner.shape[0] and owner[ny, nx] >= 0 and owner[ny, nx] != province:
                            candidate = int(owner[ny, nx])
                            if candidate not in closed:
                                candidates.append(candidate)
                    if candidates:
                        choices = sorted(set(candidates))
                        owner[y, x] = min(choices, key=lambda p: scores[p, y, x])
                        changed = True
        if not changed:
            break
    return owner


def smooth_spikes(owner: np.ndarray, mask: np.ndarray, scores: np.ndarray, seeds, protected: np.ndarray, closed=frozenset()):
    seed_pixels = {(sx, sy) for _, sx, sy, _ in seeds}
    for _ in range(4):
        changes = []
        for y, x in zip(*np.nonzero(mask)):
            if protected[y, x] or (x, y) in seed_pixels:
                continue
            province = int(owner[y, x])
            neighbours = []
            same = 0
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < owner.shape[1] and 0 <= ny < owner.shape[0] and mask[ny, nx]:
                    p = int(owner[ny, nx])
                    neighbours.append(p)
                    same += p == province
            if same <= 1 and neighbours:
                counts = Counter(neighbours)
                best_count = max(counts.values())
                choices = [p for p, count in counts.items() if count == best_count and p != province and p not in closed]
                if choices:
                    changes.append((x, y, min(choices, key=lambda p: scores[p, y, x])))
        for x, y, province in changes:
            owner[y, x] = province
    return repair_connectivity(owner, scores, seeds, protected, closed)


def competitive_cores(mask: np.ndarray, fields: np.ndarray, seeds, quotas):
    """Grow several exact-size connected cores together without choking peers."""
    owner = np.full(mask.shape, -1, dtype=np.int16)
    frontiers = {}
    counts = Counter()
    queued = {}
    for province in quotas:
        _, sx, sy, _ = seeds[province]
        owner[sy, sx] = province
        counts[province] = 1
        queued[province] = np.zeros(mask.shape, dtype=bool)
        frontiers[province] = []

    def add_frontier(province, x, y):
        _, seat_x, seat_y, _ = seeds[province]
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0]
                    and mask[ny, nx] and owner[ny, nx] < 0
                    and not queued[province][ny, nx]):
                queued[province][ny, nx] = True
                # Seat distance keeps the three tiny eastern jurisdictions
                # compact; the geodesic field still bends them around terrain.
                compactness = (nx - seat_x) ** 2 + (ny - seat_y) ** 2
                priority = compactness * 18.0 + float(fields[province, ny, nx])
                heapq.heappush(frontiers[province], (priority, nx, ny))

    for province in quotas:
        _, sx, sy, _ = seeds[province]
        add_frontier(province, sx, sy)

    while any(counts[p] < quotas[p] for p in quotas):
        progressed = False
        for province, quota in quotas.items():
            if counts[province] >= quota:
                continue
            queue = frontiers[province]
            while queue and owner[queue[0][2], queue[0][1]] >= 0:
                heapq.heappop(queue)
            if not queue:
                continue
            _, x, y = heapq.heappop(queue)
            owner[y, x] = province
            counts[province] += 1
            add_frontier(province, x, y)
            progressed = True
        if not progressed:
            raise ValueError(f"Could not complete eastern cores: {dict(counts)}")
    return owner


def main():
    base.OUT.mkdir(parents=True, exist_ok=True)
    source = np.asarray(Image.open(base.SOURCE).convert("RGB"))
    full_mask = base.packed_mask(source, base.HEBEI_COLORS)
    y0, x0 = np.min(np.argwhere(full_mask), axis=0)
    y1, x1 = np.max(np.argwhere(full_mask), axis=0)
    mask = full_mask[y0:y1 + 1, x0:x1 + 1]

    features = base.load_features()
    bounds = base.geo_bounds(features)
    box = (x0, y0, x1, y1)
    full_seeds = []
    for name, lon, lat, area in base.PROVINCES:
        x, y = base.snap(full_mask, *base.project(lon, lat, bounds, box))
        full_seeds.append((name, x, y, area))
    seeds = [(name, x - x0, y - y0, area) for name, x, y, area in full_seeds]
    full_guide = base.raster_guide(features, bounds, box, full_mask)
    guide = full_guide[y0:y1 + 1, x0:x1 + 1]

    fields = distance_fields(mask, guide, seeds)
    owner, scores = balanced_owner(fields, mask, TARGET_SIZES)

    # Lock the three eastern provinces as compact connected cores. This makes
    # Shanhaiguan a true chokepoint and prevents Yongping/Luanzhou starvation.
    closed = frozenset({7, 8, 9})
    protected_owner = competitive_cores(
        mask, fields, seeds, {7: 130, 8: 130, 9: 50})
    protected = protected_owner >= 0
    owner[protected] = protected_owner[protected]
    for province in closed:
        extras = (owner == province) & (protected_owner != province)
        for y, x in zip(*np.nonzero(extras)):
            choices = np.argsort(scores[:, y, x])
            owner[y, x] = next(int(p) for p in choices if p not in closed)

    owner = repair_connectivity(owner, scores, seeds, protected, closed)
    owner = smooth_spikes(owner, mask, scores, seeds, protected, closed)
    owner[protected] = protected_owner[protected]
    for province in closed:
        extras = (owner == province) & (protected_owner != province)
        for y, x in zip(*np.nonzero(extras)):
            choices = np.argsort(scores[:, y, x])
            owner[y, x] = next(int(p) for p in choices if p not in closed)
    owner = repair_connectivity(owner, scores, seeds, protected, closed)

    colours = base.palette(len(seeds))
    draft = source.copy()
    local = draft[y0:y1 + 1, x0:x1 + 1]
    for i, colour in enumerate(colours):
        local[owner == i] = colour
    assert np.array_equal(draft[~full_mask], source[~full_mask])
    Image.fromarray(draft).save(base.OUT / "hebei_geojson_23_v2_full_draft.bmp")

    pad = 7
    cx0, cy0, cx1, cy1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    crop = draft[cy0:cy1 + 1, cx0:cx1 + 1]
    Image.fromarray(crop).save(base.OUT / "hebei_geojson_23_v2_draft.bmp")
    scale = 7
    raw = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    raw.save(base.OUT / "hebei_geojson_23_v2_raw.png")

    local_full_mask = full_mask[cy0:cy1 + 1, cx0:cx1 + 1]
    boundary = np.zeros(local_full_mask.shape, dtype=bool)
    boundary[1:] |= local_full_mask[1:] & np.any(crop[1:] != crop[:-1], axis=2)
    boundary[:, 1:] |= local_full_mask[:, 1:] & np.any(crop[:, 1:] != crop[:, :-1], axis=2)
    shown = np.asarray(raw).copy()
    shown[np.repeat(np.repeat(boundary, scale, 0), scale, 1)] = (35, 35, 35)
    map_img = Image.fromarray(shown)

    canvas = Image.new("RGB", (map_img.width + 560, max(map_img.height, 900)), "white")
    canvas.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 28)
    body = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 16)
    number = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 16)
    lx = map_img.width + 24
    draw.text((lx, 20), "河北23省边界美化草案 V2", fill=(20, 20, 20), font=title)
    draw.text((lx, 61), "山海关约50像素；燕都锁定；边界去狭颈与尖刺", fill=(80, 80, 80), font=small)
    area_order = ["宣镇", "燕北", "永平", "保河", "恒赵", "冀南"]
    ordered = [i for area in area_order for i, seed in enumerate(full_seeds) if seed[3] == area]
    for order_i, seed_i in enumerate(ordered):
        name, sx, sy, area = full_seeds[seed_i]
        col, row = order_i // 12, order_i % 12
        tx, ty = lx + col * 255, 105 + row * 48
        draw.rectangle((tx, ty + 3, tx + 25, ty + 28), fill=colours[seed_i], outline=(35, 35, 35))
        size = int(np.count_nonzero(owner == seed_i))
        draw.text((tx + 34, ty), f"{seed_i + 1:02d} {name} · {area} ({size})", fill=(25, 25, 25), font=body)
        px, py = (sx - cx0) * scale, (sy - cy0) * scale
        draw.text((px, py), str(seed_i + 1), fill="black", font=number, stroke_width=3, stroke_fill="white")
    draw.text((lx, 705), "山海关锁定为50像素；永平、滦州均明显扩大", fill=(55, 55, 55), font=small)
    draw.text((lx, 735), "河北外轮廓及燕都五省逐像素不变", fill=(55, 55, 55), font=small)
    draw.text((lx, 765), "未写入正式 provinces.bmp", fill=(55, 55, 55), font=small)
    canvas.save(base.OUT / "hebei_geojson_23_v2_annotated.png")

    counts = [int(np.count_nonzero(owner == i)) for i in range(len(seeds))]
    disconnected = {seeds[i][0]: len(components(owner, i)) for i in range(len(seeds)) if len(components(owner, i)) != 1}
    print("HEBEI_V2_COUNTS", counts)
    print("HEBEI_V2_DISCONNECTED", disconnected)
    print("HEBEI_V2_OUTSIDE_CHANGED", int(np.count_nonzero(np.any(draft[~full_mask] != source[~full_mask], axis=1))))


if __name__ == "__main__":
    main()
