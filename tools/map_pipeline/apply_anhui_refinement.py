"""Split the canonical Anhui source provinces into seventeen reviewed provinces.

The operation preserves the existing navigable Huai and Yangtze pixels and all
geometry outside the six vanilla Anhui land masks.  Terrain- and river-weighted
multi-source floods create compact borders, while each split group includes all
of its output colors so rerunning the script is idempotent.
"""

from __future__ import annotations

from collections import deque
import heapq
import math
from pathlib import Path

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_DIR = REPO_ROOT / "guangdong_independent_practice/map"

PROVINCE_COLORS = {
    2144: (82, 62, 176),    # Yingzhou (retained Fuyang color)
    5058: (68, 138, 214),   # Bozhou
    5059: (45, 105, 185),   # Shouzhou
    2143: (190, 53, 53),    # Fengyang
    5063: (230, 142, 76),   # Chuzhou
    5064: (239, 169, 99),   # Hezhou
    1838: (208, 134, 173),  # Luzhou (retained Hefei color)
    5060: (226, 127, 54),   # Lu'an
    5061: (232, 181, 97),   # Chaohu
    5062: (244, 187, 122),  # Wuwei
    686: (98, 124, 64),     # Anqing
    5065: (103, 188, 132),  # Chizhou
    2146: (185, 197, 39),   # Ningguo
    5066: (56, 146, 94),    # Wuhu
    5068: (128, 199, 148),  # Guangde
    2147: (150, 42, 42),    # Huizhou
    5067: (190, 91, 163),   # Taiping
}

# Bitmap-coordinate seats.  The Huai divides the first two source masks into
# separate components; seats on both banks ensure every material component is
# assigned deliberately.
SPLIT_GROUPS = (
    ((2144, 5058, 5059), {
        5058: (4608, 834), 2144: (4607, 852), 5059: (4622, 861),
    }),
    ((2143, 5063, 5064), {
        2143: (4644, 839), 5063: (4659, 854), 5064: (4639, 862),
    }),
    ((1838, 5060, 5061, 5062), {
        5060: (4614, 873), 1838: (4629, 868),
        5061: (4645, 871), 5062: (4644, 882),
    }),
    ((686, 5065), {
        686: (4617, 887), 5065: (4634, 898),
    }),
    ((2146, 5066, 5068), {
        5066: (4650, 878), 2146: (4660, 894), 5068: (4670, 888),
    }),
    ((2147, 5067), {
        5067: (4637, 892), 2147: (4648, 911),
    }),
)


def color_mask(values: np.ndarray, province_ids: tuple[int, ...]) -> np.ndarray:
    result = np.zeros(values.shape[:2], dtype=bool)
    for province_id in province_ids:
        result |= np.all(
            values == np.array(PROVINCE_COLORS[province_id], dtype=np.uint8),
            axis=2,
        )
    return result


def nearest_mask_pixel(mask: np.ndarray, point: tuple[int, int]) -> tuple[int, int]:
    x, y = point
    if mask[y, x]:
        return x, y
    ys, xs = np.where(mask)
    index = int(np.argmin((xs - x) ** 2 + (ys - y) ** 2))
    return int(xs[index]), int(ys[index])


def assign_residual_components(
    labels: np.ndarray,
    mask: np.ndarray,
    seeds: dict[int, tuple[int, int]],
) -> None:
    """Assign river-cut one-pixel remnants to their nearest planned seat."""
    residual = mask & (labels < 0)
    seen = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    for start_y, start_x in zip(*np.where(residual)):
        if seen[start_y, start_x]:
            continue
        queue = deque([(int(start_y), int(start_x))])
        seen[start_y, start_x] = True
        component: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            component.append((y, x))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                next_y, next_x = y + dy, x + dx
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and residual[next_y, next_x]
                    and not seen[next_y, next_x]
                ):
                    seen[next_y, next_x] = True
                    queue.append((next_y, next_x))
        province_id = min(
            seeds,
            key=lambda candidate: min(
                (x - seeds[candidate][0]) ** 2 + (y - seeds[candidate][1]) ** 2
                for y, x in component
            ),
        )
        for y, x in component:
            labels[y, x] = province_id


def split_connected_mask(
    mask: np.ndarray,
    seeds: dict[int, tuple[int, int]],
    heightmap: np.ndarray,
    rivers: np.ndarray,
) -> np.ndarray:
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
            river_cost = 1.6 if int(rivers[next_y, next_x]) < 254 else 0.0
            relief_cost = abs(
                int(heightmap[next_y, next_x]) - int(heightmap[y, x])
            ) * 0.04
            noise = (
                math.sin(next_x * 0.67 + next_y * 0.31)
                + math.sin(next_x * 0.23 - next_y * 0.43)
            ) * 0.11
            candidate = distance + 1.0 + river_cost + relief_cost + noise
            if candidate + 1e-9 < distances[next_y, next_x]:
                distances[next_y, next_x] = candidate
                labels[next_y, next_x] = province_id
                heapq.heappush(queue, (candidate, province_id, next_y, next_x))

    assign_residual_components(labels, mask, seeds)
    if np.any(mask & (labels < 0)):
        raise ValueError("Anhui split left unassigned source pixels")
    return labels


def main() -> None:
    provinces_path = MAP_DIR / "provinces.bmp"
    with Image.open(provinces_path) as source:
        values = np.array(source.convert("RGB"), dtype=np.uint8, copy=True)
    with Image.open(MAP_DIR / "heightmap.bmp") as source:
        heightmap = np.asarray(source.convert("L"), dtype=np.uint8)
    with Image.open(MAP_DIR / "rivers.bmp") as source:
        rivers = np.asarray(source, dtype=np.uint8)

    for province_ids, seeds in SPLIT_GROUPS:
        mask = color_mask(values, province_ids)
        labels = split_connected_mask(mask, seeds, heightmap, rivers)
        for province_id in province_ids:
            values[mask & (labels == province_id)] = np.array(
                PROVINCE_COLORS[province_id], dtype=np.uint8
            )

    Image.fromarray(values, mode="RGB").save(provinces_path, format="BMP")
    print("ANHUI_REFINEMENT_GEOMETRY_APPLIED")


if __name__ == "__main__":
    main()
