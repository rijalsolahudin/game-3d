"""GAME-52: pemilihan tile, cek cakupan, dan idempotensi unduh; tanpa jaringan."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box, shape

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_dem_copernicus", ROOT / "scripts" / "fetch_dem_copernicus.py")
dem = importlib.util.module_from_spec(spec)
sys.modules["fetch_dem_copernicus"] = dem
spec.loader.exec_module(dem)


def tiles(poly):
    return [dem.tile_id(*c) for c in dem.select_tiles(poly)]


def test_tile_naming_southern_hemisphere():
    assert dem.tile_id(-8, 109) == "Copernicus_DSM_COG_10_S08_00_E109_00_DEM"
    assert dem.tile_id(0, 6) == "Copernicus_DSM_COG_10_N00_00_E006_00_DEM"
    assert dem.tile_id(51, -3) == "Copernicus_DSM_COG_10_N51_00_W003_00_DEM"
    assert dem.tile_url(dem.tile_id(-8, 109)).endswith(
        "/Copernicus_DSM_COG_10_S08_00_E109_00_DEM/Copernicus_DSM_COG_10_S08_00_E109_00_DEM.tif"
    )


def test_boundary_selects_single_tile_s08_e109():
    fc = json.loads((ROOT / "data" / "boundary.geojson").read_text(encoding="utf-8"))
    poly = shape(fc["features"][0]["geometry"])
    assert tiles(poly) == ["Copernicus_DSM_COG_10_S08_00_E109_00_DEM"]


def test_polygon_south_of_equator_floors_down():
    # lat -7.35 berada di tile yang pojok kiri-bawahnya -8 (S08), bukan S07
    assert dem.select_tiles(box(109.4, -7.4, 109.5, -7.3)) == [(-8, 109)]


def test_polygon_crossing_tile_borders():
    cells = dem.select_tiles(box(109.9, -7.1, 110.1, -6.9))  # melintasi lintang -7 dan bujur 110
    assert sorted(cells) == [(-8, 109), (-8, 110), (-7, 109), (-7, 110)]
    assert sorted(dem.select_tiles(box(108.9, -7.5, 109.1, -7.4))) == [(-8, 108), (-8, 109)]


def test_polygon_on_nominal_edge_follows_half_pixel_grid():
    h = dem.HALF_PIXEL_DEG
    # tile E109/S08 sebenarnya bujur [109-h, 110-h], lintang [-8+h, -7+h]
    assert dem.select_tiles(box(109.0, -7.99, 109.99, -7.01)) == [(-8, 109)]
    assert dem.select_tiles(box(109.0 + h, -8.0 + 2 * h, 110.0 - 2 * h, -7.0)) == [(-8, 109)]


def test_lon_just_below_integer_pulls_next_tile():
    assert sorted(dem.select_tiles(box(109.5, -7.5, 109.9999, -7.4))) == [(-8, 109), (-8, 110)]


def test_lat_just_above_tile_top_pulls_next_tile():
    # S08 berbatas lintang [-7.99986, -6.99986]
    assert dem.select_tiles(box(109.5, -7.5, 109.6, -6.9999)) == [(-8, 109)]
    assert sorted(dem.select_tiles(box(109.5, -7.5, 109.6, -6.9998))) == [(-8, 109), (-7, 109)]
    assert sorted(dem.select_tiles(box(109.5, -7.9999, 109.6, -7.5))) == [(-9, 109), (-8, 109)]


def make_tif(path, west, north, size=100, step=0.001, nodata=-32767.0, hole=None):
    # meniru grid Copernicus: kiri bergeser -setengah piksel, atas +setengah piksel dari nominal
    west, north = west - step / 2, north + step / 2
    arr = np.linspace(100, 300, size * size, dtype="float32").reshape(size, size)
    if hole:
        arr[hole] = nodata
    with rasterio.open(
        path, "w", driver="GTiff", height=size, width=size, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(west, north, step, step), nodata=nodata,
    ) as dst:
        dst.write(arr, 1)


def test_coverage_ok(tmp_path):
    p = tmp_path / "a.tif"
    make_tif(p, 109.0, -7.0)  # lon 109.0-109.1, lat -7.1..-7.0
    stats = dem.check_coverage([p], box(109.02, -7.08, 109.06, -7.03))
    assert stats["pixels"] > 0
    assert 100 <= stats["min_m"] <= stats["mean_m"] <= stats["max_m"] <= 300


def test_coverage_fails_when_bounds_too_small(tmp_path):
    p = tmp_path / "a.tif"
    make_tif(p, 109.0, -7.0)
    with pytest.raises(dem.CoverageError, match="tidak mencakup"):
        dem.check_coverage([p], box(109.05, -7.08, 109.15, -7.03))


def test_coverage_fails_on_nodata_inside_polygon(tmp_path):
    p = tmp_path / "a.tif"
    make_tif(p, 109.0, -7.0, hole=(slice(40, 45), slice(40, 45)))
    with pytest.raises(dem.CoverageError, match="nodata"):
        dem.check_coverage([p], box(109.02, -7.08, 109.06, -7.03))


def test_coverage_ignores_nodata_outside_polygon(tmp_path):
    p = tmp_path / "a.tif"
    make_tif(p, 109.0, -7.0, hole=(slice(0, 5), slice(0, 5)))
    assert dem.check_coverage([p], box(109.02, -7.08, 109.06, -7.03))["pixels"] > 0


def test_coverage_across_two_tiles(tmp_path):
    a, b = tmp_path / "a.tif", tmp_path / "b.tif"
    make_tif(a, 109.0, -7.0)
    make_tif(b, 109.1, -7.0)
    assert dem.check_coverage([a, b], box(109.05, -7.08, 109.15, -7.03))["pixels"] > 0


def test_second_run_does_not_redownload(tmp_path, monkeypatch):
    calls = []

    def fake_download(url, dest):
        calls.append(url)
        dest.write_bytes(b"data")
        return {"size_bytes": 4, "sha256": dem.hashlib.sha256(b"data").hexdigest(), "etag": "x"}

    monkeypatch.setattr(dem, "download", fake_download)
    cells = [(-8, 109)]
    dem.fetch_tiles(cells, tmp_path)
    dem.fetch_tiles(cells, tmp_path)
    assert len(calls) == 1
    (tmp_path / f"{dem.tile_id(-8, 109)}.tif").write_bytes(b"rusak")  # file rusak -> unduh ulang
    dem.fetch_tiles(cells, tmp_path)
    assert len(calls) == 2


def write_meta(tmp_path, meta):
    (tmp_path / dem.METADATA_NAME).write_text(json.dumps(meta), encoding="utf-8")


GOOD = {"size_bytes": 4, "sha256": "a" * 64}


@pytest.mark.parametrize("meta", [
    [],
    {"tiles": []},
    {"tiles": {"t": "x"}},
    {"tiles": {"t": {"size_bytes": 0, "sha256": "a" * 64}}},
    {"tiles": {"t": {"size_bytes": "4", "sha256": "a" * 64}}},
    {"tiles": {"t": {"size_bytes": True, "sha256": "a" * 64}}},
    {"tiles": {"t": {"size_bytes": 4, "sha256": "xyz"}}},
])
def test_invalid_metadata_treated_as_missing(tmp_path, meta, capsys):
    write_meta(tmp_path, meta)
    assert dem.load_metadata(tmp_path) == {"tiles": {}}
    assert "PERINGATAN" in capsys.readouterr().err


def test_corrupt_json_metadata_treated_as_missing(tmp_path):
    (tmp_path / dem.METADATA_NAME).write_text("{bukan json", encoding="utf-8")
    assert dem.load_metadata(tmp_path) == {"tiles": {}}


def test_valid_metadata_loaded(tmp_path):
    write_meta(tmp_path, {"tiles": {"t": GOOD}})
    assert dem.load_metadata(tmp_path)["tiles"]["t"] == GOOD


def geojson(tmp_path, geometry, crs=None):
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": geometry}]}
    if crs:
        fc["crs"] = {"type": "name", "properties": {"name": crs}}
    p = tmp_path / "b.geojson"
    p.write_text(json.dumps(fc), encoding="utf-8")
    return p


SQUARE = {"type": "Polygon", "coordinates": [[[109, -7], [109.1, -7], [109.1, -7.1], [109, -7.1], [109, -7]]]}


def test_load_polygon_accepts_polygon_and_crs84(tmp_path):
    assert dem.load_polygon(geojson(tmp_path, SQUARE, "urn:ogc:def:crs:OGC:1.3:CRS84")).area > 0
    assert dem.load_polygon(geojson(tmp_path, SQUARE)).area > 0


def test_load_polygon_rejects_point(tmp_path):
    with pytest.raises(ValueError, match="Polygon"):
        dem.load_polygon(geojson(tmp_path, {"type": "Point", "coordinates": [109, -7]}))


def test_load_polygon_rejects_wrong_crs(tmp_path):
    with pytest.raises(ValueError, match="CRS"):
        dem.load_polygon(geojson(tmp_path, SQUARE, "urn:ogc:def:crs:EPSG::32749"))


def test_main_reports_bad_boundary(tmp_path, capsys):
    p = geojson(tmp_path, {"type": "Point", "coordinates": [109, -7]})
    assert dem.main(["--boundary", str(p), "--out-dir", str(tmp_path)]) == 1
    assert "GAGAL membaca batas" in capsys.readouterr().err
