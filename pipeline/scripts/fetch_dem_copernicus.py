"""GAME-52: unduh DEM sementara Copernicus GLO-30 (DSM, ~30 m) untuk area cakupan.

Dijalankan dari folder pipeline/:
    uv run python scripts/fetch_dem_copernicus.py
    uv run python scripts/fetch_dem_copernicus.py --boundary data/boundary.geojson
    uv run python scripts/fetch_dem_copernicus.py --check-only   # hanya verifikasi file lokal, tanpa jaringan

Tile dipilih dari bounds polygon batas, diunduh apa adanya (tanpa reproyeksi/potong; itu GAME-16)
ke data/raw/dem/copernicus/ beserta metadata (dem_copernicus.json). Menjalankan ulang tidak
mengunduh ulang file yang ukuran dan sha256-nya cocok dengan metadata.

Sumber: bucket AWS open data `copernicus-dem-30m` (HTTPS publik, tanpa kredensial).
(c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS
by the European Union and ESA; all rights reserved.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from shapely.geometry import box, shape
from shapely.geometry.base import BaseGeometry

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "data" / "boundary.geojson"
OUT_DIR = ROOT / "data" / "raw" / "dem" / "copernicus"
METADATA_NAME = "dem_copernicus.json"

BUCKET_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
TILE_TEMPLATE = "Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM"
UA = {"User-Agent": "game-3d-pipeline/0.1 (GAME-52 DEM fetch)"}
TIMEOUT = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0)
MAX_ATTEMPTS = 4
BACKOFF_S = 3.0
CHUNK_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"[0-9a-f]{64}")
WGS84_CRS_NAMES = ("EPSG:4326", "OGC:1.3:CRS84", "EPSG::4326")
# Grid Copernicus bergeser setengah piksel (1 arc-second): tile E109/S08 berbatas
# bujur [109-h, 110-h] dan lintang [-8+h, -7+h] (diverifikasi dari bounds raster asli).
HALF_PIXEL_DEG = 0.5 / 3600

SOURCE = "Copernicus DEM GLO-30 (DSM, COG) via AWS Open Data, bucket copernicus-dem-30m"
LICENSE = "Copernicus DEM licence (free of charge for general public use; atribusi wajib)"
ATTRIBUTION = (
    "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under "
    "COPERNICUS by the European Union and ESA; all rights reserved"
)


class CoverageError(RuntimeError):
    """Raster tidak menutupi polygon batas (bounds kurang atau ada nodata di dalamnya)."""


# --- pemilihan tile ---------------------------------------------------------

def tile_id(lat_floor: int, lon_floor: int) -> str:
    """Nama tile dari pojok kiri-bawah. Lintang selatan memakai nilai absolut: -8 -> S08."""
    lat = f"{'N' if lat_floor >= 0 else 'S'}{abs(lat_floor):02d}"
    lon = f"{'E' if lon_floor >= 0 else 'W'}{abs(lon_floor):03d}"
    return TILE_TEMPLATE.format(lat=lat, lon=lon)


def tile_url(tid: str) -> str:
    return f"{BUCKET_URL}/{tid}/{tid}.tif"


def select_tiles(poly: BaseGeometry) -> list[tuple[int, int]]:
    """Daftar sel (lat_floor, lon_floor) tile 1x1 derajat yang beririsan dengan bounds polygon."""
    minx, miny, maxx, maxy = poly.bounds
    h = HALF_PIXEL_DEG
    lons = range(math.floor(minx + h), math.floor(maxx + h) + 1)
    lats = range(math.floor(miny - h), math.floor(maxy - h) + 1)
    return [(la, lo) for la in lats for lo in lons]


# --- unduh ------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_BYTES), b""):
            h.update(chunk)
    return h.hexdigest()


def valid_metadata(meta: object) -> bool:
    """tiles: dict[str, {size_bytes: int > 0, sha256: hex 64 karakter}]."""
    if not isinstance(meta, dict) or not isinstance(meta.get("tiles"), dict):
        return False
    for key, e in meta["tiles"].items():
        if not isinstance(key, str) or not isinstance(e, dict):
            return False
        size = e.get("size_bytes")
        sha = e.get("sha256")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            return False
        if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
            return False
    return True


def load_metadata(out_dir: Path) -> dict:
    p = out_dir / METADATA_NAME
    if p.exists():
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = None
        if valid_metadata(meta):
            return meta
        print(f"PERINGATAN: {p} tidak valid, dianggap tidak ada (file akan diverifikasi/diunduh ulang)",
              file=sys.stderr)
    return {"tiles": {}}


def is_valid_local(path: Path, entry: dict | None) -> bool:
    """File dianggap valid bila ada metadata dan ukuran + sha256 cocok."""
    if not entry or not path.exists() or path.stat().st_size != entry.get("size_bytes"):
        return False
    return sha256_of(path) == entry.get("sha256")


def download(url: str, dest: Path) -> dict:
    """Streaming ke file sementara, verifikasi ukuran, lalu rename. Retry dengan backoff."""
    tmp = dest.with_name(dest.name + ".part")
    last: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            h = hashlib.sha256()
            size = 0
            with httpx.stream("GET", url, headers=UA, timeout=TIMEOUT, follow_redirects=True) as r:
                r.raise_for_status()
                expected = int(r.headers.get("content-length", -1))
                with tmp.open("wb") as f:
                    for chunk in r.iter_bytes(CHUNK_BYTES):
                        f.write(chunk)
                        h.update(chunk)
                        size += len(chunk)
                etag = r.headers.get("etag", "").strip('"')
            if expected >= 0 and size != expected:
                raise OSError(f"ukuran tidak cocok: terunduh {size}, Content-Length {expected}")
            tmp.replace(dest)
            return {"size_bytes": size, "sha256": h.hexdigest(), "etag": etag}
        except (httpx.HTTPError, OSError) as e:
            last = e
            tmp.unlink(missing_ok=True)
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (403, 404):
                break  # tile tidak ada: retry tidak membantu
            print(f"  percobaan {attempt}/{MAX_ATTEMPTS} gagal: {e}", file=sys.stderr)
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_S * attempt)
    raise RuntimeError(f"gagal mengunduh {url}: {last}")


def fetch_tiles(cells: list[tuple[int, int]], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = load_metadata(out_dir)
    paths: list[Path] = []
    for cell in cells:
        tid = tile_id(*cell)
        dest = out_dir / f"{tid}.tif"
        entry = meta["tiles"].get(tid)
        if is_valid_local(dest, entry):
            print(f"{tid}: sudah ada dan valid, dilewati")
        else:
            url = tile_url(tid)
            print(f"{tid}: mengunduh {url}")
            info = download(url, dest)
            meta["tiles"][tid] = {
                "file": dest.name,
                "url": url,
                "downloaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                **info,
            }
            meta.update(
                source=SOURCE,
                license=LICENSE,
                attribution=ATTRIBUTION,
                resolution="1 arc-second (~30 m)",
                product="DSM (termasuk pohon/bangunan), bukan DTM",
                crs="EPSG:4326",
            )
            (out_dir / METADATA_NAME).write_text(
                json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        paths.append(dest)
    return paths


# --- cek cakupan ------------------------------------------------------------

def snap_bounds(bounds: tuple, ds) -> tuple:
    """Bulatkan bounds keluar ke grid piksel dataset agar merge tidak menggeser piksel di sambungan tile."""
    t = ds.transform
    x0, y0, rx, ry = t.c, t.f, t.a, -t.e
    minx, miny, maxx, maxy = bounds
    return (
        x0 + math.floor((minx - x0) / rx) * rx,
        y0 - math.ceil((y0 - miny) / ry) * ry,
        x0 + math.ceil((maxx - x0) / rx) * rx,
        y0 - math.floor((y0 - maxy) / ry) * ry,
    )


def check_coverage(paths: list[Path], poly: BaseGeometry) -> dict:
    """Pastikan bounds raster mencakup polygon dan tidak ada nodata di dalamnya.

    Mengembalikan statistik ketinggian (min/max/mean, piksel yang disentuh polygon).
    Memicu CoverageError dengan pesan jelas bila gagal.
    """
    datasets = [rasterio.open(p) for p in paths]
    try:
        for ds in datasets:
            if ds.crs is None or ds.crs.to_epsg() != 4326:
                raise CoverageError(f"{ds.name}: CRS {ds.crs} bukan EPSG:4326")
        union = box(*datasets[0].bounds)
        for ds in datasets[1:]:
            union = union.union(box(*ds.bounds))
        if not union.covers(poly):
            missing = poly.difference(union)
            raise CoverageError(
                f"bounds raster {union.bounds} tidak mencakup polygon batas; "
                f"bagian di luar raster: {missing.bounds}"
            )
        nodata = datasets[0].nodata
        data, transform = merge(datasets, bounds=snap_bounds(poly.bounds, datasets[0]), nodata=nodata)
        arr = data[0].astype("float64")
        inside = geometry_mask([poly], out_shape=arr.shape, transform=transform, invert=True, all_touched=True)
        if not inside.any():
            raise CoverageError("polygon tidak menyentuh piksel raster mana pun")
        vals = arr[inside]
        bad = ~np.isfinite(vals)
        if nodata is not None:
            bad |= vals == nodata
        if bad.any():
            raise CoverageError(f"{int(bad.sum())} dari {vals.size} piksel di dalam polygon adalah nodata")
        return {
            "pixels": int(vals.size),
            "min_m": float(vals.min()),
            "max_m": float(vals.max()),
            "mean_m": float(vals.mean()),
        }
    finally:
        for ds in datasets:
            ds.close()


def load_polygon(path: Path) -> BaseGeometry:
    fc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(fc, dict) or not fc.get("features"):
        raise ValueError(f"{path}: bukan FeatureCollection atau tidak ada feature")
    crs_name = ((fc.get("crs") or {}).get("properties") or {}).get("name")
    if crs_name is not None and not any(n in str(crs_name) for n in WGS84_CRS_NAMES):
        raise ValueError(f"{path}: CRS {crs_name!r} bukan EPSG:4326/CRS84")
    geom = fc["features"][0].get("geometry")
    if not isinstance(geom, dict) or geom.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError(f"{path}: geometri harus Polygon/MultiPolygon, bukan "
                         f"{geom.get('type') if isinstance(geom, dict) else geom!r}")
    return shape(geom)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--boundary", type=Path, default=BOUNDARY)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--check-only", action="store_true", help="jangan unduh; hanya verifikasi file lokal")
    args = ap.parse_args(argv)

    try:
        poly = load_polygon(args.boundary)
    except (OSError, ValueError) as e:
        print(f"GAGAL membaca batas: {e}", file=sys.stderr)
        return 1
    cells = select_tiles(poly)
    print(f"Tile terpilih: {[tile_id(*c) for c in cells]}")
    if args.check_only:
        meta = load_metadata(args.out_dir)
        paths = [args.out_dir / f"{tile_id(*c)}.tif" for c in cells]
        for c, p in zip(cells, paths):
            if not is_valid_local(p, meta["tiles"].get(tile_id(*c))):
                print(f"GAGAL: {p} tidak ada atau checksum tidak cocok", file=sys.stderr)
                return 1
    else:
        paths = fetch_tiles(cells, args.out_dir)
    try:
        stats = check_coverage(paths, poly)
    except CoverageError as e:
        print(f"GAGAL cakupan: {e}", file=sys.stderr)
        return 1
    print(
        f"Cakupan OK: {stats['pixels']} piksel; tinggi di dalam polygon "
        f"min {stats['min_m']:.2f} m, max {stats['max_m']:.2f} m, mean {stats['mean_m']:.2f} m"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
