import json
from pathlib import Path

import pytest
from shapely.geometry import Point, shape
from shapely.ops import transform

from geo.projection import lonlat_to_local, lonlat_to_utm, transformer_to_utm

DATA = Path(__file__).resolve().parents[1] / "data"
VILLAGE = (109.4864955, -7.3487136)  # node OSM 1308706192 (lon, lat)


@pytest.fixture(scope="module")
def fc():
    return json.loads((DATA / "boundary.geojson").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def feat(fc):
    assert len(fc["features"]) == 1
    return fc["features"][0]


@pytest.fixture(scope="module")
def poly(feat):
    return shape(feat["geometry"])


@pytest.fixture(scope="module")
def origin():
    return json.loads((DATA / "origin.json").read_text(encoding="utf-8"))


def area_km2(g):
    return transform(transformer_to_utm().transform, g).area / 1e6


def test_geojson_valid_and_crs(fc, feat, poly):
    assert fc["type"] == "FeatureCollection"
    assert "CRS84" in fc["crs"]["properties"]["name"]  # lon/lat WGS84
    assert poly.is_valid and poly.geom_type == "Polygon"
    minx, miny, maxx, maxy = poly.bounds
    assert 108 < minx < maxx < 111 and -8.5 < miny < maxy < -6.5
    assert feat["properties"]["crs"] == "EPSG:4326"


def test_provisional_properties(feat):
    p = feat["properties"]
    assert p["provisional"] is True
    assert p["method"] == "circle_around_osm_village_node"
    assert p["osm_node"] == 1308706192
    assert p["radius_m"] > 0
    assert p["license"] == "ODbL (OSM)"
    assert p["retrieved_at"] and "diganti" in p["note"]


def test_circle_matches_radius(feat, poly):
    r = feat["properties"]["radius_m"]
    center = Point(*lonlat_to_utm(*VILLAGE))
    u = transform(transformer_to_utm().transform, poly)
    assert u.contains(center)
    dists = [center.distance(Point(c)) for c in u.exterior.coords]
    assert min(dists) == pytest.approx(r, abs=0.5) and max(dists) == pytest.approx(r, abs=0.5)
    assert area_km2(poly) == pytest.approx(3.14159265 * r * r / 1e6, rel=0.01)
    assert feat["properties"]["area_km2"] == pytest.approx(area_km2(poly), abs=1e-3)


def test_origin_inside_polygon(poly, origin):
    assert poly.contains(Point(origin["lng"], origin["lat"]))
    assert len(str(origin["lat"]).split(".")[1]) >= 6
    assert len(str(origin["lng"]).split(".")[1]) >= 6
    assert origin["provisional"] is True and origin["source"] and origin["reason"]


def test_projection_local_origin_is_zero(origin):
    assert lonlat_to_local(origin["lng"], origin["lat"], origin["lng"], origin["lat"]) == (0.0, 0.0)
    ux, uy = lonlat_to_utm(origin["lng"], origin["lat"])
    assert [round(ux, 2), round(uy, 2)] == origin["utm49s"]
