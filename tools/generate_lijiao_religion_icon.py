#!/usr/bin/env python3
"""Replace only the Confucian (frame 9) religion emblem with the 礼鼎 icon."""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
SOURCE = ROOT / "tools/assets/religion/zhx_lijiao_religion_icon_source.png"
PREVIEW = ROOT / "tools/assets/religion/zhx_lijiao_religion_icon_preview.png"
DEFAULT_VANILLA = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)
FRAME_INDEX = 8  # zero-based; religion definition icon = 9
SHEETS = {
    "icon_religion.dds": 64,
    "country_icon_religion.dds": 64,
    "icon_religion_small.dds": 32,
    "province_view_religion.dds": 32,
}


def alpha_bbox(image: Image.Image, threshold: int = 8) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value >= threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("religion icon source has no visible pixels")
    return bbox


def emblem(size: int) -> Image.Image:
    source = Image.open(SOURCE).convert("RGBA")
    source = source.crop(alpha_bbox(source))
    padding = 3 if size == 64 else 2
    available = size - 2 * padding
    scale = min(available / source.width, available / source.height)
    dimensions = (
        max(1, round(source.width * scale)),
        max(1, round(source.height * scale)),
    )

    # Resize premultiplied RGBA to avoid a dark fringe around transparent edges.
    source = source.convert("RGBa").resize(
        dimensions, Image.Resampling.LANCZOS
    ).convert("RGBA")
    source = ImageEnhance.Contrast(source).enhance(1.08)
    source = source.filter(
        ImageFilter.UnsharpMask(
            radius=0.8 if size == 64 else 0.55,
            percent=120,
            threshold=2,
        )
    )

    x = (size - source.width) // 2
    y = (size - source.height) // 2
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    shadow_alpha = source.getchannel("A").filter(
        ImageFilter.GaussianBlur(1.2 if size == 64 else 0.65)
    )
    shadow_alpha = shadow_alpha.point(lambda value: value * 90 // 255)
    shadow = Image.new("RGBA", source.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_alpha)
    canvas.alpha_composite(shadow, (x + 1, y + 1))
    canvas.alpha_composite(source, (x, y))
    return canvas


def dds_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="DDS")
    return buffer.getvalue()


def patched_sheet(vanilla_root: Path, name: str, frame_size: int) -> Image.Image:
    source_path = vanilla_root / "gfx/interface" / name
    sheet = Image.open(source_path).convert("RGBA")
    if sheet.height != frame_size or sheet.width % frame_size:
        raise ValueError(f"{name}: unexpected sheet dimensions {sheet.size}")
    if sheet.width // frame_size <= FRAME_INDEX:
        raise ValueError(f"{name}: frame 9 is missing")
    sheet.paste(emblem(frame_size), (FRAME_INDEX * frame_size, 0))
    return sheet


def preview(sheets: dict[str, Image.Image]) -> Image.Image:
    canvas = Image.new("RGBA", (720, 470), (35, 38, 42, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 12), "Ritual Teaching emblem · frame 9 only", fill="white")
    rows = [
        ("icon_religion.dds", 64, 42, 3),
        ("icon_religion_small.dds", 32, 270, 5),
    ]
    for name, frame_size, y, display_scale in rows:
        sheet = sheets[name]
        draw.text((18, y), f"{name}: frames 8 / 9 / 10", fill=(210, 214, 220, 255))
        strip = sheet.crop(
            (
                (FRAME_INDEX - 1) * frame_size,
                0,
                (FRAME_INDEX + 2) * frame_size,
                frame_size,
            )
        )
        strip = strip.resize(
            (strip.width * display_scale, strip.height * display_scale),
            Image.Resampling.NEAREST,
        )
        canvas.alpha_composite(strip, (18, y + 22))
    return canvas


def run(vanilla_root: Path, check: bool) -> None:
    rendered: dict[str, Image.Image] = {}
    for name, frame_size in SHEETS.items():
        sheet = patched_sheet(vanilla_root, name, frame_size)
        rendered[name] = sheet
        target = MOD / "gfx/interface" / name
        data = dds_bytes(sheet)
        if check:
            if not target.exists() or target.read_bytes() != data:
                raise ValueError(f"{name}: stale 礼教 religion icon sheet")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    preview_image = preview(rendered)
    if check:
        buffer = io.BytesIO()
        preview_image.save(buffer, format="PNG")
        if not PREVIEW.exists() or PREVIEW.read_bytes() != buffer.getvalue():
            raise ValueError("礼教 religion icon preview is stale")
    else:
        preview_image.save(PREVIEW)

    print(f"{'checked' if check else 'generated'} four religion sheets; frame 9 only")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.vanilla_root.resolve(), args.check)


if __name__ == "__main__":
    main()
