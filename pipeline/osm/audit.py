"""Orkestrasi audit: dari raw OSM (+ pembanding opsional) ke dict hasil yang dirender osm.report."""
from __future__ import annotations

import json
from pathlib import Path

from osm import completeness, network, stats
from osm.geom import origin_utm, project
from osm.meta import load_meta
from osm.parse import boundary_polygon, clip_to_boundary, load_raw, parse_elements

# kategori yang diharapkan ada untuk kemiripan visual desa (dipakai di bagian "yang hilang")
REF_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "open_buildings_meta.schema.json"

VISUAL_EXPECTED = {
    "landuse": ("farmland", "orchard", "meadow", "forest", "residential", "grass"),
    "natural": ("water", "wood", "tree_row", "tree", "scrub", "wetland"),
    "waterway": ("river", "stream", "canal", "ditch", "drain"),
    "leisure": ("pitch", "park", "garden"),
    "amenity": ("place_of_worship", "school", "townhall", "marketplace", "grave_yard"),
    "place": ("village", "hamlet", "isolated_dwelling", "locality"),
}


def run(raw_path: Path, boundary_path: Path, origin_path: Path, ref_path: Path | None = None) -> dict:
    """Jalankan audit. MetaError bila metadata raw/pembanding hilang, tidak valid, atau sha256 tidak cocok."""
    meta = load_meta(raw_path)
    boundary = boundary_polygon(boundary_path)
    boundary_utm = project(boundary)
    origin = json.loads(origin_path.read_text(encoding="utf-8"))
    oxy = origin_utm(origin)

    items, skipped = parse_elements(load_raw(raw_path))
    kept = clip_to_boundary(items, boundary)
    roads_all = network.road_items(kept)

    blds = stats.buildings(kept, boundary_utm)
    res = {
        "meta": meta,
        "origin_utm": [round(v, 2) for v in oxy],
        "boundary": _boundary_info(boundary_path, boundary_utm),
        "skipped_no_geometry": skipped,
        "counts": stats.category_counts(kept),
        "road_km": stats.road_lengths_km(kept, boundary_utm),
        "waterway_km": stats.waterway_lengths_km(kept, boundary_utm),
        "buildings": stats.building_summary(blds, oxy),
        "network": network.analyze(roads_all, boundary_utm),
        "road_proximity": _buildings_far_from_roads(blds, roads_all),
    }
    res["visual_missing"] = {
        k: [v for v in vals if v not in res["counts"].get(k, {})] for k, vals in VISUAL_EXPECTED.items()}
    if ref_path and ref_path.exists():
        res["reference"] = _reference(ref_path, blds, boundary_utm, oxy)
    return res


def _boundary_info(path: Path, boundary_utm) -> dict:
    props = json.loads(path.read_text(encoding="utf-8"))["features"][0]["properties"]
    return {"area_km2": round(boundary_utm.area / 1e6, 4), "provisional": bool(props.get("provisional")),
            "method": props.get("method", ""), "radius_m": props.get("radius_m")}


def _buildings_far_from_roads(blds: list[dict], roads: list[dict]) -> dict:
    """Bangunan OSM yang jauh dari jalan OSM mana pun (indikasi jalan/gang akses hilang)."""
    from shapely.strtree import STRtree

    if not roads or not blds:
        return {"threshold_m": FAR_M, "count": 0, "pct": 0.0}
    lines = [project(r["geom"]) for r in roads]
    tree = STRtree(lines)
    far = 0
    for b in blds:
        idx = tree.nearest(b["geom"].centroid)
        if lines[idx].distance(b["geom"]) > FAR_M:
            far += 1
    return {"threshold_m": FAR_M, "count": far, "pct": round(100 * far / len(blds), 1)}


FAR_M = 60.0  # bangunan > FAR_M dari jalan OSM terdekat dianggap tanpa akses terpetakan


def _reference(ref_path: Path, blds, boundary_utm, oxy) -> dict:
    ref_meta = load_meta(ref_path, REF_SCHEMA)
    parsed = completeness.read_reference(ref_path)
    ref = completeness.select_reference(parsed["rows"], boundary_utm)
    return {
        "meta": ref_meta,
        "rows_total": parsed["total"],
        "rows_invalid": parsed["invalid"],
        "min_confidence": completeness.MIN_CONFIDENCE,
        "match_overlap": completeness.MATCH_OVERLAP,
        "summary": completeness.summary(blds, ref),
        "sensitivity": completeness.sensitivity(
            blds, lambda c: completeness.select_reference(parsed["rows"], boundary_utm, c)),
        "per_chunk": completeness.per_chunk(blds, ref, oxy),
        "missing_cells": completeness.missing_clusters(blds, ref, oxy),
        "cell_m": completeness.CELL_M,
        "occupancy": completeness.cell_occupancy(blds, ref, boundary_utm, oxy),
    }
