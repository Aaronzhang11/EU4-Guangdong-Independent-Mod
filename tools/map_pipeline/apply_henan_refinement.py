"""Split the canonical Henan source provinces into five reviewed areas.

The existing Dongjing royal domain and navigable Huai are preserved.  New
boundaries are generated only inside the five original Henan land masks.  A
terrain- and river-weighted multi-source flood produces compact connected
shapes whose borders bend around the local relief and minor rivers.
"""

from __future__ import annotations

import heapq
import math
from pathlib import Path

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_DIR = REPO_ROOT / "guangdong_independent_practice/map"

PROVINCE_COLORS = {
    1836: (208, 130, 79),   # Luoyang
    4967: (197, 38, 160),   # Shanzhou
    5045: (41, 159, 207),   # Mengjin
    5046: (173, 73, 194),   # Yanshi
    5047: (23, 186, 116),   # Weihui
    5048: (209, 92, 66),    # Zhangde
    5049: (117, 176, 219),  # Huazhou
    2176: (88, 144, 64),    # Guide
    5050: (222, 166, 47),   # Suizhou
    5051: (126, 69, 213),   # Chenzhou
    5052: (63, 194, 179),   # Xuzhou
    687: (226, 126, 128),   # Nanyang
    5053: (201, 120, 171),  # Ruzhou
    5055: (149, 190, 68),   # Dengzhou
    2175: (171, 198, 23),   # Xinyang
    5054: (87, 109, 203),   # Runing
}

# Huaiqing (692) is retired.  Its inherited colour remains an accepted input
# only so a replay from an old bitmap can absorb those pixels into the three
# live Zhang-Wei provinces; it is never emitted as an output colour.
RETIRED_SOURCE_COLORS = {
    692: (98, 136, 128),
}

# Bitmap-coordinate seeds.  Group masks include all of their output colors,
# making the operation idempotent after the first split.
SPLIT_GROUPS = (
    ((1836, 4967, 5045, 5046), (), {
        4967: (4538, 828), 1836: (4553, 822),
        5045: (4565, 814), 5046: (4567, 832),
    }),
    ((5047, 5048, 5049), (RETIRED_SOURCE_COLORS[692],), {
        5048: (4584, 785), 5049: (4594, 796),
        5047: (4588, 807),
    }),
    ((2176, 5050, 5051, 5052), (), {
        5050: (4617, 826), 2176: (4608, 831),
        5051: (4604, 841), 5052: (4594, 833),
    }),
    ((687, 2175, 5053, 5054, 5055), (), {
        687: (4552, 847), 5055: (4560, 856),
        5053: (4572, 840), 5054: (4595, 853),
        2175: (4602, 868),
    }),
)


def color_mask(
    values: np.ndarray,
    province_ids: tuple[int, ...],
    legacy_source_colors: tuple[tuple[int, int, int], ...] = (),
) -> np.ndarray:
    result = np.zeros(values.shape[:2], dtype=bool)
    for province_id in province_ids:
        result |= np.all(
            values == np.array(PROVINCE_COLORS[province_id], dtype=np.uint8),
            axis=2,
        )
    for colour in legacy_source_colors:
        result |= np.all(values == np.array(colour, dtype=np.uint8), axis=2)
    return result


def nearest_mask_pixel(mask: np.ndarray, point: tuple[int, int]) -> tuple[int, int]:
    x, y = point
    if mask[y, x]:
        return x, y
    ys, xs = np.where(mask)
    index = int(np.argmin((xs - x) ** 2 + (ys - y) ** 2))
    return int(xs[index]), int(ys[index])


def split_connected_mask(
    mask: np.ndarray,
    seeds: dict[int, tuple[int, int]],
    heightmap: np.ndarray,
    rivers: np.ndarray,
) -> np.ndarray:
    """Return connected labels from a weighted four-neighbour flood."""
    height, width = mask.shape
    labels = np.full(mask.shape, -1, dtype=np.int32)
    distances = np.full(mask.shape, np.inf, dtype=np.float64)
    queue: list[tuple[float, int, int, int]] = []

    for province_id, point in seeds.items():
        x, y = nearest_mask_pixel(mask, point)
        distances[y, x] = 0.0
        labels[y, x] = province_id
        heapq.heappush(queue, (0.0, province_id, y, x))

    while queue:
        distance, province_id, y, x = heapq.heappop(queue)
        if distance != distances[y, x] or labels[y, x] != province_id:
            continue
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            next_y, next_x = y + dy, x + dx
            if not (0 <= next_y < height and 0 <= next_x < width):
                continue
            if not mask[next_y, next_x]:
                continue
            # Minor rivers and sharp relief are expensive to cross, so equal
            # distance fronts tend to meet along them.  The deterministic
            # multi-frequency term prevents ruler-straight Voronoi borders.
            river_cost = 1.7 if int(rivers[next_y, next_x]) < 254 else 0.0
            relief_cost = abs(
                int(heightmap[next_y, next_x]) - int(heightmap[y, x])
            ) * 0.035
            noise = (
                math.sin(next_x * 0.71 + next_y * 0.29)
                + math.sin(next_x * 0.19 - next_y * 0.47)
            ) * 0.12
            candidate = distance + 1.0 + river_cost + relief_cost + noise
            if candidate + 1e-9 < distances[next_y, next_x]:
                distances[next_y, next_x] = candidate
                labels[next_y, next_x] = province_id
                heapq.heappush(
                    queue, (candidate, province_id, next_y, next_x)
                )

    if np.any(mask & (labels < 0)):
        raise ValueError("Henan split left unassigned source pixels")
    return labels


def main() -> None:
    provinces_path = MAP_DIR / "provinces.bmp"
    with Image.open(provinces_path) as source:
        values = np.array(source.convert("RGB"), dtype=np.uint8, copy=True)
    with Image.open(MAP_DIR / "heightmap.bmp") as source:
        heightmap = np.asarray(source.convert("L"), dtype=np.uint8)
    with Image.open(MAP_DIR / "rivers.bmp") as source:
        rivers = np.asarray(source, dtype=np.uint8)

    for province_ids, legacy_source_colors, seeds in SPLIT_GROUPS:
        mask = color_mask(values, province_ids, legacy_source_colors)
        labels = split_connected_mask(mask, seeds, heightmap, rivers)
        for province_id in province_ids:
            values[mask & (labels == province_id)] = np.array(
                PROVINCE_COLORS[province_id], dtype=np.uint8
            )

    for province_id, colour in RETIRED_SOURCE_COLORS.items():
        pixels = int(np.all(values == np.array(colour, dtype=np.uint8), axis=2).sum())
        if pixels:
            raise ValueError(
                f"Retired Henan province {province_id} still has {pixels} pixels"
            )

    Image.fromarray(values, mode="RGB").save(provinces_path, format="BMP")
    print("HENAN_REFINEMENT_GEOMETRY_APPLIED")


if __name__ == "__main__":
    main()
