"""Build the legacy five-province B01 Guangdong review image.

This superseded AI geometry is retained only for historical comparison.  It
does not overwrite the installed game or the mod's hand-drawn production map.
The script reads EU4 1.37.5, applies five deterministic in-memory province
splits, and writes review PNGs plus a machine-readable validation report.  An
optional candidate ``provinces.bmp`` can be written only to a disposable build
directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("b01_guangdong.json")
DEFAULT_REGISTRY = REPO_ROOT / "docs/map/china_province_split_registry.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs/map/previews"
EXPECTED_SIZE = (5632, 2048)


@dataclass(frozen=True)
class RegistryProvince:
    design_key: str
    game_id: int
    color: tuple[int, int, int]
    new_name_zh: str
    parent_id: int


def read_registry(path: Path) -> dict[str, RegistryProvince]:
    entries: dict[str, RegistryProvince] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = row["design_key"]
            try:
                entry = RegistryProvince(
                    design_key=key,
                    game_id=int(row["game_id"]),
                    color=(int(row["rgb_r"]), int(row["rgb_g"]), int(row["rgb_b"])),
                    new_name_zh=row["new_name_zh"],
                    parent_id=int(row["parent_id"]),
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"{key}: run allocate_registry.py --write before building previews"
                ) from error
            if key in entries:
                raise ValueError(f"Duplicate design key in registry: {key}")
            entries[key] = entry
    return entries


def read_definitions(
    path: Path,
) -> tuple[
    dict[int, tuple[int, int, int]],
    dict[tuple[int, int, int], int],
    dict[int, str],
]:
    id_to_color: dict[int, tuple[int, int, int]] = {}
    color_to_id: dict[tuple[int, int, int], int] = {}
    names: dict[int, str] = {}
    with path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if not row or not row[0].isdigit():
                continue
            province_id = int(row[0])
            color = (int(row[1]), int(row[2]), int(row[3]))
            id_to_color[province_id] = color
            color_to_id[color] = province_id
            names[province_id] = row[4]
    return id_to_color, color_to_id, names


def read_sea_ids(default_map_path: Path) -> set[int]:
    text = default_map_path.read_text(encoding="cp1252", errors="replace")
    text = re.sub(r"#.*$", "", text, flags=re.MULTILINE)
    match = re.search(r"sea_starts\s*=\s*\{([^}]*)\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not find sea_starts in {default_map_path}")
    return {int(value) for value in re.findall(r"\b\d+\b", match.group(1))}


def read_special_adjacencies(path: Path) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    with path.open(encoding="cp1252", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if len(row) < 2:
                continue
            try:
                first = int(row[0])
                second = int(row[1])
            except ValueError:
                continue
            if first < 0 or second < 0:
                continue
            pairs.add(tuple(sorted((first, second))))
    return pairs


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_baseline(map_dir: Path, expected_hashes: dict[str, str]) -> dict[str, str]:
    actual_hashes: dict[str, str] = {}
    for relative_name, expected_hash in expected_hashes.items():
        path = map_dir / relative_name
        actual_hash = sha256_file(path)
        actual_hashes[relative_name] = actual_hash
        if actual_hash != expected_hash:
            raise ValueError(
                f"{relative_name}: expected EU4 1.37.5 SHA-256 "
                f"{expected_hash}, found {actual_hash}"
            )
    return actual_hashes


def local_bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError("Province mask has no pixels")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def snap_to_mask(
    mask: np.ndarray,
    reference: tuple[int, int],
    offset: tuple[int, int],
) -> tuple[int, int]:
    """Snap a global reference point to the nearest local mask pixel."""

    x_offset, y_offset = offset
    target_x = reference[0] - x_offset
    target_y = reference[1] - y_offset
    ys, xs = np.where(mask)
    squared = (xs - target_x) ** 2 + (ys - target_y) ** 2
    index = int(np.argmin(squared))
    return int(xs[index]), int(ys[index])


def component_from_seed(mask: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    output = np.zeros(mask.shape, dtype=bool)
    x_seed, y_seed = seed
    if not mask[y_seed, x_seed]:
        return output
    queue: deque[tuple[int, int]] = deque([(x_seed, y_seed)])
    output[y_seed, x_seed] = True
    while queue:
        x, y = queue.popleft()
        for next_x, next_y in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= next_x < mask.shape[1] and 0 <= next_y < mask.shape[0]):
                continue
            if not mask[next_y, next_x] or output[next_y, next_x]:
                continue
            output[next_y, next_x] = True
            queue.append((next_x, next_y))
    return output


def component_sizes(mask: np.ndarray) -> list[int]:
    remaining = mask.copy()
    sizes: list[int] = []
    while remaining.any():
        y_seed, x_seed = np.argwhere(remaining)[0]
        component = component_from_seed(remaining, (int(x_seed), int(y_seed)))
        size = int(component.sum())
        sizes.append(size)
        remaining[component] = False
    return sorted(sizes, reverse=True)


def shared_edge_count(first_mask: np.ndarray, second_mask: np.ndarray) -> int:
    horizontal = int(np.sum(first_mask[:, 1:] & second_mask[:, :-1]))
    horizontal += int(np.sum(first_mask[:, :-1] & second_mask[:, 1:]))
    vertical = int(np.sum(first_mask[1:, :] & second_mask[:-1, :]))
    vertical += int(np.sum(first_mask[:-1, :] & second_mask[1:, :]))
    return horizontal + vertical


def neighboring_ids(
    province_map: np.ndarray,
    mask: np.ndarray,
    color_to_id: dict[tuple[int, int, int], int],
) -> set[int]:
    neighbor_colors: set[tuple[int, int, int]] = set()
    for delta_y, delta_x in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        shifted_mask = np.roll(mask, shift=(delta_y, delta_x), axis=(0, 1))
        edge = shifted_mask & ~mask
        if delta_y == 1:
            edge[0, :] = False
        elif delta_y == -1:
            edge[-1, :] = False
        elif delta_x == 1:
            edge[:, 0] = False
        else:
            edge[:, -1] = False
        for color in np.unique(province_map[edge].reshape(-1, 3), axis=0):
            neighbor_colors.add(tuple(int(channel) for channel in color))
    return {
        color_to_id[color]
        for color in neighbor_colors
        if color in color_to_id
    }


def coastal_pixels(
    province_map: np.ndarray,
    parent_mask: np.ndarray,
    color_to_id: dict[tuple[int, int, int], int],
    sea_ids: set[int],
) -> np.ndarray:
    coast = np.zeros(parent_mask.shape, dtype=bool)
    for delta_y, delta_x in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        shifted = np.roll(province_map, shift=(delta_y, delta_x), axis=(0, 1))
        if delta_y == 1:
            shifted[0, :, :] = province_map[0, :, :]
        elif delta_y == -1:
            shifted[-1, :, :] = province_map[-1, :, :]
        elif delta_x == 1:
            shifted[:, 0, :] = province_map[:, 0, :]
        else:
            shifted[:, -1, :] = province_map[:, -1, :]
        unique_colors = np.unique(shifted[parent_mask].reshape(-1, 3), axis=0)
        sea_colors = {
            tuple(int(channel) for channel in color)
            for color in unique_colors
            if color_to_id.get(tuple(int(channel) for channel in color)) in sea_ids
        }
        if sea_colors:
            coast |= parent_mask & np.any(
                np.all(shifted[:, :, None, :] == np.array(list(sea_colors))[None, None, :, :], axis=3),
                axis=2,
            )
    return coast


def geometry_candidate(
    parent_mask: np.ndarray,
    geometry: dict[str, Any],
    offset: tuple[int, int],
) -> np.ndarray:
    """Rasterize a configured boundary without anti-aliasing."""

    geometry_type = geometry.get("type")
    if geometry_type == "local_half_plane":
        a = int(geometry["a"])
        b = int(geometry["b"])
        threshold = int(geometry["threshold"])
        if a == 0 and b == 0:
            raise ValueError("Half-plane boundary cannot have a zero normal")
        y_coordinates, x_coordinates = np.indices(parent_mask.shape)
        selection = a * x_coordinates + b * y_coordinates <= threshold
    elif geometry_type == "global_polygon":
        width = parent_mask.shape[1]
        height = parent_mask.shape[0]
        x_offset, y_offset = offset
        vertices = [
            (int(point[0]) - x_offset, int(point[1]) - y_offset)
            for point in geometry["vertices"]
        ]
        if len(vertices) < 3:
            raise ValueError("A province polygon needs at least three vertices")
        polygon_image = Image.new("1", (width, height), 0)
        ImageDraw.Draw(polygon_image).polygon(vertices, fill=1)
        selection = np.array(polygon_image, dtype=bool)
    else:
        raise ValueError(f"Unsupported geometry type: {geometry_type!r}")
    return parent_mask & selection


def has_solid_square(mask: np.ndarray, size: int) -> bool:
    if size <= 0:
        raise ValueError("Solid-square size must be positive")
    if mask.shape[0] < size or mask.shape[1] < size:
        return False
    integral = np.pad(
        mask.astype(np.int32).cumsum(axis=0).cumsum(axis=1),
        ((1, 0), (1, 0)),
    )
    totals = (
        integral[size:, size:]
        - integral[:-size, size:]
        - integral[size:, :-size]
        + integral[:-size, :-size]
    )
    return bool(np.any(totals == size * size))


def boundary_segments(pixel_map: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    vertical = np.any(pixel_map[:, 1:, :] != pixel_map[:, :-1, :], axis=2)
    horizontal = np.any(pixel_map[1:, :, :] != pixel_map[:-1, :, :], axis=2)
    return vertical, horizontal


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_boundaries(
    draw: ImageDraw.ImageDraw,
    crop_pixels: np.ndarray,
    scale: int,
    offset_y: int,
    color: str = "#161922",
    width: int = 2,
) -> None:
    vertical, horizontal = boundary_segments(crop_pixels)
    for y, x in np.argwhere(vertical):
        draw.line(
            (
                (x + 1) * scale,
                offset_y + y * scale,
                (x + 1) * scale,
                offset_y + (y + 1) * scale,
            ),
            fill=color,
            width=width,
        )
    for y, x in np.argwhere(horizontal):
        draw.line(
            (
                x * scale,
                offset_y + (y + 1) * scale,
                (x + 1) * scale,
                offset_y + (y + 1) * scale,
            ),
            fill=color,
            width=width,
        )


def render_review(
    changed_map: np.ndarray,
    heightmap: np.ndarray,
    rivers: np.ndarray,
    crop_box: tuple[int, int, int, int],
    scale: int,
    split_results: list[dict[str, Any]],
    output_path: Path,
) -> None:
    left, top, right, bottom = crop_box
    crop = changed_map[top:bottom, left:right]
    crop_height, crop_width = crop.shape[:2]
    panel_width = crop_width * scale
    panel_height = crop_height * scale
    header_height = 190
    gap = 24
    canvas = Image.new(
        "RGB",
        (panel_width * 2 + gap, header_height + panel_height),
        "#10131a",
    )

    political = Image.fromarray(crop, mode="RGB").resize(
        (panel_width, panel_height),
        Image.Resampling.NEAREST,
    )
    canvas.paste(political, (0, header_height))

    height_crop = heightmap[top:bottom, left:right].astype(np.float32)
    normalized = np.clip((height_crop - 70) / 85, 0, 1)
    physical_array = np.zeros((crop_height, crop_width, 3), dtype=np.uint8)
    physical_array[:, :, 0] = (56 + normalized * 104).astype(np.uint8)
    physical_array[:, :, 1] = (80 + normalized * 92).astype(np.uint8)
    physical_array[:, :, 2] = (48 + normalized * 52).astype(np.uint8)
    river_crop = rivers[top:bottom, left:right]
    physical_array[np.isin(river_crop, [0, 1, 2, 3, 4])] = (20, 168, 220)
    physical = Image.fromarray(physical_array, mode="RGB").resize(
        (panel_width, panel_height),
        Image.Resampling.NEAREST,
    )
    canvas.paste(physical, (panel_width + gap, header_height))

    draw = ImageDraw.Draw(canvas)
    title_font = load_font(34)
    body_font = load_font(22)
    small_font = load_font(17)
    draw.text((24, 18), "B01 广东拆省审图图（非正式游戏资产）", font=title_font, fill="white")
    draw.text(
        (24, 64),
        "左：省份颜色与候选边界    右：高度／河流参考与相同边界",
        font=body_font,
        fill="#cbd5e1",
    )
    draw.text(
        (24, 102),
        "海岸线与原版省界保持不变；白点为新省种子，青叉为母省锚点，黑线为像素边界。",
        font=small_font,
        fill="#94a3b8",
    )

    legend_x = 24
    legend_y = 138
    for result in split_results:
        color = tuple(result["rgb"])
        draw.rectangle((legend_x, legend_y, legend_x + 24, legend_y + 24), fill=color)
        label = (
            f"{result['design_key']} {result['new_name_zh']} "
            f"ID {result['game_id']} · {result['new_pixels']} px "
            f"({result['actual_fraction']:.1%})"
        )
        draw.text((legend_x + 32, legend_y - 1), label, font=small_font, fill="white")
        legend_x += 330

    draw_boundaries(draw, crop, scale, header_height)
    shifted_draw = ImageDraw.Draw(canvas)
    vertical, horizontal = boundary_segments(crop)
    right_offset = panel_width + gap
    for y, x in np.argwhere(vertical):
        shifted_draw.line(
            (
                right_offset + (x + 1) * scale,
                header_height + y * scale,
                right_offset + (x + 1) * scale,
                header_height + (y + 1) * scale,
            ),
            fill="#10131a",
            width=2,
        )
    for y, x in np.argwhere(horizontal):
        shifted_draw.line(
            (
                right_offset + x * scale,
                header_height + (y + 1) * scale,
                right_offset + (x + 1) * scale,
                header_height + (y + 1) * scale,
            ),
            fill="#10131a",
            width=2,
        )

    for result in split_results:
        global_x, global_y = result["snapped_new_seed"]
        for panel_x in (0, panel_width + gap):
            point_x = panel_x + (global_x - left) * scale
            point_y = header_height + (global_y - top) * scale
            draw.ellipse(
                (point_x - 7, point_y - 7, point_x + 7, point_y + 7),
                fill="white",
                outline="#10131a",
                width=3,
            )
            draw.text(
                (point_x + 10, point_y - 12),
                result["new_name_zh"],
                font=body_font,
                fill="white",
                stroke_width=3,
                stroke_fill="#10131a",
            )

        for global_x, global_y in result["snapped_retained_seeds"]:
            for panel_x in (0, panel_width + gap):
                point_x = panel_x + (global_x - left) * scale
                point_y = header_height + (global_y - top) * scale
                draw.line(
                    (
                        point_x - 6,
                        point_y - 6,
                        point_x + 6,
                        point_y + 6,
                    ),
                    fill="#38bdf8",
                    width=3,
                )
                draw.line(
                    (
                        point_x - 6,
                        point_y + 6,
                        point_x + 6,
                        point_y - 6,
                    ),
                    fill="#38bdf8",
                    width=3,
                )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def render_pixel_crop(
    changed_map: np.ndarray,
    crop_box: tuple[int, int, int, int],
    scale: int,
    output_path: Path,
) -> None:
    left, top, right, bottom = crop_box
    image = Image.fromarray(changed_map[top:bottom, left:right], mode="RGB")
    image = image.resize(
        ((right - left) * scale, (bottom - top) * scale),
        Image.Resampling.NEAREST,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def write_and_validate_candidate(
    path: Path,
    changed_map: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(changed_map, mode="RGB").save(path, format="BMP")
    with Image.open(path) as candidate:
        if candidate.format != "BMP":
            raise ValueError(f"{path}: expected BMP container, found {candidate.format}")
        if candidate.size != EXPECTED_SIZE:
            raise ValueError(f"{path}: expected size {EXPECTED_SIZE}, found {candidate.size}")
        if candidate.mode != "RGB":
            raise ValueError(f"{path}: expected 24-bit RGB, found {candidate.mode}")
        reopened = np.array(candidate, dtype=np.uint8)
    if not np.array_equal(reopened, changed_map):
        raise ValueError(f"{path}: saved pixels do not match the validated in-memory map")


def safe_candidate_path(path: Path) -> Path:
    staging_root = (REPO_ROOT / "build/map").resolve()
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(staging_root)
    except ValueError as error:
        raise ValueError(
            f"Candidate BMP must stay under the disposable staging root "
            f"{staging_root}; refused {resolved}"
        ) from error
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--candidate-bmp",
        type=Path,
        help="optional disposable output path for a full candidate provinces.bmp",
    )
    args = parser.parse_args()
    candidate_path = safe_candidate_path(args.candidate_bmp) if args.candidate_bmp else None

    map_dir = args.vanilla_root / "map"
    provinces_path = map_dir / "provinces.bmp"
    source_image = Image.open(provinces_path)
    if source_image.size != EXPECTED_SIZE:
        raise ValueError(f"Expected provinces.bmp size {EXPECTED_SIZE}, found {source_image.size}")
    if source_image.mode != "RGB":
        raise ValueError(f"Expected 24-bit RGB provinces.bmp, found mode {source_image.mode}")
    province_map = np.array(source_image, dtype=np.uint8)
    changed_map = province_map.copy()

    registry = read_registry(args.registry)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    baseline_hashes = validate_baseline(
        map_dir,
        {
            str(name): str(file_hash)
            for name, file_hash in config["baseline_file_sha256"].items()
        },
    )
    id_to_color, color_to_id, definition_names = read_definitions(map_dir / "definition.csv")
    sea_ids = read_sea_ids(map_dir / "default.map")
    special_adjacencies = read_special_adjacencies(map_dir / "adjacencies.csv")
    for required_pair in config.get("required_special_adjacencies", []):
        pair = tuple(sorted(int(value) for value in required_pair))
        if pair not in special_adjacencies:
            raise ValueError(f"Missing required vanilla special adjacency: {pair}")

    new_colors: dict[tuple[int, int, int], int] = {}
    new_ids: set[int] = set()
    parent_ids: set[int] = set()
    child_entries: dict[str, RegistryProvince] = {}
    child_specifications: dict[str, dict[str, Any]] = {}
    for partition in config["partitions"]:
        parent_id = int(partition["parent_id"])
        if parent_id in parent_ids:
            raise ValueError(f"Duplicate B01 parent partition: {parent_id}")
        parent_ids.add(parent_id)
        for specification in partition["children"]:
            key = specification["design_key"]
            entry = registry[key]
            if entry.parent_id != parent_id:
                raise ValueError(
                    f"{key}: registry parent {entry.parent_id} "
                    f"does not match config parent {parent_id}"
                )
            if entry.game_id in id_to_color:
                raise ValueError(f"{key}: game ID {entry.game_id} collides with vanilla")
            if entry.game_id in new_ids:
                raise ValueError(f"{key}: duplicate new game ID {entry.game_id}")
            if entry.color in color_to_id or entry.color in new_colors:
                raise ValueError(f"{key}: RGB {entry.color} is not unique")
            if key in child_entries:
                raise ValueError(f"Duplicate B01 child specification: {key}")
            new_ids.add(entry.game_id)
            new_colors[entry.color] = entry.game_id
            child_entries[key] = entry
            child_specifications[key] = specification
    color_to_id.update(new_colors)
    child_lineage = {
        entry.game_id: entry.parent_id for entry in child_entries.values()
    }

    split_results: list[dict[str, Any]] = []
    partition_work: list[dict[str, Any]] = []
    validations: list[str] = []
    maximum_snap_distance = float(config["maximum_snap_distance_pixels"])
    minimum_solid_square = int(config["minimum_solid_square_size"])

    # Build every child from the unmodified source parent. Multi-child parents
    # are partitioned in one pass, so config order cannot change their pixels.
    for partition in config["partitions"]:
        parent_id = int(partition["parent_id"])
        parent_color = id_to_color[parent_id]
        parent_mask = np.all(
            province_map == np.array(parent_color, dtype=np.uint8),
            axis=2,
        )
        left, top, right, bottom = local_bbox(parent_mask)
        local_parent = parent_mask[top:bottom, left:right]
        parent_pixels = int(parent_mask.sum())
        parent_coast = coastal_pixels(
            province_map,
            parent_mask,
            color_to_id,
            sea_ids,
        )
        local_coast = parent_coast[top:bottom, left:right]

        configured_retained_points = [
            tuple(int(value) for value in point)
            for point in partition["retained_reference_points"]
        ]
        retained_seeds = [
            snap_to_mask(local_parent, point, (left, top))
            for point in configured_retained_points
        ]
        snapped_retained_points = [
            (left + seed[0], top + seed[1]) for seed in retained_seeds
        ]
        retained_snap_distances = [
            float(
                (
                    (configured[0] - snapped[0]) ** 2
                    + (configured[1] - snapped[1]) ** 2
                )
                ** 0.5
            )
            for configured, snapped in zip(
                configured_retained_points,
                snapped_retained_points,
                strict=True,
            )
        ]
        if max(retained_snap_distances, default=0.0) > maximum_snap_distance:
            raise ValueError(
                f"{parent_id}: a retained seed snapped "
                f"{max(retained_snap_distances):.2f}px, over the "
                f"{maximum_snap_distance:.2f}px limit"
            )

        original_mainland = component_from_seed(local_parent, retained_seeds[0])
        if not original_mainland.any():
            raise ValueError(f"{parent_id}: retained anchor has no parent component")

        children_work: list[dict[str, Any]] = []
        children_union = np.zeros(local_parent.shape, dtype=bool)
        for specification in partition["children"]:
            key = specification["design_key"]
            entry = child_entries[key]
            candidate = geometry_candidate(
                local_parent,
                specification["geometry"],
                (left, top),
            )
            if not bool(specification["desired_coastal"]):
                candidate &= ~local_coast
            if not candidate.any():
                raise ValueError(f"{key}: configured geometry contains no parent pixels")

            configured_new_seed = tuple(
                int(value) for value in specification["new_seed"]
            )
            local_new_seed = snap_to_mask(
                candidate,
                configured_new_seed,
                (left, top),
            )
            snapped_new_seed = (
                left + local_new_seed[0],
                top + local_new_seed[1],
            )
            new_seed_snap_distance = float(
                (
                    (configured_new_seed[0] - snapped_new_seed[0]) ** 2
                    + (configured_new_seed[1] - snapped_new_seed[1]) ** 2
                )
                ** 0.5
            )
            if new_seed_snap_distance > maximum_snap_distance:
                raise ValueError(
                    f"{key}: seed snapped {new_seed_snap_distance:.2f}px, "
                    f"over the {maximum_snap_distance:.2f}px limit"
                )

            local_new = component_from_seed(candidate, local_new_seed)
            discarded_candidate = candidate & ~local_new
            if discarded_candidate.any():
                raise ValueError(
                    f"{key}: geometry produced detached candidate pixels "
                    f"{component_sizes(discarded_candidate)}"
                )
            if np.any(local_new & ~original_mainland):
                raise ValueError(f"{key}: child captured an original detached island")
            if np.any(local_new & children_union):
                raise ValueError(f"{key}: child geometry overlaps a sibling")
            if not has_solid_square(local_new, minimum_solid_square):
                raise ValueError(
                    f"{key}: no {minimum_solid_square}x{minimum_solid_square} "
                    f"solid clickable core"
                )

            new_pixels = int(local_new.sum())
            actual_fraction = new_pixels / parent_pixels
            target_fraction = float(specification["target_area_fraction"])
            tolerance = float(specification["area_tolerance"])
            if abs(actual_fraction - target_fraction) > tolerance:
                raise ValueError(
                    f"{key}: area fraction {actual_fraction:.3f} is too far "
                    f"from target {target_fraction:.3f} ± {tolerance:.3f}"
                )

            children_union |= local_new
            global_new = np.zeros(parent_mask.shape, dtype=bool)
            global_new[top:bottom, left:right] = local_new
            children_work.append(
                {
                    "specification": specification,
                    "entry": entry,
                    "local_mask": local_new,
                    "global_mask": global_new,
                    "configured_new_seed": configured_new_seed,
                    "snapped_new_seed": snapped_new_seed,
                    "new_seed_snap_distance": new_seed_snap_distance,
                    "new_pixels": new_pixels,
                    "actual_fraction": actual_fraction,
                    "target_fraction": target_fraction,
                }
            )

        retained_mainland = original_mainland & ~children_union
        retained_mainland_components = component_sizes(retained_mainland)
        if len(retained_mainland_components) != 1:
            raise ValueError(
                f"{parent_id}: retained mainland was fragmented: "
                f"{retained_mainland_components}"
            )
        retained_local = local_parent & ~children_union
        for local_seed, global_seed in zip(
            retained_seeds,
            snapped_retained_points,
            strict=True,
        ):
            if not retained_local[local_seed[1], local_seed[0]]:
                raise ValueError(
                    f"{parent_id}: retained anchor {global_seed} moved to a child"
                )

        expected_siblings = {
            tuple(sorted((str(pair[0]), str(pair[1]))))
            for pair in partition["expected_sibling_adjacencies"]
        }
        actual_siblings: set[tuple[str, str]] = set()
        sibling_edges: list[dict[str, Any]] = []
        for first_index, first_child in enumerate(children_work):
            for second_child in children_work[first_index + 1 :]:
                first_key = first_child["entry"].design_key
                second_key = second_child["entry"].design_key
                pair = tuple(sorted((first_key, second_key)))
                edge_count = shared_edge_count(
                    first_child["local_mask"],
                    second_child["local_mask"],
                )
                if edge_count:
                    actual_siblings.add(pair)
                    sibling_edges.append(
                        {
                            "design_keys": list(pair),
                            "shared_edges": edge_count,
                        }
                    )
                if pair in expected_siblings and edge_count < int(
                    config["minimum_shared_sibling_edges"]
                ):
                    raise ValueError(
                        f"{parent_id}: siblings {pair} share only {edge_count} edges"
                    )
        if actual_siblings != expected_siblings:
            raise ValueError(
                f"{parent_id}: sibling adjacencies {sorted(actual_siblings)} "
                f"do not match expected {sorted(expected_siblings)}"
            )

        original_components = component_sizes(local_parent)
        retained_components = component_sizes(retained_local)
        for child in children_work:
            entry = child["entry"]
            specification = child["specification"]
            result = {
                "design_key": entry.design_key,
                "game_id": entry.game_id,
                "rgb": list(entry.color),
                "parent_id": parent_id,
                "parent_definition_name": definition_names[parent_id],
                "retained_name_zh": partition["retained_name_zh"],
                "retained_anchor_policy": partition["retained_anchor_policy"],
                "new_name_zh": specification["new_name_zh"],
                "parent_pixels": parent_pixels,
                "new_pixels": child["new_pixels"],
                "retained_pixels": int(retained_local.sum()),
                "target_fraction": child["target_fraction"],
                "actual_fraction": child["actual_fraction"],
                "geometry": specification["geometry"],
                "original_components": original_components,
                "new_components": component_sizes(child["local_mask"]),
                "retained_components": retained_components,
                "retained_mainland_components": retained_mainland_components,
                "solid_square_size": minimum_solid_square,
                "configured_new_seed": list(child["configured_new_seed"]),
                "snapped_new_seed": list(child["snapped_new_seed"]),
                "new_seed_snap_distance": child["new_seed_snap_distance"],
                "configured_retained_reference_points": [
                    list(point) for point in configured_retained_points
                ],
                "snapped_retained_seeds": [
                    list(point) for point in snapped_retained_points
                ],
                "retained_snap_distances": retained_snap_distances,
                "neighbor_ids": [],
                "coastal": False,
                "notes": specification["notes"],
            }
            child["result"] = result
            split_results.append(result)

        partition_work.append(
            {
                "specification": partition,
                "parent_id": parent_id,
                "parent_mask": parent_mask,
                "local_parent": local_parent,
                "retained_local": retained_local,
                "children": children_work,
                "sibling_edges": sibling_edges,
            }
        )

    # All masks were generated from the unchanged baseline; paint only after
    # every parent partition has passed its local checks.
    for partition in partition_work:
        for child in partition["children"]:
            changed_map[child["global_mask"]] = np.array(
                child["entry"].color,
                dtype=np.uint8,
            )

    changed_pixels = np.any(changed_map != province_map, axis=2)
    allowed_pixels = np.zeros(changed_pixels.shape, dtype=bool)
    for parent_id in parent_ids:
        parent_color = np.array(id_to_color[parent_id], dtype=np.uint8)
        allowed_pixels |= np.all(province_map == parent_color, axis=2)
    if np.any(changed_pixels & ~allowed_pixels):
        raise ValueError("B01 changed pixels outside its configured parent provinces")
    expected_changed_pixels = sum(int(result["new_pixels"]) for result in split_results)
    if int(changed_pixels.sum()) != expected_changed_pixels:
        raise ValueError(
            f"Expected {expected_changed_pixels} changed pixels, "
            f"found {int(changed_pixels.sum())}"
        )

    partition_reports: list[dict[str, Any]] = []
    for partition in partition_work:
        partition_specification = partition["specification"]
        parent_id = partition["parent_id"]
        original_parent_mask = partition["parent_mask"]
        parent_color = np.array(id_to_color[parent_id], dtype=np.uint8)
        retained_parent_mask = np.all(changed_map == parent_color, axis=2)
        children_masks = [
            child["global_mask"] for child in partition["children"]
        ]
        recombined = retained_parent_mask.copy()
        for child_mask in children_masks:
            if np.any(recombined & child_mask):
                raise ValueError(f"{parent_id}: partition masks overlap")
            recombined |= child_mask
        if not np.array_equal(original_parent_mask, recombined):
            raise ValueError(f"{parent_id}: partition does not conserve source pixels")

        original_parent_neighbors = neighboring_ids(
            province_map,
            original_parent_mask,
            color_to_id,
        )
        retained_parent_neighbors = neighboring_ids(
            changed_map,
            retained_parent_mask,
            color_to_id,
        )
        retained_parent_coastal = bool(retained_parent_neighbors & sea_ids)
        if retained_parent_coastal != bool(
            partition_specification["retained_desired_coastal"]
        ):
            raise ValueError(
                f"{parent_id}: retained coastal={retained_parent_coastal}, "
                f"expected {partition_specification['retained_desired_coastal']}"
            )

        region_neighbor_union = set(retained_parent_neighbors)
        internal_ids = {parent_id}
        for child in partition["children"]:
            internal_ids.add(child["entry"].game_id)
            result = child["result"]
            final_mask = child["global_mask"]
            final_neighbors = neighboring_ids(changed_map, final_mask, color_to_id)
            expected_neighbors = {
                int(province_id)
                for province_id in child["specification"]["expected_neighbor_ids"]
            }
            if final_neighbors != expected_neighbors:
                raise ValueError(
                    f"{result['design_key']}: neighbors {sorted(final_neighbors)} "
                    f"do not match expected {sorted(expected_neighbors)}"
                )
            final_coastal = bool(final_neighbors & sea_ids)
            if final_coastal != bool(child["specification"]["desired_coastal"]):
                raise ValueError(
                    f"{result['design_key']}: coastal={final_coastal}, expected "
                    f"{child['specification']['desired_coastal']}"
                )
            shared_parent_edges = shared_edge_count(
                final_mask,
                retained_parent_mask,
            )
            minimum_shared_edges = int(config["minimum_shared_parent_edges"])
            if shared_parent_edges < minimum_shared_edges:
                raise ValueError(
                    f"{result['design_key']}: only {shared_parent_edges} "
                    f"shared parent edges; minimum is {minimum_shared_edges}"
                )

            region_neighbor_union |= final_neighbors
            result["neighbor_ids"] = sorted(final_neighbors)
            result["coastal"] = final_coastal
            result["shared_parent_edges"] = shared_parent_edges
            result["original_parent_neighbor_ids"] = sorted(
                original_parent_neighbors
            )
            result["retained_parent_neighbor_ids"] = sorted(
                retained_parent_neighbors
            )
            result["retained_parent_lost_neighbor_ids"] = sorted(
                original_parent_neighbors - retained_parent_neighbors
            )
            result["retained_parent_gained_neighbor_ids"] = sorted(
                retained_parent_neighbors - original_parent_neighbors
            )
            result["original_parent_coastal"] = bool(
                original_parent_neighbors & sea_ids
            )
            result["retained_parent_coastal"] = retained_parent_coastal
            validations.append(
                f"{result['design_key']}: {result['new_pixels']}px, "
                f"{result['actual_fraction']:.1%}, "
                f"shared_parent_edges={shared_parent_edges}, "
                f"neighbors={sorted(final_neighbors)}"
            )

        collapsed_external_neighbors = {
            child_lineage.get(neighbor_id, neighbor_id)
            for neighbor_id in region_neighbor_union - internal_ids
        }
        if collapsed_external_neighbors != original_parent_neighbors:
            raise ValueError(
                f"{parent_id}: external adjacency lineage changed from "
                f"{sorted(original_parent_neighbors)} to "
                f"{sorted(collapsed_external_neighbors)}"
            )
        partition_reports.append(
            {
                "parent_id": parent_id,
                "retained_name_zh": partition_specification["retained_name_zh"],
                "retained_anchor_policy": partition_specification[
                    "retained_anchor_policy"
                ],
                "original_pixels": int(original_parent_mask.sum()),
                "retained_pixels": int(retained_parent_mask.sum()),
                "child_design_keys": [
                    child["entry"].design_key for child in partition["children"]
                ],
                "sibling_edges": partition["sibling_edges"],
                "original_external_neighbor_ids": sorted(
                    original_parent_neighbors
                ),
                "collapsed_final_external_neighbor_ids": sorted(
                    collapsed_external_neighbors
                ),
                "retained_coastal": retained_parent_coastal,
            }
        )

    heightmap = np.array(Image.open(map_dir / "heightmap.bmp").convert("L"))
    rivers = np.array(Image.open(map_dir / "rivers.bmp"))
    crop_box = tuple(int(value) for value in config["review_crop"])
    scale = int(config["review_scale"])
    review_path = args.output_dir / "B01_guangdong_review.png"
    raw_path = args.output_dir / "B01_guangdong_pixels.png"
    report_path = args.output_dir / "B01_guangdong_report.json"
    render_review(
        changed_map=changed_map,
        heightmap=heightmap,
        rivers=rivers,
        crop_box=crop_box,
        scale=scale,
        split_results=split_results,
        output_path=review_path,
    )
    render_pixel_crop(
        changed_map=changed_map,
        crop_box=crop_box,
        scale=scale,
        output_path=raw_path,
    )
    if candidate_path:
        write_and_validate_candidate(candidate_path, changed_map)

    report = {
        "status": "PREVIEW_GEOMETRY_PASS",
        "scope": "B01 geometry preview only; not a loadable EU4 map",
        "baseline_version": config["baseline_version"],
        "baseline_verified_by_sha256": True,
        "baseline_file_sha256": baseline_hashes,
        "image_size": list(source_image.size),
        "image_mode": source_image.mode,
        "review_crop": list(crop_box),
        "changed_pixels": int(changed_pixels.sum()),
        "partitions": partition_reports,
        "splits": split_results,
        "checks": validations,
        "candidate_bmp_written": bool(candidate_path),
        "production_map_written": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"{review_path}: written")
    print(f"{raw_path}: written")
    print(f"{report_path}: PREVIEW_GEOMETRY_PASS")
    for validation in validations:
        print(validation)
    if candidate_path:
        print(f"{candidate_path}: disposable candidate written")


if __name__ == "__main__":
    main()
