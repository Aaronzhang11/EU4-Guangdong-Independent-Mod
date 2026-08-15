#!/usr/bin/env python3
"""Render B47 v3 with the modern Hubei-Henan boundary as a hard constraint."""

from __future__ import annotations

from collections import deque
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v1 = load_module("b47_v1_for_v3", HERE / "render_b47_geojson_proposal.py")
v2 = load_module("b47_v2_for_v3", HERE / "render_b47_geojson_v2.py")

BASE = HERE / "pre_b47_provinces.bmp"
V2_REVIEWED = HERE / "b47_geojson_v2_reviewed_provinces.bmp"
REVIEWED = HERE / "b47_geojson_v3_reviewed_provinces.bmp"
REVIEW = HERE / "b47_geojson_v3_review.png"
MANIFEST = HERE / "preview_manifest_v3.json"

HUBEI_IDS = (5008, 5341, 2171, 5342, 5010, 5343, 5015, 5344, 2172, 5345, 5014, 681, 5346, 5013)
HENAN_IDS = (687, 5347, 5055, 5348, 5053, 5054, 5349, 2175, 5350)
DOMAIN_IDS = {1: HUBEI_IDS, 2: HENAN_IDS}
DOMAIN_NAMES = {1: "Hubei", 2: "Henan"}


def province_domains(editable: np.ndarray, target_box: tuple[int, int, int, int]) -> tuple[np.ndarray, dict[str, object]]:
    hubei = v1.load_geojson(v1.HUBEI_URL, "420000_full_district.json")
    henan = v1.load_geojson(v1.HENAN_URL, "410000_full_district.json")
    features = hubei["features"] + henan["features"]
    selected = []
    all_points: list[tuple[float, float]] = []
    for feature in features:
        props = feature["properties"]
        parent_code = int((props.get("parent") or {}).get("adcode", 0))
        if (parent_code, props["name"]) not in v1.FEATURE_TARGET:
            continue
        selected.append(feature)
        for polygon in v1.polygons(feature["geometry"]):
            all_points.extend((float(point[0]), float(point[1])) for point in polygon[0])
    if len(selected) != len(v1.FEATURE_TARGET):
        raise ValueError("B47 v3 lacks one or more reviewed GeoJSON features")

    lon_min = min(point[0] for point in all_points)
    lon_max = max(point[0] for point in all_points)
    lat_min = min(point[1] for point in all_points)
    lat_max = max(point[1] for point in all_points)
    x_min, y_min, x_max, y_max = target_box

    def project(point) -> tuple[int, int]:
        lon, lat = float(point[0]), float(point[1])
        x = x_min + (lon - lon_min) / (lon_max - lon_min) * (x_max - x_min - 1)
        y = y_min + (lat_max - lat) / (lat_max - lat_min) * (y_max - y_min - 1)
        return round(x), round(y)

    labels_image = Image.new("I", (editable.shape[1], editable.shape[0]), 0)
    draw = ImageDraw.Draw(labels_image)
    for feature in selected:
        props = feature["properties"]
        parent_code = str(int((props.get("parent") or {}).get("adcode", 0)))
        domain_id = 1 if parent_code.startswith("42") else 2 if parent_code.startswith("41") else 0
        if not domain_id:
            raise ValueError(f"Unknown B47 province domain for parent code {parent_code}")
        for polygon in v1.polygons(feature["geometry"]):
            exterior = [project(point) for point in polygon[0]]
            if len(exterior) >= 3:
                draw.polygon(exterior, fill=domain_id)
    labels = np.asarray(labels_image, dtype=np.int16).copy()
    labels[~editable] = 0

    # Projected county polygons carry the actual modern provincial border.
    # Fill raster gaps by nearest labelled pixel inside each locked land
    # component, never across the union's exterior.
    for component in v1.component_masks(editable):
        queue = deque((int(y), int(x)) for y, x in zip(*np.where(component & (labels > 0)), strict=True))
        if not queue:
            raise ValueError("An editable component has no modern-province GeoJSON seed")
        while queue:
            y, x = queue.popleft()
            for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if (
                    0 <= next_y < labels.shape[0]
                    and 0 <= next_x < labels.shape[1]
                    and component[next_y, next_x]
                    and labels[next_y, next_x] == 0
                ):
                    labels[next_y, next_x] = labels[y, x]
                    queue.append((next_y, next_x))
    if np.any(editable & (labels == 0)):
        raise ValueError("Modern-province domain raster left editable pixels unassigned")
    return labels, {
        "feature_count": len(selected),
        "geojson_bounds": [lon_min, lat_min, lon_max, lat_max],
        "hubei_pixels": int(np.count_nonzero(labels == 1)),
        "henan_pixels": int(np.count_nonzero(labels == 2)),
    }


def fill_component(component: np.ndarray, province_ids: list[int], seeds: dict[int, np.ndarray]) -> dict[int, np.ndarray]:
    labels = np.zeros(component.shape, dtype=np.int32)
    queue: deque[tuple[int, int]] = deque()
    for province_id in province_ids:
        seed = v1.largest_component(seeds[province_id] & component)
        if not seed.any():
            source_x, source_y = v1.label_point(seeds[province_id])
            target_x, target_y = v1.nearest_mask_point(component, source_x, source_y)
            seed[target_y, target_x] = True
        labels[seed] = province_id
        queue.extend((int(y), int(x)) for y, x in zip(*np.where(seed), strict=True))
    while queue:
        y, x = queue.popleft()
        for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if (
                0 <= next_y < labels.shape[0]
                and 0 <= next_x < labels.shape[1]
                and component[next_y, next_x]
                and labels[next_y, next_x] == 0
            ):
                labels[next_y, next_x] = labels[y, x]
                queue.append((next_y, next_x))
    if np.any(component & (labels == 0)):
        raise ValueError("Province-constrained component contains unassigned pixels")
    return {province_id: labels == province_id for province_id in province_ids}


def build_v3() -> tuple[np.ndarray, dict[int, np.ndarray], np.ndarray, tuple[int, int, int, int], np.ndarray, dict[str, object]]:
    if not BASE.exists() or not V2_REVIEWED.exists():
        raise FileNotFoundError("B47 v3 requires the pre-B47 backup and frozen v2 bitmap")
    base = np.asarray(Image.open(BASE).convert("RGB"), dtype=np.uint8)
    reviewed = np.asarray(Image.open(V2_REVIEWED).convert("RGB"), dtype=np.uint8)
    id_to_rgb, _rgb_to_id, _names = v1.definitions()
    editable = np.zeros(base.shape[:2], dtype=bool)
    for province_id in v1.PARENT_IDS:
        editable |= np.all(base == np.asarray(id_to_rgb[province_id], dtype=np.uint8), axis=2)
    ys, xs = np.where(editable)
    target_box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    domains, metadata = province_domains(editable, target_box)
    left, top, right, bottom = target_box
    local_editable = editable[top:bottom, left:right]
    local_domains = domains[top:bottom, left:right]
    old_masks = {
        province_id: np.all(reviewed[top:bottom, left:right] == np.asarray(id_to_rgb[province_id], dtype=np.uint8), axis=2)
        for province_id in v1.CELL_BY_ID
    }
    local_masks = {province_id: np.zeros(local_editable.shape, dtype=bool) for province_id in v1.CELL_BY_ID}
    target_counts: dict[int, int] = {}

    for domain_id, domain_province_ids in DOMAIN_IDS.items():
        domain = local_editable & (local_domains == domain_id)
        domain_components = v1.component_masks(domain)
        assignment: dict[int, int] = {}
        for province_id in domain_province_ids:
            overlaps = [int(np.count_nonzero(old_masks[province_id] & component)) for component in domain_components]
            assignment[province_id] = int(np.argmax(overlaps))
        for component_index, component in enumerate(domain_components):
            province_ids = [province_id for province_id in domain_province_ids if assignment[province_id] == component_index]
            if not province_ids:
                raise ValueError(f"{DOMAIN_NAMES[domain_id]} component has no assigned B47 province")
            initial = fill_component(component, province_ids, old_masks)
            for province_id, mask in initial.items():
                local_masks[province_id] |= mask
            seeds = {province_id: v1.label_point(local_masks[province_id]) for province_id in province_ids}
            target_counts.update(v2.rebalance_component(local_masks, component, province_ids, seeds))

    covered = np.zeros(local_editable.shape, dtype=bool)
    for domain_id, province_ids in DOMAIN_IDS.items():
        domain = local_domains == domain_id
        for province_id in province_ids:
            mask = local_masks[province_id]
            if len(v1.component_masks(mask)) != 1:
                raise ValueError(f"{v1.CELL_BY_ID[province_id].name} disconnected in B47 v3")
            if np.any(mask & ~domain):
                raise ValueError(f"{v1.CELL_BY_ID[province_id].name} crosses the modern Hubei-Henan boundary")
            if np.any(covered & mask):
                raise ValueError("B47 v3 province masks overlap")
            covered |= mask
    if not np.array_equal(covered, local_editable):
        raise ValueError("B47 v3 does not exactly cover the locked exterior")

    full_masks: dict[int, np.ndarray] = {}
    for province_id, local in local_masks.items():
        full = np.zeros(editable.shape, dtype=bool)
        full[top:bottom, left:right] = local
        full_masks[province_id] = full
    review_box = (max(0, left - 7), max(0, top - 7), min(base.shape[1], right + 7), min(base.shape[0], bottom + 7))
    metadata["target_pixel_counts"] = {str(key): value for key, value in target_counts.items()}
    return base, full_masks, editable, review_box, domains, metadata


def main() -> None:
    base, masks, editable, box, domains, metadata = build_v3()
    v1.REVIEWED_BMP = REVIEWED
    changed = v1.write_reviewed_bmp(base, masks)
    country = v1.render_map(masks, box, "polity")
    area = v1.render_map(masks, box, "area")
    v1.compose_review(
        country,
        area,
        title="B47 荆襄—豫南二次细化 · 鄂豫省界约束修订版",
        subtitle="现代鄂豫省界硬约束｜域内可跨旧省界均衡｜23省全部连通｜总发展度133守恒",
        output=REVIEW,
    )
    province_pixel_counts = {str(key): int(mask.sum()) for key, mask in masks.items()}
    boundary_violations = {
        "hubei_cells_in_henan": int(sum(np.count_nonzero(masks[province_id] & (domains == 2)) for province_id in HUBEI_IDS)),
        "henan_cells_in_hubei": int(sum(np.count_nonzero(masks[province_id] & (domains == 1)) for province_id in HENAN_IDS)),
    }
    payload = {
        "batch": "B47_jingxiang_yunan_geojson_preview_v3",
        "status": "reviewed_geometry_for_canonical_apply",
        "canonical_map_modified": False,
        "geometry_policy": "lock the union exterior and enforce the projected modern Hubei-Henan boundary; rebalance only within each province domain",
        "parent_ids": list(v1.PARENT_IDS),
        "target_ids": sorted(masks),
        "editable_pixel_count": int(editable.sum()),
        "changed_preview_pixels": changed,
        "changed_pixels_outside_editable_mask": 0,
        "development_total": sum(cell.development for cell in v1.CELLS),
        "province_pixel_counts": province_pixel_counts,
        "minimum_province_pixels": min(province_pixel_counts.values()),
        "modern_boundary_violations": boundary_violations,
        "domain_metadata": metadata,
        "outputs": [str(REVIEWED), str(REVIEW)],
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if any(boundary_violations.values()):
        raise ValueError(f"B47 v3 modern border violations: {boundary_violations}")
    print(
        "B47_V3_PREVIEW PASS "
        f"cells=23 dev=133 editable={int(editable.sum())} changed={changed} exterior=0 "
        f"min_pixels={payload['minimum_province_pixels']} boundary_violations=0"
    )
    print(REVIEW)


if __name__ == "__main__":
    main()
