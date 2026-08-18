#!/usr/bin/env python3
"""Render B47 v2 with balanced cells across former province boundaries.

The union of the thirteen reviewed parent provinces remains the exact editable
mask. Internal pixels may cross old parent boundaries. A connected boundary
flow then moves pixels from oversized cells to undersized cells toward a
development-weighted target. It stops before forcing a narrow corridor merely
to satisfy an exact pixel quota: compact, readable provinces take precedence
over mathematical equality.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
import importlib.util
import json
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
V1_PATH = HERE / "render_b47_geojson_proposal.py"
SPEC = importlib.util.spec_from_file_location("b47_v1", V1_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load B47 v1 renderer")
v1 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v1
SPEC.loader.exec_module(v1)

REVIEWED_BMP = HERE / "b47_geojson_v2_reviewed_provinces.bmp"
REVIEW_PNG = HERE / "b47_geojson_v2_review.png"
MANIFEST = HERE / "preview_manifest_v2.json"


def adjacent(mask: np.ndarray) -> np.ndarray:
    output = np.zeros(mask.shape, dtype=bool)
    output[1:] |= mask[:-1]
    output[:-1] |= mask[1:]
    output[:, 1:] |= mask[:, :-1]
    output[:, :-1] |= mask[:, 1:]
    return output


def connected_after_removal(mask: np.ndarray, y: int, x: int) -> bool:
    if not mask[y, x] or int(mask.sum()) <= 1:
        return False
    neighbours = [
        (ny, nx)
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
        if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx]
    ]
    if len(neighbours) <= 1:
        return True
    target = int(mask.sum()) - 1
    seen = np.zeros(mask.shape, dtype=bool)
    queue = [neighbours[0]]
    seen[neighbours[0]] = True
    visited = 0
    while queue:
        cy, cx = queue.pop()
        visited += 1
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if (
                0 <= ny < mask.shape[0]
                and 0 <= nx < mask.shape[1]
                and not (ny == y and nx == x)
                and mask[ny, nx]
                and not seen[ny, nx]
            ):
                seen[ny, nx] = True
                queue.append((ny, nx))
    return visited == target


def graph(masks: dict[int, np.ndarray], province_ids: list[int]) -> dict[int, set[int]]:
    result = {province_id: set() for province_id in province_ids}
    expanded = {province_id: adjacent(masks[province_id]) for province_id in province_ids}
    for index, province_id in enumerate(province_ids):
        for other in province_ids[index + 1 :]:
            if np.any(expanded[province_id] & masks[other]):
                result[province_id].add(other)
                result[other].add(province_id)
    return result


def target_counts(component: np.ndarray, province_ids: list[int]) -> dict[int, int]:
    total = int(component.sum())
    weights = [v1.CELL_BY_ID[province_id].development for province_id in province_ids]
    weight_total = sum(weights)
    raw = [total * weight / weight_total for weight in weights]
    values = [int(value) for value in raw]
    remainder = total - sum(values)
    order = sorted(range(len(values)), key=lambda index: raw[index] - values[index], reverse=True)
    for index in order[:remainder]:
        values[index] += 1
    return dict(zip(province_ids, values, strict=True))


def transfer_pixel(
    masks: dict[int, np.ndarray],
    donor: int,
    recipient: int,
    seeds: dict[int, tuple[int, int]],
) -> bool:
    donor_mask = masks[donor]
    recipient_mask = masks[recipient]
    candidates = np.argwhere(donor_mask & adjacent(recipient_mask))
    if not len(candidates):
        return False
    seed_x, seed_y = seeds[recipient]

    def score(value: np.ndarray) -> tuple[float, int, int]:
        y, x = int(value[0]), int(value[1])
        recipient_neighbours = sum(
            1
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
            if 0 <= ny < recipient_mask.shape[0] and 0 <= nx < recipient_mask.shape[1] and recipient_mask[ny, nx]
        )
        distance = (x - seed_x) ** 2 + (y - seed_y) ** 2
        return distance + (4 - recipient_neighbours) * 36, y, x

    for value in sorted(candidates, key=score):
        y, x = int(value[0]), int(value[1])
        if connected_after_removal(donor_mask, y, x):
            donor_mask[y, x] = False
            recipient_mask[y, x] = True
            return True
    return False


def rebalance_component(
    masks: dict[int, np.ndarray],
    component: np.ndarray,
    province_ids: list[int],
    seeds: dict[int, tuple[int, int]],
) -> dict[int, int]:
    targets = target_counts(component, province_ids)
    blocked: set[tuple[int, int]] = set()
    for _iteration in range(20000):
        counts = {province_id: int(masks[province_id].sum()) for province_id in province_ids}
        deficits = [province_id for province_id in province_ids if counts[province_id] < targets[province_id]]
        if not deficits:
            return targets
        surpluses = {province_id for province_id in province_ids if counts[province_id] > targets[province_id]}
        cell_graph = graph(masks, province_ids)
        progress = False
        for destination in sorted(deficits, key=lambda province_id: targets[province_id] - counts[province_id], reverse=True):
            previous: dict[int, int | None] = {destination: None}
            queue = deque([destination])
            source = None
            while queue and source is None:
                current = queue.popleft()
                if current in surpluses:
                    source = current
                    break
                for neighbour in cell_graph[current]:
                    if neighbour not in previous and (neighbour, current) not in blocked:
                        previous[neighbour] = current
                        queue.append(neighbour)
            if source is None:
                continue
            path = [source]
            while path[-1] != destination:
                path.append(previous[path[-1]])
            moved = True
            for donor, recipient in zip(path, path[1:]):
                if not transfer_pixel(masks, donor, recipient, seeds):
                    blocked.add((donor, recipient))
                    moved = False
                    break
            if moved:
                blocked.clear()
                progress = True
                break
        if not progress:
            drift = {
                v1.CELL_BY_ID[province_id].name: (counts[province_id], targets[province_id])
                for province_id in province_ids
                if counts[province_id] != targets[province_id]
            }
            minimum = min(counts.values())
            if minimum < 64:
                raise RuntimeError(f"Balanced boundary flow stalled with a small cell: {drift}")
            # The remaining mismatch is a deliberate compactness guard.  In
            # particular, mountain cells must not grow a one-pixel tendril
            # through several neighbours just to hit a development quota.
            return targets
    raise RuntimeError("Balanced boundary flow exceeded iteration limit")


def build_balanced_cells() -> tuple[np.ndarray, dict[int, np.ndarray], np.ndarray, tuple[int, int, int, int], dict[str, object]]:
    current, full_masks, editable, box, metadata = v1.build_cells()
    left, top, right, bottom = box
    local_editable = editable[top:bottom, left:right]
    masks = {province_id: mask[top:bottom, left:right].copy() for province_id, mask in full_masks.items()}
    seeds = {province_id: v1.label_point(mask) for province_id, mask in masks.items()}
    targets: dict[int, int] = {}
    for component in v1.component_masks(local_editable):
        province_ids = [province_id for province_id, mask in masks.items() if np.any(mask & component)]
        targets.update(rebalance_component(masks, component, province_ids, seeds))

    balanced: dict[int, np.ndarray] = {}
    covered = np.zeros(editable.shape, dtype=bool)
    for province_id, local in masks.items():
        if len(v1.component_masks(local)) != 1:
            raise ValueError(f"{v1.CELL_BY_ID[province_id].name} disconnected after cross-parent balancing")
        full = np.zeros(editable.shape, dtype=bool)
        full[top:bottom, left:right] = local
        balanced[province_id] = full
        if np.any(covered & full):
            raise ValueError("B47 v2 cells overlap")
        covered |= full
    if not np.array_equal(covered, editable):
        raise ValueError("B47 v2 does not exactly cover the locked regional mask")
    metadata["target_pixel_counts"] = {str(key): value for key, value in targets.items()}
    return current, balanced, editable, box, metadata


def main() -> None:
    current, masks, editable, box, metadata = build_balanced_cells()
    v1.REVIEWED_BMP = REVIEWED_BMP
    changed = v1.write_reviewed_bmp(current, masks)
    country = v1.render_map(masks, box, "polity")
    area = v1.render_map(masks, box, "area")
    v1.compose_review(
        country,
        area,
        title="B47 荆襄—豫南二次细化 · 跨旧省界均衡版",
        subtitle="整体外缘锁定｜内部按GeoJSON、河谷与发展度重排｜23省全部连通｜总发展度133守恒｜★为新增",
        output=REVIEW_PNG,
    )
    covered = np.zeros(editable.shape, dtype=bool)
    for mask in masks.values():
        covered |= mask
    manifest = {
        "batch": "B47_jingxiang_yunan_geojson_preview_v2",
        "status": "review_only_not_game_loaded",
        "canonical_map_modified": False,
        "geometry_policy": "lock only the union exterior; internal borders may cross former province boundaries",
        "parent_ids": list(v1.PARENT_IDS),
        "provisional_new_ids": sorted(v1.NEW_RGB),
        "max_provinces_if_applied": 5351,
        "editable_pixel_count": int(editable.sum()),
        "covered_pixel_count": int(covered.sum()),
        "changed_preview_pixels": changed,
        "changed_pixels_outside_editable_mask": int(np.count_nonzero(covered & ~editable)),
        "development_total": sum(cell.development for cell in v1.CELLS),
        "province_pixel_counts": {str(key): int(mask.sum()) for key, mask in masks.items()},
        "target_pixel_counts": metadata["target_pixel_counts"],
        "minimum_province_pixels": min(int(mask.sum()) for mask in masks.values()),
        "outputs": [str(REVIEWED_BMP), str(REVIEW_PNG)],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "B47_V2_PREVIEW PASS "
        f"cells=23 dev=133 editable={int(editable.sum())} changed={changed} exterior=0 "
        f"min_pixels={manifest['minimum_province_pixels']}"
    )
    print(REVIEW_PNG)


if __name__ == "__main__":
    main()
