#!/usr/bin/env python3
"""Render a review-only Fujian impassable-mountain transplant.

The three silhouettes are copied pixel-for-pixel from Steam Workshop item
1728520255 (DMI).  They receive one shared integer translation determined by
the Fujian coastline alignment.  The skill's guarded-patch builder then
repairs playable province fragments in a candidate copy.  This script never
writes the canonical provinces.bmp.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
SOURCE = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
OUT = ROOT / "planning/fujian_impassable_dmi_plan"
SKILL_PATCH = Path(
    "/Users/xinanyapiao/.codex/skills/eu4-reference-bmp-transplant/"
    "scripts/build_guarded_patch.py"
)

# DMI's China is displaced by (+438, +9) relative to this mod.  A local
# coastline correlation around Fujian starts at (-11, -18).  A four-pixel
# westward route-lock correction yields (-15, -18), preserving the central
# 延平—永春 pass after fragment cleanup.  The same correction is deliberately
# shared by all three ranges so their mutual layout remains identical to the
# reference.
BASE_OFFSET_X = 438
BASE_OFFSET_Y = 9
LOCAL_DX = -15
LOCAL_DY = -18
CROP = (4585, 910, 4710, 1030)

# The user-supplied output RGB values are authoritative.  The one-channel
# differences from DMI affect colour only, never mask geometry.
FEATURES = {
    5158: {"name": "武夷山", "rgb": (0, 146, 38)},
    5156: {"name": "浙闽丘陵", "rgb": (229, 105, 47)},
    5157: {"name": "杉岭", "rgb": (50, 12, 180)},
}

# These routes are deliberately checked after the guarded insertion.  They
# keep north, centre and south Fujian connected without flattening the ranges.
ROUTE_LOCKS = [
    {"name": "建宁—延平", "pair": (2152, 5099)},
    {"name": "延平—永春", "pair": (5099, 5098)},
    {"name": "汀州—龙岩", "pair": (2153, 5100)},
    {"name": "福宁—福州", "pair": (5096, 669)},
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def definitions(path: Path) -> tuple[dict[int, tuple[int, int, int]], dict[tuple[int, int, int], int]]:
    by_id: dict[int, tuple[int, int, int]] = {}
    with path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                by_id[int(row[0])] = tuple(map(int, row[1:4]))
    return by_id, {rgb: province_id for province_id, rgb in by_id.items()}


def mask_for(values: np.ndarray, rgb: tuple[int, int, int]) -> np.ndarray:
    return np.all(values == rgb, axis=2)


def shift_mask(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    result = np.zeros_like(mask)
    height, width = mask.shape
    sx0, sy0 = max(0, -dx), max(0, -dy)
    sx1, sy1 = min(width, width - dx), min(height, height - dy)
    tx0, ty0 = sx0 + dx, sy0 + dy
    tx1, ty1 = sx1 + dx, sy1 + dy
    if sx1 > sx0 and sy1 > sy0:
        result[ty0:ty1, tx0:tx1] = mask[sy0:sy1, sx0:sx1]
    return result


def bbox(mask: np.ndarray) -> list[int]:
    yy, xx = np.where(mask)
    return [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]


def component_sizes(mask: np.ndarray) -> list[int]:
    seen = np.zeros(mask.shape, dtype=bool)
    sizes: list[int] = []
    for sy, sx in zip(*np.where(mask), strict=True):
        if seen[sy, sx]:
            continue
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        size = 0
        while stack:
            y, x = stack.pop()
            size += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def apply_rgba_patch(base: np.ndarray, patch: Path, box: list[int]) -> np.ndarray:
    rgba = np.asarray(Image.open(patch).convert("RGBA"))
    x0, y0, x1, y1 = box
    if rgba.shape[:2] != (y1 - y0, x1 - x0):
        raise ValueError("Guarded patch dimensions do not match report")
    result = base.copy()
    local = result[y0:y1, x0:x1]
    editable = rgba[:, :, 3] > 0
    local[editable] = rgba[:, :, :3][editable]
    return result


def direct_border_count(values: np.ndarray, first: tuple[int, int, int], second: tuple[int, int, int]) -> int:
    a = mask_for(values, first)
    b = mask_for(values, second)
    return int(
        np.sum((a[:, :-1] & b[:, 1:]) | (b[:, :-1] & a[:, 1:]))
        + np.sum((a[:-1, :] & b[1:, :]) | (b[:-1, :] & a[1:, :]))
    )


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    pingfang = Path("/System/Library/Fonts/PingFang.ttc")
    if pingfang.exists():
        return ImageFont.truetype(str(pingfang), size=size, index=1 if bold else 0)
    return ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", size=size)


def annotated_preview(before: np.ndarray, after: np.ndarray, manifest: dict[str, object]) -> None:
    scale = 5
    width, height = CROP[2] - CROP[0], CROP[3] - CROP[1]
    left = Image.fromarray(before).crop(CROP).resize((width * scale, height * scale), Image.Resampling.NEAREST)
    right = Image.fromarray(after).crop(CROP).resize(left.size, Image.Resampling.NEAREST)
    gap = 28
    header = 148
    canvas = Image.new("RGB", (left.width * 2 + gap, left.height + header), (238, 236, 229))
    canvas.paste(left, (0, header))
    canvas.paste(right, (left.width + gap, header))
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 12), "福建不可通行山脉·1:1 轮廓规划", font=font(28, True), fill=(25, 27, 29))
    draw.text((18, 54), "左：当前地图　　右：大明日不落原轮廓 + 当前省界碎片回流", font=font(17), fill=(62, 64, 67))
    draw.text((18, 88), "武夷山 0,146,38　浙闽丘陵 229,105,47　杉岭 50,12,180", font=font(16), fill=(62, 64, 67))
    draw.text((18, 116), "共同位移：西 15 px / 北 18 px；无缩放、旋转、描边或形变", font=font(15), fill=(82, 84, 87))
    draw.text((left.width + gap + 18, 116), f"候选改动 {manifest['changed_pixels']} px；正式地图未修改", font=font(15), fill=(82, 84, 87))
    canvas.save(OUT / "fujian_impassable_annotated_preview.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    guarded_out = OUT / "guarded_patch"
    canonical = MOD / "map/provinces.bmp"
    canonical_hash = sha256(canonical)
    target = np.asarray(Image.open(canonical).convert("RGB"))
    source = np.asarray(Image.open(SOURCE / "map/provinces.bmp").convert("RGB"))
    source_defs, _source_rgb_to_id = definitions(SOURCE / "map/definition.csv")
    target_defs, _target_rgb_to_id = definitions(MOD / "map/definition.csv")

    translated = source[
        BASE_OFFSET_Y:BASE_OFFSET_Y + target.shape[0],
        BASE_OFFSET_X:BASE_OFFSET_X + target.shape[1],
    ]
    if translated.shape != target.shape:
        raise ValueError(f"Translated source shape {translated.shape} != target {target.shape}")

    candidate = target.copy()
    feature_rows = []
    for source_id, feature in FEATURES.items():
        source_mask = mask_for(translated, source_defs[source_id])
        output_mask = shift_mask(source_mask, LOCAL_DX, LOCAL_DY)
        candidate[output_mask] = feature["rgb"]
        feature_rows.append(
            {
                "name": feature["name"],
                "source_id": source_id,
                "source_rgb": list(source_defs[source_id]),
                "output_rgb": list(feature["rgb"]),
                "pixels": int(output_mask.sum()),
                "component_sizes": component_sizes(output_mask),
                "output_bbox": bbox(output_mask),
                "translation": [LOCAL_DX, LOCAL_DY],
            }
        )

    raw_candidate = OUT / "fujian_impassable_candidate_full.bmp"
    Image.fromarray(candidate).save(raw_candidate, format="BMP")
    Image.fromarray(candidate).crop(CROP).save(OUT / "fujian_impassable_candidate_1to1.bmp", format="BMP")

    spec = {
        "features": [
            {
                "name": row["name"],
                "rgb": row["output_rgb"],
                "source_bbox": row["output_bbox"],
                "target_xy": row["output_bbox"][:2],
                "scale": 1.0,
            }
            for row in feature_rows
        ],
        "cleanup_margin": 16,
        "cleanup_fragments": True,
        "absorb_enclosed_pockets": False,
        "preview_zoom": 5,
    }
    spec_path = OUT / "guarded_patch_spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(SKILL_PATCH),
            "--current", str(canonical),
            "--reference", str(raw_candidate),
            "--spec", str(spec_path),
            "--output-dir", str(guarded_out),
            "--definition", str(MOD / "map/definition.csv"),
        ],
        check=True,
    )
    guarded_report = json.loads((guarded_out / "report.json").read_text(encoding="utf-8"))
    final = apply_rgba_patch(target, guarded_out / "after_patch.png", guarded_report["patch_box"])
    Image.fromarray(final).crop(CROP).save(OUT / "fujian_impassable_guarded_1to1.bmp", format="BMP")

    geometry = {}
    for row in feature_rows:
        rgb = tuple(row["output_rgb"])
        actual = mask_for(final, rgb)
        actual_components = component_sizes(actual)
        geometry[row["name"]] = {
            "pixels": int(actual.sum()),
            "component_sizes": actual_components,
            "bbox": bbox(actual),
            "exact_source_geometry_preserved": (
                int(actual.sum()) == row["pixels"] and actual_components == row["component_sizes"]
            ),
        }
        if not geometry[row["name"]]["exact_source_geometry_preserved"]:
            raise ValueError(f"Geometry changed for {row['name']}")

    route_rows = []
    for route in ROUTE_LOCKS:
        first, second = route["pair"]
        before_count = direct_border_count(target, target_defs[first], target_defs[second])
        after_count = direct_border_count(final, target_defs[first], target_defs[second])
        route_rows.append(
            {
                "name": route["name"],
                "province_pair": [first, second],
                "before_border_pixels": before_count,
                "after_border_pixels": after_count,
                "open": after_count > 0,
            }
        )
        if after_count <= 0:
            raise ValueError(f"Route lock closed: {route['name']}")

    output_colours = [tuple(feature["rgb"]) for feature in FEATURES.values()]
    manifest = {
        "status": "review_only",
        "canonical_modified": False,
        "canonical_sha256": canonical_hash,
        "source_mod": str(SOURCE),
        "coastline_alignment": {
            "base_translation": [-BASE_OFFSET_X, -BASE_OFFSET_Y],
            "local_translation": [LOCAL_DX, LOCAL_DY],
            "final_translation": [-BASE_OFFSET_X + LOCAL_DX, -BASE_OFFSET_Y + LOCAL_DY],
            "method": "Fujian coastline edge correlation",
        },
        "features": feature_rows,
        "rgb_collision_before": {
            ",".join(map(str, rgb)): int(mask_for(target, rgb).sum()) for rgb in output_colours
        },
        "guarded_patch": guarded_report,
        "geometry_validation": geometry,
        "route_locks": route_rows,
        "changed_pixels": int(np.any(target != final, axis=2).sum()),
    }
    if sha256(canonical) != canonical_hash:
        raise RuntimeError("Canonical provinces.bmp changed during review-only rendering")
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    annotated_preview(target, final, manifest)
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
