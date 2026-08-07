#!/usr/bin/env python3
"""Deterministic low-poly geometry for the Qin Epang Palace map model.

The real Epang Palace front-hall project never reached a completed palace
state.  This model is therefore an alternate-history completion grounded in
the excavated long rammed-earth terrace and comparable Qin high-platform
architecture.  Blender previews and the EU4 mesh exporter consume this same
geometry so they cannot silently drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable


MODEL_VERSION = "GDD_B42_EPANG_PALACE_V1"


@dataclass(frozen=True)
class MaterialSpec:
    texture: str
    color: tuple[float, float, float, float]
    roughness: float


MATERIALS: dict[str, MaterialSpec] = {
    "earth": MaterialSpec("gdd_epang_earth_diffuse.dds", (0.47, 0.30, 0.145, 1.0), 0.94),
    "stone": MaterialSpec("gdd_epang_stone_diffuse.dds", (0.50, 0.46, 0.38, 1.0), 0.90),
    "red": MaterialSpec("gdd_epang_red_diffuse.dds", (0.43, 0.105, 0.050, 1.0), 0.80),
    "wood": MaterialSpec("gdd_epang_wood_diffuse.dds", (0.19, 0.050, 0.022, 1.0), 0.76),
    "roof": MaterialSpec("gdd_epang_roof_diffuse.dds", (0.095, 0.115, 0.105, 1.0), 0.68),
    "dark": MaterialSpec("gdd_epang_dark_diffuse.dds", (0.038, 0.030, 0.023, 1.0), 0.78),
    "bronze": MaterialSpec("gdd_epang_bronze_diffuse.dds", (0.27, 0.19, 0.075, 1.0), 0.48),
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

    def box(
        self,
        material: str,
        x: float,
        y: float,
        z: float,
        width: float,
        height: float,
        depth: float,
    ) -> None:
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
        sides: int = 8,
    ) -> None:
        s = self.surface(material)
        points = [
            (x + radius * math.cos(2.0 * math.pi * i / sides), z + radius * math.sin(2.0 * math.pi * i / sides))
            for i in range(sides)
        ]
        for i in range(sides):
            j = (i + 1) % sides
            p0, p1 = points[i], points[j]
            s.add_quad(
                (p0[0], y, p0[1]),
                (p0[0], y + height, p0[1]),
                (p1[0], y + height, p1[1]),
                (p1[0], y, p1[1]),
            )
            s.add_triangle((x, y + height, z), (p1[0], y + height, p1[1]), (p0[0], y + height, p0[1]))
            s.add_triangle((x, y, z), (p0[0], y, p0[1]), (p1[0], y, p1[1]))

    def hip_roof(
        self,
        x: float,
        y: float,
        z: float,
        width: float,
        depth: float,
        height: float,
    ) -> float:
        self.box("wood", x, y - 0.055, z, width * 0.99, 0.065, depth * 0.99)
        self.rectangular_frustum("roof", x, y, z, width, depth, width * 0.34, depth * 0.24, height)
        self.box("dark", x, y + height - 0.012, z, width * 0.34, 0.045, 0.055)
        return y + height

    def column_row(
        self,
        x: float,
        y: float,
        z: float,
        width: float,
        height: float,
        count: int,
        radius: float = 0.055,
    ) -> None:
        if count < 2:
            raise ValueError("a column row needs at least two columns")
        for index in range(count):
            column_x = x - width / 2.0 + width * index / (count - 1)
            self.cylinder("red", column_x, y, z, radius, height, 8)

    def open_hall(
        self,
        x: float,
        y: float,
        z: float,
        width: float,
        depth: float,
        wall_height: float,
        roof_height: float,
        columns: int,
        inner_width: float = 0.76,
    ) -> float:
        self.box("stone", x, y, z, width * 0.95, 0.095, depth * 0.90)
        body_y = y + 0.095
        self.box("dark", x, body_y + 0.04, z, width * inner_width, wall_height * 0.76, depth * 0.52)
        row_width = width * 0.82
        for row_z in (z - depth * 0.34, z + depth * 0.34):
            self.column_row(x, body_y, row_z, row_width, wall_height, columns)
        self.box("wood", x, body_y + wall_height * 0.78, z, width * 0.90, 0.09, depth * 0.80)
        roof_y = body_y + wall_height
        return self.hip_roof(x, roof_y, z, width, depth, roof_height)

    def closed_pavilion(
        self,
        x: float,
        y: float,
        z: float,
        width: float,
        depth: float,
        wall_height: float,
        roof_height: float,
    ) -> float:
        self.box("stone", x, y, z, width * 0.94, 0.085, depth * 0.90)
        self.box("red", x, y + 0.085, z, width * 0.76, wall_height, depth * 0.64)
        self.box("dark", x, y + 0.14, z - depth * 0.33, width * 0.46, wall_height * 0.58, 0.025)
        self.box("wood", x, y + wall_height * 0.77, z, width * 0.86, 0.075, depth * 0.74)
        return self.hip_roof(x, y + 0.085 + wall_height, z, width, depth, roof_height)

    def front_stair(
        self,
        x: float,
        y: float,
        platform_front_z: float,
        width: float,
        depth: float,
        height: float,
        steps: int,
    ) -> None:
        for index in range(steps):
            remaining_depth = depth * (steps - index) / steps
            step_height = height / steps
            centre_z = platform_front_z - remaining_depth / 2.0
            self.box("stone", x, y + index * step_height, centre_z, width, step_height, remaining_depth)


def _build_terrace(model: PalaceGeometry) -> None:
    # The nearly 3:1 platform is the archaeologically grounded identifying form.
    model.rectangular_frustum("earth", 0.0, 0.0, 0.0, 12.8, 4.45, 12.05, 3.82, 0.50)
    model.box("earth", 0.0, 0.50, 0.0, 12.05, 0.13, 3.82)
    model.box("stone", 0.0, 0.63, 0.05, 10.95, 0.095, 3.18)

    # Thin retaining courses make the massive rammed-earth base legible at map scale.
    for z in (-1.87, 1.87):
        model.box("stone", 0.0, 0.48, z, 11.76, 0.075, 0.075)
    for x in (-5.98, 5.98):
        model.box("stone", x, 0.48, 0.0, 0.075, 0.075, 3.64)

    model.front_stair(0.0, 0.0, -2.20, 2.55, 1.55, 0.72, 7)
    for x in (-4.72, 4.72):
        model.front_stair(x, 0.0, -2.18, 0.92, 0.82, 0.67, 5)


def _build_front_hall(model: PalaceGeometry) -> None:
    platform_y = 0.725
    # Wide lower hall and a narrower upper storey form a Qin-style high-platform silhouette.
    model.open_hall(0.0, platform_y, 0.02, 6.35, 2.12, 0.58, 0.29, 11)
    model.box("stone", 0.0, 1.48, 0.08, 3.72, 0.075, 1.46)
    upper_top = model.open_hall(0.0, 1.555, 0.08, 3.88, 1.56, 0.42, 0.245, 7, inner_width=0.70)

    # A restrained bronze ridge cap reads at distance without introducing Ming yellow roofs.
    for x in (-0.34, 0.0, 0.34):
        model.cylinder("bronze", x, upper_top - 0.005, 0.08, 0.035, 0.12, 8)

    # Low wings keep the footprint monumental and horizontal.
    for x in (-4.35, 4.35):
        model.open_hall(x, platform_y, 0.12, 2.32, 1.55, 0.43, 0.225, 5, inner_width=0.68)


def _build_galleries_and_que(model: PalaceGeometry) -> None:
    platform_y = 0.725
    # Rear gallery gives the visible repeated pillar rhythm documented at Qin high-platform sites.
    model.open_hall(0.0, platform_y, 1.43, 9.20, 0.62, 0.30, 0.145, 15, inner_width=0.84)

    # Small southern que pavilions frame the processional stair without forming a dense palace city.
    for x in (-4.86, 4.86):
        top = model.closed_pavilion(x, platform_y, -1.22, 1.08, 1.04, 0.40, 0.22)
        model.cylinder("bronze", x, top - 0.006, -1.22, 0.035, 0.10, 8)

    # Short return galleries connect the outer towers visually to the main wings.
    for x in (-5.18, 5.18):
        model.box("stone", x, platform_y, -0.20, 0.60, 0.08, 1.36)
        for z in (-0.70, -0.25, 0.20):
            model.cylinder("red", x, platform_y + 0.08, z, 0.050, 0.31, 8)
        model.box("wood", x, platform_y + 0.35, -0.22, 0.66, 0.055, 1.48)
        model.rectangular_frustum("roof", x, platform_y + 0.405, -0.22, 0.76, 1.58, 0.30, 0.56, 0.15)


def build_palace() -> PalaceGeometry:
    model = PalaceGeometry()
    _build_terrace(model)
    _build_front_hall(model)
    _build_galleries_and_que(model)
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
