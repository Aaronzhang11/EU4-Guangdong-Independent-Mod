"""Transplant the workshop Huai waterway into the canonical mod map.

The reference geometry comes from workshop item 2935149060.  Its local Huai
slice aligns with this mod after a translation of x - 448 and y - 21.  The
translated row runs are embedded here so the build remains reproducible and
does not depend on a locally installed workshop copy.

Hongze Lake (province 1896) already occupies the aligned target position, so
its hand-drawn target geometry is preserved.  The copied route retains the
reference layout: four river reaches west of Hongze and two east of it, with
the easternmost reach opening directly into the Yellow Sea.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_DIR = REPO_ROOT / "guangdong_independent_practice/map"

# The RGB values are copied from the six source water provinces.  They do not
# collide with any existing definition color in this mod.
HUAI_COLORS = {
    5039: (164, 203, 202),  # Upper Huai
    5040: (30, 137, 5),     # Middle Huai
    5041: (92, 138, 44),    # Yingshou Reach
    5042: (245, 231, 89),   # Fengsi Reach
    5043: (146, 89, 54),    # Huai'an Reach
    5044: (88, 69, 100),    # Huai Estuary
}
HONGZE_COLOR = (13, 0, 244)  # Existing province 1896
HONGZE_ROW_RUNS = (
    (835, 4657, 4658), (836, 4653, 4653), (836, 4655, 4659),
    (837, 4652, 4660), (838, 4652, 4660), (839, 4651, 4659),
    (840, 4651, 4658), (841, 4650, 4658), (842, 4653, 4654),
    (842, 4656, 4658), (843, 4653, 4653), (843, 4657, 4657),
)

# Inclusive bitmap row runs: (y, x_start, x_end).  These are the exact source
# province masks translated by (-448, -21), rather than a newly approximated
# polyline.
HUAI_ROW_RUNS = {
    5039: (
        (855, 4577, 4579), (856, 4567, 4570), (856, 4576, 4580),
        (857, 4567, 4571), (857, 4575, 4577), (857, 4579, 4580),
        (857, 4586, 4589), (857, 4592, 4595), (858, 4570, 4576),
        (858, 4579, 4595), (859, 4571, 4575), (859, 4580, 4586),
        (859, 4589, 4592),
    ),
    5040: (
        (850, 4621, 4622), (851, 4621, 4622), (852, 4619, 4622),
        (853, 4605, 4609), (853, 4618, 4621), (854, 4603, 4619),
        (855, 4602, 4606), (855, 4610, 4619), (856, 4596, 4604),
        (857, 4596, 4602), (858, 4596, 4596),
    ),
    5041: (
        (845, 4630, 4636), (846, 4629, 4636), (847, 4628, 4630),
        (848, 4627, 4629), (849, 4621, 4624), (849, 4627, 4628),
        (850, 4623, 4628), (851, 4624, 4627),
    ),
    5042: (
        (840, 4644, 4648), (841, 4642, 4648), (842, 4641, 4643),
        (842, 4647, 4649), (843, 4640, 4642), (843, 4648, 4649),
        (843, 4654, 4654), (844, 4638, 4641), (844, 4648, 4654),
        (845, 4637, 4639), (845, 4648, 4653), (846, 4637, 4639),
    ),
    5043: (
        (830, 4666, 4671), (831, 4665, 4671), (832, 4665, 4666),
        (833, 4664, 4665), (834, 4663, 4665), (835, 4661, 4664),
        (836, 4660, 4662), (837, 4661, 4661),
    ),
    5044: (
        (816, 4682, 4683), (817, 4682, 4683), (818, 4681, 4683),
        (819, 4680, 4682), (820, 4680, 4681), (821, 4679, 4681),
        (822, 4678, 4680), (823, 4676, 4679), (824, 4675, 4678),
        (825, 4673, 4676), (826, 4672, 4674), (827, 4672, 4673),
        (828, 4672, 4673), (829, 4671, 4672), (830, 4672, 4672),
    ),
}


def province_mask(province_map: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
    return np.all(province_map == np.array(color, dtype=np.uint8), axis=2)


def paint_provinces(path: Path) -> np.ndarray:
    with Image.open(path) as source:
        values = np.array(source.convert("RGB"), dtype=np.uint8, copy=True)
    for province_id, row_runs in HUAI_ROW_RUNS.items():
        color = np.array(HUAI_COLORS[province_id], dtype=np.uint8)
        for y, x_start, x_end in row_runs:
            values[y, x_start:x_end + 1] = color
    # Add the translated reference-lake pixels to the already aligned local
    # Hongze shape.  This preserves the established lake while guaranteeing
    # the same west/east river contacts as the source waterway.
    for y, x_start, x_end in HONGZE_ROW_RUNS:
        values[y, x_start:x_end + 1] = np.array(HONGZE_COLOR, dtype=np.uint8)
    Image.fromarray(values, mode="RGB").save(path, format="BMP")
    return values


def paint_heightmap(path: Path, province_map: np.ndarray) -> None:
    with Image.open(path) as source:
        values = np.array(source.convert("L"), dtype=np.uint8, copy=True)
    for province_id, color in HUAI_COLORS.items():
        values[province_mask(province_map, color)] = 90 if province_id == 5044 else 93
    values[province_mask(province_map, HONGZE_COLOR)] = 92
    Image.fromarray(values, mode="L").save(path, format="BMP")


def paint_rivers(path: Path, province_map: np.ndarray) -> None:
    with Image.open(path) as source:
        palette = source.getpalette()
        values = np.array(source, dtype=np.uint8, copy=True)
    water_mask = province_mask(province_map, HONGZE_COLOR)
    for color in HUAI_COLORS.values():
        water_mask |= province_mask(province_map, color)
    # Palette index 254 is the ordinary water background in rivers.bmp.
    values[water_mask] = 254
    image = Image.fromarray(values, mode="P")
    image.putpalette(palette)
    image.save(path, format="BMP")


def main() -> None:
    provinces_path = MAP_DIR / "provinces.bmp"
    province_map = paint_provinces(provinces_path)
    paint_heightmap(MAP_DIR / "heightmap.bmp", province_map)
    paint_rivers(MAP_DIR / "rivers.bmp", province_map)
    print("HUAI_WORKSHOP_GEOMETRY_APPLIED")


if __name__ == "__main__":
    main()
