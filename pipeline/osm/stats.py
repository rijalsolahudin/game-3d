"""Statistik per kategori: jumlah, panjang jalan per tipe, luas bangunan, sebaran per chunk (semua di UTM 49S)."""
from __future__ import annotations

from collections import Counter, defaultdict

from osm.geom import chunk_id, project

MIN_BUILDING_AREA_M2 = 8.0  # footprint lebih kecil dianggap janggal (bukan rumah)
LINEAR_AREAL = ("LineString", "MultiLineString")
AREAL = ("Polygon", "MultiPolygon")


def category_counts(items: list[dict]) -> dict[str, dict[str, int]]:
    """{kategori: {nilai tag: jumlah}} (hanya item yang beririsan dengan batas)."""
    out: dict[str, Counter] = defaultdict(Counter)
    for it in items:
        for c in it["cats"]:
            out[c][it["tags"][c]] += 1
    return {c: dict(sorted(v.items())) for c, v in sorted(out.items())}


def road_lengths_km(items: list[dict], boundary_utm) -> dict[str, dict]:
    """Panjang jalan per tipe highway yang berada DI DALAM batas (clip), total km dan jumlah way."""
    out: dict[str, dict] = {}
    for it in items:
        if "highway" not in it["tags"] or it["geom"].geom_type not in LINEAR_AREAL:
            continue
        length = project(it["geom"]).intersection(boundary_utm).length
        if length <= 0:
            continue
        r = out.setdefault(it["tags"]["highway"], {"ways": 0, "km": 0.0})
        r["ways"] += 1
        r["km"] += length / 1000
    return {k: {"ways": v["ways"], "km": round(v["km"], 3)} for k, v in sorted(out.items(), key=lambda kv: -kv[1]["km"])}


def waterway_lengths_km(items: list[dict], boundary_utm) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for it in items:
        if "waterway" in it["tags"] and it["geom"].geom_type in LINEAR_AREAL:
            out[it["tags"]["waterway"]] += project(it["geom"]).intersection(boundary_utm).length / 1000
    return {k: round(v, 3) for k, v in sorted(out.items())}


def buildings(items: list[dict], boundary_utm) -> list[dict]:
    """Bangunan (poligon) dengan titik wakil di dalam batas, geometri di UTM, beserta luas."""
    out = []
    for it in items:
        if "building" not in it["tags"] or it["geom"].geom_type not in AREAL:
            continue
        g = project(it["geom"])
        if not boundary_utm.contains(g.representative_point()):
            continue
        out.append({"id": f"{it['type']}/{it['id']}", "tags": it["tags"], "geom": g, "area": g.area})
    return out


def building_summary(blds: list[dict], origin_xy: tuple[float, float]) -> dict:
    areas = sorted(b["area"] for b in blds)
    per_chunk = Counter(chunk_id(b["geom"].centroid.x, b["geom"].centroid.y, origin_xy) for b in blds)
    n = len(areas)
    return {
        "count": n,
        "total_area_m2": round(sum(areas), 1),
        "median_area_m2": round(areas[n // 2], 1) if n else 0.0,
        "tiny_lt_min": sum(1 for a in areas if a < MIN_BUILDING_AREA_M2),
        "tiny_ids": [b["id"] for b in blds if b["area"] < MIN_BUILDING_AREA_M2][:20],
        "by_type": dict(sorted(Counter(b["tags"]["building"] for b in blds).items())),
        "with_name": sum(1 for b in blds if "name" in b["tags"]),
        "with_levels": sum(1 for b in blds if "building:levels" in b["tags"]),
        "with_roof": sum(1 for b in blds if "roof:shape" in b["tags"]),
        "with_addr": sum(1 for b in blds if any(k.startswith("addr:") for k in b["tags"])),
        "per_chunk": dict(sorted(per_chunk.items(), key=lambda kv: tuple(int(p) for p in kv[0].split("_")))),
    }
