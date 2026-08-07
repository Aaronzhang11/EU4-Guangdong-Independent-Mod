#!/usr/bin/env python3
"""Build and install the B42 Epang Palace ambient map model.

This transaction changes no province pixels or gameplay data.  It creates a
deterministic Clausewitz mesh, its materials and entity declarations, then
adds one marker-owned object to the current ambient_object.txt without
disturbing the existing Luoyang palace marker.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from epang_palace_geometry import MATERIALS, MODEL_VERSION, Surface, build_palace, combined_bounds  # noqa: E402


BATCH = "GDD_B42_EPANG_PALACE"
MARKER_BEGIN = f"# {BATCH}_BEGIN"
MARKER_END = f"# {BATCH}_END"
PROVINCE_ID = 5271
PROVINCE_NAME = "Binzhou"
PROVINCE_RGB = (195, 253, 181)
PLACEMENT = (4498.0, 0.04, 1223.0)
ROTATION = (0.0, -5.0, 0.0)
AMBIENT_SCALE = 0.38


def parse_args() -> argparse.Namespace:
    default_repo = SCRIPT_DIR.parents[1]
    default_vanilla = Path.home() / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=default_repo)
    parser.add_argument("--vanilla-root", type=Path, default=default_vanilla)
    parser.add_argument("--blender", type=Path, default=Path("/Applications/Blender.app/Contents/MacOS/Blender"))
    parser.add_argument("--skip-blender", action="store_true")
    parser.add_argument("--force-render", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def write_json(path: Path, value: object) -> None:
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def encode_object(name: str, depth: int) -> bytes:
    encoded = name.encode("latin-1")
    if len(encoded) >= 64:
        raise ValueError(f"PDX object name is too long: {name}")
    return b"[" * depth + encoded + b"\0"


def encode_values(values: Iterable[int | float | str]) -> bytes:
    data = list(values)
    if not data:
        return b""
    if all(type(value) is int for value in data):
        return b"i" + struct.pack("<i", len(data)) + struct.pack(f"<{len(data)}i", *data)
    if all(type(value) is float for value in data):
        return b"f" + struct.pack("<i", len(data)) + struct.pack(f"<{len(data)}f", *data)
    if all(type(value) is str for value in data):
        if len(data) != 1:
            raise ValueError("Clausewitz mesh strings are scalar properties")
        encoded = data[0].encode("latin-1") + b"\0"
        return b"s" + struct.pack("<i", 1) + struct.pack("<i", len(encoded)) + encoded
    raise TypeError("PDX properties must contain one homogeneous primitive type")


def encode_property(name: str, values: Iterable[int | float | str]) -> bytes:
    encoded_name = name.encode("latin-1")
    if len(encoded_name) > 127:
        raise ValueError(f"PDX property name is too long: {name}")
    return b"!" + struct.pack("b", len(encoded_name)) + encoded_name + encode_values(values)


def write_clausewitz_mesh(path: Path, surfaces: dict[str, Surface]) -> None:
    payload = bytearray(b"@@b@")
    payload += encode_property("pdxasset", [1, 0])
    payload += encode_object("object", 1)
    payload += encode_object("gdd_epang_palace_shape", 2)
    for material_name, surface in surfaces.items():
        if not surface.positions:
            continue
        minimum, maximum = surface.bounds()
        payload += encode_object("mesh", 3)
        payload += encode_property("p", [float(value) for value in surface.positions])
        payload += encode_property("n", [float(value) for value in surface.normals])
        payload += encode_property("ta", [float(value) for value in surface.tangents])
        payload += encode_property("u0", [float(value) for value in surface.uvs])
        payload += encode_property("tri", surface.triangles)
        payload += encode_object("aabb", 4)
        payload += encode_property("min", [float(value) for value in minimum])
        payload += encode_property("max", [float(value) for value in maximum])
        payload += encode_object("material", 4)
        payload += encode_property("shader", ["PdxMeshSnow"])
        payload += encode_property("diff", [MATERIALS[material_name].texture])
        payload += encode_property("n", ["gdd_epang_flat_normal.dds"])
        payload += encode_property("spec", ["gdd_epang_flat_spec.dds"])
    payload += encode_object("locator", 1)
    atomic_write(path, bytes(payload))


def texture_pixels(name: str, size: int = 64) -> bytes:
    base = tuple(round(channel * 255) for channel in MATERIALS[name].color[:3])
    result = bytearray()
    for y in range(size):
        for x in range(size):
            if name == "roof":
                delta = 11 if x % 8 in (0, 1) else -4
            elif name == "stone":
                delta = ((x * 13 + y * 7) % 17) - 8
            elif name in ("red", "wood"):
                delta = 8 if x % 16 in (0, 1) else ((y * 3 + x) % 7) - 3
            elif name == "earth":
                delta = ((x * 5 + y * 11) % 17) - 8
                if y % 12 == 0:
                    delta -= 7
            elif name == "bronze":
                delta = 10 if (x + y) % 18 < 3 else -3
            else:
                delta = 0
            red, green, blue = (max(0, min(255, channel + delta)) for channel in base)
            result.extend((blue, green, red, 255))
    return bytes(result)


def write_uncompressed_dds(path: Path, width: int, height: int, bgra_pixels: bytes) -> None:
    if len(bgra_pixels) != width * height * 4:
        raise ValueError("DDS pixel buffer has the wrong size")
    flags = 0x0000100F  # CAPS | HEIGHT | WIDTH | PITCH | PIXELFORMAT
    pixel_flags = 0x00000041  # RGB | ALPHA
    header_values = [
        124,
        flags,
        height,
        width,
        width * 4,
        0,
        0,
        *([0] * 11),
        32,
        pixel_flags,
        0,
        32,
        0x00FF0000,
        0x0000FF00,
        0x000000FF,
        0xFF000000,
        0x00001000,
        0,
        0,
        0,
        0,
    ]
    header = struct.pack("<31I", *header_values)
    atomic_write(path, b"DDS " + header + bgra_pixels)


def build_textures(model_dir: Path) -> list[Path]:
    outputs: list[Path] = []
    for name, spec in MATERIALS.items():
        output = model_dir / spec.texture
        write_uncompressed_dds(output, 64, 64, texture_pixels(name))
        outputs.append(output)
    normal = model_dir / "gdd_epang_flat_normal.dds"
    specular = model_dir / "gdd_epang_flat_spec.dds"
    write_uncompressed_dds(normal, 4, 4, bytes((255, 128, 128, 255)) * 16)
    write_uncompressed_dds(specular, 4, 4, bytes((0, 20, 0, 255)) * 16)
    outputs.extend((normal, specular))
    return outputs


def ambient_block() -> str:
    return f"""{MARKER_BEGIN}
type={{
\ttype=\"gdd_epang_palace_entity\"
\tuse_animation=no
\tscale={AMBIENT_SCALE:.6f}
\ttime_duration=300.000000
\tobject={{
\t\tname=\"gdd_epang_palace\"
\t\thidden_on_start=no
\t\tposition={{
\t\t\t{PLACEMENT[0]:.3f} {PLACEMENT[1]:.3f} {PLACEMENT[2]:.3f}
\t\t}}
\t\trotation={{
\t\t\t{ROTATION[0]:.3f} {ROTATION[1]:.3f} {ROTATION[2]:.3f}
\t\t}}
\t}}
}}
{MARKER_END}
"""


def update_ambient_object(target: Path, vanilla_source: Path, backup: Path) -> tuple[str, str]:
    if target.exists():
        source_bytes = target.read_bytes()
    else:
        source_bytes = vanilla_source.read_bytes()
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        with backup.open("wb") as raw_handle:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as handle:
                handle.write(source_bytes)
    text = source_bytes.decode("utf-8-sig").replace("\r\n", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    pattern = re.compile(rf"\n?{re.escape(MARKER_BEGIN)}.*?{re.escape(MARKER_END)}\n?", re.DOTALL)
    base_text = pattern.sub("", text)
    base_text = re.sub(r"\n{3,}", "\n\n", base_text).rstrip() + "\n"
    marker_text = ambient_block()
    output_text = base_text + "\n" + marker_text
    atomic_write(target, output_text.encode("utf-8"))
    return sha256_bytes(base_text.encode("utf-8")), sha256_bytes(marker_text.encode("utf-8"))


def render_with_blender(repo: Path, blender: Path, planning: Path, force: bool) -> list[Path]:
    preview = planning / "preview/gdd_epang_palace_preview.png"
    blend = planning / "source/gdd_epang_palace.blend"
    stamp_path = planning / "blender_build_stamp.json"
    renderer = repo / "tools/model_pipeline/render_epang_palace_blender.py"
    geometry = repo / "tools/model_pipeline/epang_palace_geometry.py"
    version_result = subprocess.run([str(blender), "--version"], check=True, text=True, capture_output=True)
    blender_version = version_result.stdout.splitlines()[0]
    desired_stamp = {
        "blender": blender_version,
        "geometry_sha256": sha256(geometry),
        "renderer_sha256": sha256(renderer),
    }
    current_stamp = json.loads(stamp_path.read_text("utf-8")) if stamp_path.exists() else None
    if not force and current_stamp == desired_stamp and preview.exists() and blend.exists():
        return [blend, preview, stamp_path]
    command = [
        str(blender),
        "--background",
        "--factory-startup",
        "--python",
        str(renderer),
        "--",
        "--blend",
        str(blend),
        "--preview",
        str(preview),
    ]
    subprocess.run(command, check=True)
    write_json(stamp_path, desired_stamp)
    return [blend, preview, stamp_path]


def read_definition(mod: Path) -> tuple[int, int, int, str]:
    definition = mod / "map/definition.csv"
    matches: list[tuple[int, int, int, str]] = []
    with definition.open("r", encoding="latin-1", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if len(row) >= 5 and row[0].isdigit() and int(row[0]) == PROVINCE_ID:
                matches.append((int(row[1]), int(row[2]), int(row[3]), row[4]))
    if len(matches) != 1:
        raise ValueError(f"expected one definition row for {PROVINCE_ID}, found {len(matches)}")
    return matches[0]


def rotate_footprint(bounds: tuple[tuple[float, float, float], tuple[float, float, float]]) -> list[tuple[float, float]]:
    minimum, maximum = bounds
    angle = math.radians(ROTATION[1])
    cosine, sine = math.cos(angle), math.sin(angle)
    world_points: list[tuple[float, float]] = []
    for local_x in (minimum[0], maximum[0]):
        for local_z in (minimum[2], maximum[2]):
            scaled_x = local_x * AMBIENT_SCALE
            scaled_z = local_z * AMBIENT_SCALE
            world_x = PLACEMENT[0] + scaled_x * cosine - scaled_z * sine
            world_z = PLACEMENT[2] + scaled_x * sine + scaled_z * cosine
            world_points.append((world_x, world_z))
    return world_points


def validate_placement(
    mod: Path,
    bounds: tuple[tuple[float, float, float], tuple[float, float, float]],
) -> dict[str, object]:
    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("Pillow is required for the placement validation") from error

    definition_rgb_name = read_definition(mod)
    if definition_rgb_name[:3] != PROVINCE_RGB:
        raise ValueError(f"province {PROVINCE_ID} RGB drifted: {definition_rgb_name[:3]} != {PROVINCE_RGB}")

    provinces = Image.open(mod / "map/provinces.bmp").convert("RGB")
    rivers = Image.open(mod / "map/rivers.bmp")
    heightmap = Image.open(mod / "map/heightmap.bmp")
    if provinces.size != rivers.size or provinces.size != heightmap.size:
        raise ValueError("map bitmap dimensions do not agree")

    footprint = rotate_footprint(bounds)
    min_x = math.floor(min(point[0] for point in footprint) - 0.5)
    max_x = math.ceil(max(point[0] for point in footprint) + 0.5)
    min_z = math.floor(min(point[1] for point in footprint) - 0.5)
    max_z = math.ceil(max(point[1] for point in footprint) + 0.5)
    samples: list[tuple[int, int]] = []
    heights: list[int] = []
    for map_z in range(min_z, max_z + 1):
        bitmap_y = provinces.height - 1 - map_z
        for map_x in range(min_x, max_x + 1):
            if not (0 <= map_x < provinces.width and 0 <= bitmap_y < provinces.height):
                raise ValueError(f"footprint sample lies outside map: {(map_x, map_z)}")
            pixel = provinces.getpixel((map_x, bitmap_y))
            if pixel != PROVINCE_RGB:
                raise ValueError(f"footprint crosses province boundary at {(map_x, map_z)}: {pixel}")
            river_value = rivers.getpixel((map_x, bitmap_y))
            if river_value != 255:
                raise ValueError(f"footprint touches river data at {(map_x, map_z)}: {river_value}")
            samples.append((map_x, map_z))
            heights.append(int(heightmap.getpixel((map_x, bitmap_y))))

    anchors = {
        "Binzhou city": (4500.0, 1231.0),
        "Xianyang city": (4506.0, 1223.0),
        "Haojing city": (4499.0, 1215.0),
        "Changan city": (4511.0, 1220.0),
    }
    distances = {
        name: round(math.hypot(PLACEMENT[0] - point[0], PLACEMENT[2] - point[1]), 3)
        for name, point in anchors.items()
    }
    if min(distances.values()) < 7.5:
        raise ValueError(f"placement is too close to an existing city anchor: {distances}")

    return {
        "definition_name": definition_rgb_name[3],
        "centre_pixel": list(PROVINCE_RGB),
        "footprint_corners": [[round(x, 4), round(z, 4)] for x, z in footprint],
        "sample_window": [min_x, min_z, max_x, max_z],
        "sample_count": len(samples),
        "river_values": [255],
        "height_range": [min(heights), max(heights)],
        "anchor_distances": distances,
    }


def parse_clausewitz_mesh(mesh: bytes) -> list[dict[str, list[int | float | str]]]:
    """Parse the subset of the PDX binary format emitted above for a round-trip check."""
    if not mesh.startswith(b"@@b@"):
        raise ValueError("mesh is missing the Clausewitz binary header")
    offset = 4
    current_context = "root"
    current_mesh: dict[str, list[int | float | str]] | None = None
    meshes: list[dict[str, list[int | float | str]]] = []
    while offset < len(mesh):
        token = mesh[offset : offset + 1]
        if token == b"[":
            depth = 0
            while offset < len(mesh) and mesh[offset : offset + 1] == b"[":
                depth += 1
                offset += 1
            end = mesh.index(b"\0", offset)
            object_name = mesh[offset:end].decode("latin-1")
            offset = end + 1
            current_context = object_name
            if depth == 3 and object_name == "mesh":
                current_mesh = {}
                meshes.append(current_mesh)
            elif depth <= 2 or object_name == "locator":
                current_mesh = None
            continue
        if token != b"!":
            raise ValueError(f"unexpected PDX token at byte {offset}: {token!r}")

        offset += 1
        name_length = struct.unpack_from("b", mesh, offset)[0]
        offset += 1
        property_name = mesh[offset : offset + name_length].decode("latin-1")
        offset += name_length
        value_type = mesh[offset : offset + 1]
        offset += 1
        count = struct.unpack_from("<i", mesh, offset)[0]
        offset += 4
        values: list[int | float | str]
        if value_type == b"i":
            values = list(struct.unpack_from(f"<{count}i", mesh, offset))
            offset += count * 4
        elif value_type == b"f":
            values = list(struct.unpack_from(f"<{count}f", mesh, offset))
            offset += count * 4
        elif value_type == b"s":
            if count != 1:
                raise ValueError(f"unexpected string count for {property_name}: {count}")
            string_length = struct.unpack_from("<i", mesh, offset)[0]
            offset += 4
            raw_string = mesh[offset : offset + string_length]
            offset += string_length
            values = [raw_string.rstrip(b"\0").decode("latin-1")]
        else:
            raise ValueError(f"unknown PDX value type for {property_name}: {value_type!r}")
        if current_mesh is not None:
            current_mesh[f"{current_context}.{property_name}"] = values
    return meshes


def validate_mesh_semantics(mesh: bytes) -> dict[str, object]:
    meshes = parse_clausewitz_mesh(mesh)
    if len(meshes) != len(MATERIALS):
        raise ValueError(f"expected {len(MATERIALS)} submeshes, parsed {len(meshes)}")
    expected_textures = {spec.texture for spec in MATERIALS.values()}
    parsed_textures: set[str] = set()
    total_vertices = 0
    total_triangles = 0
    for index, submesh in enumerate(meshes):
        positions = submesh.get("mesh.p", [])
        normals = submesh.get("mesh.n", [])
        tangents = submesh.get("mesh.ta", [])
        uvs = submesh.get("mesh.u0", [])
        triangles = submesh.get("mesh.tri", [])
        if len(positions) % 3:
            raise ValueError(f"submesh {index} has a malformed position array")
        vertices = len(positions) // 3
        if len(normals) != vertices * 3 or len(tangents) != vertices * 4 or len(uvs) != vertices * 2:
            raise ValueError(f"submesh {index} vertex streams disagree")
        if len(triangles) % 3 or (triangles and max(int(value) for value in triangles) >= vertices):
            raise ValueError(f"submesh {index} has invalid triangle indices")
        if submesh.get("material.shader") != ["PdxMeshSnow"]:
            raise ValueError(f"submesh {index} has the wrong shader")
        diffuse = submesh.get("material.diff", [])
        if len(diffuse) != 1:
            raise ValueError(f"submesh {index} has no unique diffuse texture")
        parsed_textures.add(str(diffuse[0]))
        total_vertices += vertices
        total_triangles += len(triangles) // 3
    if parsed_textures != expected_textures:
        raise ValueError(f"diffuse texture set drifted: {parsed_textures} != {expected_textures}")
    return {
        "parsed_submeshes": len(meshes),
        "parsed_vertices": total_vertices,
        "parsed_triangles": total_triangles,
        "parsed_diffuse_textures": sorted(parsed_textures),
    }


def validate_outputs(mesh_path: Path, texture_paths: list[Path], ambient_path: Path) -> dict[str, object]:
    mesh = mesh_path.read_bytes()
    mesh_validation = validate_mesh_semantics(mesh)
    material_count = sum(1 for surface_name in MATERIALS if MATERIALS[surface_name].texture.encode("ascii") in mesh)
    if material_count != len(MATERIALS):
        raise ValueError(f"mesh references {material_count}/{len(MATERIALS)} diffuse textures")
    for texture_path in texture_paths:
        if not texture_path.read_bytes().startswith(b"DDS "):
            raise ValueError(f"invalid DDS header: {texture_path}")

    ambient_text = ambient_path.read_text("utf-8-sig")
    if ambient_text.count(MARKER_BEGIN) != 1 or ambient_text.count(MARKER_END) != 1:
        raise ValueError("Epang Palace ambient marker is missing or duplicated")
    if ambient_text.count("# GDD_B41_LUOYANG_PALACE_BEGIN") != 1:
        raise ValueError("the existing Luoyang palace ambient marker was not preserved")
    if ambient_text.count("{") != ambient_text.count("}"):
        raise ValueError("ambient_object.txt braces are unbalanced")
    return {
        "mesh_bytes": len(mesh),
        "material_count": material_count,
        "dds_count": len(texture_paths),
        "mesh_round_trip": mesh_validation,
        "ambient_marker_count": 1,
        "luoyang_marker_preserved": True,
        "ambient_braces_balanced": True,
    }


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    mod = repo / "guangdong_independent_practice"
    vanilla = args.vanilla_root.resolve()
    planning = repo / "planning/epang_palace_model"
    model_dir = mod / "gfx/models/Buildings"
    mesh_path = model_dir / "gdd_epang_palace.mesh"
    entity_path = mod / "gfx/entities/gdd_epang_palace.asset"
    gfx_path = mod / "interface/assets/gdd_epang_palace.gfx"
    ambient_path = mod / "map/ambient_object.txt"
    vanilla_ambient = vanilla / "map/ambient_object.txt"
    backup = planning / "backup/pre_b42_ambient_object.txt.gz"

    if not vanilla_ambient.exists():
        raise FileNotFoundError(f"vanilla ambient_object.txt not found: {vanilla_ambient}")

    locked_map_paths = [mod / "map/provinces.bmp", mod / "map/rivers.bmp", mod / "map/heightmap.bmp"]
    locked_map_hashes_before = {str(path.relative_to(repo)): sha256(path) for path in locked_map_paths}

    geometry = build_palace()
    bounds = combined_bounds(geometry.surfaces.values())
    if bounds[0][1] < 0.0:
        raise ValueError(f"model extends below the ground plane: {bounds}")
    placement_validation = validate_placement(mod, bounds)

    write_clausewitz_mesh(mesh_path, geometry.surfaces)
    texture_paths = build_textures(model_dir)
    atomic_write(
        gfx_path,
        b'''objectTypes = {\n\tpdxmesh = {\n\t\tname = "gdd_epang_palace_mesh"\n\t\tfile = "gfx/models/Buildings/gdd_epang_palace.mesh"\n\t\tscale = 1.0\n\t\tcull_distance = 700.0f\n\t}\n}\n''',
    )
    atomic_write(
        entity_path,
        b'''entity = {\n\tname = "gdd_epang_palace_entity"\n\tpdxmesh = "gdd_epang_palace_mesh"\n}\n''',
    )
    source_ambient_sha, ambient_marker_sha = update_ambient_object(ambient_path, vanilla_ambient, backup)

    preview_candidates = [
        planning / "source/gdd_epang_palace.blend",
        planning / "preview/gdd_epang_palace_preview.png",
        planning / "blender_build_stamp.json",
    ]
    preview_paths = [path for path in preview_candidates if path.exists()]
    if not args.skip_blender:
        if not args.blender.exists():
            raise FileNotFoundError(f"Blender executable not found: {args.blender}")
        preview_paths = render_with_blender(repo, args.blender.resolve(), planning, args.force_render)

    locked_map_hashes_after = {str(path.relative_to(repo)): sha256(path) for path in locked_map_paths}
    if locked_map_hashes_before != locked_map_hashes_after:
        raise RuntimeError("a locked map bitmap changed during the model transaction")
    output_validation = validate_outputs(mesh_path, texture_paths, ambient_path)

    geometry_summary = {
        "bounds": [list(bounds[0]), list(bounds[1])],
        "vertices": sum(surface.vertex_count for surface in geometry.surfaces.values()),
        "triangles": sum(surface.triangle_count for surface in geometry.surfaces.values()),
        "submeshes": sum(bool(surface.positions) for surface in geometry.surfaces.values()),
    }
    manifest = {
        "batch": BATCH,
        "purpose": "Add an original alternate-history completed Epang Palace ambient map model beside Xianyang.",
        "model_version": MODEL_VERSION,
        "province": {"id": PROVINCE_ID, "name": PROVINCE_NAME, "rgb": list(PROVINCE_RGB)},
        "placement": {"position": list(PLACEMENT), "rotation": list(ROTATION), "scale": AMBIENT_SCALE},
        "geometry": geometry_summary,
        "design_basis": {
            "archaeological_fact": "The identifying form is the excavated long rammed-earth front-hall terrace.",
            "interpretation": "The timber halls are an alternate-history completion based on Qin high-platform architecture.",
            "scale_reference": "Vanilla nammi2_forbidden_city uses ambient scale 0.35; Epang uses the same scale with a lower, wider silhouette.",
        },
        "map_policy": {
            "bitmap_changes": 0,
            "editable_pixel_mask": None,
            "locked_exterior": "All provinces.bmp pixels are locked; the transaction does not open the bitmap for writing.",
            "area_and_region": "unchanged",
            "gameplay_memberships": "unchanged",
            "history_policy": "Province histories are unchanged.",
            "localisation_policy": "No localisation keys are added or changed.",
        },
        "validation": {"placement": placement_validation, "outputs": output_validation},
        "locked_map_sha256": locked_map_hashes_after,
        "ambient_source_without_b42_sha256": source_ambient_sha,
        "ambient_marker_sha256": ambient_marker_sha,
        "backup": str(backup.relative_to(repo)),
        "preview": "planning/epang_palace_model/preview/gdd_epang_palace_preview.png",
    }
    manifest_path = planning / "batch_manifest.json"
    write_json(manifest_path, manifest)

    owned = [mesh_path, *texture_paths, entity_path, gfx_path, backup, manifest_path, *preview_paths]
    build_manifest_path = planning / "build_manifest.json"
    build_manifest = {
        "batch": BATCH,
        "files": {str(path.relative_to(repo)): sha256(path) for path in sorted(set(owned)) if path.exists()},
        "shared_files": {
            str(ambient_path.relative_to(repo)): {
                "policy": "shared-mutated; hash only the marker owned by this batch",
                "marker_sha256": ambient_marker_sha,
            }
        },
    }
    write_json(build_manifest_path, build_manifest)
    print(json.dumps(geometry_summary, indent=2))
    print(json.dumps(placement_validation, indent=2))
    print(f"ambient placement: {PLACEMENT}, province {PROVINCE_ID}")
    print(f"wrote {len(build_manifest['files']) + 1} owned files plus one shared ambient marker")


if __name__ == "__main__":
    main()
