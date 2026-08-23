#!/usr/bin/env python3
"""Render the six Hundred Schools emblem sources into EU4 TGA sprites."""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
ASSETS = ROOT / "tools/assets/doctrine"
GFX = MOD / "gfx/interface"
PREVIEW = ASSETS / "zhx_doctrine_emblems_preview.png"
NO_DOCTRINE_TARGET = GFX / "zhx_no_doctrine_school.tga"

SCHOOLS = {
    "ru": ("Ru", "jade gui + bamboo slips"),
    "fa": ("Fa", "law tablet + measure"),
    "mo": ("Mo", "carpenter square + ink line"),
    "dao": ("Dao", "jade bi + cloud-water ribbon"),
    "bing": ("Bing", "bronze tiger tally"),
    "zongheng": ("Zongheng", "crossed envoy tallies"),
}
SIZES = {"": 64, "_school": 52, "_small": 32}


def source_path(slug: str) -> Path:
    return ASSETS / f"zhx_doctrine_{slug}_icon_source.png"


def target_path(slug: str, suffix: str) -> Path:
    return GFX / f"zhx_doctrine_{slug}{suffix}.tga"


def alpha_bbox(image: Image.Image, threshold: int = 8) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value >= threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("doctrine emblem source has no visible pixels")
    return bbox


def validate_source(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    if any(image.getpixel(point)[3] != 0 for point in ((0, 0), (image.width - 1, 0), (0, image.height - 1), (image.width - 1, image.height - 1))):
        raise ValueError(f"{path.name}: corners must be transparent")
    alpha_bbox(image)
    return image


def emblem(slug: str, size: int) -> Image.Image:
    source = validate_source(source_path(slug))
    source = source.crop(alpha_bbox(source))
    padding = 3 if size >= 52 else 2
    available = size - 2 * padding
    scale = min(available / source.width, available / source.height)
    dimensions = (
        max(1, round(source.width * scale)),
        max(1, round(source.height * scale)),
    )

    # Resize premultiplied pixels to prevent dark or magenta edge fringes.
    source = source.convert("RGBa").resize(
        dimensions, Image.Resampling.LANCZOS
    ).convert("RGBA")
    source = ImageEnhance.Contrast(source).enhance(1.08)
    source = source.filter(
        ImageFilter.UnsharpMask(
            radius=0.8 if size >= 52 else 0.55,
            percent=125,
            threshold=2,
        )
    )

    x = (size - source.width) // 2
    y = (size - source.height) // 2
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_alpha = source.getchannel("A").filter(
        ImageFilter.GaussianBlur(1.1 if size >= 52 else 0.6)
    )
    shadow_alpha = shadow_alpha.point(lambda value: value * 70 // 255)
    shadow = Image.new("RGBA", source.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_alpha)
    canvas.alpha_composite(shadow, (x + 1, y + 1))
    canvas.alpha_composite(source, (x, y))
    return canvas


def tga_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="TGA", compression="tga_rle")
    return buffer.getvalue()


def preview(rendered: dict[tuple[str, int], Image.Image]) -> Image.Image:
    canvas = Image.new("RGBA", (1200, 390), (27, 31, 35, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 14), "Hundred Schools doctrine emblems · source / 64 px / 52 px / 32 px", fill="white")
    card_width = 190
    for index, (slug, (label, motif)) in enumerate(SCHOOLS.items()):
        x = 16 + index * (card_width + 7)
        draw.rounded_rectangle((x, 42, x + card_width, 372), radius=9, fill=(44, 49, 54, 255))
        draw.text((x + 10, 52), label, fill=(236, 209, 137, 255))
        draw.text((x + 10, 68), motif, fill=(190, 196, 201, 255))
        source = validate_source(source_path(slug)).crop(alpha_bbox(validate_source(source_path(slug))))
        source.thumbnail((164, 205), Image.Resampling.LANCZOS)
        canvas.alpha_composite(source, (x + (card_width - source.width) // 2, 102 + (205 - source.height) // 2))
        canvas.alpha_composite(rendered[(slug, 64)], (x + 12, 298))
        canvas.alpha_composite(rendered[(slug, 52)], (x + 76, 304))
        icon32 = rendered[(slug, 32)].resize((64, 64), Image.Resampling.NEAREST)
        canvas.alpha_composite(icon32, (x + 126, 298))
    return canvas


def run(check: bool) -> None:
    rendered: dict[tuple[str, int], Image.Image] = {}
    for slug in SCHOOLS:
        for suffix, size in SIZES.items():
            image = emblem(slug, size)
            rendered[(slug, size)] = image
            target = target_path(slug, suffix)
            data = tga_bytes(image)
            if check:
                if not target.exists() or target.read_bytes() != data:
                    raise ValueError(f"{target.name}: stale doctrine emblem")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

    # EU4 has no clear_religious_school effect. This fully transparent sprite
    # retires an obsolete display mirror without showing a substitute doctrine.
    no_doctrine_data = tga_bytes(Image.new("RGBA", (52, 52), (0, 0, 0, 0)))
    if check:
        if (
            not NO_DOCTRINE_TARGET.exists()
            or NO_DOCTRINE_TARGET.read_bytes() != no_doctrine_data
        ):
            raise ValueError("transparent no-doctrine school sprite is stale")
    else:
        NO_DOCTRINE_TARGET.parent.mkdir(parents=True, exist_ok=True)
        NO_DOCTRINE_TARGET.write_bytes(no_doctrine_data)

    preview_image = preview(rendered)
    buffer = io.BytesIO()
    preview_image.save(buffer, format="PNG")
    if check:
        if not PREVIEW.exists() or PREVIEW.read_bytes() != buffer.getvalue():
            raise ValueError("doctrine emblem preview is stale")
    else:
        PREVIEW.write_bytes(buffer.getvalue())
    print(
        f"{'checked' if check else 'generated'} 18 doctrine sprites, "
        "one transparent sentinel and preview"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.check)


if __name__ == "__main__":
    main()
