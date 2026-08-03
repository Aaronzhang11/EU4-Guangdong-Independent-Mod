"""Apply the reviewed ten-province Guizhou geometry to the canonical bitmap.

The reviewed crop uses the modern Guizhou outline but 1444-style internal
provinces.  Only pixels belonging to the four vanilla Guizhou source colors or
to one of the ten reviewed output colors are changed, so surrounding map work
inside the crop is preserved.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = REPO_ROOT / "guangdong_independent_practice/map/provinces.bmp"
REVIEW_CROP = REPO_ROOT / "docs/map/previews/B17_guizhou_10_province_draft.bmp"
CROP_BOX = (4395, 895, 4545, 1025)

SOURCE_COLORS = {
    (79, 254, 112),   # 2168 Bozhou
    (96, 100, 255),   # 674 Guiyang -> Guizhu
    (224, 98, 192),   # 673 Zhenyuan -> Duyun
    (45, 117, 59),    # 4199 Tongren -> Sinan
}

OUTPUT_COLORS = {
    (79, 254, 112),   # 2168 Bozhou
    (126, 83, 54),    # 5069 Wusa
    (196, 140, 54),   # 5070 Shuixi
    (62, 166, 210),   # 5071 Puding
    (96, 100, 255),   # 674 Guizhu
    (226, 116, 42),   # 5072 Pu'an
    (224, 98, 192),   # 673 Duyun
    (71, 132, 198),   # 5073 Qingping
    (141, 82, 190),   # 5074 Liping
    (45, 117, 59),    # 4199 Sinan
}


def mask_for_colors(values: np.ndarray, colors: set[tuple[int, int, int]]) -> np.ndarray:
    mask = np.zeros(values.shape[:2], dtype=bool)
    for color in colors:
        mask |= np.all(values == np.array(color, dtype=np.uint8), axis=2)
    return mask


def main() -> None:
    with Image.open(MAP_PATH) as image:
        values = np.array(image.convert("RGB"), dtype=np.uint8, copy=True)
    with Image.open(REVIEW_CROP) as image:
        reviewed = np.array(image.convert("RGB"), dtype=np.uint8, copy=True)

    left, top, right, bottom = CROP_BOX
    target = values[top:bottom, left:right]
    if reviewed.shape != target.shape:
        raise ValueError(
            f"Reviewed Guizhou crop is {reviewed.shape}, expected {target.shape}"
        )

    source_mask = mask_for_colors(target, SOURCE_COLORS)
    output_mask = mask_for_colors(reviewed, OUTPUT_COLORS)
    changed_mask = source_mask | output_mask
    target[changed_mask] = reviewed[changed_mask]

    Image.fromarray(values, mode="RGB").save(MAP_PATH, format="BMP")
    print(f"GUIZHOU_REFINEMENT_GEOMETRY_APPLIED:{int(changed_mask.sum())}")


if __name__ == "__main__":
    main()
