#!/usr/bin/env python3
"""Extract and register the documented small-seal 舟 mask for ZHO."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zlib
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "tools/assets/zhuxia_seal_masks.json.zlib"
REFERENCE = ROOT / "tools/assets/zho_flag/zho_small_seal_reference.jpg"
SOURCE_MASK = ROOT / "tools/assets/zho_flag/zho_small_seal_mask.png"
PREVIEW = ROOT / "planning/zho_flag_b77/zho_small_seal_flag_preview.png"

SIZE = 128
GLYPH_WIDTH = 72
GLYPH_HEIGHT = 108
BACKGROUND = (183, 168, 75)
INK = (232, 218, 164)
REFERENCE_SHA256 = "0fe8786b12c637133bf4d31fa8cd58beab7e0dda36e7d52430f59b0935dc1685"


def build_mask() -> Image.Image:
    """Turn the cited black-on-white Shuowen form into a centred alpha mask."""
    if not REFERENCE.exists():
        raise FileNotFoundError(f"missing documented ZHO glyph reference: {REFERENCE}")
    digest = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
    if digest != REFERENCE_SHA256:
        raise ValueError(f"documented ZHO glyph reference hash drifted: {digest}")
    reference = Image.open(REFERENCE).convert("L")
    # White becomes transparent and black becomes opaque. The source is a tiny
    # JPEG scan, so clear its pale compression halo and lift stroke opacity for
    # the 32 px in-game shield without redrawing or widening the glyph.
    ink = ImageOps.invert(reference).point(
        lambda value: 0 if value < 40 else min(255, round(value * 1.5))
    )
    bounds = ink.getbbox()
    if not bounds:
        raise ValueError("documented ZHO glyph reference contains no visible ink")
    glyph = ink.crop(bounds)
    scale = min(GLYPH_WIDTH / glyph.width, GLYPH_HEIGHT / glyph.height)
    glyph = glyph.resize(
        (max(1, round(glyph.width * scale)), max(1, round(glyph.height * scale))),
        Image.Resampling.LANCZOS,
    )
    mask = Image.new("L", (SIZE, SIZE), 0)
    x = (SIZE - glyph.width) // 2
    y = (SIZE - glyph.height) // 2
    mask.paste(glyph, (x, y))
    return mask


def png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def preview_bytes(mask: Image.Image) -> bytes:
    flag = Image.new("RGB", (SIZE, SIZE), BACKGROUND)
    flag.paste(Image.new("RGB", flag.size, INK), (0, 0), mask)
    return png_bytes(flag)


def archive_bytes(mask: Image.Image) -> bytes:
    content = json.loads(zlib.decompress(ARCHIVE.read_bytes()))
    content["ZHO"] = base64.b64encode(mask.tobytes()).decode("ascii")
    raw = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return zlib.compress(raw, level=9)


def run(check: bool = False) -> None:
    mask = build_mask()
    outputs = {
        SOURCE_MASK: png_bytes(mask),
        PREVIEW: preview_bytes(mask),
        ARCHIVE: archive_bytes(mask),
    }
    changed: list[str] = []
    for path, data in outputs.items():
        if check:
            if not path.exists() or path.read_bytes() != data:
                raise ValueError(f"stale ZHO small-seal asset: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            previous = path.read_bytes() if path.exists() else None
            if previous != data:
                path.write_bytes(data)
                changed.append(str(path.relative_to(ROOT)))
    print(f"{'checked' if check else 'generated'} ZHO small-seal mask; changed={changed}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.check)


if __name__ == "__main__":
    main()
