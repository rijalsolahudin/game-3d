"""Geometri ekspor: pembulatan, pemotongan polyline/polygon tepat di garis batas chunk, orientasi ring."""
from __future__ import annotations

import itertools
import math

import shapely
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient

from geo.chunks import chunk_coords

Point = tuple[float, float]


def rnd(v: float, decimals: int) -> float:
    return round(float(v), decimals) + 0.0  # +0.0 menghilangkan -0.0


def to_local_geom(proj, geom):
    """Geometri shapely lon/lat -> lokal lewat modul proyeksi bersama."""
    return shapely.transform(geom, proj.to_local_array, interleaved=False)


def _dedupe(points: list[Point]) -> list[Point]:
    out: list[Point] = []
    for p in points:
        if not out or out[-1] != p:
            out.append(p)
    return out


def _segment_cuts(a: Point, b: Point, size: int, decimals: int) -> list[Point]:
    """Titik potong segmen a-b dengan garis grid x=k*size dan z=k*size, terurut dari a ke b."""
    cuts: list[tuple[float, Point]] = []
    for axis in (0, 1):
        lo, hi = sorted((a[axis], b[axis]))
        if lo == hi:
            continue
        for k in range(math.floor(lo / size) + 1, math.ceil(hi / size)):
            line = float(k * size)
            if not lo < line < hi:
                continue
            t = (line - a[axis]) / (b[axis] - a[axis])
            val = rnd(a[1 - axis] + t * (b[1 - axis] - a[1 - axis]), decimals)
            cuts.append((t, (line, val) if axis == 0 else (val, line)))
    return [p for _, p in sorted(cuts)]


def split_polyline(points, size: int, decimals: int) -> list[dict]:
    """Bulatkan lalu potong polyline di garis batas chunk.

    Titik potong dihitung sekali dan dipakai sebagai ujung bersama potongan sebelum dan sesudahnya,
    jadi identik di kedua chunk. Kembalian: [{"chunk": (cx, cz), "points": [...]}] berurutan sepanjang garis.
    """
    pts = _dedupe([(rnd(x, decimals), rnd(z, decimals)) for x, z in points])
    if len(pts) < 2:
        return []
    nodes: list[Point] = [pts[0]]
    for a, b in itertools.pairwise(pts):
        nodes.extend(_segment_cuts(a, b, size, decimals))
        nodes.append(b)
    nodes = _dedupe(nodes)
    pieces: list[dict] = []
    for a, b in itertools.pairwise(nodes):
        key = chunk_coords((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, size)
        if pieces and pieces[-1]["chunk"] == key:
            pieces[-1]["points"].append(b)
        else:
            pieces.append({"chunk": key, "points": [a, b]})
    return pieces


def polyline_length(points) -> float:
    return sum(math.dist(a, b) for a, b in itertools.pairwise(points))


def flatten_polygons(geom) -> list[Polygon]:
    """Semua Polygon di dalam geometri apa pun (garis/titik diabaikan)."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if hasattr(geom, "geoms"):
        out: list[Polygon] = []
        for g in geom.geoms:
            out.extend(flatten_polygons(g))
        return out
    return []


def split_polygon(poly: Polygon, size: int, decimals: int, min_area: float):
    """Potong polygon per chunk. Kembalian: ([((cx, cz), polygon)] terurut, jumlah sisa terlalu kecil yang dibuang)."""
    minx, minz, maxx, maxz = poly.bounds
    out, dropped = [], 0
    for cx in range(math.floor(minx / size), math.floor(maxx / size) + 1):
        for cz in range(math.floor(minz / size), math.floor(maxz / size) + 1):
            piece = poly.intersection(box(cx * size, cz * size, (cx + 1) * size, (cz + 1) * size))
            for part in flatten_polygons(piece):
                for p in flatten_polygons(shapely.set_precision(part, 10.0 ** -decimals)):
                    if p.area < min_area:
                        dropped += 1
                    else:
                        out.append(((cx, cz), p))
    return out, dropped


def rings_of(poly: Polygon, decimals: int) -> list[list[list[float]]]:
    """Ring luar CCW lalu lubang CW; tanpa titik penutup (titik awal tidak diulang)."""
    poly = orient(poly, 1.0)
    return [[[rnd(x, decimals), rnd(z, decimals)] for x, z in list(r.coords)[:-1]]
            for r in (poly.exterior, *poly.interiors)]
