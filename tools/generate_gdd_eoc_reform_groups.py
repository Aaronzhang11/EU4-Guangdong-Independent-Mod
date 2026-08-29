#!/usr/bin/env python3
"""Generate the transparent reform/member overlay for the Celestial Empire UI.

The three reform groups deliberately have no raster body: their native gold
frames, headings, buttons, votes and enacted marks sit directly over the main
wine-red background.  Only the lower-left member body and its compact inset
jade ribbon are painted here.
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "guangdong_independent_practice/gfx/interface/gdd_eoc_reform_groups.tga"
SOURCE_BACKGROUND = ROOT / "guangdong_independent_practice/gfx/interface/gdd_eoc_bg_authority.tga"
DECREE_SOURCE = ROOT / "guangdong_independent_practice/gfx/interface/decree_button.dds"
DECREE_OUTPUT = ROOT / "guangdong_independent_practice/gfx/interface/gdd_eoc_decree_button_compact.tga"

# The source provides authentic jade folds.  A colour mask extracts the cloth
# from its old wine-red surroundings before it is rebuilt as a symmetric,
# compact ribbon fully inside the member frame.
MEMBER_HEADER_SOURCE = (350, 700, 630, 755)
MEMBER_HEADER_TARGET = (40, 638, 226, 669)

WIDTH = 1020
HEIGHT = 900
SCALE = 3

# The overlay follows the widened 1020x900 background. Boxes are expressed in
# celestial_window coordinates and translated by the background icon's offset
# before drawing.
BACKGROUND_X = 66
BACKGROUND_Y = 18
PANELS = (
    (796, 108, 1038, 352, (27, 61, 49, 220)),   # ordinary reforms
    (796, 371, 1038, 676, (81, 31, 33, 222)),   # centralising reforms
    (796, 691, 1038, 878, (29, 48, 58, 222)),   # decentralising reforms
    (98, 650, 318, 900, (25, 62, 48, 224)),     # Zhou-member roster, bottom anchored
)


def scaled(value: int) -> int:
    return value * SCALE


def scaled_box(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return tuple(scaled(value) for value in box)


def local_box(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    return (
        left - BACKGROUND_X,
        top - BACKGROUND_Y,
        right - BACKGROUND_X,
        bottom - BACKGROUND_Y,
    )


def draw_panel(
    draw: ImageDraw.ImageDraw,
    panel_left: int,
    top: int,
    panel_right: int,
    bottom: int,
    colour: tuple[int, int, int, int],
    body_colour: tuple[int, int, int, int] | None = None,
    draw_generated_header: bool = True,
) -> None:
    left, local_top, right, local_bottom = local_box(
        (panel_left, top, panel_right, bottom)
    )

    shadow = (left + 3, local_top + 4, right + 4, local_bottom + 5)
    draw.rounded_rectangle(
        scaled_box(shadow),
        radius=8 * SCALE,
        fill=(13, 8, 7, 150),
    )

    gold_light = (226, 187, 91, 255)
    body = body_colour or (
        max(13, colour[0] - 18),
        max(12, colour[1] - 18),
        max(12, colour[2] - 18),
        205,
    )

    draw.rounded_rectangle(
        scaled_box((left + 3, local_top + 3, right - 3, local_bottom - 3)),
        radius=5 * SCALE,
        fill=body,
    )

    if draw_generated_header:
        header = (left + 8, local_top + 8, right - 8, local_top + 34)
        draw.rounded_rectangle(
            scaled_box(header),
            radius=4 * SCALE,
            fill=colour,
        )
        draw.line(
            scaled_box((left + 13, local_top + 32, right - 13, local_top + 32)),
            fill=gold_light,
            width=SCALE,
        )

    # Subtle aged bands keep the panels integrated with the original wine-red
    # background without competing with the opaque reform buttons.
    for y in range(local_top + 43, local_bottom - 8, 13):
        draw.line(
            scaled_box((left + 9, y, right - 9, y)),
            fill=(151, 109, 54, 18),
            width=SCALE,
        )

    # The gold border itself is a native cornered-tile GUI control layered
    # above this text-free colour fill (GFX_gdd_eoc_reform_frame).


def extract_member_ribbon(source: Image.Image) -> Image.Image:
    crop = source.crop(MEMBER_HEADER_SOURCE).convert("RGBA")
    mask = Image.new("L", crop.size, 0)
    source_pixels = crop.load()
    mask_pixels = mask.load()
    for y in range(crop.height):
        for x in range(crop.width):
            red, green, blue, alpha = source_pixels[x, y]
            # The old backdrop is wine-red (R > G); the ribbon cloth is jade
            # (G > R and G > B).  Feather the threshold to retain painted folds.
            jade = min(green - red, green - blue)
            mask_pixels[x, y] = max(0, min(alpha, (jade + 2) * 18))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.55))
    crop.putalpha(mask)
    return crop


def paint_member_header(image: Image.Image, source: Image.Image) -> None:
    left, top, right, bottom = MEMBER_HEADER_TARGET
    ribbon = extract_member_ribbon(source).resize(
        (right - left, bottom - top),
        Image.Resampling.LANCZOS,
    )
    image.alpha_composite(ribbon, (left, top))


def render() -> bytes:
    image = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Do not paint the three reform panels. Their native transparent-centre
    # frames remain in the GUI while the main wine-red background shows through.

    member_left, member_top, member_right, member_bottom, member_colour = PANELS[3]
    draw_panel(
        draw,
        member_left,
        member_top,
        member_right,
        member_bottom,
        member_colour,
        body_colour=(64, 30, 34, 224),
        draw_generated_header=False,
    )

    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    source = Image.open(SOURCE_BACKGROUND).convert("RGBA")
    paint_member_header(image, source)
    buffer = BytesIO()
    image.save(buffer, format="TGA", compression="tga_rle")
    return buffer.getvalue()


def render_compact_decree_button() -> bytes:
    """Resize the scroll so Clausewitz centres its unscaled button text."""
    image = Image.open(DECREE_SOURCE).convert("RGBA")
    image = image.resize((170, 30), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="TGA", compression="tga_rle")
    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the checked-in overlay does not match the generator",
    )
    args = parser.parse_args()

    expected = render()
    expected_decree = render_compact_decree_button()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != expected:
            raise SystemExit(f"outdated generated asset: {OUTPUT}")
        if not DECREE_OUTPUT.exists() or DECREE_OUTPUT.read_bytes() != expected_decree:
            raise SystemExit(f"outdated generated asset: {DECREE_OUTPUT}")
        print(f"ok: {OUTPUT}")
        print(f"ok: {DECREE_OUTPUT}")
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(expected)
    DECREE_OUTPUT.write_bytes(expected_decree)
    print(OUTPUT)
    print(DECREE_OUTPUT)


if __name__ == "__main__":
    main()
