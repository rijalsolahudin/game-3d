"""Modul proyeksi bersama: WGS84 (EPSG:4326) <-> UTM 49S (EPSG:32749) <-> lokal.

Satu-satunya sumber kebenaran konversi koordinat dunia nyata -> game.
Semua skrip pipeline WAJIB memakai modul ini (jangan hitung proyeksi sendiri).

Konvensi lokal: x = timur, z = utara, 1 unit = 1 m, (0, 0) = origin
(`data/origin.json`). Lokal = UTM 49S dikurangi UTM origin (jarak grid UTM,
skala ~0.999945 terhadap jarak geodesik di Tumanggal; 0.9996 hanya di meridian tengah 111E).

Pemakaian cepat::

    from geo.projection import default_projection
    p = default_projection()               # origin dari data/origin.json
    x, z = p.to_local(lon, lat)            # titik tunggal
    xs, zs = p.to_local_array(lons, lats)  # numpy
    fc_local = p.geojson_to_local(fc)      # GeoJSON apa pun -> koordinat [x, z]
    lon, lat = p.to_lonlat(x, z)           # konversi balik
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import numpy as np
from pyproj import Transformer

WGS84 = "EPSG:4326"
UTM_49S = "EPSG:32749"

_PIPELINE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ORIGIN_PATH = _PIPELINE_DIR / "data" / "origin.json"
ORIGIN_SCHEMA_PATH = _PIPELINE_DIR / "schemas" / "origin.schema.json"

_to_utm = Transformer.from_crs(WGS84, UTM_49S, always_xy=True)
_to_wgs = Transformer.from_crs(UTM_49S, WGS84, always_xy=True)


# --- konversi dasar (kompatibel dengan GAME-5) -------------------------------

def lonlat_to_utm(lon: float, lat: float) -> tuple[float, float]:
    return _to_utm.transform(lon, lat)


def utm_to_lonlat(x: float, y: float) -> tuple[float, float]:
    return _to_wgs.transform(x, y)


def lonlat_to_local(lon: float, lat: float, origin_lon: float, origin_lat: float) -> tuple[float, float]:
    """Koordinat lokal game (x = timur, z = utara, meter) relatif origin."""
    return LocalProjection(origin_lon, origin_lat).to_local(lon, lat)


def transformer_to_utm() -> Transformer:
    """Transformer always_xy (lon,lat -> x,y) untuk shapely.ops.transform."""
    return _to_utm


def transformer_to_wgs() -> Transformer:
    """Transformer always_xy (x,y -> lon,lat) untuk shapely.ops.transform."""
    return _to_wgs


# --- origin ------------------------------------------------------------------

class OriginError(ValueError):
    """origin.json tidak sesuai skema."""


class SchemaError(ValueError):
    """Skema memuat keyword/type di luar subset yang didukung validator ini."""


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


_JSON_TYPES: dict[str, Callable[[Any], bool]] = {
    "number": lambda v: _is_number(v) and math.isfinite(v),  # NaN/Infinity ditolak
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
}
_SUPPORTED_KEYWORDS = {
    "$schema", "title", "description", "type", "required", "properties", "const", "minimum", "maximum",
}  # fmt: skip


def _check_schema_subset(schema: dict, where: str = "skema") -> None:
    unknown = set(schema) - _SUPPORTED_KEYWORDS
    if unknown:
        raise SchemaError(f"{where}: keyword tidak didukung validator: {sorted(unknown)}")
    if "type" in schema and schema["type"] not in _JSON_TYPES:
        raise SchemaError(f"{where}: type tidak didukung: {schema['type']!r}")
    for key, rule in schema.get("properties", {}).items():
        _check_schema_subset(rule, f"{where}.properties.{key}")


def validate_origin(data: Any, schema_path: Path = ORIGIN_SCHEMA_PATH) -> None:
    """Validasi origin terhadap `schemas/origin.schema.json`.

    Subset didukung: type (number/integer/string/boolean/object/array), required, properties, const,
    minimum, maximum. Keyword/type lain di skema melempar SchemaError (tidak diabaikan diam-diam).
    """
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    _check_schema_subset(schema)
    if not isinstance(data, dict):
        raise OriginError("origin harus berupa object")
    for key in schema.get("required", []):
        if key not in data:
            raise OriginError(f"origin: field wajib '{key}' tidak ada")
    for key, rule in schema.get("properties", {}).items():
        if key not in data:
            continue
        value = data[key]
        expected = rule.get("type")
        if expected and not _JSON_TYPES[expected](value):
            raise OriginError(f"origin.{key} harus bertipe {expected} (dan terhingga bila number)")
        if "const" in rule and value != rule["const"]:
            raise OriginError(f"origin.{key} harus {rule['const']!r}, dapat {value!r}")
        if "minimum" in rule and value < rule["minimum"]:
            raise OriginError(f"origin.{key}={value} di bawah minimum {rule['minimum']}")
        if "maximum" in rule and value > rule["maximum"]:
            raise OriginError(f"origin.{key}={value} di atas maksimum {rule['maximum']}")


def load_origin(path: Path | str = DEFAULT_ORIGIN_PATH) -> tuple[float, float]:
    """Baca origin (lng, lat) dari origin.json setelah validasi skema."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_origin(data)
    return float(data["lng"]), float(data["lat"])


# --- proyeksi lokal ----------------------------------------------------------

Coord = Callable[[float, float], tuple[float, float]]


@dataclass(frozen=True)
class LocalProjection:
    """Proyeksi lon/lat <-> lokal game relatif satu origin."""

    origin_lon: float
    origin_lat: float

    @property
    def origin_utm(self) -> tuple[float, float]:
        return _to_utm.transform(self.origin_lon, self.origin_lat)

    # titik tunggal
    def to_local(self, lon: float, lat: float) -> tuple[float, float]:
        """(lon, lat) -> (x timur, z utara) dalam meter."""
        ox, oy = self.origin_utm
        x, y = _to_utm.transform(lon, lat)
        return x - ox, y - oy

    def to_lonlat(self, x: float, z: float) -> tuple[float, float]:
        """(x timur, z utara) meter -> (lon, lat)."""
        ox, oy = self.origin_utm
        return _to_wgs.transform(x + ox, z + oy)

    # array numpy
    def to_local_array(self, lon, lat) -> tuple[np.ndarray, np.ndarray]:
        ox, oy = self.origin_utm
        x, y = _to_utm.transform(np.asarray(lon, dtype=float), np.asarray(lat, dtype=float))
        return np.asarray(x) - ox, np.asarray(y) - oy

    def to_lonlat_array(self, x, z) -> tuple[np.ndarray, np.ndarray]:
        ox, oy = self.origin_utm
        lon, lat = _to_wgs.transform(np.asarray(x, dtype=float) + ox, np.asarray(z, dtype=float) + oy)
        return np.asarray(lon), np.asarray(lat)

    # GeoJSON
    def geojson_to_local(self, obj: dict) -> dict:
        """GeoJSON (lon/lat) -> salinan dengan koordinat lokal [x, z] (nilai ke-3 dipertahankan)."""
        return _map_geojson(obj, self.to_local)

    def geojson_to_lonlat(self, obj: dict) -> dict:
        """GeoJSON koordinat lokal [x, z] -> salinan dengan [lon, lat]."""
        return _map_geojson(obj, self.to_lonlat)


@lru_cache(maxsize=None)
def default_projection(origin_path: Path | str = DEFAULT_ORIGIN_PATH) -> LocalProjection:
    """Proyeksi dengan origin dari `data/origin.json` (divalidasi skema)."""
    lon, lat = load_origin(origin_path)
    return LocalProjection(lon, lat)


# --- GeoJSON -----------------------------------------------------------------

_GEOMETRY_TYPES = {"Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}


def _map_position(pos: Any, fn: Coord) -> list:
    if not isinstance(pos, (list, tuple)) or len(pos) not in (2, 3):
        raise ValueError(f"posisi GeoJSON harus list/tuple 2 atau 3 angka: {pos!r}")
    if not all(_is_number(v) and math.isfinite(v) for v in pos):
        raise ValueError(f"posisi GeoJSON harus berisi angka (bukan bool/string) yang terhingga: {pos!r}")
    a, b = fn(pos[0], pos[1])
    return [a, b, *pos[2:]]


def _map_coords(coords: Any, fn: Coord) -> Any:
    if not isinstance(coords, (list, tuple)):
        raise ValueError(f"coordinates GeoJSON harus list/tuple, dapat {type(coords).__name__}: {coords!r}")
    if coords and not isinstance(coords[0], (list, tuple)):
        return _map_position(coords, fn)
    return [_map_coords(c, fn) for c in coords]


def _map_geometry(geom: dict | None, fn: Coord) -> dict | None:
    if geom is None:
        return None
    gtype = geom.get("type")
    out = copy.deepcopy(geom)
    if gtype == "GeometryCollection":
        out["geometries"] = [_map_geometry(g, fn) for g in geom["geometries"]]
        return out
    if gtype not in _GEOMETRY_TYPES:
        raise ValueError(f"tipe geometri tidak dikenal: {gtype!r}")
    out["coordinates"] = _map_coords(geom["coordinates"], fn)
    return out


def _map_geojson(obj: dict, fn: Coord) -> dict:
    """Terapkan fn(a, b) -> (a', b') ke semua koordinat; input tidak diubah."""
    gtype = obj.get("type")
    if gtype == "FeatureCollection":
        out = copy.deepcopy(obj)
        out["features"] = [_map_geojson(f, fn) for f in obj["features"]]
        return out
    if gtype == "Feature":
        out = copy.deepcopy(obj)
        out["geometry"] = _map_geometry(obj.get("geometry"), fn)
        return out
    return _map_geometry(obj, fn)
