#!/usr/bin/env python3
"""Generate the widened, integrated Empire of China background.

The checked-in 980x900 authority backdrop remains the source of every painted
element.  Besides widening the reform side, this generator clears the old
centre stack, moves the emperor artwork left, places the Mandate counter beside
it, extends the emperor nameplate across both blocks and leaves the lower
centre free for the seven great feudatories.  Interactive shields, values and
labels remain native GUI controls layered above this artwork.
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "guangdong_independent_practice/gfx/interface/gdd_eoc_bg_authority.tga"
OUTPUT = ROOT / "guangdong_independent_practice/gfx/interface/gdd_eoc_bg_authority_wide.tga"

SOURCE_WIDTH = 980
HEIGHT = 900
EXTRA_WIDTH = 40
SEAM_X = 900
SEAM_SAMPLE_WIDTH = 80

# Coordinates below are local to the background texture.  GUI coordinates are
# 66 px to the right and 18 px below these because celestial_bg is offset in
# celestialempireview.gui.
CENTRE_CLEAR = (268, 66, 734, 870)
BLANK_TEXTURE_SAMPLE = (286, 535, 706, 690)
EMPEROR_ART = (330, 82, 628, 246)
EMPEROR_ART_TARGET = (252, 82)
EMPEROR_NAMEPLATE = (332, 244, 660, 294)
EMPEROR_NAMEPLATE_TARGET = (286, 234, 690, 284)
MANDATE_COUNTER = (404, 410, 571, 531)
MANDATE_COUNTER_TARGET = (535, 73)
MANDATE_HEADER = (350, 397, 630, 432)
FEUDATORY_HEADER_TARGET = (314, 666, 684, 698)


def stretched_texture(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Return a subdued wine-red texture without copying UI ornaments."""
    sample = source.crop(BLANK_TEXTURE_SAMPLE)
    strip = sample.resize((size[0], sample.height), Image.Resampling.BICUBIC)
    texture = Image.new("RGBA", size)
    y = 0
    flip = False
    while y < size[1]:
        tile = strip.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if flip else strip
        texture.alpha_composite(tile, (0, y))
        y += strip.height
        flip = not flip
    # A very light blur suppresses tile boundaries without flattening the
    # paper-and-brocade grain into the conspicuous vertical smear caused by a
    # single full-height stretch.
    return texture.filter(ImageFilter.GaussianBlur(radius=0.65))


def rebuild_centre(source: Image.Image, output: Image.Image) -> None:
    """Recompose the emperor/Mandate area and clear the old member frame."""
    left, top, right, bottom = CENTRE_CLEAR
    output.paste(stretched_texture(source, (right - left, bottom - top)), (left, top))

    emperor = source.crop(EMPEROR_ART)
    output.alpha_composite(emperor, EMPEROR_ART_TARGET)

    nameplate = source.crop(EMPEROR_NAMEPLATE).resize(
        (
            EMPEROR_NAMEPLATE_TARGET[2] - EMPEROR_NAMEPLATE_TARGET[0],
            EMPEROR_NAMEPLATE_TARGET[3] - EMPEROR_NAMEPLATE_TARGET[1],
        ),
        Image.Resampling.LANCZOS,
    )
    output.alpha_composite(
        nameplate,
        (EMPEROR_NAMEPLATE_TARGET[0], EMPEROR_NAMEPLATE_TARGET[1]),
    )

    mandate = source.crop(MANDATE_COUNTER)
    output.alpha_composite(mandate, MANDATE_COUNTER_TARGET)

    # Reuse the exact Mandate title ribbon for the seven-feudatory heading.
    # Only its width changes; colour, edge shading and painted texture remain
    # identical to the top-right Mandate ribbon.
    feudatory_header = source.crop(MANDATE_HEADER).resize(
        (
            FEUDATORY_HEADER_TARGET[2] - FEUDATORY_HEADER_TARGET[0],
            FEUDATORY_HEADER_TARGET[3] - FEUDATORY_HEADER_TARGET[1],
        ),
        Image.Resampling.LANCZOS,
    )
    output.alpha_composite(
        feudatory_header,
        (FEUDATORY_HEADER_TARGET[0], FEUDATORY_HEADER_TARGET[1]),
    )


def render_image() -> Image.Image:
    source = Image.open(SOURCE).convert("RGBA")
    if source.size != (SOURCE_WIDTH, HEIGHT):
        raise SystemExit(f"unexpected source size: {source.size}")

    output = Image.new("RGBA", (SOURCE_WIDTH + EXTRA_WIDTH, HEIGHT), (0, 0, 0, 0))
    seam_left = SEAM_X - SEAM_SAMPLE_WIDTH
    output.paste(source.crop((0, 0, seam_left, HEIGHT)), (0, 0))

    # Stretch a real wine-red/frame strip instead of introducing a flat band;
    # this preserves both the paper texture and the horizontal top/bottom trim.
    seam = source.crop((seam_left, 0, SEAM_X, HEIGHT))
    seam = seam.resize(
        (SEAM_SAMPLE_WIDTH + EXTRA_WIDTH, HEIGHT), Image.Resampling.LANCZOS
    )
    output.paste(seam, (seam_left, 0))

    right = source.crop((SEAM_X, 0, SOURCE_WIDTH, HEIGHT))
    output.paste(right, (SEAM_X + EXTRA_WIDTH, 0))

    rebuild_centre(source, output)
    return output


def render() -> bytes:
    output = render_image()

    buffer = BytesIO()
    output.save(buffer, format="TGA", compression="tga_rle")
    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the checked-in widened background is stale",
    )
    args = parser.parse_args()

    expected = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != expected:
            raise SystemExit(f"outdated generated asset: {OUTPUT}")
        print(f"ok: {OUTPUT}")
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(expected)
    print(OUTPUT)


if __name__ == "__main__":
    main()
