#!/usr/bin/env python3
"""Deterministic low-poly geometry for the Luoyang Sui-Tang palace map model.

The module has no Blender dependency.  The EU4 mesh builder and the Blender
preview builder both consume the same geometry so the editable preview cannot
silently drift away from the game-loaded asset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable


MODEL_VERSION = "GDD_B41_LUOYANG_PALACE_V1"


@dataclass(frozen=True)
class MaterialSpec:
    texture: str
    color: tuple[float, float, float, float]
    roughness: float


MATERIALS: dict[str, MaterialSpec] = {
    "stone": MaterialSpec("gdd_luoyang_stone_diffuse.dds", (0.59, 0.55, 0.47, 1.0), 0.88),
    "red": MaterialSpec("gdd_luoyang_red_diffuse.dds", (0.49, 0.16, 0.085, 1.0), 0.78),
    "wood": MaterialSpec("gdd_luoyang_wood_diffuse.dds", (0.24, 0.075, 0.035, 1.0), 0.72),
    "roof": MaterialSpec("gdd_luoyang_roof_diffuse.dds", (0.12, 0.16, 0.15, 1.0), 0.62),
    "earth": MaterialSpec("gdd_luoyang_earth_diffuse.dds", (0.48, 0.32, 0.18, 1.0), 0.92),
    "gold": MaterialSpec("gdd_luoyang_gold_diffuse.dds", (0.67, 0.43, 0.08, 1.0), 0.34),
    "dark": MaterialSpec("gdd_luoyang_dark_diffuse.dds", (0.055, 0.045, 0.035, 1.0), 0.74),
}


Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalise(v: Vec3) -> Vec3:
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length < 1e-9:
        raise ValueError("degenerate vector")
    return (v[0] / length, v[1] / length, v[2] / length)


@dataclass
class Surface:
    positions: list[float] = field(default_factory=list)
    normals: list[float] = field(default_factory=list)
    tangents: list[float] = field(default_factory=list)
    uvs: list[float] = field(default_factory=list)
    triangles: list[int] = field(default_factory=list)

    def add_triangle(
        self,
        a: Vec3,
        b: Vec3,
        c: Vec3,
        uv: tuple[Vec2, Vec2, Vec2] = ((0.08, 0.08), (0.92, 0.08), (0.92, 0.92)),
    ) -> None:
        normal = _normalise(_cross(_sub(b, a), _sub(c, a)))
        reference = (1.0, 0.0, 0.0) if abs(normal[1]) > 0.85 else (0.0, 1.0, 0.0)
        tangent = _normalise(_cross(reference, normal))
        start = len(self.positions) // 3
        for point, texcoord in zip((a, b, c), uv):
            self.positions.extend(point)
            self.normals.extend(normal)
            self.tangents.extend((*tangent, 1.0))
            self.uvs.extend(texcoord)
        self.triangles.extend((start, start + 1, start + 2))

    def add_quad(self, a: Vec3, b: Vec3, c: Vec3, d: Vec3) -> None:
        self.add_triangle(a, b, c, ((0.05, 0.05), (0.05, 0.95), (0.95, 0.95)))
        self.add_triangle(a, c, d, ((0.05, 0.05), (0.95, 0.95), (0.95, 0.05)))

    @property
    def vertex_count(self) -> int:
        return len(self.positions) // 3

    @property
    def triangle_count(self) -> int:
        return len(self.triangles) // 3

    def bounds(self) -> tuple[Vec3, Vec3]:
        xs = self.positions[0::3]
        ys = self.positions[1::3]
        zs = self.positions[2::3]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


class PalaceGeometry:
    def __init__(self) -> None:
        self.surfaces = {name: Surface() for name in MATERIALS}

    def surface(self, material: str) -> Surface:
        return self.surfaces[material]

    def box(self, material: str, x: float, y: float, z: float, width: float, height: float, depth: float) -> None:
        """Add a box using a bottom-centre position."""
        s = self.surface(material)
        x0, x1 = x - width / 2.0, x + width / 2.0
        y0, y1 = y, y + height
        z0, z1 = z - depth / 2.0, z + depth / 2.0
        s.add_quad((x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0))
        s.add_quad((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))
        s.add_quad((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0))
        s.add_quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
        s.add_quad((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0))
        s.add_quad((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))

    def rectangular_frustum(
        self,
        material: str,
        x: float,
        y: float,
        z: float,
        lower_width: float,
        lower_depth: float,
        upper_width: float,
        upper_depth: float,
        height: float,
    ) -> None:
        s = self.surface(material)
        lx0, lx1 = x - lower_width / 2.0, x + lower_width / 2.0
        lz0, lz1 = z - lower_depth / 2.0, z + lower_depth / 2.0
        ux0, ux1 = x - upper_width / 2.0, x + upper_width / 2.0
        uz0, uz1 = z - upper_depth / 2.0, z + upper_depth / 2.0
        y1 = y + height
        s.add_quad((lx0, y, lz0), (ux0, y1, uz0), (ux1, y1, uz0), (lx1, y, lz0))
        s.add_quad((lx1, y, lz1), (ux1, y1, uz1), (ux0, y1, uz1), (lx0, y, lz1))
        s.add_quad((lx0, y, lz1), (ux0, y1, uz1), (ux0, y1, uz0), (lx0, y, lz0))
        s.add_quad((lx1, y, lz0), (ux1, y1, uz0), (ux1, y1, uz1), (lx1, y, lz1))
        s.add_quad((ux0, y1, uz0), (ux0, y1, uz1), (ux1, y1, uz1), (ux1, y1, uz0))

    def cylinder(
        self,
        material: str,
        x: float,
        y: float,
        z: float,
        radius: float,
        height: float,
        sides: int = 12,
    ) -> None:
        s = self.surface(material)
        points = [
            (x + radius * math.cos(2.0 * math.pi * i / sides), z + radius * math.sin(2.0 * math.pi * i / sides))
            for i in range(sides)
        ]
        for i in range(sides):
            j = (i + 1) % sides
            p0, p1 = points[i], points[j]
            s.add_quad((p0[0], y, p0[1]), (p0[0], y + height, p0[1]), (p1[0], y + height, p1[1]), (p1[0], y, p1[1]))
            s.add_triangle((x, y + height, z), (p1[0], y + height, p1[1]), (p0[0], y + height, p0[1]))
            s.add_triangle((x, y, z), (p0[0], y, p0[1]), (p1[0], y, p1[1]))

    def conical_frustum(
        self,
        material: str,
        x: float,
        y: float,
        z: float,
        lower_radius: float,
        upper_radius: float,
        height: float,
        sides: int = 12,
    ) -> None:
        s = self.surface(material)
        lower = [
            (x + lower_radius * math.cos(2.0 * math.pi * i / sides), z + lower_radius * math.sin(2.0 * math.pi * i / sides))
            for i in range(sides)
        ]
        upper = [
            (x + upper_radius * math.cos(2.0 * math.pi * i / sides), z + upper_radius * math.sin(2.0 * math.pi * i / sides))
            for i in range(sides)
        ]
        for i in range(sides):
            j = (i + 1) % sides
            s.add_quad(
                (lower[i][0], y, lower[i][1]),
                (upper[i][0], y + height, upper[i][1]),
                (upper[j][0], y + height, upper[j][1]),
                (lower[j][0], y, lower[j][1]),
            )
            s.add_triangle((x, y + height, z), (upper[j][0], y + height, upper[j][1]), (upper[i][0], y + height, upper[i][1]))

    def stair(self, x: float, y: float, z: float, width: float, depth: float, height: float, steps: int = 4) -> None:
        for index in range(steps):
            step_depth = depth * (steps - index) / steps
            step_height = height / steps
            self.box("stone", x, y + index * step_height, z, width, step_height, step_depth)

    def hip_roof(self, x: float, y: float, z: float, width: float, depth: float, height: float = 0.28) -> None:
        self.box("wood", x, y - 0.055, z, width * 0.98, 0.06, depth * 0.98)
        self.rectangular_frustum("roof", x, y, z, width, depth, width * 0.37, depth * 0.25, height)
        self.box("gold", x, y + height - 0.018, z, width * 0.35, 0.035, 0.045)

    def pavilion(
        self,
        x: float,
        y: float,
        z: float,
        width: float,
        depth: float,
        wall_height: float,
        roof_height: float = 0.28,
        dark_panels: bool = True,
    ) -> float:
        self.box("stone", x, y, z, width * 0.94, 0.10, depth * 0.94)
        self.box("red", x, y + 0.10, z, width * 0.78, wall_height, depth * 0.72)
        self.box("wood", x, y + 0.10 + wall_height * 0.72, z, width * 0.86, 0.08, depth * 0.79)
        if dark_panels:
            panel_y = y + 0.18
            panel_height = max(0.12, wall_height * 0.45)
            self.box("dark", x, panel_y, z - depth * 0.365, width * 0.48, panel_height, 0.025)
            self.box("dark", x, panel_y, z + depth * 0.365, width * 0.48, panel_height, 0.025)
        roof_y = y + 0.10 + wall_height
        self.hip_roof(x, roof_y, z, width, depth, roof_height)
        return roof_y + roof_height

    def finial(self, x: float, y: float, z: float, height: float = 0.28) -> None:
        self.cylinder("gold", x, y, z, 0.055, height * 0.55, 8)
        self.conical_frustum("gold", x, y + height * 0.55, z, 0.11, 0.01, height * 0.45, 8)


def _build_yingtian_gate(model: PalaceGeometry) -> None:
    gate_z = -4.55
    model.box("stone", 0.0, 0.0, gate_z, 7.2, 0.16, 0.95)
    model.box("red", 0.0, 0.16, gate_z, 6.85, 0.66, 0.72)
    for x in (-0.72, 0.0, 0.72):
        model.box("dark", x, 0.17, gate_z - 0.375, 0.38, 0.47, 0.035)

    central_top = model.pavilion(0.0, 0.79, gate_z, 2.65, 1.42, 0.48, 0.30)
    model.finial(0.0, central_top, gate_z, 0.22)
    for x in (-2.45, 2.45):
        model.pavilion(x, 0.75, gate_z, 1.55, 1.22, 0.40, 0.25)

    # Projecting que towers make the silhouette unlike a straight Forbidden City gate.
    for x in (-3.35, 3.35):
        model.box("stone", x, 0.0, -4.05, 0.75, 0.18, 1.45)
        tower_top = model.pavilion(x, 0.18, -4.05, 1.08, 1.38, 0.50, 0.27)
        model.finial(x, tower_top, -4.05, 0.16)


def _build_walls_and_courtyard(model: PalaceGeometry) -> None:
    model.box("stone", 0.0, 0.0, -1.75, 0.74, 0.035, 5.2)
    model.box("stone", 0.0, 0.0, 3.15, 0.68, 0.035, 3.0)
    for x in (-3.48, 3.48):
        model.box("earth", x, 0.0, 0.10, 0.24, 0.38, 8.45)
        model.box("roof", x, 0.38, 0.10, 0.35, 0.10, 8.55)
    model.box("earth", 0.0, 0.0, 4.35, 6.95, 0.38, 0.24)
    model.box("roof", 0.0, 0.38, 4.35, 7.05, 0.10, 0.35)
    for x in (-3.36, 3.36):
        model.pavilion(x, 0.38, 4.28, 0.92, 0.92, 0.34, 0.20, dark_panels=False)
    for x in (-1.15, 1.15):
        model.cylinder("gold", x, 0.035, -1.60, 0.105, 0.18, 10)
        model.conical_frustum("gold", x, 0.215, -1.60, 0.16, 0.08, 0.10, 10)


def _build_mingtang(model: PalaceGeometry) -> None:
    x, z = 0.0, -0.10
    model.cylinder("stone", x, 0.02, z, 1.62, 0.12, 12)
    model.cylinder("stone", x, 0.14, z, 1.43, 0.11, 12)
    model.stair(x, 0.02, z - 1.67, 0.76, 0.58, 0.22, 4)
    model.cylinder("red", x, 0.25, z, 1.10, 0.55, 12)
    model.cylinder("wood", x, 0.66, z, 1.18, 0.12, 12)
    model.conical_frustum("roof", x, 0.80, z, 1.48, 0.78, 0.37, 12)
    model.cylinder("red", x, 1.17, z, 0.70, 0.43, 12)
    model.cylinder("wood", x, 1.47, z, 0.76, 0.10, 12)
    model.conical_frustum("roof", x, 1.60, z, 1.00, 0.11, 0.50, 12)
    model.finial(x, 2.10, z, 0.30)


def _build_tiantang(model: PalaceGeometry) -> None:
    x, z = 0.0, 3.18
    model.box("stone", x, 0.02, z, 2.35, 0.16, 2.05)
    level_y = 0.18
    widths = (1.92, 1.62, 1.34, 1.06)
    depths = (1.58, 1.36, 1.16, 0.94)
    for index, (width, depth) in enumerate(zip(widths, depths)):
        wall_height = 0.42 if index < 2 else 0.38
        top = model.pavilion(x, level_y, z, width, depth, wall_height, 0.24 - index * 0.015)
        level_y = top + 0.035
    model.finial(x, level_y, z, 0.32)


def build_palace() -> PalaceGeometry:
    model = PalaceGeometry()
    _build_yingtian_gate(model)
    _build_walls_and_courtyard(model)
    _build_mingtang(model)
    _build_tiantang(model)
    return model


def combined_bounds(surfaces: Iterable[Surface]) -> tuple[Vec3, Vec3]:
    active = [surface for surface in surfaces if surface.positions]
    mins, maxs = zip(*(surface.bounds() for surface in active))
    return (
        min(item[0] for item in mins),
        min(item[1] for item in mins),
        min(item[2] for item in mins),
    ), (
        max(item[0] for item in maxs),
        max(item[1] for item in maxs),
        max(item[2] for item in maxs),
    )


if __name__ == "__main__":
    palace = build_palace()
    bounds = combined_bounds(palace.surfaces.values())
    print(MODEL_VERSION)
    print("bounds", bounds)
    for name, surface in palace.surfaces.items():
        print(name, surface.vertex_count, surface.triangle_count)
