#!/usr/bin/env python3
"""Shared, deterministic Shang-inscription flag artwork.

The emblems are deliberately drawn as a small set of thick vector strokes.
That keeps the archaeological silhouette readable after EU4 masks a 128 px
flag into a much smaller shield.  They are reconstructions, not modern font
glyphs and not claims of an exact tracing of a particular rubbing.
"""

from __future__ import annotations

import io
import random

from PIL import Image, ImageDraw


SIZE = 128
SCALE = 4


def _scaled_points(points):
    return [(round(x * SCALE), round(y * SCALE)) for x, y in points]


def _mix(left, right, amount: float):
    return tuple(round(a * (1 - amount) + b * amount) for a, b in zip(left, right))


def _line(draw, points, fill, width: int, joint: str = "curve") -> None:
    draw.line(_scaled_points(points), fill=fill, width=width * SCALE, joint=joint)


def _carved_line(draw, points, ink, edge, width: int = 6) -> None:
    """Draw an incised-looking stroke with a narrow contrasting shoulder."""
    _line(draw, points, edge, width + 4)
    _line(draw, points, ink, width)


def _ellipse(draw, box, fill=None, outline=None, width: int = 1) -> None:
    draw.ellipse(
        tuple(round(value * SCALE) for value in box),
        fill=fill,
        outline=outline,
        width=width * SCALE,
    )


def _rect(draw, box, fill=None, outline=None, width: int = 1) -> None:
    draw.rectangle(
        tuple(round(value * SCALE) for value in box),
        fill=fill,
        outline=outline,
        width=width * SCALE,
    )


def _draw_ji(draw, ink, edge) -> None:
    """Oracle-style 箕/其: a legged, lattice-woven winnowing basket."""
    _carved_line(draw, [(35, 30), (42, 37), (86, 37), (93, 30)], ink, edge, 6)
    _carved_line(draw, [(42, 37), (36, 91), (52, 104), (76, 104), (92, 91), (86, 37)], ink, edge, 6)
    for y in (53, 70, 87):
        inset = (y - 37) * 0.10
        _carved_line(draw, [(40 - inset, y), (88 + inset, y)], ink, edge, 4)
    for x, bottom in ((52, 99), (64, 104), (76, 99)):
        _carved_line(draw, [(x, 40), (x, bottom)], ink, edge, 4)
    _carved_line(draw, [(52, 104), (45, 116)], ink, edge, 5)
    _carved_line(draw, [(76, 104), (83, 116)], ink, edge, 5)


def _draw_zhu(draw, ink, edge) -> None:
    """Oracle/early-bronze 竹 clan emblem: paired stems and pendent leaves."""
    _carved_line(draw, [(51, 106), (51, 45), (45, 25)], ink, edge, 7)
    _carved_line(draw, [(77, 106), (77, 45), (83, 25)], ink, edge, 7)
    for points in (
        [(49, 37), (32, 30), (25, 39)],
        [(50, 52), (33, 47), (27, 57)],
        [(52, 67), (38, 63), (31, 73)],
        [(79, 37), (96, 30), (103, 39)],
        [(78, 52), (95, 47), (101, 57)],
        [(76, 67), (90, 63), (97, 73)],
    ):
        _carved_line(draw, points, ink, edge, 5)
    _carved_line(draw, [(46, 106), (58, 106)], ink, edge, 5)
    _carved_line(draw, [(70, 106), (82, 106)], ink, edge, 5)


def _draw_wuzhong(draw, ink, edge) -> None:
    """Compact two-part 無終 clan emblem after the Middle Shang dagger type."""
    # 無 retains the early dancing-person silhouette rather than a modern
    # block character: head, crossed arms with feathered ends, body and legs.
    _ellipse(
        draw,
        (58, 15, 70, 27),
        fill=ink,
        outline=edge,
        width=3,
    )
    _carved_line(draw, [(64, 27), (64, 67)], ink, edge, 6)
    _carved_line(draw, [(64, 38), (38, 50), (25, 42)], ink, edge, 6)
    _carved_line(draw, [(64, 38), (90, 50), (103, 42)], ink, edge, 6)
    _carved_line(draw, [(31, 45), (25, 56)], ink, edge, 4)
    _carved_line(draw, [(97, 45), (103, 56)], ink, edge, 4)
    _carved_line(draw, [(64, 67), (48, 82)], ink, edge, 6)
    _carved_line(draw, [(64, 67), (80, 82)], ink, edge, 6)

    # 終 is compressed to the tied-thread and crossing terminal strokes found
    # in early compound clan marks.  The open diamond remains clear at 32 px.
    _carved_line(draw, [(38, 98), (49, 88), (64, 102), (79, 88), (90, 98)], ink, edge, 5)
    _carved_line(draw, [(49, 112), (64, 102), (79, 112)], ink, edge, 5)
    _carved_line(draw, [(64, 88), (64, 119)], ink, edge, 4)


DRAWERS = {
    "ji": _draw_ji,
    "zhu": _draw_zhu,
    "wuzhong": _draw_wuzhong,
}


def render_shang_flag(
    tag: str,
    emblem: str,
    background: tuple[int, int, int],
    ink: tuple[int, int, int],
    accent: tuple[int, int, int],
) -> Image.Image:
    """Render one shared Shang-heritage flag as a 128×128 RGB image."""
    if emblem not in DRAWERS:
        raise ValueError(f"unknown Shang emblem: {emblem}")
    image = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (*background, 255))
    draw = ImageDraw.Draw(image)

    dark_edge = _mix(background, ink, 0.72)
    disc = _mix(background, accent, 0.24)
    _rect(draw, (2, 2, 126, 126), outline=dark_edge, width=3)
    _rect(draw, (7, 7, 121, 121), outline=ink, width=1)
    _ellipse(draw, (13, 13, 115, 115), fill=disc, outline=accent, width=3)
    _ellipse(draw, (18, 18, 110, 110), outline=ink, width=1)
    DRAWERS[emblem](draw, ink, dark_edge)

    rendered = image.convert("RGB").resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    rng = random.Random(f"shang-inscription-flag:{tag}")
    pixels = rendered.load()
    for y in range(SIZE):
        for x in range(SIZE):
            weave = 1 if (x % 5 == 0 or y % 6 == 0) else 0
            delta = rng.choice((-2, -1, 0, 0, 0, 1, 2)) + weave
            pixels[x, y] = tuple(max(0, min(255, channel + delta)) for channel in pixels[x, y])
    return rendered


def shang_flag_bytes(
    tag: str,
    emblem: str,
    background: tuple[int, int, int],
    ink: tuple[int, int, int],
    accent: tuple[int, int, int],
) -> bytes:
    stream = io.BytesIO()
    render_shang_flag(tag, emblem, background, ink, accent).save(
        stream,
        format="TGA",
        compression=None,
    )
    return stream.getvalue()
