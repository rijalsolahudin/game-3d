"""GAME-15: origin, titik kontrol, round-trip, GeoJSON, chunk ID."""
import json
import math
from pathlib import Path

import numpy as np
import pytest
from pyproj import Geod, Proj

from geo.chunks import CHUNK_SIZE_M, chunk_bounds, chunk_coords, chunk_id, parse_chunk_id
from geo.projection import (
    UTM_49S,
    LocalProjection,
    OriginError,
    SchemaError,
    default_projection,
    load_origin,
    validate_origin,
)

ORIGIN_JSON = Path(__file__).resolve().parents[1] / "data" / "origin.json"

# Titik kontrol: node OSM nyata di sekitar Tumanggal (Overpass API, diambil 2026-11-21,
# (c) OpenStreetMap contributors, ODbL). Format: (sumber, lon, lat).
CONTROL_POINTS = [
    ("OSM node/1308706192 place=village Tumanggal", 109.4864955, -7.3487136),
    ("OSM node/6552373113 ujung selatan way/697906351 highway=residential", 109.486589, -7.349857),
    ("OSM node/6552373093 ujung utara way/697906351 highway=residential", 109.4893807, -7.3444476),
    ("OSM node/6552544786 ujung way/697721233 highway=residential", 109.4879329, -7.3402253),
    ("OSM node/6552545113 ujung way/697721253 highway=unclassified", 109.4895369, -7.3567769),
    ("OSM node/12757426180 ujung way/1377775603 highway=residential", 109.4867903, -7.3577039),
]
CONTROL_TOLERANCE_M = 0.5


@pytest.fixture(scope="module")
def proj() -> LocalProjection:
    return default_projection()


# --- origin ---

def test_origin_loaded_from_json_matches_file(proj):
    data = json.loads(ORIGIN_JSON.read_text(encoding="utf-8"))
    assert (proj.origin_lon, proj.origin_lat) == (data["lng"], data["lat"])
    assert load_origin(ORIGIN_JSON) == (data["lng"], data["lat"])


def test_origin_maps_to_zero(proj):
    assert proj.to_local(proj.origin_lon, proj.origin_lat) == (0.0, 0.0)


@pytest.mark.parametrize(
    "bad",
    [
        {"lat": -7.3, "crs": "EPSG:4326"},  # lng hilang
        {"lat": "x", "lng": 109.4, "crs": "EPSG:4326"},  # tipe salah
        {"lat": 91, "lng": 109.4, "crs": "EPSG:4326"},  # di luar jangkauan
        {"lat": -7.3, "lng": 109.4, "crs": "EPSG:32749"},  # crs salah
        {"lat": True, "lng": 109.4, "crs": "EPSG:4326"},  # bool bukan number
        {"lat": float("nan"), "lng": 109.4, "crs": "EPSG:4326"},
        {"lat": -7.3, "lng": float("inf"), "crs": "EPSG:4326"},
        {"lat": float("-inf"), "lng": 109.4, "crs": "EPSG:4326"},
        [],
    ],
)
def test_origin_schema_rejects_invalid(bad):
    with pytest.raises(OriginError):
        validate_origin(bad)


def test_load_origin_rejects_nan_literal_in_file(tmp_path):
    f = tmp_path / "origin.json"
    f.write_text('{"lat": NaN, "lng": 109.4, "crs": "EPSG:4326"}', encoding="utf-8")
    with pytest.raises(OriginError):
        load_origin(f)


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "object", "properties": {"lat": {"type": "number", "exclusiveMinimum": 0}}},
        {"type": "object", "pattern": "x"},
        {"type": "object", "properties": {"lat": {"type": "null"}}},
        {"type": "tuple"},
    ],
)
def test_unsupported_schema_keyword_or_type_raises(tmp_path, schema):
    f = tmp_path / "s.json"
    f.write_text(json.dumps(schema), encoding="utf-8")
    with pytest.raises(SchemaError):
        validate_origin({"lat": 1}, schema_path=f)


def test_supported_extra_types_work(tmp_path):
    f = tmp_path / "s.json"
    schema = {
        "type": "object",
        "required": ["n", "s", "b", "a"],
        "properties": {
            "n": {"type": "integer"},
            "s": {"type": "string"},
            "b": {"type": "boolean"},
            "a": {"type": "array"},
        },
    }
    f.write_text(json.dumps(schema), encoding="utf-8")
    validate_origin({"n": 1, "s": "x", "b": False, "a": []}, schema_path=f)
    with pytest.raises(OriginError):
        validate_origin({"n": 1.5, "s": "x", "b": False, "a": []}, schema_path=f)
    with pytest.raises(OriginError):
        validate_origin({"n": 1, "s": "x", "b": 0, "a": []}, schema_path=f)


def test_load_origin_rejects_invalid_file(tmp_path):
    f = tmp_path / "origin.json"
    f.write_text(json.dumps({"lat": -7.3}), encoding="utf-8")
    with pytest.raises(OriginError):
        load_origin(f)


# --- titik kontrol (pembanding independen: pyproj.Geod geodesik) ---

@pytest.mark.parametrize("name,lon,lat", CONTROL_POINTS, ids=[c[0] for c in CONTROL_POINTS])
def test_control_points_within_half_meter(proj, name, lon, lat):
    geod = Geod(ellps="WGS84")
    az, _, dist = geod.inv(proj.origin_lon, proj.origin_lat, lon, lat)
    # Lokal memakai jarak grid UTM: bandingkan dengan jarak geodesik dikali faktor skala
    # dan azimut geodesik dikoreksi konvergensi meridian (dari pyproj.Proj.get_factors).
    f = Proj(UTM_49S).get_factors(proj.origin_lon, proj.origin_lat)
    scale = f.meridional_scale
    grid_az = math.radians(az - f.meridian_convergence)
    ex, ez = dist * scale * math.sin(grid_az), dist * scale * math.cos(grid_az)
    x, z = proj.to_local(lon, lat)
    err = math.hypot(x - ex, z - ez)
    assert err < CONTROL_TOLERANCE_M, f"{name}: selisih {err:.3f} m"


@pytest.mark.parametrize("name,lon,lat", CONTROL_POINTS, ids=[c[0] for c in CONTROL_POINTS])
def test_control_point_distance_matches_geodesic_without_correction(proj, name, lon, lat):
    # Jarak lokal vs jarak geodesik murni: selisih hanya faktor skala UTM (~5e-5), < 0.5 m s.d. ~1 km.
    _, _, dist = Geod(ellps="WGS84").inv(proj.origin_lon, proj.origin_lat, lon, lat)
    x, z = proj.to_local(lon, lat)
    assert abs(math.hypot(x, z) - dist) < CONTROL_TOLERANCE_M


def test_axes_east_north(proj):
    x, z = proj.to_local(proj.origin_lon + 0.001, proj.origin_lat + 0.001)
    assert 100 < x < 120 and 100 < z < 120
    x, z = proj.to_local(proj.origin_lon - 0.001, proj.origin_lat - 0.001)
    assert x < -100 and z < -100


# --- round-trip ---

def test_roundtrip_single_below_1mm(proj):
    for _, lon, lat in CONTROL_POINTS:
        x, z = proj.to_local(lon, lat)
        lon2, lat2 = proj.to_lonlat(x, z)
        back_x, back_z = proj.to_local(lon2, lat2)
        assert math.hypot(back_x - x, back_z - z) < 1e-3
        # posisi lat/lng pulang ke titik awal (1e-9 derajat ~ 0.1 mm)
        assert lon2 == pytest.approx(lon, abs=1e-9)
        assert lat2 == pytest.approx(lat, abs=1e-9)


def test_array_matches_scalar_and_roundtrip(proj):
    lons = np.array([c[1] for c in CONTROL_POINTS])
    lats = np.array([c[2] for c in CONTROL_POINTS])
    xs, zs = proj.to_local_array(lons, lats)
    for i, (_, lon, lat) in enumerate(CONTROL_POINTS):
        assert (xs[i], zs[i]) == pytest.approx(proj.to_local(lon, lat), abs=1e-9)
    lon2, lat2 = proj.to_lonlat_array(xs, zs)
    np.testing.assert_allclose(lon2, lons, atol=1e-9)
    np.testing.assert_allclose(lat2, lats, atol=1e-9)


# --- GeoJSON ---

def _ll(dx, dy, proj):
    return [proj.origin_lon + dx, proj.origin_lat + dy]


def _flatten(g):
    """Semua angka koordinat geometri (termasuk GeometryCollection) sebagai list datar."""
    if g["type"] == "GeometryCollection":
        return [n for sub in g["geometries"] for n in _flatten(sub)]
    return np.asarray(g["coordinates"], dtype=float).ravel().tolist()


def test_geojson_all_geometry_types_and_roundtrip(proj):
    p = proj
    geoms = [
        {"type": "Point", "coordinates": _ll(0, 0, p)},
        {"type": "MultiPoint", "coordinates": [_ll(0.001, 0, p), _ll(0, 0.001, p)]},
        {"type": "LineString", "coordinates": [_ll(0, 0, p), _ll(0.001, 0.001, p)]},
        {
            "type": "MultiLineString",
            "coordinates": [[_ll(0, 0, p), _ll(0.001, 0, p)], [_ll(0, 0, p), _ll(0, 0.001, p)]],
        },
        {
            "type": "Polygon",
            "coordinates": [[_ll(0, 0, p), _ll(0.001, 0, p), _ll(0.001, 0.001, p), _ll(0, 0, p)]],
        },
        {
            "type": "MultiPolygon",
            "coordinates": [[[_ll(0, 0, p), _ll(0.001, 0, p), _ll(0.001, 0.001, p), _ll(0, 0, p)]]],
        },
        {"type": "GeometryCollection", "geometries": [{"type": "Point", "coordinates": _ll(0.001, 0.001, p)}]},
    ]
    for g in geoms:
        loc = p.geojson_to_local(g)
        assert loc["type"] == g["type"]
        back = p.geojson_to_lonlat(loc)
        assert _flatten(back) == pytest.approx(_flatten(g), abs=1e-9)


def test_geojson_feature_collection_keeps_properties_and_does_not_mutate(proj):
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1},
                "geometry": {"type": "Point", "coordinates": [proj.origin_lon, proj.origin_lat, 512.5]},
            },
            {"type": "Feature", "properties": {}, "geometry": None},
        ],
    }
    snapshot = json.dumps(fc, sort_keys=True)
    out = proj.geojson_to_local(fc)
    assert json.dumps(fc, sort_keys=True) == snapshot
    assert out["features"][0]["properties"] == {"id": 1}
    assert out["features"][0]["geometry"]["coordinates"] == [0.0, 0.0, 512.5]  # elevasi dipertahankan
    assert out["features"][1]["geometry"] is None


def test_geojson_bare_geometry_and_unknown_type(proj):
    out = proj.geojson_to_local({"type": "Point", "coordinates": [proj.origin_lon, proj.origin_lat]})
    assert out["coordinates"] == [0.0, 0.0]
    with pytest.raises(ValueError):
        proj.geojson_to_local({"type": "Circle", "coordinates": [0, 0]})


@pytest.mark.parametrize(
    "geom",
    [
        {"type": "Point", "coordinates": ["109.4", "-7.3"]},
        {"type": "Point", "coordinates": [True, False]},
        {"type": "Point", "coordinates": [109.4]},
        {"type": "Point", "coordinates": [109.4, -7.3, 1.0, 2.0]},
        {"type": "Point", "coordinates": [float("nan"), -7.3]},
        {"type": "Point", "coordinates": "109.4,-7.3"},
        {"type": "Point", "coordinates": 5},
        {"type": "LineString", "coordinates": [[109.4, -7.3], ["a", "b"]]},
        {"type": "LineString", "coordinates": ["ab", "cd"]},
        {"type": "Polygon", "coordinates": [[[109.4, -7.3], None]]},
    ],
)
def test_geojson_invalid_coordinates_raise_valueerror(proj, geom):
    with pytest.raises(ValueError):
        proj.geojson_to_local(geom)


def test_geojson_deterministic(proj):
    g = {"type": "LineString", "coordinates": [_ll(0.0003, 0.0002, proj), _ll(0.0011, -0.0004, proj)]}
    assert proj.geojson_to_local(g) == proj.geojson_to_local(g)


# --- chunk ---

@pytest.mark.parametrize(
    "x,z,expected",
    [
        (0, 0, "0_0"),
        (255.999, 255.999, "0_0"),
        (256, 256, "1_1"),
        (-0.001, -0.001, "-1_-1"),
        (-256, -256, "-1_-1"),
        (-256.001, 0, "-2_0"),
        (-1000, 700, "-4_2"),
    ],
)
def test_chunk_id(x, z, expected):
    assert chunk_id(x, z) == expected


def test_chunk_bounds_contain_point_and_negative():
    assert CHUNK_SIZE_M == 256
    assert chunk_bounds("0_0") == (0.0, 0.0, 256.0, 256.0)
    assert chunk_bounds("-1_-2") == (-256.0, -512.0, 0.0, -256.0)
    assert chunk_bounds(3, -1) == (768.0, -256.0, 1024.0, 0.0)
    for x, z in [(-0.5, 300.2), (-999.9, -0.1), (512.0, 512.0)]:
        minx, minz, maxx, maxz = chunk_bounds(chunk_id(x, z))
        assert minx <= x < maxx and minz <= z < maxz
        assert chunk_coords(x, z) == parse_chunk_id(chunk_id(x, z))


@pytest.mark.parametrize("bad", ["a_b", "1-2", "1_", "1_2_3", "", "1_2\n", "-0_1", "1_-0", "01_2", "+1_2", " 1_2"])
def test_parse_chunk_id_rejects_invalid(bad):
    with pytest.raises(ValueError):
        parse_chunk_id(bad)
