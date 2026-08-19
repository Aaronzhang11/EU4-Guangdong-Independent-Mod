#!/usr/bin/env python3
"""Apply the reviewed terminal border corrections around Mengjin and Zhangde.

The main Henan split predates the later Wangji and Shanxi refinements.  These
small run-length corrections are therefore applied to the final composite map
instead of changing the earlier flood seeds and perturbing the whole region.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
PROVINCES_PATH = REPO_ROOT / "guangdong_independent_practice/map/provinces.bmp"

PROVINCE_COLOURS = {
    4966: (73, 212, 204),    # Xingyang
    5045: (41, 159, 207),    # Mengjin
    5046: (173, 73, 194),    # Yanshi
    5048: (209, 92, 66),     # Zhangde
    5049: (117, 176, 219),   # Huazhou
    5252: (111, 90, 160),    # Zezhou
}

# Each run is (y, inclusive x start, inclusive x end).  Source-colour guards
# make reruns idempotent and prevent a later geometry change from being
# silently painted over.
CORRECTIONS = (
    (
        5048,
        (5049,),
        (
            (787, 4593, 4594),
            (788, 4592, 4594),
            (789, 4591, 4594),
            (790, 4590, 4593),
            (791, 4589, 4592),
            (792, 4588, 4591),
        ),
    ),
    (
        5045,
        (4966, 5046, 5252),
        (
            (818, 4575, 4576),
            (819, 4573, 4576),
            (820, 4574, 4576),
            (821, 4572, 4575),
            (822, 4569, 4574),
            (823, 4567, 4574),
            (824, 4565, 4574),
            (825, 4568, 4572),
        ),
    ),
)


def apply(provinces_path: Path = PROVINCES_PATH) -> int:
    with Image.open(provinces_path) as source:
        values = np.array(source.convert("RGB"), dtype=np.uint8, copy=True)

    changed = 0
    for target_id, source_ids, runs in CORRECTIONS:
        target = np.array(PROVINCE_COLOURS[target_id], dtype=np.uint8)
        allowed = {
            PROVINCE_COLOURS[province_id]
            for province_id in (target_id, *source_ids)
        }
        for y, start_x, end_x in runs:
            pixels = values[y, start_x : end_x + 1]
            unexpected = {
                tuple(int(channel) for channel in pixel)
                for pixel in pixels
                if tuple(int(channel) for channel in pixel) not in allowed
            }
            if unexpected:
                raise ValueError(
                    f"Unexpected colours in correction run {y}:{start_x}-{end_x}: "
                    f"{sorted(unexpected)}"
                )
            changed += int(np.count_nonzero(np.any(pixels != target, axis=1)))
            pixels[:] = target

    # A fresh RGB image keeps provinces.bmp on the classic 40-byte DIB header
    # expected by the rest of the map pipeline.
    Image.fromarray(values, mode="RGB").save(provinces_path, format="BMP")
    header = provinces_path.read_bytes()[:54]
    if int.from_bytes(header[14:18], "little") != 40:
        raise ValueError("provinces.bmp is not using the classic BMP header")
    if int.from_bytes(header[10:14], "little") != 54:
        raise ValueError("provinces.bmp has an unexpected pixel-data offset")
    return changed


def main() -> None:
    changed = apply()
    print(f"HENAN_BORDER_CORRECTIONS_APPLIED changed_pixels={changed}")


if __name__ == "__main__":
    main()
