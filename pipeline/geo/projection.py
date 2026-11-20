"""Modul proyeksi bersama: WGS84 (EPSG:4326) <-> UTM 49S (EPSG:32749) <-> lokal.

Semua skrip pipeline WAJIB memakai modul ini untuk konversi koordinat.
"""
from __future__ import annotations

from pyproj import Transformer

WGS84 = "EPSG:4326"
UTM_49S = "EPSG:32749"

_to_utm = Transformer.from_crs(WGS84, UTM_49S, always_xy=True)
_to_wgs = Transformer.from_crs(UTM_49S, WGS84, always_xy=True)


def lonlat_to_utm(lon: float, lat: float) -> tuple[float, float]:
    return _to_utm.transform(lon, lat)


def utm_to_lonlat(x: float, y: float) -> tuple[float, float]:
    return _to_wgs.transform(x, y)


def lonlat_to_local(lon: float, lat: float, origin_lon: float, origin_lat: float) -> tuple[float, float]:
    """Koordinat lokal game (x = timur, z = utara, meter) relatif origin."""
    x, y = lonlat_to_utm(lon, lat)
    ox, oy = lonlat_to_utm(origin_lon, origin_lat)
    return x - ox, y - oy


def transformer_to_utm() -> Transformer:
    """Transformer always_xy (lon,lat -> x,y) untuk shapely.ops.transform."""
    return _to_utm


def transformer_to_wgs() -> Transformer:
    """Transformer always_xy (x,y -> lon,lat) untuk shapely.ops.transform."""
    return _to_wgs
