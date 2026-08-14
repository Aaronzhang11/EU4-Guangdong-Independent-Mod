#!/usr/bin/env python3
"""Read-only geometry audit for EU4 impassable mountain provinces."""

from __future__ import annotations

import argparse
import csv
import struct
import sys
from collections import Counter
from pathlib import Path


def rgb_key(red: int, green: int, blue: int) -> int:
    return (red << 16) | (green << 8) | blue


def key_to_rgb(value: int) -> tuple[int, int, int]:
    return (value >> 16) & 255, (value >> 8) & 255, value & 255


def parse_mountain(value: str) -> tuple[int, int]:
    try:
        province_text, rgb_text = value.split(":", 1)
        channels = [int(item) for item in rgb_text.split(",")]
        province_id = int(province_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "山体格式应为 ID:R,G,B，例如 5310:37,173,211"
        ) from error

    if len(channels) != 3 or any(channel < 0 or channel > 255 for channel in channels):
        raise argparse.ArgumentTypeError("RGB必须包含三个0至255的整数")

    return province_id, rgb_key(*channels)


def parse_pair(value: str) -> tuple[int, int]:
    try:
        left, right = (int(item) for item in value.split(":", 1))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "邻接格式应为 ID:ID，例如 5216:5001"
        ) from error

    if left == right:
        raise argparse.ArgumentTypeError("邻接两端不能使用相同ID")

    return tuple(sorted((left, right)))


def read_definition(
    path: Path,
) -> tuple[
    dict[int, int],
    dict[int, int],
    list[str],
    dict[int, set[int]],
]:
    id_to_color: dict[int, int] = {}
    color_to_id: dict[int, int] = {}
    errors: list[str] = []
    duplicate_colors: dict[int, set[int]] = {}

    with path.open("r", encoding="cp1252", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")

        for row_number, row in enumerate(reader, start=1):
            if len(row) < 4 or not row[0].isdigit():
                continue

            province_id = int(row[0])

            try:
                red, green, blue = (int(value) for value in row[1:4])
            except ValueError:
                errors.append(f"definition.csv第{row_number}行RGB不是整数")
                continue

            color = rgb_key(red, green, blue)

            previous_color = id_to_color.get(province_id)
            if previous_color is not None and previous_color != color:
                errors.append(f"省份ID {province_id}存在多个RGB")

            previous_id = color_to_id.get(color)

            if previous_id is not None and previous_id != province_id:
                province_ids = duplicate_colors.setdefault(
                    color,
                    {previous_id},
                )
                province_ids.add(province_id)
            else:
                color_to_id[color] = province_id

            id_to_color[province_id] = color

    return id_to_color, color_to_id, errors, duplicate_colors


def read_bmp(path: Path) -> dict[str, object]:
    data = path.read_bytes()

    if len(data) < 54 or data[:2] != b"BM":
        raise ValueError("文件不是有效的Windows BMP")

    declared_size = struct.unpack_from("<I", data, 2)[0]
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    width, signed_height = struct.unpack_from("<ii", data, 18)
    planes = struct.unpack_from("<H", data, 26)[0]
    bits_per_pixel = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]

    if width <= 0 or signed_height == 0:
        raise ValueError("BMP宽度或高度无效")

    height = abs(signed_height)
    row_stride = (width * 3 + 3) & ~3
    required_size = pixel_offset + row_stride * height

    if required_size > len(data):
        raise ValueError("BMP像素数据不完整")

    return {
        "data": data,
        "declared_size": declared_size,
        "actual_size": len(data),
        "pixel_offset": pixel_offset,
        "dib_size": dib_size,
        "width": width,
        "height": height,
        "bottom_up": signed_height > 0,
        "planes": planes,
        "bits_per_pixel": bits_per_pixel,
        "compression": compression,
        "row_stride": row_stride,
    }


def component_sizes(
    points: set[int],
    width: int,
    height: int,
) -> list[int]:
    remaining = set(points)
    sizes: list[int] = []
    total_pixels = width * height

    while remaining:
        start = remaining.pop()
        stack = [start]
        size = 0

        while stack:
            current = stack.pop()
            size += 1
            x_coordinate = current % width

            neighbours: list[int] = []

            if x_coordinate > 0:
                neighbours.append(current - 1)

            if x_coordinate + 1 < width:
                neighbours.append(current + 1)

            if current >= width:
                neighbours.append(current - width)

            if current + width < total_pixels:
                neighbours.append(current + width)

            for neighbour in neighbours:
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    stack.append(neighbour)

        sizes.append(size)

    return sorted(sizes, reverse=True)


def analyse(
    bmp: dict[str, object],
    color_to_id: dict[int, int],
    tracked_ids: set[int],
    mountain_ids: set[int],
    target_pairs: set[tuple[int, int]],
) -> tuple[
    dict[int, set[int]],
    dict[int, list[int]],
    Counter[tuple[int, int]],
    Counter[int],
]:
    data = bmp["data"]
    width = int(bmp["width"])
    height = int(bmp["height"])
    pixel_offset = int(bmp["pixel_offset"])
    row_stride = int(bmp["row_stride"])
    bottom_up = bool(bmp["bottom_up"])

    pixels_by_id: dict[int, set[int]] = {
        province_id: set() for province_id in tracked_ids
    }

    bounding_boxes: dict[int, list[int]] = {
        province_id: [width, height, -1, -1] for province_id in mountain_ids
    }

    edge_counts: Counter[tuple[int, int]] = Counter()
    unknown_colors: Counter[int] = Counter()
    previous_ids: list[int] | None = None

    raw_data = memoryview(data)

    for display_y in range(height):
        file_y = height - 1 - display_y if bottom_up else display_y
        start = pixel_offset + file_y * row_stride
        row = raw_data[start : start + width * 3]

        colors = [
            (row[index + 2] << 16) | (row[index + 1] << 8) | row[index]
            for index in range(0, width * 3, 3)
        ]

        province_ids = [color_to_id.get(color, -1) for color in colors]

        for x_coordinate, (color, province_id) in enumerate(
            zip(colors, province_ids)
        ):
            if province_id == -1:
                unknown_colors[color] += 1
                continue

            if province_id in tracked_ids:
                pixel_index = display_y * width + x_coordinate
                pixels_by_id[province_id].add(pixel_index)

            if province_id in mountain_ids:
                box = bounding_boxes[province_id]
                box[0] = min(box[0], x_coordinate)
                box[1] = min(box[1], display_y)
                box[2] = max(box[2], x_coordinate)
                box[3] = max(box[3], display_y)

        for x_coordinate in range(width - 1):
            left = province_ids[x_coordinate]
            right = province_ids[x_coordinate + 1]

            if left == -1 or right == -1 or left == right:
                continue

            pair = tuple(sorted((left, right)))

            if pair in target_pairs:
                edge_counts[pair] += 1

        if previous_ids is not None:
            for x_coordinate in range(width):
                upper = previous_ids[x_coordinate]
                lower = province_ids[x_coordinate]

                if upper == -1 or lower == -1 or upper == lower:
                    continue

                pair = tuple(sorted((upper, lower)))

                if pair in target_pairs:
                    edge_counts[pair] += 1

        previous_ids = province_ids

    return pixels_by_id, bounding_boxes, edge_counts, unknown_colors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="只读检查EU4不可通行山脉候选BMP"
    )

    parser.add_argument(
        "--mod-root",
        type=Path,
        required=True,
        help="包含map目录的模组根目录",
    )

    parser.add_argument(
        "--bmp",
        type=Path,
        required=True,
        help="需要检查的候选或正式provinces.bmp",
    )

    parser.add_argument(
        "--mountain",
        type=parse_mountain,
        action="append",
        required=True,
        help="新增山体，格式ID:R,G,B；可以重复",
    )

    parser.add_argument(
        "--block",
        type=parse_pair,
        action="append",
        default=[],
        help="必须切断的邻接，格式ID:ID",
    )

    parser.add_argument(
        "--keep",
        type=parse_pair,
        action="append",
        default=[],
        help="必须保留的邻接，格式ID:ID",
    )

    parser.add_argument(
        "--min-keep-edges",
        type=int,
        default=5,
        help="保留道路所需的最少公共边，默认5",
    )

    parser.add_argument(
        "--expected-width",
        type=int,
        default=5632,
    )

    parser.add_argument(
        "--expected-height",
        type=int,
        default=2048,
    )

    arguments = parser.parse_args()

    mod_root = arguments.mod_root.resolve()
    bmp_path = arguments.bmp.resolve()
    definition_path = mod_root / "map" / "definition.csv"

    failures: list[str] = []
    warnings: list[str] = []

    if not definition_path.is_file():
        print(f"[FAIL] 找不到 {definition_path}")
        return 1

    if not bmp_path.is_file():
        print(f"[FAIL] 找不到 {bmp_path}")
        return 1

    (
        id_to_color,
        color_to_id,
        definition_errors,
        duplicate_colors,
    ) = read_definition(definition_path)

    failures.extend(definition_errors)

    if duplicate_colors:
        warnings.append(
            f"definition.csv包含{len(duplicate_colors)}种历史重复RGB，"
            "主要来自RNW占位省份；这些既有重复项不作为本批次失败"
        )

    mountains: dict[int, int] = {}

    for province_id, color in arguments.mountain:
        if province_id in mountains and mountains[province_id] != color:
            failures.append(f"山体ID {province_id}被分配多个RGB")

        if color in mountains.values() and mountains.get(province_id) != color:
            failures.append(
                f"山体RGB {key_to_rgb(color)}被多个新增ID使用"
            )

        existing_color = id_to_color.get(province_id)
        if existing_color is not None and existing_color != color:
            failures.append(
                f"山体ID {province_id}与definition.csv中的RGB冲突"
            )

        existing_id = color_to_id.get(color)
        if existing_id is not None and existing_id != province_id:
            failures.append(
                f"山体RGB {key_to_rgb(color)}已经属于省份 {existing_id}"
            )

        mountains[province_id] = color

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    for province_id, color in mountains.items():
        color_to_id[color] = province_id

    try:
        bmp = read_bmp(bmp_path)
    except ValueError as error:
        print(f"[FAIL] {error}")
        return 1

    width = int(bmp["width"])
    height = int(bmp["height"])

    if width != arguments.expected_width:
        failures.append(
            f"BMP宽度为{width}，预期{arguments.expected_width}"
        )

    if height != arguments.expected_height:
        failures.append(
            f"BMP高度为{height}，预期{arguments.expected_height}"
        )

    if int(bmp["planes"]) != 1:
        failures.append("BMP planes不是1")

    if int(bmp["bits_per_pixel"]) != 24:
        failures.append(
            f"BMP位深为{bmp['bits_per_pixel']}，预期24"
        )

    if int(bmp["compression"]) != 0:
        failures.append("BMP不是无压缩BI_RGB")

    if int(bmp["declared_size"]) not in (0, int(bmp["actual_size"])):
        warnings.append("BMP头部声明大小与实际文件大小不同")

    if int(bmp["dib_size"]) != 40 or int(bmp["pixel_offset"]) != 54:
        warnings.append(
            "BMP不是经典40字节DIB头或像素偏移不是54；"
            "EU4可能仍能读取，但应复核导出设置"
        )

    blocked_pairs = set(arguments.block)
    kept_pairs = set(arguments.keep)
    target_pairs = blocked_pairs | kept_pairs

    tracked_ids = set(mountains)

    for left, right in target_pairs:
        tracked_ids.add(left)
        tracked_ids.add(right)

    (
        pixels_by_id,
        bounding_boxes,
        edge_counts,
        unknown_colors,
    ) = analyse(
        bmp,
        color_to_id,
        tracked_ids,
        set(mountains),
        target_pairs,
    )

    if unknown_colors:
        failures.append(
            f"BMP中发现{len(unknown_colors)}种未登记颜色，"
            f"共{sum(unknown_colors.values())}个像素"
        )

        for color, count in unknown_colors.most_common(10):
            failures.append(
                f"未登记RGB {key_to_rgb(color)}：{count}像素"
            )

    for province_id, color in mountains.items():
        points = pixels_by_id[province_id]
        components = component_sizes(points, width, height)

        if not points:
            failures.append(
                f"山体 {province_id} / {key_to_rgb(color)}没有像素"
            )
            continue

        if len(components) != 1:
            failures.append(
                f"山体 {province_id}包含{len(components)}个四向连通块："
                f"{components}"
            )

        print(
            f"[INFO] 山体 {province_id} RGB={key_to_rgb(color)} "
            f"像素={len(points)} 连通块={components} "
            f"bbox={bounding_boxes[province_id]}"
        )

    for pair in sorted(blocked_pairs):
        edge_count = edge_counts[pair]

        if edge_count != 0:
            failures.append(
                f"应切断邻接 {pair[0]}-{pair[1]}，"
                f"但仍有{edge_count}条公共边"
            )
        else:
            print(f"[OK] 已切断邻接 {pair[0]}-{pair[1]}")

    for pair in sorted(kept_pairs):
        edge_count = edge_counts[pair]

        if edge_count < arguments.min_keep_edges:
            failures.append(
                f"应保留邻接 {pair[0]}-{pair[1]}，"
                f"但仅有{edge_count}条公共边"
            )
        else:
            print(
                f"[OK] 已保留邻接 {pair[0]}-{pair[1]}："
                f"{edge_count}条公共边"
            )

    for province_id in sorted(tracked_ids - set(mountains)):
        points = pixels_by_id[province_id]

        if not points:
            failures.append(f"目标省份 {province_id}在BMP中没有像素")
            continue

        components = component_sizes(points, width, height)

        if len(components) > 1:
            warnings.append(
                f"目标省份 {province_id}包含{len(components)}个连通块："
                f"{components}"
            )

    print(
        f"[INFO] BMP={bmp_path}\n"
        f"[INFO] 尺寸={width}x{height} "
        f"位深={bmp['bits_per_pixel']} "
        f"压缩={bmp['compression']} "
        f"DIB={bmp['dib_size']} "
        f"像素偏移={bmp['pixel_offset']}"
    )

    for warning in warnings:
        print(f"[WARN] {warning}")

    for failure in failures:
        print(f"[FAIL] {failure}")

    if failures:
        print(f"[RESULT] FAILED：{len(failures)}项失败")
        return 1

    print("[RESULT] PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
