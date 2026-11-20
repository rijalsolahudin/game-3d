"""Helper geometri audit: proyeksi lewat modul bersama geo.projection, ID chunk."""
from __future__ import annotations

import math

import shapely

from geo.projection import lonlat_to_utm, transformer_to_utm

CHUNK_M = 256.0  # ukuran chunk (domain.md)


def project(geom):
    """Geometri EPSG:4326 -> UTM 49S (meter), vektor lewat transformer bersama."""
    return shapely.transform(geom, transformer_to_utm().transform, interleaved=False)


def origin_utm(origin: dict) -> tuple[float, float]:
    return lonlat_to_utm(origin["lng"], origin["lat"])


def chunk_id(utm_x: float, utm_y: float, origin_xy: tuple[float, float], size: float = CHUNK_M) -> str:
    """ID chunk "{x}_{z}": x = timur, z = utara relatif origin, indeks = floor(m / size)."""
    return f"{math.floor((utm_x - origin_xy[0]) / size)}_{math.floor((utm_y - origin_xy[1]) / size)}"
