"""Test GAME-6: query, parsing, clip, validasi metadata, statistik, jaringan, kelengkapan, laporan. Tanpa jaringan."""
import json

import pytest
from shapely.geometry import Polygon, box

from geo.projection import lonlat_to_utm, utm_to_lonlat
from osm import completeness, network, stats
from osm.geom import chunk_id, project
from osm.meta import MetaError, build_meta, load_meta, validate_meta
from osm.parse import (RawFormatError, clip_to_boundary, element_geometry, is_area_way, parse_elements,
                       validate_raw)
from osm.query import TAG_KEYS, build_query
from osm.report import render

OX, OY = lonlat_to_utm(109.4868011, -7.3486842)  # origin usulan


def ll(dx, dy):
    """Titik (lon, lat) pada offset meter dari origin."""
    return utm_to_lonlat(OX + dx, OY + dy)


def geom(*offsets):
    return [{"lon": ll(*o)[0], "lat": ll(*o)[1]} for o in offsets]


def way(i, tags, *offsets, nodes=None):
    return {"type": "way", "id": i, "tags": tags, "geometry": geom(*offsets),
            "nodes": nodes or list(range(i * 100, i * 100 + len(offsets)))}


def square(i, x, y, s=10, tags=None):
    pts = [(x, y), (x + s, y), (x + s, y + s), (x, y + s), (x, y)]
    return way(i, tags or {"building": "yes"}, *pts)


@pytest.fixture
def raw():
    return {"osm3s": {"timestamp_osm_base": "2026-01-01T00:00:00Z"}, "elements": [
        {"type": "node", "id": 1, "lat": -7.3487, "lon": 109.4864},  # node referensi tanpa tag
        {"type": "node", "id": 2, "lat": -7.3487, "lon": 109.4865, "tags": {"place": "village", "name": "X"}},
        way(10, {"highway": "residential"}, (0, 0), (100, 0), nodes=[1, 2]),
        square(20, 20, 20),
        square(21, 5000, 5000),  # di luar batas
        {"type": "relation", "id": 30, "tags": {"type": "multipolygon", "building": "yes"}, "members": [
            {"type": "way", "role": "outer", "geometry": geom((200, 200), (260, 200), (260, 260), (200, 260), (200, 200))},
            {"type": "way", "role": "inner", "geometry": geom((220, 220), (240, 220), (240, 240), (220, 240), (220, 220))},
        ]},
        {"type": "node", "id": 3, "lat": -7.35, "lon": 109.49, "tags": {"foo": "bar"}},  # bukan kategori
    ]}


@pytest.fixture
def boundary():
    lo, la = ll(-500, -500)
    hi_lo, hi_la = ll(500, 500)
    return box(lo, la, hi_lo, hi_la)


def test_query_covers_all_categories_and_bbox():
    q = build_query((-7.36, 109.47, -7.33, 109.50))
    for k in TAG_KEYS:
        assert f'nwr["{k}"](' in q
    for k in ("highway", "waterway", "natural", "landuse", "leisure", "amenity", "building", "barrier", "man_made", "place"):
        assert k in TAG_KEYS
    assert "-7.3600000,109.4700000,-7.3300000,109.5000000" in q and "out geom" in q and "node(w.a)" in q


def test_validate_raw_rejects_bad():
    with pytest.raises(RawFormatError):
        validate_raw({"nope": []})
    with pytest.raises(RawFormatError):
        validate_raw({"elements": [{"type": "node", "id": 1}]})
    with pytest.raises(RawFormatError):
        validate_raw({"elements": [{"type": "alien", "id": 1}]})


def test_area_rules():
    assert is_area_way({"building": "yes"}, True)
    assert not is_area_way({"building": "yes"}, False)
    assert not is_area_way({"highway": "residential"}, True)
    assert is_area_way({"highway": "pedestrian", "area": "yes"}, True)
    assert not is_area_way({"natural": "tree_row"}, True)
    assert is_area_way({"natural": "water"}, True)


def test_multipolygon_has_hole(raw):
    g = element_geometry(raw["elements"][5])
    assert g.geom_type == "Polygon" and len(g.interiors) == 1
    assert project(g).area == pytest.approx(60 * 60 - 20 * 20, rel=0.01)


def test_parse_and_clip(raw, boundary):
    validate_raw(raw)
    items, skipped = parse_elements(raw)
    assert skipped == []
    assert {(i["type"], i["id"]) for i in items} == {("node", 2), ("way", 10), ("way", 20), ("way", 21), ("relation", 30)}
    kept = clip_to_boundary(items, boundary)
    assert {i["id"] for i in kept} == {2, 10, 20, 30}
    assert [(i["type"], i["id"]) for i in items] == sorted((i["type"], i["id"]) for i in items)  # deterministik


def test_incomplete_relation_is_reported_not_dropped():
    items, skipped = parse_elements({"elements": [{"type": "relation", "id": 9, "tags": {"building": "yes"}, "members": []}]})
    assert items == [] and skipped == [{"type": "relation", "id": 9, "cats": ["building"]}]


def test_meta_roundtrip_and_validation(raw, tmp_path):
    p = tmp_path / "osm_all_2026-01-01.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    m = build_meta(data=raw, raw_file=p, endpoint="https://x", query="q", bbox_swne=(1, 2, 3, 4),
                   downloaded_at="2026-01-01T10:00:00Z", provisional=True)
    assert m["download_date"] == "2026-01-01" and m["osm_base_timestamp"] == "2026-01-01T00:00:00Z"
    assert m["element_counts"]["way"] == 3 and m["element_counts"]["relation"] == 1
    assert m["license"].startswith("ODbL") and "OpenStreetMap" in m["attribution"]
    del m["raw_sha256"]
    with pytest.raises(MetaError):
        validate_meta(m)
    m["raw_sha256"] = 5
    with pytest.raises(MetaError):
        validate_meta(m)


def test_chunk_id_floor_and_sign():
    assert chunk_id(OX + 10, OY + 10, (OX, OY)) == "0_0"
    assert chunk_id(OX - 1, OY + 256, (OX, OY)) == "-1_1"
    assert chunk_id(OX + 255.9, OY - 0.1, (OX, OY)) == "0_-1"


def _items(raw, boundary):
    items, _ = parse_elements(raw)
    return clip_to_boundary(items, boundary)


def test_stats(raw, boundary):
    kept = _items(raw, boundary)
    bu = project(boundary)
    assert stats.road_lengths_km(kept, bu) == {"residential": {"ways": 1, "km": 0.1}}
    blds = stats.buildings(kept, bu)
    assert len(blds) == 2
    s = stats.building_summary(blds, (OX, OY))
    assert s["count"] == 2 and s["total_area_m2"] == pytest.approx(100 + 3200, rel=0.01)
    assert s["per_chunk"] == {"0_0": 2}
    assert stats.category_counts(kept)["building"] == {"yes": 2}


def test_network_components_deadend_gap():
    # way A: (0,0)-(100,0) dan B: (100,0)-(100,100) berbagi simpul 2; C berujung 10 m dari A tanpa simpul
    a = way(1, {"highway": "residential"}, (0, 0), (100, 0), nodes=[1, 2])
    b = way(2, {"highway": "residential"}, (100, 0), (100, 100), nodes=[2, 3])
    c = way(3, {"highway": "residential"}, (50, 10), (50, 200), nodes=[7, 8])
    far = way(4, {"highway": "residential"}, (300, 300), (300, 400), nodes=[20, 21])
    roads = [{**r, "geom": element_geometry(r)} for r in (a, b, c, far)]
    comps = network.components(roads)
    assert sorted(len(x) for x in comps) == [1, 1, 2]
    res = network.analyze(roads, project(box(*ll(-1000, -1000), *ll(1000, 1000))))
    assert res["roads"] == 4 and len(res["components"]) == 3
    gaps = {g["way"]: g for g in res["gaps"]}
    assert gaps["way/3"]["gap_m"] == pytest.approx(10, abs=0.5) and gaps["way/3"]["near_way"] == "way/1"
    assert any(d["way"] == "way/4" for d in res["dead_ends"])
    assert res["unnamed"] == {"residential": 4} and res["crossings"] == []


def test_network_crossing_without_node():
    a = way(1, {"highway": "residential"}, (-50, 0), (50, 0), nodes=[1, 2])
    b = way(2, {"highway": "residential"}, (0, -50), (0, 50), nodes=[3, 4])
    roads = [{**r, "geom": element_geometry(r)} for r in (a, b)]
    res = network.analyze(roads, project(box(*ll(-1000, -1000), *ll(1000, 1000))))
    assert len(res["crossings"]) == 1


def test_completeness_match():
    osm = [{"geom": Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])}]
    ref = [{"source": "google", "conf": 0.9, "geom": Polygon([(1, 1), (9, 1), (9, 9), (1, 9)]), "area": 64.0},
           {"source": "google", "conf": 0.9, "geom": Polygon([(50, 50), (60, 50), (60, 60), (50, 60)]), "area": 100.0}]
    s = completeness.summary(osm, ref)
    assert s["coverage_pct"] == 50.0 and s["osm_confirmed_by_ref"] == 1 and s["lincoln_petersen_total"] == 2
    assert s["ref_missing_area_m2"] == 100.0


def test_load_reference_filters_confidence_and_boundary(tmp_path):
    def wkt_sq(dx, dy):
        pts = [ll(dx, dy), ll(dx + 10, dy), ll(dx + 10, dy + 10), ll(dx, dy + 10), ll(dx, dy)]
        return "POLYGON((" + ",".join(f"{x} {y}" for x, y in pts) + "))"

    rows = [{"source": "google", "confidence": 0.9, "area_m2": 100, "wkt": wkt_sq(0, 0)},
            {"source": "google", "confidence": 0.5, "area_m2": 100, "wkt": wkt_sq(20, 0)},
            {"source": "microsoft", "confidence": -1, "area_m2": 100, "wkt": wkt_sq(40, 0)},
            {"source": "google", "confidence": 0.9, "area_m2": 100, "wkt": wkt_sq(5000, 0)}]
    p = tmp_path / "ref.json"
    p.write_text(json.dumps(rows), encoding="utf-8")
    out = completeness.load_reference(p, project(box(*ll(-500, -500), *ll(500, 500))))
    assert [r["source"] for r in out] == ["google", "microsoft"]


def test_report_deterministic_and_private(raw, boundary):
    from osm.audit import run  # noqa: F401  (import sanity)

    kept = _items(raw, boundary)
    bu = project(boundary)
    blds = stats.buildings(kept, bu)
    blds[0]["tags"] = {"building": "yes", "name": "RAHASIA-PEMILIK", "addr:street": "RAHASIA-JALAN"}
    res = {
        "meta": {"raw_file": "x.json", "downloaded_at": "2026-01-01T00:00:00Z", "osm_base_timestamp": "t",
                 "source": "s", "endpoint": "e", "element_counts": {"total": 1, "node": 0, "way": 1, "relation": 0},
                 "bbox_swne": [0, 0, 0, 0], "license": "ODbL 1.0", "attribution": "(c) OpenStreetMap contributors",
                 "raw_sha256": "a" * 64},
        "origin_utm": [OX, OY], "boundary": {"area_km2": 1.0, "provisional": True, "method": "circle", "radius_m": 1500.0}, "skipped_no_geometry": [],
        "counts": stats.category_counts(kept), "road_km": stats.road_lengths_km(kept, bu), "waterway_km": {},
        "buildings": stats.building_summary(blds, (OX, OY)),
        "network": {"roads": 1, "components": [{"ways": 1, "km": 0.1, "sample": "way/10", "types": {}}],
                    "dead_ends": [], "gaps": [], "crossings": [], "named": {}, "unnamed": {"residential": 1},
                    "attrs": {"surface": 0, "width": 0, "lanes": 0, "oneway": 0, "maxspeed": 0}},
        "road_proximity": {"threshold_m": 60.0, "count": 0, "pct": 0.0},
        "visual_missing": {"landuse": ["farmland"]},
    }
    a, b = render(res), render(res)
    assert a == b
    assert "RAHASIA" not in a
    assert "ODbL" in a and "Perlu pelengkapan" in a


def test_meta_rejects_bool_for_number(tmp_path):
    schema = tmp_path / "s.json"
    schema.write_text(json.dumps({"required": ["n"], "properties": {"n": {"type": "integer"}}}), encoding="utf-8")
    validate_meta({"n": 3}, schema)
    with pytest.raises(MetaError):
        validate_meta({"n": True}, schema)


def test_load_meta_checks_sha_and_missing_file(raw, tmp_path):
    p = tmp_path / "osm_all_2026-01-01.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(MetaError, match="tidak ada"):
        load_meta(p)
    m = build_meta(data=raw, raw_file=p, endpoint="e", query="q", bbox_swne=(1, 2, 3, 4),
                   downloaded_at="2026-01-01T10:00:00Z", provisional=False)
    p.with_suffix(".meta.json").write_text(json.dumps(m), encoding="utf-8")
    assert load_meta(p)["raw_sha256"] == m["raw_sha256"]
    p.write_text(json.dumps(raw) + " ", encoding="utf-8")  # raw berubah
    with pytest.raises(MetaError, match="sha256"):
        load_meta(p)


def test_read_reference_counts_invalid_rows(tmp_path):
    good = "POLYGON((0 0,0.001 0,0.001 0.001,0 0.001,0 0))"
    rows = [{"source": "google", "confidence": 0.9, "wkt": good},
            {"source": "google", "confidence": None, "wkt": good},   # google tanpa confidence
            {"source": "google", "confidence": True, "wkt": good},   # bool bukan angka
            {"source": "bing", "confidence": 0.9, "wkt": good},      # sumber tak dikenal
            {"source": "microsoft", "confidence": -1, "wkt": "POLYGON((bukan wkt"},
            {"source": "microsoft", "confidence": -1, "wkt": "POINT(1 1)"},
            "bukan dict"]
    p = tmp_path / "r.json"
    p.write_text(json.dumps(rows), encoding="utf-8")
    out = completeness.read_reference(p)
    assert out["total"] == 7 and out["invalid"] == 6 and len(out["rows"]) == 1
    p.write_text(json.dumps({"bukan": "list"}), encoding="utf-8")
    with pytest.raises(completeness.ReferenceFormatError):
        completeness.read_reference(p)
