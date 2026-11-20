"""Baca DEM GeoTIFF (CRS apa pun) dan sampel pada lattice lokal dengan interpolasi bikubik.

Konversi lokal -> lon/lat lewat `geo.projection` (modul bersama). Bila CRS DEM bukan
EPSG:4326, lon/lat diteruskan ke CRS DEM dengan pyproj (itu CRS data sumber, bukan proyeksi game).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer

from geo.projection import WGS84, LocalProjection

_HASH_BLOCK = 1024 * 1024


class CoverageError(RuntimeError):
    """Lattice keluar dari DEM atau menyentuh nodata."""


class ElevationRangeError(ValueError):
    """Tinggi sampel di luar rentang wajar (kemungkinan nodata tak bertanda atau DEM rusak)."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(_HASH_BLOCK):
            h.update(block)
    return h.hexdigest()


def _catmull_rom_weights(t: np.ndarray) -> list[np.ndarray]:
    """Bobot kernel Catmull-Rom (bikubik, a = -0.5) untuk tap i0-1, i0, i0+1, i0+2."""
    t2, t3 = t * t, t * t * t
    return [
        0.5 * (-t3 + 2 * t2 - t),
        0.5 * (3 * t3 - 5 * t2 + 2),
        0.5 * (-3 * t3 + 4 * t2 + t),
        0.5 * (t3 - t2),
    ]


def bicubic(data: np.ndarray, fcol: np.ndarray, frow: np.ndarray) -> np.ndarray:
    """Interpolasi Catmull-Rom di koordinat piksel pecahan (pusat piksel = bilangan bulat)."""
    h, w = data.shape
    c0 = np.floor(fcol).astype(np.int64)
    r0 = np.floor(frow).astype(np.int64)
    if c0.min() < 1 or r0.min() < 1 or c0.max() > w - 3 or r0.max() > h - 3:
        raise CoverageError("titik sampel di luar DEM (butuh margin 2 piksel untuk bikubik)")
    wc = _catmull_rom_weights(fcol - c0)
    wr = _catmull_rom_weights(frow - r0)
    out = np.zeros(fcol.shape, dtype=np.float64)
    for j in range(4):
        rows = r0 + (j - 1)
        acc = np.zeros(fcol.shape, dtype=np.float64)
        for i in range(4):
            acc += wc[i] * data[rows, c0 + (i - 1)]
        out += wr[j] * acc
    return out


class Dem:
    """DEM terbaca penuh ke memori (float64, nodata -> NaN)."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with rasterio.open(self.path) as ds:
            if ds.crs is None:
                raise ValueError(f"DEM tanpa CRS: {self.path}")
            self.crs = ds.crs
            self.transform = ds.transform
            data = ds.read(1).astype(np.float64)
            if ds.nodata is not None:
                data[data == ds.nodata] = np.nan
        self.data = data
        self.sha256 = sha256_file(self.path)
        self._inverse = ~self.transform
        self._to_dem = None if self.crs == rasterio.crs.CRS.from_string(WGS84) else Transformer.from_crs(
            WGS84, self.crs, always_xy=True
        )

    @property
    def crs_name(self) -> str:
        return self.crs.to_string()

    def bilinear_at_lonlat(self, lon: float, lat: float) -> float:
        """Pembanding akurasi: interpolasi bilinear DEM asli di satu titik lon/lat."""
        x, y = (lon, lat) if self._to_dem is None else self._to_dem.transform(lon, lat)
        col, row = self._inverse @ (x, y)
        fc, fr = col - 0.5, row - 0.5
        c0, r0 = int(np.floor(fc)), int(np.floor(fr))
        h, w = self.data.shape
        if c0 < 0 or r0 < 0 or c0 + 1 >= w or r0 + 1 >= h:
            raise CoverageError(f"titik ({lon}, {lat}) di luar raster DEM")
        tc, tr = fc - c0, fr - r0
        d = self.data
        top = d[r0, c0] * (1 - tc) + d[r0, c0 + 1] * tc
        bot = d[r0 + 1, c0] * (1 - tc) + d[r0 + 1, c0 + 1] * tc
        value = float(top * (1 - tr) + bot * tr)
        if not np.isfinite(value):
            raise CoverageError(f"titik ({lon}, {lat}) menyentuh nodata DEM")
        return value

    def sample_local(self, proj: LocalProjection, xs: np.ndarray, zs: np.ndarray, block_rows: int) -> np.ndarray:
        """Tinggi (m) pada lattice xs (timur) x zs (utara) -> array [len(zs), len(xs)]."""
        out = np.empty((len(zs), len(xs)), dtype=np.float64)
        for start in range(0, len(zs), block_rows):
            zb = zs[start : start + block_rows]
            gx, gz = np.meshgrid(xs, zb)
            lon, lat = proj.to_lonlat_array(gx, gz)
            if self._to_dem is not None:
                lon, lat = self._to_dem.transform(lon, lat)
            col, row = self._inverse @ (lon, lat)
            out[start : start + len(zb)] = bicubic(self.data, col - 0.5, row - 0.5)
        if not np.isfinite(out).all():
            raise CoverageError("hasil sampel mengandung nodata/NaN (DEM tidak menutupi area penuh)")
        return out
