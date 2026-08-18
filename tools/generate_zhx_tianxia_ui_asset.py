#!/usr/bin/env python3
"""Generate the original Zhou/Tianxia GUI backdrop used by the mod.

The image intentionally contains no text. All labels remain normal EU4 GUI
objects so localisation, values and scripted visibility stay independent from
the raster asset.
"""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "guangdong_independent_practice/gfx/interface/zhx_tianxia_bg.tga"
DRAG_OUTPUT = ROOT / "guangdong_independent_practice/gfx/interface/zhx_tianxia_drag_surface.tga"
SCALE = 2
WIDTH = 900
HEIGHT = 930
WINDOW_WIDTH = 980
WINDOW_HEIGHT = 990


def scaled_box(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return tuple(value * SCALE for value in box)


def main() -> None:
    # WindowType requires a named background button in order to be draggable.
    # Keep that hit surface visually transparent and separate from the visible art:
    # engine-owned background controls are otherwise snapped to (0, 0), shifting
    # the artwork away from the coordinates used by every label and shield.
    # Alpha 0 textures are discarded by the GUI renderer and stop receiving
    # drag input. Alpha 1 is visually imperceptible but keeps the hit surface.
    drag_surface = Image.new(
        "RGBA", (WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0, 0, 1)
    )
    DRAG_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    drag_surface.save(DRAG_OUTPUT, format="TGA", compression="tga_rle")
    print(DRAG_OUTPUT)

    image = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    gold = (184, 132, 55, 255)
    light_gold = (231, 195, 108, 255)
    dark_gold = (92, 56, 25, 255)
    wine = (55, 22, 27, 248)
    panel = (78, 34, 39, 246)
    panel_dark = (45, 20, 25, 248)
    jade = (31, 96, 73, 255)
    jade_dark = (15, 52, 43, 255)

    draw.rounded_rectangle(
        scaled_box((3, 3, 897, 927)),
        radius=26 * SCALE,
        fill=wine,
        outline=dark_gold,
        width=9 * SCALE,
    )
    draw.rounded_rectangle(
        scaled_box((10, 10, 890, 920)),
        radius=21 * SCALE,
        outline=gold,
        width=3 * SCALE,
    )
    draw.rounded_rectangle(
        scaled_box((17, 17, 883, 913)),
        radius=17 * SCALE,
        outline=light_gold,
        width=1 * SCALE,
    )

    # Header ribbon and its folded ends.
    draw.rounded_rectangle(
        scaled_box((85, 22, 815, 82)),
        radius=18 * SCALE,
        fill=jade,
        outline=gold,
        width=3 * SCALE,
    )
    draw.polygon(
        [(42 * SCALE, 38 * SCALE), (98 * SCALE, 27 * SCALE),
         (98 * SCALE, 77 * SCALE), (50 * SCALE, 67 * SCALE)],
        fill=jade_dark,
        outline=gold,
    )
    draw.polygon(
        [(858 * SCALE, 38 * SCALE), (802 * SCALE, 27 * SCALE),
         (802 * SCALE, 77 * SCALE), (850 * SCALE, 67 * SCALE)],
        fill=jade_dark,
        outline=gold,
    )
    draw.line(scaled_box((118, 72, 782, 72)), fill=light_gold, width=1 * SCALE)

    # Three summary cards, two full mechanic cards and a shield roster.
    cards = [
        (30, 100, 286, 250),
        (306, 100, 594, 250),
        (614, 100, 870, 250),
        (30, 270, 438, 480),
        (462, 270, 870, 480),
        (30, 500, 870, 910),
    ]
    for box in cards:
        draw.rounded_rectangle(
            scaled_box(box),
            radius=11 * SCALE,
            fill=panel,
            outline=dark_gold,
            width=5 * SCALE,
        )
        inner = (box[0] + 6, box[1] + 6, box[2] - 6, box[3] - 6)
        draw.rounded_rectangle(
            scaled_box(inner),
            radius=8 * SCALE,
            outline=gold,
            width=2 * SCALE,
        )

    # Section title ribbons sit wholly inside their cards.
    ribbons = [
        (48, 110, 268, 139),
        (324, 110, 576, 139),
        (632, 110, 852, 139),
        (55, 282, 413, 316),
        (487, 282, 845, 316),
        (55, 512, 845, 546),
    ]
    for box in ribbons:
        draw.rounded_rectangle(
            scaled_box(box),
            radius=8 * SCALE,
            fill=jade_dark,
            outline=gold,
            width=2 * SCALE,
        )

    # Progress track and restrained decorative dividers.
    draw.rounded_rectangle(
        scaled_box((350, 187, 550, 214)),
        radius=7 * SCALE,
        fill=panel_dark,
        outline=gold,
        width=2 * SCALE,
    )
    for x in range(370, 550, 20):
        draw.line(scaled_box((x, 191, x, 210)), fill=dark_gold, width=1 * SCALE)

    for x in (44, 856):
        for y in (156, 214, 310, 870):
            draw.ellipse(
                scaled_box((x - 8, y - 8, x + 8, y + 8)),
                fill=jade_dark,
                outline=gold,
                width=2 * SCALE,
            )

    draw.line(scaled_box((66, 468, 402, 468)), fill=dark_gold, width=2 * SCALE)
    draw.line(scaled_box((498, 468, 834, 468)), fill=dark_gold, width=2 * SCALE)
    draw.line(scaled_box((66, 890, 834, 890)), fill=dark_gold, width=2 * SCALE)

    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format="TGA", compression="tga_rle")
    print(OUTPUT)

    # Pixel-exact overlays for ritual harmony from -100 to 100. One texture is
    # generated per ten points so the scripted GUI can select a precise visual
    # bucket without relying on an engine-owned progress-bar controller.
    for value in range(-100, 101, 10):
        if value < 0:
            name = f"m{abs(value):03d}"
            strength = abs(value) / 100
            start = 100 - round(97 * strength)
            end = 100
            if value <= -70:
                active_colour = (143, 42, 45, 255)
            else:
                active_colour = (181, 102, 41, 255)
        elif value > 0:
            name = f"p{value:03d}"
            strength = value / 100
            start = 100
            end = 100 + round(97 * strength)
            active_colour = (
                round(62 - 13 * strength),
                round(115 + 30 * strength),
                round(80 + 4 * strength),
                255,
            )
        else:
            name = "zero"
            start = 96
            end = 104
            active_colour = light_gold

        bar = Image.new("RGBA", (200 * SCALE, 27 * SCALE), (0, 0, 0, 0))
        bar_draw = ImageDraw.Draw(bar)
        bar_draw.rounded_rectangle(
            scaled_box((0, 0, 199, 26)),
            radius=7 * SCALE,
            fill=panel_dark,
            outline=gold,
            width=2 * SCALE,
        )
        bar_draw.rounded_rectangle(
            scaled_box((start, 3, end, 23)),
            radius=4 * SCALE,
            fill=active_colour,
        )
        bar_draw.line(
            scaled_box((100, 2, 100, 24)),
            fill=light_gold,
            width=1 * SCALE,
        )
        bar = bar.resize((200, 27), Image.Resampling.LANCZOS)
        bar_output = OUTPUT.parent / f"zhx_ritual_bar_{name}.tga"
        bar.save(bar_output, format="TGA", compression="tga_rle")
        print(bar_output)

    # Remove the obsolete five-tier overlays from the earlier prototype.
    for stale_name in ("ordered", "stable", "balanced", "fractured", "collapsed"):
        (OUTPUT.parent / f"zhx_ritual_bar_{stale_name}.tga").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
