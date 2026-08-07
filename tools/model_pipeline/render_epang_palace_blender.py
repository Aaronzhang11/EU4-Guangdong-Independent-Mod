#!/usr/bin/env python3
"""Build the editable Blender source and render the Epang Palace preview."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from epang_palace_geometry import MATERIALS, build_palace  # noqa: E402


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--preview", required=True, type=Path)
    return parser.parse_args(argv)


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_material(name: str) -> bpy.types.Material:
    spec = MATERIALS[name]
    material = bpy.data.materials.new(name=f"GDD_Epang_{name}")
    material.diffuse_color = spec.color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = spec.color
    shader.inputs["Roughness"].default_value = spec.roughness
    if name == "bronze":
        shader.inputs["Metallic"].default_value = 0.58
    return material


def build_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)

    palace = build_palace()
    collection = bpy.data.collections.new("GDD Epang Palace")
    bpy.context.scene.collection.children.link(collection)
    materials = {name: create_material(name) for name in MATERIALS}

    for name, surface in palace.surfaces.items():
        if not surface.positions:
            continue
        # Clausewitz is Y-up; Blender is Z-up.
        vertices = [
            (surface.positions[index], surface.positions[index + 2], surface.positions[index + 1])
            for index in range(0, len(surface.positions), 3)
        ]
        faces = [tuple(surface.triangles[index : index + 3]) for index in range(0, len(surface.triangles), 3)]
        mesh = bpy.data.meshes.new(f"gdd_epang_{name}_mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(materials[name])
        mesh.update()
        obj = bpy.data.objects.new(f"gdd_epang_{name}", mesh)
        collection.objects.link(obj)

    ground_material = bpy.data.materials.new("GDD_Epang_preview_ground")
    ground_material.diffuse_color = (0.29, 0.22, 0.14, 1.0)
    ground_material.use_nodes = True
    ground_shader = ground_material.node_tree.nodes.get("Principled BSDF")
    ground_shader.inputs["Base Color"].default_value = (0.29, 0.22, 0.14, 1.0)
    ground_shader.inputs["Roughness"].default_value = 0.98
    bpy.ops.mesh.primitive_plane_add(size=26.0, location=(0.0, 0.0, -0.018))
    ground = bpy.context.object
    ground.name = "Preview ground (not exported to EU4)"
    ground.data.materials.append(ground_material)

    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.045, 0.052, 0.055, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.38

    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = 2.35
    sun_data.angle = math.radians(22.0)
    sun = bpy.data.objects.new("Sun", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(31.0), math.radians(-19.0), math.radians(-38.0))

    fill_data = bpy.data.lights.new("Fill", type="AREA")
    fill_data.energy = 700.0
    fill_data.shape = "DISK"
    fill_data.size = 9.0
    fill = bpy.data.objects.new("Fill", fill_data)
    bpy.context.scene.collection.objects.link(fill)
    fill.location = (-8.5, -6.0, 10.5)
    look_at(fill, (0.0, 0.0, 0.9))

    rim_data = bpy.data.lights.new("Rim", type="AREA")
    rim_data.energy = 420.0
    rim_data.size = 7.0
    rim = bpy.data.objects.new("Rim", rim_data)
    bpy.context.scene.collection.objects.link(rim)
    rim.location = (8.0, 5.5, 7.5)
    look_at(rim, (0.0, 0.0, 1.0))

    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (13.6, -16.8, 11.8)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 16.3
    look_at(camera, (0.0, 0.0, 0.92))
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"


def main() -> None:
    args = parse_args()
    args.blend.parent.mkdir(parents=True, exist_ok=True)
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    build_scene()
    bpy.context.scene.render.filepath = str(args.preview)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend))
    bpy.ops.render.render(write_still=True)
    print(f"saved blend: {args.blend}")
    print(f"saved preview: {args.preview}")


if __name__ == "__main__":
    main()
