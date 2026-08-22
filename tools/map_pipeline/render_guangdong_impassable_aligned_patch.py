#!/usr/bin/env python3
"""Build a review-only, border-reflowed Guangdong mountain patch.

This wrapper intentionally uses the eu4-reference-bmp-transplant skill's
``build_guarded_patch.py`` for exact 1:1 insertion and fragment cleanup.  It
first returns the two superseded Nanling masks to their nearest adjacent
playable provinces, then composes a final canonical-before/final-after guarded
patch.  The canonical provinces.bmp is never written.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render_guangdong_impassable_plan as plan


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
OUT = ROOT / "planning/guangdong_impassable_dmi_plan/aligned_patch"
SKILL_PATCH = Path(
    "/Users/xinanyapiao/.codex/skills/eu4-reference-bmp-transplant/"
    "scripts/build_guarded_patch.py"
)


def definitions(path: Path) -> tuple[dict[int, tuple[int, int, int]], dict[tuple[int, int, int], int]]:
    by_id: dict[int, tuple[int, int, int]] = {}
    with path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0].isdigit():
                by_id[int(row[0])] = tuple(map(int, row[1:4]))
    return by_id, {rgb: province_id for province_id, rgb in by_id.items()}


def numeric_block(text: str, key: str) -> set[int]:
    match = re.search(rf"(?ms)^\s*{re.escape(key)}\s*=\s*\{{(.*?)^\s*\}}", text)
    if not match:
        return set()
    clean = re.sub(r"#.*", "", match.group(1))
    return {int(value) for value in re.findall(r"\b\d+\b", clean)}


def mask_for(values: np.ndarray, rgb: tuple[int, int, int]) -> np.ndarray:
    return np.all(values == rgb, axis=2)


def components(mask: np.ndarray) -> list[int]:
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


def reflow_old_mountains(
    current: np.ndarray,
    by_id: dict[int, tuple[int, int, int]],
    playable_ids: set[int],
) -> tuple[np.ndarray, dict[str, object]]:
    result = current.copy()
    report: dict[str, object] = {}
    for old_id in (5310, 5311):
        old_mask = mask_for(current, by_id[old_id])
        yy, xx = np.where(old_mask)
        contacts: dict[tuple[int, int, int], list[tuple[int, int]]] = {}
        for y, x in zip(yy, xx, strict=True):
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = int(y + dy), int(x + dx)
                if not (0 <= ny < current.shape[0] and 0 <= nx < current.shape[1]) or old_mask[ny, nx]:
                    continue
                rgb = tuple(int(value) for value in current[ny, nx])
                recipient = rgb_to_id.get(rgb)
                if recipient in playable_ids:
                    contacts.setdefault(rgb, []).append((ny, nx))
        if not contacts:
            raise ValueError(f"Old mountain {old_id} has no adjacent playable recipients")

        assigned: dict[tuple[int, int, int], int] = {rgb: 0 for rgb in contacts}
        for y, x in zip(yy, xx, strict=True):
            best_rgb = min(
                contacts,
                key=lambda rgb: (
                    min(abs(int(y) - sy) + abs(int(x) - sx) for sy, sx in contacts[rgb]),
                    -len(contacts[rgb]),
                    rgb,
                ),
            )
            result[y, x] = best_rgb
            assigned[best_rgb] += 1
        report[str(old_id)] = {
            "pixels_reflowed": int(old_mask.sum()),
            "recipients": {
                str(rgb_to_id[rgb]): {"rgb": list(rgb), "pixels": count}
                for rgb, count in sorted(assigned.items(), key=lambda item: rgb_to_id[item[0]])
                if count
            },
        }
    return result, report


def apply_rgba_patch(base: np.ndarray, patch: Path, box: list[int]) -> np.ndarray:
    rgba = np.asarray(Image.open(patch).convert("RGBA"))
    x0, y0, x1, y1 = box
    if rgba.shape[:2] != (y1 - y0, x1 - x0):
        raise ValueError("Skill patch dimensions do not match its report")
    result = base.copy()
    local = result[y0:y1, x0:x1]
    editable = rgba[:, :, 3] > 0
    local[editable] = rgba[:, :, :3][editable]
    return result


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = Path("/System/Library/Fonts/PingFang.ttc")
    if path.exists():
        return ImageFont.truetype(str(path), size=size, index=1 if bold else 0)
    return ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", size=size)


def save_final_patch(current: np.ndarray, final: np.ndarray, report: dict[str, object]) -> None:
    changed = np.any(current != final, axis=2)
    yy, xx = np.where(changed)
    margin = 5
    x0, y0 = max(0, int(xx.min()) - margin), max(0, int(yy.min()) - margin)
    x1, y1 = min(current.shape[1], int(xx.max()) + margin + 1), min(current.shape[0], int(yy.max()) + margin + 1)
    before = current[y0:y1, x0:x1]
    after = final[y0:y1, x0:x1]
    alpha = np.any(before != after, axis=2).astype(np.uint8) * 255
    Image.fromarray(np.dstack((before, alpha)), mode="RGBA").save(OUT / "before_patch.png")
    Image.fromarray(np.dstack((after, alpha)), mode="RGBA").save(OUT / "after_patch.png")
    Image.fromarray(final).crop(plan.CROP).save(OUT / "aligned_candidate_1to1.bmp", format="BMP")

    zoom = 4
    crop = plan.CROP
    left = Image.fromarray(current).crop(crop).resize(
        ((crop[2] - crop[0]) * zoom, (crop[3] - crop[1]) * zoom), Image.Resampling.NEAREST
    )
    right = Image.fromarray(final).crop(crop).resize(left.size, Image.Resampling.NEAREST)
    header = 88
    canvas = Image.new("RGB", (left.width * 2 + 26, left.height + header), (239, 237, 230))
    canvas.paste(left, (0, header))
    canvas.paste(right, (left.width + 26, header))
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 12), "广东山脉·省界完全回流稿", font=font(27, True), fill=(25, 27, 29))
    draw.text((18, 52), "左：当前地图　　右：旧南岭回流 + 1:1 山体嵌入 + 新碎片修复", font=font(16), fill=(62, 64, 67))
    draw.text((left.width + 44, 52), f"共改 {int(changed.sum())} px；正式地图未修改", font=font(16), fill=(62, 64, 67))
    canvas.save(OUT / "aligned_preview.png")

    report["final_patch_box"] = [x0, y0, x1, y1]
    report["final_changed_pixels"] = int(changed.sum())
    report["canonical_modified"] = False


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plan.render()
    canonical = MOD / "map/provinces.bmp"
    current = np.asarray(Image.open(canonical).convert("RGB"))
    global rgb_to_id
    by_id, rgb_to_id = definitions(MOD / "map/definition.csv")
    default_text = (MOD / "map/default.map").read_text(encoding="cp1252", errors="replace")
    climate_text = (MOD / "map/climate.txt").read_text(encoding="cp1252", errors="replace")
    excluded = numeric_block(default_text, "sea_starts") | numeric_block(default_text, "lakes") | numeric_block(climate_text, "impassable")
    playable_ids = set(by_id) - excluded

    base, reflow_report = reflow_old_mountains(current, by_id, playable_ids)
    base_path = OUT / "old_nanling_reflowed_base.bmp"
    Image.fromarray(base).save(base_path, format="BMP")

    parent_manifest = json.loads((plan.OUT / "manifest.json").read_text(encoding="utf-8"))
    features = []
    for feature in parent_manifest["proposal"]:
        x0, y0, x1, y1 = feature["output_bbox"]
        features.append(
            {
                "name": feature["name"],
                "rgb": feature["output_rgb"],
                "source_bbox": [x0, y0, x1, y1],
                "target_xy": [x0, y0],
                "scale": 1.0,
            }
        )
    spec = {
        "features": features,
        "cleanup_margin": 14,
        "cleanup_fragments": True,
        "absorb_enclosed_pockets": False,
        "preview_zoom": 5,
    }
    spec_path = OUT / "skill_patch_spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    skill_out = OUT / "skill_insertion"
    subprocess.run(
        [
            sys.executable,
            str(SKILL_PATCH),
            "--current", str(base_path),
            "--reference", str(plan.OUT / "guangdong_impassable_candidate_full.bmp"),
            "--spec", str(spec_path),
            "--output-dir", str(skill_out),
            "--definition", str(MOD / "map/definition.csv"),
        ],
        check=True,
    )
    skill_report = json.loads((skill_out / "report.json").read_text(encoding="utf-8"))
    final = apply_rgba_patch(base, skill_out / "after_patch.png", skill_report["patch_box"])

    touched_colours = {
        tuple(int(value) for value in rgb)
        for rgb in np.unique(current[np.any(current != final, axis=2)].reshape(-1, 3), axis=0)
    }
    new_colours = {rgb for _name, rgb in plan.PROPOSED.values()}
    connectivity = {}
    for rgb in sorted(touched_colours - new_colours):
        province_id = rgb_to_id.get(rgb)
        if province_id is None or province_id in excluded:
            continue
        before_sizes = components(mask_for(current, rgb))
        after_sizes = components(mask_for(final, rgb))
        connectivity[str(province_id)] = {"before": before_sizes, "after": after_sizes}
        if len(after_sizes) > len(before_sizes):
            raise ValueError(f"Playable province {province_id} gained components: {before_sizes} -> {after_sizes}")

    mountain_validation = {}
    for feature in parent_manifest["proposal"]:
        rgb = tuple(feature["output_rgb"])
        actual = mask_for(final, rgb)
        mountain_validation[feature["name"]] = {
            "rgb": list(rgb),
            "expected_pixels": feature["output_pixels"],
            "actual_pixels": int(actual.sum()),
            "expected_components": feature["component_sizes"],
            "actual_components": components(actual),
        }
        if int(actual.sum()) != feature["output_pixels"] or components(actual) != feature["component_sizes"]:
            raise ValueError(f"Mountain geometry changed for {feature['name']}")

    report: dict[str, object] = {
        "status": "review_only_guarded_patch",
        "old_nanling_reflow": reflow_report,
        "skill_insertion_report": skill_report,
        "playable_connectivity": connectivity,
        "mountain_validation": mountain_validation,
    }
    save_final_patch(current, final, report)
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT / "aligned_preview.png")
    print(OUT / "before_patch.png")
    print(OUT / "after_patch.png")
    print(OUT / "report.json")


if __name__ == "__main__":
    main()
