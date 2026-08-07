#!/usr/bin/env python3
"""Build and install the B41 Luoyang Sui-Tang palace ambient map model.

This transaction intentionally changes no province pixels or gameplay data.  It
creates a deterministic Clausewitz mesh, its materials and entity declarations,
then appends one marker-owned object to a vanilla-derived ambient_object.txt.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from luoyang_palace_geometry import MATERIALS, MODEL_VERSION, Surface, build_palace, combined_bounds  # noqa: E402


BATCH = "GDD_B41_LUOYANG_PALACE"
MARKER_BEGIN = f"# {BATCH}_BEGIN"
MARKER_END = f"# {BATCH}_END"
PROVINCE_ID = 1836
PROVINCE_RGB = (208, 130, 79)
PLACEMENT = (4550.0, 0.04, 1215.0)
ROTATION = (0.0, -18.0, 0.0)
AMBIENT_SCALE = 0.27


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
    payload += encode_object("gdd_luoyang_palace_shape", 2)
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
        payload += encode_property("n", ["gdd_luoyang_flat_normal.dds"])
        payload += encode_property("spec", ["gdd_luoyang_flat_spec.dds"])
    payload += encode_object("locator", 1)
    atomic_write(path, bytes(payload))


def texture_pixels(name: str, size: int = 64) -> bytes:
    base = tuple(round(channel * 255) for channel in MATERIALS[name].color[:3])
    result = bytearray()
    for y in range(size):
        for x in range(size):
            if name == "roof":
                delta = 13 if x % 8 in (0, 1) else -4
            elif name == "stone":
                delta = ((x * 13 + y * 7) % 17) - 8
            elif name in ("red", "wood"):
                delta = 9 if x % 16 in (0, 1) else ((y * 3 + x) % 7) - 3
            elif name == "earth":
                delta = ((x * 5 + y * 11) % 13) - 6
            elif name == "gold":
                delta = 14 if (x + y) % 16 < 3 else -2
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
    normal = model_dir / "gdd_luoyang_flat_normal.dds"
    specular = model_dir / "gdd_luoyang_flat_spec.dds"
    write_uncompressed_dds(normal, 4, 4, bytes((255, 128, 128, 255)) * 16)
    write_uncompressed_dds(specular, 4, 4, bytes((0, 24, 0, 255)) * 16)
    outputs.extend((normal, specular))
    return outputs


def ambient_block() -> str:
    return f"""{MARKER_BEGIN}
type={{
\ttype=\"gdd_luoyang_palace_entity\"
\tuse_animation=no
\tscale={AMBIENT_SCALE:.6f}
\ttime_duration=300.000000
\tobject={{
\t\tname=\"gdd_luoyang_palace\"
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
    preview = planning / "preview/gdd_luoyang_palace_preview.png"
    blend = planning / "source/gdd_luoyang_palace.blend"
    stamp_path = planning / "blender_build_stamp.json"
    renderer = repo / "tools/model_pipeline/render_luoyang_palace_blender.py"
    geometry = repo / "tools/model_pipeline/luoyang_palace_geometry.py"
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


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    mod = repo / "guangdong_independent_practice"
    vanilla = args.vanilla_root.resolve()
    planning = repo / "planning/luoyang_palace_model"
    model_dir = mod / "gfx/models/Buildings"
    mesh_path = model_dir / "gdd_luoyang_palace.mesh"
    entity_path = mod / "gfx/entities/gdd_luoyang_palace.asset"
    gfx_path = mod / "interface/assets/gdd_luoyang_palace.gfx"
    ambient_path = mod / "map/ambient_object.txt"
    vanilla_ambient = vanilla / "map/ambient_object.txt"
    backup = planning / "backup/pre_b41_ambient_object.txt.gz"

    if not vanilla_ambient.exists():
        raise FileNotFoundError(f"vanilla ambient_object.txt not found: {vanilla_ambient}")
    geometry = build_palace()
    bounds = combined_bounds(geometry.surfaces.values())
    write_clausewitz_mesh(mesh_path, geometry.surfaces)
    texture_paths = build_textures(model_dir)

    atomic_write(
        gfx_path,
        b'''objectTypes = {\n\tpdxmesh = {\n\t\tname = "gdd_luoyang_palace_mesh"\n\t\tfile = "gfx/models/Buildings/gdd_luoyang_palace.mesh"\n\t\tscale = 1.0\n\t\tcull_distance = 700.0f\n\t}\n}\n''',
    )
    atomic_write(
        entity_path,
        b'''entity = {\n\tname = "gdd_luoyang_palace_entity"\n\tpdxmesh = "gdd_luoyang_palace_mesh"\n}\n''',
    )
    source_ambient_sha, ambient_marker_sha = update_ambient_object(ambient_path, vanilla_ambient, backup)

    preview_candidates = [
        planning / "source/gdd_luoyang_palace.blend",
        planning / "preview/gdd_luoyang_palace_preview.png",
        planning / "blender_build_stamp.json",
    ]
    preview_paths = [path for path in preview_candidates if path.exists()]
    if not args.skip_blender:
        if not args.blender.exists():
            raise FileNotFoundError(f"Blender executable not found: {args.blender}")
        preview_paths = render_with_blender(repo, args.blender.resolve(), planning, args.force_render)

    manifest = {
        "batch": BATCH,
        "purpose": "Add an original Sui-Tang Luoyang palace ambient map model.",
        "model_version": MODEL_VERSION,
        "province": {"id": PROVINCE_ID, "name": "Luoyang", "rgb": list(PROVINCE_RGB)},
        "placement": {"position": list(PLACEMENT), "rotation": list(ROTATION), "scale": AMBIENT_SCALE},
        "geometry": {
            "bounds": [list(bounds[0]), list(bounds[1])],
            "vertices": sum(surface.vertex_count for surface in geometry.surfaces.values()),
            "triangles": sum(surface.triangle_count for surface in geometry.surfaces.values()),
        },
        "map_policy": {
            "bitmap_changes": 0,
            "editable_pixel_mask": None,
            "locked_exterior": "All provinces.bmp pixels are locked; the transaction does not open the bitmap.",
            "area": "chengzhou_area (unchanged)",
            "region": "zhongyuan_region (unchanged)",
            "gameplay_memberships": "unchanged",
            "history_policy": "Province 1836 history is unchanged.",
            "localisation_policy": "No localisation keys are added or changed.",
        },
        "ambient_source_sha256": source_ambient_sha,
        "ambient_marker_sha256": ambient_marker_sha,
        "backup": str(backup.relative_to(repo)),
        "preview": "planning/luoyang_palace_model/preview/gdd_luoyang_palace_preview.png",
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
    print(json.dumps(manifest["geometry"], indent=2))
    print(f"ambient placement: {PLACEMENT}, province {PROVINCE_ID}")
    print(f"wrote {len(build_manifest['files']) + 1} owned files")


if __name__ == "__main__":
    main()
