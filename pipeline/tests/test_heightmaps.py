"""GAME-16: heightmap per chunk. DEM sintetis kecil (tanpa jaringan); DEM asli opsional."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from geo.chunks import chunk_id
from geo.projection import default_projection
from terrain import schema_check
from terrain.build import build_heightmaps
from terrain.chunk_select import select_chunks
from terrain.config import HeightmapConfig
from terrain.dem import CoverageError, Dem, ElevationRangeError

ROOT = Path(__file__).resolve().parents[1]
REAL_DEM_DIR = ROOT / "data" / "raw" / "dem" / "copernicus"
BOUNDARY_PATH = ROOT / "data" / "boundary.geojson"

PX_DEG = 1 / 3600
CFG = HeightmapConfig(resolution=33)  # 8 m/piksel agar test cepat
PROJ = default_projection()


def _synthetic_dem(path: Path, nodata_hole: bool = False) -> Path:
    """DEM EPSG:4326 ~6.6 x 5.5 km di sekitar origin: bidang miring + gelombang landai."""
    w, h = 216, 180
    lon0, lat0 = PROJ.origin_lon - w / 2 * PX_DEG, PROJ.origin_lat + h / 2 * PX_DEG
    cols = lon0 + (np.arange(w) + 0.5) * PX_DEG
    rows = lat0 - (np.arange(h) + 0.5) * PX_DEG
    lon, lat = np.meshgrid(cols, rows)
    z = 100 + 300 * (lon - lon0) + 200 * (lat - lat0) + 8 * np.sin(2 * np.pi * lon / 0.02)
    z = z.astype("float32")
    if nodata_hole:
        z[h // 2 - 3 : h // 2 + 3, w // 2 - 3 : w // 2 + 3] = -9999
    with rasterio.open(
        path, "w", driver="GTiff", width=w, height=h, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(lon0, lat0, PX_DEG, PX_DEG), nodata=-9999,
    ) as ds:  # fmt: skip
        ds.write(z, 1)
    return path


def _boundary(path: Path) -> Path:
    d = 0.003  # ~330 m: melintasi chunk negatif dan positif di sekitar origin
    lo, la = PROJ.origin_lon, PROJ.origin_lat
    ring = [[lo - d, la - d], [lo + d, la - d], [lo + d, la + d], [lo - d, la + d], [lo - d, la - d]]
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}
    ]}  # fmt: skip
    path.write_text(json.dumps(fc), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def inputs(tmp_path_factory):
    d = tmp_path_factory.mktemp("in")
    return _synthetic_dem(d / "dem.tif"), _boundary(d / "boundary.geojson")


@pytest.fixture(scope="module")
def built(inputs, tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    result = build_heightmaps(inputs[0], inputs[1], out, CFG)
    return out, result


def _read_raw(out: Path, cid: str, res: int = CFG.resolution) -> np.ndarray:
    return np.fromfile(out / f"{cid}.raw", dtype="<u2").reshape(res, res)


def _height_at(out: Path, x: float, z: float) -> float:
    """Dekode heightmap + interpolasi bilinear di titik lokal (cara importer membaca)."""
    idx = json.loads((out / "index.json").read_text())
    n, sp = idx["resolution"] - 1, idx["sample_spacing_m"]
    cx, cz = map(int, chunk_id(x, z).split("_"))
    a = _read_raw(out, f"{cx}_{cz}", n + 1).astype(np.float64)
    fx, fz = (x - cx * 256) / sp, (z - cz * 256) / sp
    i, k = min(int(fx), n - 1), min(int(fz), n - 1)
    tx, tz = fx - i, fz - k
    v = (a[k, i] * (1 - tx) + a[k, i + 1] * tx) * (1 - tz) + (a[k + 1, i] * (1 - tx) + a[k + 1, i + 1] * tx) * tz
    return idx["height_min_m"] + v / 65535 * (idx["height_max_m"] - idx["height_min_m"])


# --- pemilihan chunk ---------------------------------------------------------

def test_select_chunks_negative_and_margin():
    poly = box(-10, -10, 10, 10)  # menyentuh empat chunk di sekitar origin
    assert select_chunks(poly, 0) == [(-1, -1), (-1, 0), (0, -1), (0, 0)]
    sel = select_chunks(poly, 1)
    assert len(sel) == 16 and (-2, -2) in sel and (1, 1) in sel and (-3, 0) not in sel


def test_select_chunks_far_negative():
    assert select_chunks(box(-600, -300, -520, -200), 0) == [(-3, -2), (-3, -1)]


def test_select_chunks_empty_rejected():
    with pytest.raises(ValueError):
        select_chunks(box(0, 0, 0, 0).difference(box(0, 0, 0, 0)), 0)


def test_every_selected_chunk_has_files(built):
    out, result = built
    idx = json.loads((out / "index.json").read_text())
    assert idx["chunks"] == result.chunk_ids and len(idx["chunks"]) == 36  # 4x4 + margin 1 = 6x6
    assert "-3_-3" in idx["chunks"] and "2_2" in idx["chunks"]
    for cid in idx["chunks"]:
        assert (out / f"{cid}.raw").stat().st_size == CFG.resolution**2 * 2
        meta = json.loads((out / f"{cid}.json").read_text())
        schema_check.validate(meta, schema_check.load_schema("heightmap_chunk.schema.json"))
        assert meta["id"] == cid
    schema_check.validate(idx, schema_check.load_schema("heightmap_index.schema.json"))


# --- seam --------------------------------------------------------------------

def test_neighbor_edges_identical(built):
    out, result = built
    ids = set(result.chunk_ids)
    checked = 0
    for cid in ids:
        cx, cz = map(int, cid.split("_"))
        a = _read_raw(out, cid)
        east, north = f"{cx + 1}_{cz}", f"{cx}_{cz + 1}"
        if east in ids:
            assert np.array_equal(a[:, -1], _read_raw(out, east)[:, 0]), cid
            checked += 1
        if north in ids:
            assert np.array_equal(a[-1, :], _read_raw(out, north)[0, :]), cid
            checked += 1
    assert checked == 2 * 6 * 5  # 6x6 grid: 30 sambungan timur + 30 utara


# --- akurasi titik -----------------------------------------------------------

@pytest.mark.parametrize("sigma", [0.0, CFG.smooth_sigma_m])
def test_point_accuracy_vs_bilinear_dem(inputs, tmp_path, sigma):
    out = tmp_path / f"o{sigma}"
    build_heightmaps(inputs[0], inputs[1], out, replace(CFG, smooth_sigma_m=sigma))
    dem = Dem(inputs[0])
    rng = np.random.default_rng(7)
    for x, z in rng.uniform(-500, 500, (40, 2)):
        exp = dem.bilinear_at_lonlat(*PROJ.to_lonlat(x, z))
        assert abs(_height_at(out, x, z) - exp) < 1.0, (x, z)


# --- determinisme ------------------------------------------------------------

def test_deterministic_byte_identical(inputs, built, tmp_path):
    out1 = built[0]
    out2 = tmp_path / "again"
    build_heightmaps(inputs[0], inputs[1], out2, CFG)
    names1 = sorted(p.name for p in out1.iterdir())
    assert names1 == sorted(p.name for p in out2.iterdir())
    for n in names1:
        assert (out1 / n).read_bytes() == (out2 / n).read_bytes(), n


def test_rerun_into_same_dir_removes_stale_and_is_identical(inputs, tmp_path):
    out = tmp_path / "o"
    build_heightmaps(inputs[0], inputs[1], out, CFG)
    (out / "99_99.raw").write_bytes(b"x")
    before = {p.name: p.read_bytes() for p in out.iterdir() if p.name != "99_99.raw"}
    build_heightmaps(inputs[0], inputs[1], out, CFG)
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before


# --- skema, config, kegagalan ------------------------------------------------

def test_schema_validator_rejects_bad_data(built):
    out, _ = built
    schema = schema_check.load_schema("heightmap_chunk.schema.json")
    meta = json.loads((out / "0_0.json").read_text())
    bad = dict(meta, raw_max=70000)
    with pytest.raises(schema_check.ValidationError):
        schema_check.validate(bad, schema)
    bad = {k: v for k, v in meta.items() if k != "sha256"}
    with pytest.raises(schema_check.ValidationError):
        schema_check.validate(bad, schema)
    with pytest.raises(schema_check.ValidationError):
        schema_check.validate(dict(meta, id="01_0"), schema)
    with pytest.raises(schema_check.SchemaError):
        schema_check.validate(meta, {"type": "object", "oneOf": []})


def test_height_range_global_and_encoding(built):
    out, _ = built
    idx = json.loads((out / "index.json").read_text())
    span = idx["height_max_m"] - idx["height_min_m"]
    metas = [json.loads((out / f"{c}.json").read_text()) for c in idx["chunks"]]
    assert idx["height_min_m"] == pytest.approx(min(m["min_height_m"] for m in metas) - CFG.height_padding_m)
    assert idx["height_max_m"] == pytest.approx(max(m["max_height_m"] for m in metas) + CFG.height_padding_m)
    for m in metas:
        assert m["height_range_global_m"] == [idx["height_min_m"], idx["height_max_m"]]
        a = _read_raw(out, m["id"])
        assert m["raw_min"] == a.min() and m["raw_max"] == a.max()
        assert idx["height_min_m"] + a.max() / 65535 * span == pytest.approx(m["max_height_m"], abs=span / 65535)


@pytest.mark.parametrize("res", [0, 2, 100, 256])
def test_config_rejects_non_power_of_two_plus_one(res):
    with pytest.raises(ValueError):
        HeightmapConfig(resolution=res)


def test_nodata_in_dem_reported(tmp_path):
    dem = _synthetic_dem(tmp_path / "hole.tif", nodata_hole=True)
    with pytest.raises(CoverageError):
        build_heightmaps(dem, _boundary(tmp_path / "b.geojson"), tmp_path / "o", CFG)


def test_dem_not_covering_area_reported(inputs, tmp_path):
    far = tmp_path / "far.geojson"
    far.write_text(json.dumps({"type": "Polygon", "coordinates": [[[110.5, -7.0], [110.51, -7.0], [110.51, -7.01], [110.5, -7.0]]]}))
    with pytest.raises(CoverageError):
        build_heightmaps(inputs[0], far, tmp_path / "o", CFG)


# --- DEM asli (opsional) -----------------------------------------------------

REAL_TIFS = sorted(REAL_DEM_DIR.glob("*.tif"))


@pytest.mark.skipif(not REAL_TIFS, reason="DEM Copernicus tidak ada di data/raw/dem/copernicus")
def test_real_dem_default_config_accuracy(tmp_path):
    """AC: >= 300 titik acak vs bilinear DEM sumber, konfigurasi default: p95 < 1 m, maks < 2,5 m."""
    out = tmp_path / "real"
    result = build_heightmaps(REAL_TIFS[0], BOUNDARY_PATH, out)  # HeightmapConfig default
    assert len(result.chunk_ids) > 50
    dem = Dem(REAL_TIFS[0])
    pts = np.random.default_rng(1).uniform(-1300, 1300, (300, 2))
    assert all(chunk_id(x, z) in result.chunk_ids for x, z in pts)
    diffs = np.array([
        abs(_height_at(out, x, z) - dem.bilinear_at_lonlat(*PROJ.to_lonlat(x, z))) for x, z in pts
    ])
    assert np.percentile(diffs, 95) < 1.0 and diffs.max() < 2.5


# --- DEM non-EPSG:4326, validasi input, folder keluaran ----------------------

def _synthetic_dem_utm(path: Path) -> Path:
    """DEM EPSG:32749 (30 m, 6 x 6 km) di sekitar origin: bidang miring + gelombang landai."""
    px, size = 30.0, 200
    ox, oy = PROJ.origin_utm
    x0, y0 = ox - size / 2 * px, oy + size / 2 * px
    xs = x0 + (np.arange(size) + 0.5) * px
    ys = y0 - (np.arange(size) + 0.5) * px
    gx, gy = np.meshgrid(xs, ys)
    z = (100 + 0.05 * (gx - x0) + 0.03 * (gy - y0) + 8 * np.sin(2 * np.pi * gx / 2200)).astype("float32")
    with rasterio.open(
        path, "w", driver="GTiff", width=size, height=size, count=1, dtype="float32",
        crs="EPSG:32749", transform=from_origin(x0, y0, px, px),
    ) as ds:  # fmt: skip
        ds.write(z, 1)
    return path


def test_non_wgs84_dem_matches_source(inputs, tmp_path):
    dem_path = _synthetic_dem_utm(tmp_path / "utm.tif")
    out = tmp_path / "o"
    build_heightmaps(dem_path, inputs[1], out, CFG)
    dem = Dem(dem_path)
    assert dem.crs_name == "EPSG:32749"
    for x, z in np.random.default_rng(5).uniform(-500, 500, (30, 2)):
        exp = dem.bilinear_at_lonlat(*PROJ.to_lonlat(x, z))
        assert abs(_height_at(out, x, z) - exp) < 1.0, (x, z)
    idx = json.loads((out / "index.json").read_text())
    assert idx["source"]["crs"] == "EPSG:32749"


def test_bilinear_outside_raster_raises_coverage_error(inputs):
    with pytest.raises(CoverageError):
        Dem(inputs[0]).bilinear_at_lonlat(120.0, -7.0)


def _boundary_geojson(path: Path, geometry: dict) -> Path:
    path.write_text(json.dumps({"type": "Feature", "properties": {}, "geometry": geometry}))
    return path


def test_boundary_must_be_valid_polygon(inputs, tmp_path):
    lo, la = PROJ.origin_lon, PROJ.origin_lat
    point = _boundary_geojson(tmp_path / "p.geojson", {"type": "Point", "coordinates": [lo, la]})
    with pytest.raises(ValueError, match="Polygon"):
        build_heightmaps(inputs[0], point, tmp_path / "o1", CFG)
    bowtie = [[lo, la], [lo + 0.002, la + 0.002], [lo + 0.002, la], [lo, la + 0.002], [lo, la]]
    bad = _boundary_geojson(tmp_path / "b.geojson", {"type": "Polygon", "coordinates": [bowtie]})
    with pytest.raises(ValueError, match="tidak valid"):
        build_heightmaps(inputs[0], bad, tmp_path / "o2", CFG)


def test_implausible_elevation_reported(inputs, tmp_path):
    cfg = replace(CFG, valid_height_max_m=50.0)  # DEM sintetis mulai ~100 m
    with pytest.raises(ElevationRangeError, match="rentang wajar"):
        build_heightmaps(inputs[0], inputs[1], tmp_path / "o", cfg)


def test_foreign_output_dir_rejected_and_untouched(inputs, tmp_path):
    out = tmp_path / "docs"
    out.mkdir()
    (out / "catatan.txt").write_text("penting")
    with pytest.raises(ValueError, match="bukan output heightmap"):
        build_heightmaps(inputs[0], inputs[1], out, CFG)
    assert (out / "catatan.txt").read_text() == "penting"


def test_failed_build_keeps_previous_output_and_no_tmp(inputs, built, tmp_path):
    out = tmp_path / "o"
    build_heightmaps(inputs[0], inputs[1], out, CFG)
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    with pytest.raises(ElevationRangeError):
        build_heightmaps(inputs[0], inputs[1], out, replace(CFG, valid_height_max_m=50.0))
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before
    assert not (tmp_path / "o.tmp").exists() and not (tmp_path / "o.old").exists()
