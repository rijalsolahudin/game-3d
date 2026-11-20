"""Test GAME-17: ekspor chunk (fixture sintetis, tanpa jaringan): skema, penyambungan jalan, dedup, tier, privasi, determinisme."""
import copy
import itertools
import json

import pytest
from shapely import wkt as shapely_wkt
from shapely.geometry import Polygon

from export import schema
from export.assemble import build_chunks
from export.config import ExportConfig
from export.geometry import split_polyline
from export.schema import TiersError, load_tiers
from export.tags import parse_meters, safe_name
from export.writer import dumps, write_export
from geo.projection import LocalProjection

PROJ = LocalProjection(109.4868011, -7.3486842)
CFG = ExportConfig()
META = {"inputs": [], "download_dates": {}, "origin": {"lat": -7.3486842, "lng": 109.4868011, "provisional": True},
        "boundary": {"provisional": True}}


def ll(x, z):
    lon, lat = PROJ.to_lonlat(x, z)
    return {"lon": lon, "lat": lat}


def way(i, tags, *pts):
    return {"type": "way", "id": i, "tags": tags, "geometry": [ll(*p) for p in pts], "nodes": list(range(i * 100, i * 100 + len(pts)))}


def rect(i, x, z, w, h, tags=None):
    pts = [(x, z), (x + w, z), (x + w, z + h), (x, z + h), (x, z)]
    return way(i, {"building": "yes", **(tags or {})}, *pts)


def boundary(half=1500.0):
    ring = [(-half, -half), (half, -half), (half, half), (-half, half), (-half, -half)]
    return Polygon([(ll(*p)["lon"], ll(*p)["lat"]) for p in ring])


def local_wkt(x, z, w, h, source="google", conf=0.9):
    pts = [PROJ.to_lonlat(px, pz) for px, pz in [(x, z), (x + w, z), (x + w, z + h), (x, z + h), (x, z)]]
    return {"source": source, "confidence": conf, "wkt": Polygon(pts).wkt}


def run(elements, ref=None, tiers=(), cfg=CFG):
    return build_chunks({"elements": elements}, ref, boundary(), PROJ, list(tiers), cfg)


def test_road_crossing_boundary_has_identical_cut_point_and_continuity():
    chunks, _, _ = run([way(1, {"highway": "residential"}, (200, 100), (300, 140), (400, 100))])
    a = chunks["0_0"]["roads"][0]
    b = chunks["1_0"]["roads"][0]
    assert a["osm_id"] == b["osm_id"] == "way/1"
    assert (a["seq"], b["seq"]) == (0, 1)
    assert a["continues_next"] and not a["continues_prev"] and b["continues_prev"] and not b["continues_next"]
    assert a["points"][-1] == b["points"][0]
    assert a["points"][-1][0] == 256.0  # tepat di garis batas
    assert a["points"][0] == [200.0, 100.0] and b["points"][-1] == [400.0, 100.0]


def test_road_spanning_three_chunks_and_corner_crossing():
    chunks, _, _ = run([way(1, {"highway": "track"}, (-10, -10), (600, 600))])
    ids = sorted(chunks)
    assert ids == ["-1_-1", "0_0", "1_1", "2_2"]
    pieces = sorted((r for c in chunks.values() for r in c["roads"]), key=lambda r: r["seq"])
    for p, q in itertools.pairwise(pieces):
        assert p["points"][-1] == q["points"][0]
        assert p["continues_next"] and q["continues_prev"]
    assert pieces[0]["points"][0] == [-10.0, -10.0] and pieces[-1]["points"][-1] == [600.0, 600.0]


def test_junction_vertices_preserved():
    pts = [(10, 10), (50, 12), (90, 30), (120, 31)]
    pieces = split_polyline(pts, 256, 2)
    assert len(pieces) == 1 and pieces[0]["points"] == [(float(x), float(z)) for x, z in pts]


def test_road_attributes_width_default_and_tag():
    chunks, stats, notes = run([
        way(1, {"highway": "secondary", "name": "Jalan Raya", "surface": "asphalt", "bridge": "yes", "layer": "1"}, (10, 10), (100, 10)),
        way(2, {"highway": "path", "width": "2,5 m"}, (10, 50), (100, 50)),
        way(3, {"highway": "service", "width": "lebar"}, (10, 80), (100, 80)),
        way(4, {"highway": "proposed"}, (10, 90), (100, 90)),
    ])
    roads = {r["osm_id"]: r for r in chunks["0_0"]["roads"]}
    assert roads["way/1"]["width_m"] == 7.0 and roads["way/1"]["name"] == "Jalan Raya"
    assert roads["way/1"]["bridge"] is True and roads["way/1"]["layer"] == 1 and roads["way/1"]["surface"] == "asphalt"
    assert roads["way/2"]["width_m"] == 2.5
    assert roads["way/3"]["width_m"] == 3.0
    assert "way/4" not in roads
    assert notes["skipped"]["roads_width_tag_invalid_default_used"] == 1
    assert notes["skipped"]["roads_excluded_proposed"] == 1


def test_polygon_area_split_per_chunk_and_water():
    elements = [
        way(1, {"landuse": "farmland"}, (200, 10), (300, 10), (300, 60), (200, 60), (200, 10)),
        way(2, {"natural": "water"}, (10, 10), (40, 10), (40, 40), (10, 40), (10, 10)),
    ]
    chunks, _, _ = run(elements)
    a, b = chunks["0_0"]["areas"], chunks["1_0"]["areas"]
    farm0 = [x for x in a if x["category"] == "landuse"][0]
    farm1 = b[0]
    assert farm0["kind"] == farm1["kind"] == "farmland"
    assert abs(farm0["area_m2"] + farm1["area_m2"] - 5000.0) < 1.0
    assert any(x["category"] == "water" for x in a)


def test_building_in_chunk_of_centroid_not_split_or_duplicated():
    chunks, _, _ = run([rect(1, 250, 10, 12, 10)])  # melintasi x=256, centroid x=256 -> chunk 1
    total = [b for c in chunks.values() for b in c["buildings"]]
    assert len(total) == 1 and "1_0" in chunks and chunks["1_0"]["buildings"][0]["osm_id"] == "way/1"
    b = total[0]
    assert b["source"] == "osm" and b["tier"] == "C" and len(b["footprint"][0]) == 4  # tanpa titik penutup


def test_building_height_rules_and_kind():
    chunks, _, _ = run([
        rect(1, 10, 10, 8, 8, {"height": "9 m"}),
        rect(2, 30, 10, 8, 8, {"building:levels": "2"}),
        rect(3, 50, 10, 8, 8, {"building": "house"}),
        rect(4, 70, 10, 20, 20),
    ])
    h = {b["osm_id"]: b for b in chunks["0_0"]["buildings"]}
    assert (h["way/1"]["height_m"], h["way/1"]["height_source"]) == (9.0, "tag_height")
    assert (h["way/2"]["height_m"], h["way/2"]["levels"]) == (6.0, 2)
    assert h["way/3"]["height_source"] == "default_kind" and h["way/3"]["kind"] == "house"
    assert h["way/4"]["height_source"] == "default_area" and h["way/4"]["levels"] is None


def test_privacy_no_name_or_address_in_output():
    tags = {"name": "Rumah Pak Budi", "addr:street": "Jl. Rahasia", "addr:housenumber": "12", "owner": "Budi",
            "operator": "Budi", "building": "house"}
    chunks, stats, notes = run([rect(1, 10, 10, 10, 10, tags)])
    text = dumps(chunks["0_0"])
    for leaked in ("Budi", "Rahasia", "addr", "name", "owner", "operator"):
        assert leaked not in text
    assert schema.errors("chunk", chunks["0_0"]) == []


def test_schema_rejects_name_on_building():
    chunks, _, _ = run([rect(1, 10, 10, 10, 10)])
    bad = copy.deepcopy(chunks["0_0"])
    bad["buildings"][0]["name"] = "Rumah Pak Budi"
    assert schema.errors("chunk", bad)


def test_supplement_dedup_filters_and_stats():
    osm = [rect(1, 100, 100, 10, 10)]
    ref = [
        local_wkt(101, 101, 10, 10),                      # tumpang tindih OSM -> ditolak
        local_wkt(300, 100, 10, 10),                      # diterima (Google)
        local_wkt(301, 100, 10, 10, conf=0.95),           # tumpang tindih pelengkap lain -> ditolak
        local_wkt(500, 100, 10, 10, conf=0.5),            # confidence rendah
        local_wkt(600, 100, 2, 2),                        # terlalu kecil
        local_wkt(700, 100, 40, 3),                       # bentuk tidak wajar (memanjang)
        local_wkt(800, 100, 10, 10, source="microsoft", conf=None),  # Microsoft tanpa skor -> diterima
        local_wkt(5000, 5000, 10, 10),                    # di luar batas
        {"source": "google", "confidence": None, "wkt": "POLYGON EMPTY"},  # Google tanpa skor -> baris tidak valid
    ]
    chunks, stats, _ = run(osm, ref)
    srcs = sorted(b["source"] for c in chunks.values() for b in c["buildings"])
    assert srcs == ["google", "microsoft", "osm"]
    assert stats["supp_accepted_google"] == 1 and stats["supp_accepted_microsoft"] == 1
    assert stats["supp_rejected_overlap_osm_centroid"] == 1
    assert stats["supp_rejected_low_confidence"] == 1
    assert stats["supp_rejected_too_small"] == 1
    assert stats["supp_rejected_bad_shape"] == 1
    assert stats["supp_rejected_outside_boundary"] == 1
    assert stats["supp_rejected_invalid_row"] == 1
    # urutan Google dulu: yang berkonfidensi lebih tinggi (0.95) menang atas yang 0.9
    assert stats["supp_rejected_overlap_supplementary_centroid"] == 1
    ms = [b for c in chunks.values() for b in c["buildings"] if b["source"] == "microsoft"][0]
    assert "confidence" not in ms and "osm_id" not in ms


def test_tier_a_marked_from_list_and_unmatched_reported():
    tiers = [{"id": "osm-way-1", "tier": "A", "landmark": "masjid_utama"}, {"id": "osm-way-2", "tier": "B"},
             {"id": "osm-way-999", "tier": "A"}]
    chunks, stats, notes = run([rect(1, 10, 10, 10, 10), rect(2, 40, 10, 10, 10), rect(3, 70, 10, 10, 10)], tiers=tiers)
    t = {b["osm_id"]: b for b in chunks["0_0"]["buildings"]}
    assert t["way/1"]["tier"] == "A" and t["way/1"]["landmark"] == "masjid_utama"
    assert t["way/2"]["tier"] == "B" and t["way/3"]["tier"] == "C"
    assert notes["tiers_unmatched"] == ["osm-way-999"]
    assert stats["buildings_tier_A"] == 1


def test_tiers_file_validation(tmp_path):
    p = tmp_path / "tiers.json"
    p.write_text(json.dumps({"version": 1, "entries": []}))
    assert load_tiers(p) == []
    p.write_text(json.dumps({"version": 1, "entries": [{"id": "osm-way-1", "tier": "C"}]}))
    with pytest.raises(TiersError):
        load_tiers(p)
    p.write_text(json.dumps({"version": 1, "entries": [{"id": "osm-way-1", "tier": "A"}, {"id": "osm-way-1", "tier": "B"}]}))
    with pytest.raises(TiersError):
        load_tiers(p)
    p.write_text(json.dumps({"version": 1, "entries": [{"id": "osm-way-1", "tier": "A", "owner": "x"}]}))
    with pytest.raises(TiersError):
        load_tiers(p)


def test_repo_tiers_file_is_valid_and_empty():
    from export.inputs import DATA
    assert load_tiers(DATA / "tiers.json") == []


def test_invalid_chunk_reported_not_written(tmp_path):
    chunks, stats, notes = run([rect(1, 10, 10, 10, 10), rect(2, 300, 10, 10, 10)])
    chunks["1_0"]["buildings"][0]["tier"] = "Z"
    out, rep = tmp_path / "chunks", tmp_path / "report.json"
    report = write_export(chunks, stats, notes, out, rep, META)
    assert report["ok"] is False and "1_0" in report["invalid_chunks"]
    assert (out / "0_0.json").exists() and not (out / "1_0.json").exists()
    assert json.loads(rep.read_text())["invalid_chunks"]["1_0"]


def test_output_validates_and_is_deterministic(tmp_path):
    elements = [way(1, {"highway": "residential"}, (200, 100), (300, 140), (400, 100)),
                way(2, {"landuse": "farmland"}, (200, 10), (300, 10), (300, 60), (200, 60), (200, 10)),
                rect(3, 10, 10, 10, 10), rect(4, 300, 300, 12, 9)]
    ref = [local_wkt(600, 100, 10, 10)]
    digests = []
    for n in range(2):
        chunks, stats, notes = run(elements, ref)
        out = tmp_path / f"o{n}"
        report = write_export(chunks, stats, notes, out, tmp_path / f"r{n}.json", META)
        assert report["ok"]
        digests.append({f.name: f.read_bytes() for f in sorted(out.iterdir())})
    assert digests[0] == digests[1] and "index.json" in digests[0]
    index = json.loads(digests[0]["index.json"])
    assert schema.errors("index", index) == []
    assert {s["id"] for s in index["sources"]} == {"osm", "google", "microsoft"}
    assert "OpenStreetMap contributors" in index["sources"][0]["attribution"]
    for entry in index["chunks"]:
        assert schema.errors("chunk", json.loads(digests[0][entry["file"]])) == []


def test_rewrite_removes_stale_chunks(tmp_path):
    out = tmp_path / "c"
    chunks, stats, notes = run([rect(1, 10, 10, 10, 10), rect(2, 300, 10, 10, 10)])
    write_export(chunks, stats, notes, out, tmp_path / "r.json", META)
    chunks, stats, notes = run([rect(1, 10, 10, 10, 10)])
    write_export(chunks, stats, notes, out, tmp_path / "r.json", META)
    assert sorted(p.name for p in out.iterdir()) == ["0_0.json", "index.json"]


def test_boundary_clip_roads_and_building_centroid():
    chunks, _, notes = run([way(1, {"highway": "residential"}, (1400, 0), (2400, 0)),
                            way(2, {"highway": "residential"}, (3000, 0), (3100, 0)),
                            rect(3, 1600, 0, 10, 10)])
    xs = [p[0] for c in chunks.values() for r in c["roads"] for p in r["points"]]
    assert max(xs) <= 1500 + CFG.boundary_margin_m + 0.01
    assert all(r["osm_id"] != "way/2" for c in chunks.values() for r in c["roads"])
    assert not any(b for c in chunks.values() for b in c["buildings"])


def test_tag_helpers():
    assert parse_meters("4.5 m", 0.3, 40) == 4.5 and parse_meters("99", 0.3, 40) is None and parse_meters(None, 0, 1) is None
    assert safe_name("Jalan Raya") == "Jalan Raya" and safe_name("a\nb") is None


def test_supplement_rows_are_not_mutating_geometry_shapes():
    # sanity fixture: wkt helper menghasilkan polygon valid yang bisa dibaca ulang
    assert shapely_wkt.loads(local_wkt(0, 0, 5, 5)["wkt"]).is_valid


def _reject_stats(osm, ref):
    _, stats, _ = run(osm, ref)
    return {k: v for k, v in stats.items() if k.startswith("supp_rejected_")}


def test_dedup_similar_boxes_shifted_30_percent_rejected_by_ratio():
    # kotak 10x10 digeser 6 m: centroid saling di luar, irisan 40 m2 = 40% luas -> ratio
    assert _reject_stats([rect(1, 100, 100, 10, 10)], [local_wkt(106, 100, 10, 10)]) == {"supp_rejected_overlap_osm_ratio": 1}


def test_dedup_real_case_ratio_0_3_is_rejected():
    # kasus review: irisan ~29,6% dari luas terkecil dengan centroid 5,6 m; ambang lama 0,30 meloloskannya
    assert _reject_stats([rect(1, 100, 100, 10, 10)], [local_wkt(105.6, 100, 10, 10)]) == {"supp_rejected_overlap_osm_ratio": 1}


def test_dedup_centroid_inside_osm_rejected():
    stats = _reject_stats([rect(1, 100, 100, 30, 30)], [local_wkt(110, 110, 6, 5)])
    assert stats == {"supp_rejected_overlap_osm_centroid": 1}


def test_dedup_osm_centroid_inside_supplement_rejected():
    stats = _reject_stats([rect(1, 110, 110, 6, 5)], [local_wkt(100, 100, 30, 30)])
    assert stats == {"supp_rejected_overlap_osm_centroid": 1}


def test_dedup_large_absolute_overlap_with_small_ratio_rejected_by_area():
    # dua bangunan 100x30 saling tumpang 3 m (90 m2, 3%): ratio kecil tetapi mesh saling tembus
    stats = _reject_stats([rect(1, 0, 100, 100, 30)], [local_wkt(97, 100, 100, 30)])
    assert stats == {"supp_rejected_overlap_osm_area": 1}


def test_dedup_touching_neighbours_are_kept():
    _, stats, _ = run([rect(1, 100, 100, 10, 10)], [local_wkt(110.5, 100, 10, 10)])
    assert stats["supp_accepted_google"] == 1


def test_outside_boundary_checked_before_other_filters():
    far_low_conf_small = local_wkt(5000, 5000, 2, 2, conf=0.1)
    assert _reject_stats([], [far_low_conf_small]) == {"supp_rejected_outside_boundary": 1}


def test_non_finite_numbers_rejected_by_schema_and_dumps():
    chunks, _, _ = run([rect(1, 10, 10, 10, 10)])
    bad = copy.deepcopy(chunks["0_0"])
    bad["buildings"][0]["height_m"] = float("nan")
    assert schema.errors("chunk", bad)
    with pytest.raises(ValueError):
        dumps(bad)


def test_out_dir_with_foreign_files_is_refused(tmp_path):
    from export.writer import OutputDirError
    chunks, stats, notes = run([rect(1, 10, 10, 10, 10)])
    out = tmp_path / "danger"
    out.mkdir()
    (out / "precious.txt").write_text("jangan hapus")
    with pytest.raises(OutputDirError):
        write_export(chunks, stats, notes, out, tmp_path / "r.json", META)
    assert (out / "precious.txt").read_text() == "jangan hapus"
    # folder ber-index tetapi dengan file asing juga ditolak
    ok = tmp_path / "ok"
    write_export(chunks, stats, notes, ok, tmp_path / "r.json", META)
    (ok / "notes.txt").write_text("x")
    with pytest.raises(OutputDirError):
        write_export(chunks, stats, notes, ok, tmp_path / "r.json", META)
    assert (ok / "notes.txt").exists()


def test_write_leaves_no_temp_dirs(tmp_path):
    chunks, stats, notes = run([rect(1, 10, 10, 10, 10)])
    write_export(chunks, stats, notes, tmp_path / "c", tmp_path / "r.json", META)
    write_export(chunks, stats, notes, tmp_path / "c", tmp_path / "r.json", META)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["c", "r.json"]


def test_invalid_boundary_aborts_with_clear_error(tmp_path):
    from export.inputs import load_inputs
    from osm.meta import build_meta
    from osm.parse import RawFormatError
    raw = tmp_path / "raw" / "osm"
    raw.mkdir(parents=True)
    rawfile = raw / "osm_all_2026-01-01.json"
    data = {"elements": []}
    rawfile.write_text(json.dumps(data))
    meta = build_meta(data=data, raw_file=rawfile, endpoint="x", query="q", bbox_swne=[0, 0, 1, 1],
                      downloaded_at="2026-01-01T00:00:00Z", provisional=True)
    (raw / "osm_all_2026-01-01.meta.json").write_text(json.dumps(meta))
    (tmp_path / "boundary.geojson").write_text("{}")
    with pytest.raises(RawFormatError):
        load_inputs(tmp_path)


def test_schema_constants_match_tags_module():
    from export import tags
    defs = json.loads((schema.SCHEMA_DIR / "chunk.schema.json").read_text())["$defs"]
    assert defs["slug"]["pattern"] == f"^{tags.SLUG_PATTERN}$"
    assert defs["line"]["properties"]["surface"]["pattern"] == f"^{tags.SURFACE_PATTERN}$"
    assert defs["line"]["properties"]["name"]["maxLength"] == tags.MAX_NAME_LEN
    tiers = json.loads((schema.SCHEMA_DIR / "tiers.schema.json").read_text())
    assert tiers["properties"]["entries"]["items"]["properties"]["landmark"]["pattern"] == f"^{tags.SLUG_PATTERN}$"


def test_attribution_single_source_in_index_and_readme():
    from export.config import SOURCE_INFO
    from export.inputs import ROOT
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for info in SOURCE_INFO.values():
        assert info["attribution"] in readme and info["license_url"]
        assert "VIDA" in info["attribution"] or info["name"] == "OpenStreetMap"
    chunks, stats, notes = run([rect(1, 10, 10, 10, 10)])
    from export.writer import build_index
    idx = build_index({}, stats, META, CFG)
    assert [s["attribution"] for s in idx["sources"]] == [i["attribution"] for i in SOURCE_INFO.values()]
    assert schema.errors("index", idx) == []
