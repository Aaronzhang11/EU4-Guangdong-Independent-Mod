#!/usr/bin/env python3
"""Extract and register the user-approved small-seal 涼 mask for LGU."""

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
REFERENCE = ROOT / "tools/assets/liang_flag/liang_small_seal_reference.png"
SOURCE_MASK = ROOT / "tools/assets/liang_flag/liang_small_seal_mask.png"
PREVIEW = ROOT / "planning/liang_restoration_b76/liang_small_seal_flag_preview.png"

SIZE = 128
GLYPH_WIDTH = 108
GLYPH_HEIGHT = 108
BACKGROUND = (48, 91, 112)
INK = (232, 218, 164)
REFERENCE_SHA256 = "813697811e0964bdb0b59722ec427f67e28d820fb8bd61f00b5d3e298d9de437"


def build_mask() -> Image.Image:
    """Turn the approved black-on-white reference into a centred alpha mask."""
    if not REFERENCE.exists():
        raise FileNotFoundError(f"missing approved Liang glyph reference: {REFERENCE}")
    digest = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
    if digest != REFERENCE_SHA256:
        raise ValueError(f"approved Liang glyph reference hash drifted: {digest}")
    reference = Image.open(REFERENCE).convert("L")
    # White becomes transparent and black becomes opaque. Very pale scan or
    # resampling noise is cleared without changing the approved black outline.
    ink = ImageOps.invert(reference).point(lambda value: 0 if value < 10 else value)
    bounds = ink.getbbox()
    if not bounds:
        raise ValueError("approved Liang glyph reference contains no visible ink")
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
    content["LGU"] = base64.b64encode(mask.tobytes()).decode("ascii")
    raw = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
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
                raise ValueError(f"stale Liang small-seal asset: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            previous = path.read_bytes() if path.exists() else None
            if previous != data:
                path.write_bytes(data)
                changed.append(str(path.relative_to(ROOT)))
    print(f"{'checked' if check else 'generated'} LGU small-seal mask; changed={changed}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.check)


if __name__ == "__main__":
    main()
