#!/usr/bin/env python3
"""Generate the 礼教 thought-tension endpoint medallions for EU4 1.37.5."""

from __future__ import annotations

import argparse
import hashlib
import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
GFX = MOD / "gfx/interface"
DEFAULT_VANILLA = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)
OUTPUTS = {
    "low": GFX / "zhx_thought_tension_low.tga",
    "high": GFX / "zhx_thought_tension_high.tga",
}
HITBOX_OUTPUT = GFX / "zhx_thought_tension_hitbox.dds"
EXPECTED_BASELINES = {
    "low_harmony.dds": (
        "ee3234ff5f369a5f4d56c8181e8ac86c01b224824f9beb5ab617a545e0d3ecb3"
    ),
    "high_harmony.dds": (
        "4a75c9c4d1f6a725e8840ab064812b94b74534f7df44ebccbb02debd1c637ace"
    ),
}

SCALE = 4
GOLD = (218, 163, 59, 255)
GOLD_LIGHT = (245, 205, 103, 255)
GOLD_DARK = (78, 43, 19, 255)
GREEN = (18, 92, 52)
RED = (104, 25, 26)


def load_vanilla_medallion(vanilla_root: Path, name: str) -> Image.Image:
    path = vanilla_root / "gfx/interface" / name
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    expected = EXPECTED_BASELINES[name]
    if digest != expected:
        raise ValueError(
            f"unsupported EU4 harmony-icon baseline for {name}: "
            f"{digest}; expected {expected}"
        )
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    if image.size != (32, 32):
        raise ValueError(f"unexpected {name} dimensions: {image.size}")
    return image


def blank_medallion(
    vanilla_root: Path,
    source_name: str,
    colour: tuple[int, int, int],
) -> Image.Image:
    """Keep the exact vanilla rim while replacing the lotus-bearing centre."""
    image = load_vanilla_medallion(vanilla_root, source_name).resize(
        (32 * SCALE, 32 * SCALE), Image.Resampling.LANCZOS
    )
    pixels = image.load()
    center = 15.5 * SCALE
    radius = 10.9 * SCALE
    for y in range(image.height):
        for x in range(image.width):
            distance = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
            if distance <= radius:
                light = max(0.0, 1.0 - distance / radius)
                shade = 0.70 + 0.30 * light
                pixels[x, y] = (
                    min(255, int(colour[0] * shade)),
                    min(255, int(colour[1] * shade)),
                    min(255, int(colour[2] * shade)),
                    255,
                )
    return image


def finish_icon(image: Image.Image) -> Image.Image:
    """Downsample the 4x silhouette and restore edge contrast at 32 px."""
    return image.resize((32, 32), Image.Resampling.LANCZOS).filter(
        ImageFilter.UnsharpMask(radius=0.35, percent=125, threshold=2)
    )


def bound_slips(vanilla_root: Path) -> Image.Image:
    """Low tension: three upright slips integrated by one broad binding."""
    icon = blank_medallion(vanilla_root, "high_harmony.dds", GREEN)
    draw = ImageDraw.Draw(icon)
    for box in (
        (41, 34, 56, 94),
        (56, 28, 72, 98),
        (72, 34, 87, 94),
    ):
        draw.rounded_rectangle(
            box,
            radius=3,
            fill=GOLD,
            outline=GOLD_DARK,
            width=4,
        )
    draw.rounded_rectangle((37, 57, 91, 73), radius=3, fill=GOLD_DARK)
    draw.rounded_rectangle((41, 60, 87, 70), radius=2, fill=GOLD_LIGHT)
    return finish_icon(icon)


def outlined_polygon(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
) -> None:
    draw.polygon(points, fill=GOLD)
    draw.line(points + [points[0]], fill=GOLD_DARK, width=4, joint="curve")


def fanned_slips(vanilla_root: Path) -> Image.Image:
    """High tension: three intact, flat-topped slips diverging in a red field."""
    icon = blank_medallion(vanilla_root, "low_harmony.dds", RED)
    draw = ImageDraw.Draw(icon)
    outlined_polygon(draw, [(26, 44), (41, 35), (72, 88), (57, 97)])
    outlined_polygon(draw, [(87, 35), (102, 44), (71, 97), (56, 88)])
    outlined_polygon(draw, [(55, 28), (73, 28), (73, 96), (55, 96)])
    return finish_icon(icon)


def tga_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="TGA", compression="tga_rle")
    return buffer.getvalue()


def transparent_argb8888_dds(width: int, height: int) -> bytes:
    """Return an uncompressed, fully transparent DDS button hitbox."""
    data = bytearray(128 + width * height * 4)
    data[0:4] = b"DDS "
    struct.pack_into("<I", data, 4, 124)  # DDS_HEADER size
    struct.pack_into("<I", data, 8, 0x100F)  # caps, dimensions, pitch, format
    struct.pack_into("<I", data, 12, height)
    struct.pack_into("<I", data, 16, width)
    struct.pack_into("<I", data, 20, width * 4)
    struct.pack_into("<I", data, 76, 32)  # DDS_PIXELFORMAT size
    struct.pack_into("<I", data, 80, 0x41)  # RGB plus alpha pixels
    struct.pack_into("<I", data, 88, 32)
    struct.pack_into("<I", data, 92, 0x00FF0000)
    struct.pack_into("<I", data, 96, 0x0000FF00)
    struct.pack_into("<I", data, 100, 0x000000FF)
    struct.pack_into("<I", data, 104, 0xFF000000)
    struct.pack_into("<I", data, 108, 0x1000)  # DDSCAPS_TEXTURE
    return bytes(data)


def run(vanilla_root: Path, check: bool) -> None:
    rendered = {
        "low": bound_slips(vanilla_root),
        "high": fanned_slips(vanilla_root),
    }
    for state, image in rendered.items():
        target = OUTPUTS[state]
        data = tga_bytes(image)
        if check:
            if not target.exists() or target.read_bytes() != data:
                raise ValueError(f"{target.name}: stale thought-tension endpoint")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    hitbox = transparent_argb8888_dds(308, 93)
    if check:
        if not HITBOX_OUTPUT.exists() or HITBOX_OUTPUT.read_bytes() != hitbox:
            raise ValueError(f"{HITBOX_OUTPUT.name}: stale thought-tension hitbox")
    else:
        HITBOX_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        HITBOX_OUTPUT.write_bytes(hitbox)
    print(
        f"{'checked' if check else 'generated'} two thought-tension endpoints "
        "and one 308x93 transparent panel hitbox"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA)
    args = parser.parse_args()
    run(args.vanilla_root, args.check)


if __name__ == "__main__":
    main()
