#!/usr/bin/env python3
"""Generate the 礼教/景教 emblems, Nestorian saints and school overlays."""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
LIJIAO_SOURCE = ROOT / "tools/assets/religion/zhx_lijiao_religion_icon_source.png"
NESTORIAN_SOURCE = (
    ROOT / "tools/assets/religion/zhx_nestorian_religion_icon_source.png"
)
NESTORIAN_PORTRAITS = (
    ROOT / "tools/assets/religion/zhx_nestorian_nestorius_source.png",
    ROOT / "tools/assets/religion/zhx_nestorian_yelv_source.png",
    ROOT / "tools/assets/religion/zhx_nestorian_jinghui_source.png",
    ROOT / "tools/assets/religion/zhx_nestorian_thomas_source.png",
    ROOT / "tools/assets/religion/zhx_nestorian_anthony_source.png",
)
PREVIEW = ROOT / "tools/assets/religion/zhx_lijiao_religion_icon_preview.png"
SCHOOL_BUTTON = MOD / "gfx/interface/zhx_lijiao_school_button.dds"
NO_DOCTRINE_BUTTON = MOD / "gfx/interface/zhx_no_doctrine_school_button.dds"
PRACTICE_HITBOX = MOD / "gfx/interface/zhx_practice_click_hitbox.dds"
SCHOOL_TOOLTIP_HITBOX = MOD / "gfx/interface/zhx_school_tooltip_hitbox.dds"
RUSSIAN_ICONS = MOD / "gfx/interface/russian_icons_strip.dds"
DEFAULT_VANILLA = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)
LIJIAO_FRAME_INDEX = 8  # zero-based; religion definition icon = 9
NESTORIAN_FRAME_INDEX = 6  # zero-based; unused vanilla slot, icon = 7
EXPECTED_SCHOOL_BUTTON_SHA256 = (
    "091cac9c434db23d43bd90a79128c4abe6b5b0073d8a6bfb7a06965fe3c24036"
)
EXPECTED_RUSSIAN_ICONS_SHA256 = (
    "b1b78b69401223489ff9539eeb760db2a77b8bca4532b347a433a79660dbca1d"
)
EXPECTED_SHEET_SHA256 = {
    "icon_religion.dds": "d9497a5995187bad5ef39d953b4771eecd88e1699cc0ee91c032ff2162772b70",
    "country_icon_religion.dds": "1d8952f4e7979c6ad19b964823696edba5ac0c1a7d223210fb49c6a4ce7a5be9",
    "icon_religion_small.dds": "fa1c7d812424430240a6d3c90b8cf9f7a1a43ff7c350d19ed0d6a3895918d4ff",
    "province_view_religion.dds": "52954419a46bfd250a8bda6dda389494c1947b2a8bdf188da89b64976e22e772",
}
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


def lijiao_emblem(size: int) -> Image.Image:
    source = Image.open(LIJIAO_SOURCE).convert("RGBA")
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


def nestorian_emblem(size: int) -> Image.Image:
    """Scale the original cross-and-lotus source for the shared religion atlas."""
    source = Image.open(NESTORIAN_SOURCE).convert("RGBA")
    source = source.crop(alpha_bbox(source))
    padding = 2 if size == 64 else 1
    available = size - 2 * padding
    scale = min(available / source.width, available / source.height)
    dimensions = (
        max(1, round(source.width * scale)),
        max(1, round(source.height * scale)),
    )
    source = source.convert("RGBa").resize(
        dimensions, Image.Resampling.LANCZOS
    ).convert("RGBA")
    source = source.filter(
        ImageFilter.UnsharpMask(
            radius=0.7 if size == 64 else 0.45,
            percent=135,
            threshold=1,
        )
    )
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(
        source,
        ((size - source.width) // 2, (size - source.height) // 2),
    )
    return canvas


def portrait_frame(path: Path) -> Image.Image:
    """Reduce one original square portrait to a crisp 58 px native icon."""
    source = Image.open(path).convert("RGBA")
    side = min(source.size)
    left = (source.width - side) // 2
    top = (source.height - side) // 2
    source = source.crop((left, top, left + side, top + side))
    source = source.convert("RGBa").resize(
        (58, 58), Image.Resampling.LANCZOS
    ).convert("RGBA")
    return source.filter(
        ImageFilter.UnsharpMask(radius=0.45, percent=135, threshold=1)
    )


def russian_icon_sheet(vanilla_root: Path) -> Image.Image:
    source_path = vanilla_root / "gfx/interface/russian_icons_strip.dds"
    data = source_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_RUSSIAN_ICONS_SHA256:
        raise ValueError(
            "unsupported EU4 Orthodox-icon baseline: "
            f"{digest}; expected {EXPECTED_RUSSIAN_ICONS_SHA256}"
        )
    vanilla = Image.open(io.BytesIO(data)).convert("RGBA")
    if vanilla.size != (290, 58):
        raise ValueError(f"unexpected Orthodox-icon dimensions: {vanilla.size}")
    sheet = Image.new("RGBA", (580, 58), (0, 0, 0, 0))
    sheet.alpha_composite(vanilla, (0, 0))
    for index, path in enumerate(NESTORIAN_PORTRAITS, start=5):
        sheet.alpha_composite(portrait_frame(path), (index * 58, 0))
    return sheet


def dds_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="DDS")
    return buffer.getvalue()


def school_button_plate(vanilla_root: Path) -> Image.Image:
    """Return the native 42 px ring with its Islamic centre fully covered."""
    source_path = vanilla_root / "gfx/interface/muslim_school_button.dds"
    data = source_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SCHOOL_BUTTON_SHA256:
        raise ValueError(
            "unsupported EU4 scholar-button baseline: "
            f"{digest}; expected {EXPECTED_SCHOOL_BUTTON_SHA256}"
        )

    button = Image.open(io.BytesIO(data)).convert("RGBA")
    if button.size != (42, 42):
        raise ValueError(f"unexpected scholar-button dimensions: {button.size}")

    # Keep the native outer gold ring, but fully cover its Islamic centre so no
    # crescent can bleed through the transparent 礼鼎 silhouette.
    scale = 4
    plate = Image.new("RGBA", (42 * scale, 42 * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(plate)
    draw.ellipse(
        (5 * scale, 5 * scale, 36 * scale, 36 * scale),
        fill=(58, 31, 23, 255),
        outline=(191, 142, 53, 255),
        width=2 * scale,
    )
    plate = plate.resize(button.size, Image.Resampling.LANCZOS)
    button.alpha_composite(plate)
    return button


def school_button(vanilla_root: Path) -> Image.Image:
    """Re-skin the neutral native plate with the established 礼鼎."""
    button = school_button_plate(vanilla_root)
    button.alpha_composite(lijiao_emblem(28), (7, 7))
    return button


def patched_sheet(vanilla_root: Path, name: str, frame_size: int) -> Image.Image:
    source_path = vanilla_root / "gfx/interface" / name
    data = source_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHEET_SHA256[name]:
        raise ValueError(
            f"{name}: unsupported EU4 1.37.5 baseline {digest}; "
            f"expected {EXPECTED_SHEET_SHA256[name]}"
        )
    sheet = Image.open(io.BytesIO(data)).convert("RGBA")
    if sheet.height != frame_size or sheet.width % frame_size:
        raise ValueError(f"{name}: unexpected sheet dimensions {sheet.size}")
    if sheet.width // frame_size <= LIJIAO_FRAME_INDEX:
        raise ValueError(f"{name}: frame 9 is missing")
    sheet.paste(
        nestorian_emblem(frame_size),
        (NESTORIAN_FRAME_INDEX * frame_size, 0),
    )
    sheet.paste(
        lijiao_emblem(frame_size),
        (LIJIAO_FRAME_INDEX * frame_size, 0),
    )
    return sheet


def preview(
    sheets: dict[str, Image.Image], russian_icons: Image.Image
) -> Image.Image:
    canvas = Image.new("RGBA", (900, 600), (35, 38, 42, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (18, 12),
        "Religion atlas · Nestorian frame 7 · Ritual Teaching frame 9",
        fill="white",
    )
    rows = [
        ("icon_religion.dds", 64, 42, 3),
        ("icon_religion_small.dds", 32, 270, 5),
    ]
    for name, frame_size, y, display_scale in rows:
        sheet = sheets[name]
        draw.text(
            (18, y),
            f"{name}: frames 7 and 9",
            fill=(210, 214, 220, 255),
        )
        strip = sheet.crop(
            (
                NESTORIAN_FRAME_INDEX * frame_size,
                0,
                (LIJIAO_FRAME_INDEX + 1) * frame_size,
                frame_size,
            )
        )
        strip = strip.resize(
            (strip.width * display_scale, strip.height * display_scale),
            Image.Resampling.NEAREST,
        )
        canvas.alpha_composite(strip, (18, y + 22))
    draw.text((18, 488), "Patriarch icons: Orthodox 1-5 · Nestorian 6-10", fill="white")
    scaled_icons = russian_icons.resize((580, 58), Image.Resampling.NEAREST)
    canvas.alpha_composite(scaled_icons, (18, 516))
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

    russian_icons = russian_icon_sheet(vanilla_root)
    russian_data = dds_bytes(russian_icons)
    if check:
        if not RUSSIAN_ICONS.exists() or RUSSIAN_ICONS.read_bytes() != russian_data:
            raise ValueError("Nestorian patriarch-icon strip is stale")
    else:
        RUSSIAN_ICONS.parent.mkdir(parents=True, exist_ok=True)
        RUSSIAN_ICONS.write_bytes(russian_data)

    button = school_button(vanilla_root)
    button_data = dds_bytes(button)
    if check:
        if not SCHOOL_BUTTON.exists() or SCHOOL_BUTTON.read_bytes() != button_data:
            raise ValueError("礼教 school-button overlay is stale")
    else:
        SCHOOL_BUTTON.parent.mkdir(parents=True, exist_ok=True)
        SCHOOL_BUTTON.write_bytes(button_data)

    # The transparent native-school sentinel still makes EU4 draw the fixed
    # invite-scholar button. Cover its Islamic crescent with the same neutral
    # ritual plate, but omit the 礼鼎 because no doctrine is currently active.
    no_doctrine_button = school_button_plate(vanilla_root)
    no_doctrine_button_data = dds_bytes(no_doctrine_button)
    if check:
        if (
            not NO_DOCTRINE_BUTTON.exists()
            or NO_DOCTRINE_BUTTON.read_bytes() != no_doctrine_button_data
        ):
            raise ValueError("no-doctrine school-button overlay is stale")
    else:
        NO_DOCTRINE_BUTTON.parent.mkdir(parents=True, exist_ok=True)
        NO_DOCTRINE_BUTTON.write_bytes(no_doctrine_button_data)

    # Scripted GUI buttons derive their mouse rectangle from the sprite. Keep
    # the practice hit target exactly aligned with the 28x24 visible number and
    # make every pixel fully transparent so it adds no frame or hover artwork.
    practice_hitbox = Image.new("RGBA", (28, 24), (0, 0, 0, 0))
    practice_hitbox_data = dds_bytes(practice_hitbox)
    if check:
        if (
            not PRACTICE_HITBOX.exists()
            or PRACTICE_HITBOX.read_bytes() != practice_hitbox_data
        ):
            raise ValueError("practice-number click hitbox is stale")
    else:
        PRACTICE_HITBOX.parent.mkdir(parents=True, exist_ok=True)
        PRACTICE_HITBOX.write_bytes(practice_hitbox_data)

    # Native school pictures are 52px and both target views render them at
    # 0.5 scale. This invisible 26x26 icon replaces the hard-coded name-only
    # hover area without drawing the school emblem a second time.
    school_tooltip_hitbox = Image.new("RGBA", (26, 26), (0, 0, 0, 0))
    school_tooltip_hitbox_data = dds_bytes(school_tooltip_hitbox)
    if check:
        if (
            not SCHOOL_TOOLTIP_HITBOX.exists()
            or SCHOOL_TOOLTIP_HITBOX.read_bytes() != school_tooltip_hitbox_data
        ):
            raise ValueError("school-card tooltip hitbox is stale")
    else:
        SCHOOL_TOOLTIP_HITBOX.parent.mkdir(parents=True, exist_ok=True)
        SCHOOL_TOOLTIP_HITBOX.write_bytes(school_tooltip_hitbox_data)

    preview_image = preview(rendered, russian_icons)
    if check:
        buffer = io.BytesIO()
        preview_image.save(buffer, format="PNG")
        if not PREVIEW.exists() or PREVIEW.read_bytes() != buffer.getvalue():
            raise ValueError("礼教 religion icon preview is stale")
    else:
        preview_image.save(PREVIEW)

    print(
        f"{'checked' if check else 'generated'} four religion sheets, "
        "ten patriarch-icon frames, two 42 px school-button overlays and one "
        "transparent 28x24 practice hitbox and one transparent 26x26 school "
        "tooltip hitbox"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.vanilla_root.resolve(), args.check)


if __name__ == "__main__":
    main()
