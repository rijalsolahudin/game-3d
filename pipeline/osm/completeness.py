"""Perkiraan kelengkapan footprint bangunan OSM terhadap footprint pembanding (Google/Microsoft), hanya untuk audit."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from shapely import wkt
from shapely.geometry import Point
from shapely.strtree import STRtree

from osm.geom import chunk_id, project

MIN_CONFIDENCE = 0.70      # rekomendasi Google Open Buildings; Microsoft tidak punya skor (selalu dipakai)
MATCH_OVERLAP = 0.30       # irisan / luas bangunan terkecil agar dianggap bangunan yang sama
SENSITIVITY = (0.65, 0.70, 0.75, 0.80, 0.90)
CELL_M = 64.0              # ukuran sel untuk peta area tanpa bangunan OSM


REF_SOURCES = ("google", "microsoft")


class ReferenceFormatError(ValueError):
    """File pembanding bukan list baris yang diharapkan."""


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v  # tolak bool dan NaN


def _parse_row(r) -> dict | None:
    """Baris pembanding valid -> {source, conf, geom(UTM), area}; None bila tidak valid."""
    if not isinstance(r, dict) or r.get("source") not in REF_SOURCES or not isinstance(r.get("wkt"), str):
        return None
    conf = r.get("confidence")
    if conf is not None and not _num(conf):
        return None
    if r["source"] == "google" and conf is None:
        return None
    try:
        g = wkt.loads(r["wkt"])
    except Exception:  # shapely.errors.GEOSException / WKT parse error
        return None
    if g.geom_type not in ("Polygon", "MultiPolygon") or g.is_empty:
        return None
    if not g.is_valid:
        g = g.buffer(0)
        if g.is_empty:
            return None
    g = project(g)
    return {"source": r["source"], "conf": conf, "geom": g, "area": g.area}


def read_reference(path: Path) -> dict:
    """Baca dan validasi semua baris; baris tidak valid ditolak dan dihitung: {rows, invalid, total}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ReferenceFormatError("raw pembanding harus berupa list baris")
    rows = [p for p in map(_parse_row, data) if p is not None]
    return {"rows": rows, "invalid": len(data) - len(rows), "total": len(data)}


def select_reference(rows: list[dict], boundary_utm, min_conf: float = MIN_CONFIDENCE) -> list[dict]:
    """Baris dengan titik wakil di dalam batas dan (untuk Google) confidence >= min_conf."""
    return [r for r in rows
            if (r["source"] != "google" or r["conf"] >= min_conf)
            and boundary_utm.contains(r["geom"].representative_point())]


def load_reference(path: Path, boundary_utm, min_conf: float = MIN_CONFIDENCE) -> list[dict]:
    return select_reference(read_reference(path)["rows"], boundary_utm, min_conf)


def match(osm_blds: list[dict], ref: list[dict]) -> dict:
    """Pasangkan footprint OSM dan pembanding; kembalikan indeks ref tercakup & OSM terkonfirmasi."""
    tree = STRtree([b["geom"] for b in osm_blds])
    covered, osm_hit = set(), set()
    for ri, r in enumerate(ref):
        for oi in tree.query(r["geom"]):
            o = osm_blds[oi]["geom"]
            inter = r["geom"].intersection(o).area
            if inter > 0 and inter / min(r["geom"].area, o.area) >= MATCH_OVERLAP:
                covered.add(ri)
                osm_hit.add(int(oi))
    return {"covered_ref": covered, "osm_confirmed": osm_hit}


def summary(osm_blds: list[dict], ref: list[dict]) -> dict:
    m = match(osm_blds, ref)
    n_osm, n_ref = len(osm_blds), len(ref)
    covered, hit = len(m["covered_ref"]), len(m["osm_confirmed"])
    est_total = round(n_osm * n_ref / hit) if hit else None  # Lincoln-Petersen
    return {
        "n_osm": n_osm, "n_ref": n_ref, "ref_covered_by_osm": covered, "osm_confirmed_by_ref": hit,
        "coverage_pct": round(100 * covered / n_ref, 1) if n_ref else None,
        "ref_recall_pct": round(100 * hit / n_osm, 1) if n_osm else None,
        "lincoln_petersen_total": est_total,
        "osm_only": n_osm - hit,
        "ref_by_source": dict(Counter(r["source"] for r in ref)),
        "ref_total_area_m2": round(sum(r["area"] for r in ref), 1),
        "ref_missing_area_m2": round(sum(r["area"] for i, r in enumerate(ref) if i not in m["covered_ref"]), 1),
    }


def sensitivity(osm_blds: list[dict], ref_all_loader) -> list[dict]:
    """Cakupan pada beberapa ambang confidence; ref_all_loader(min_conf) -> list ref."""
    rows = []
    for c in SENSITIVITY:
        ref = ref_all_loader(c)
        s = summary(osm_blds, ref)
        rows.append({"min_conf": c, "n_ref": s["n_ref"], "coverage_pct": s["coverage_pct"],
                     "lincoln_petersen_total": s["lincoln_petersen_total"]})
    return rows


def per_chunk(osm_blds: list[dict], ref: list[dict], origin_xy) -> list[dict]:
    m = match(osm_blds, ref)
    osm_c = Counter(chunk_id(b["geom"].centroid.x, b["geom"].centroid.y, origin_xy) for b in osm_blds)
    ref_c = Counter(chunk_id(r["geom"].centroid.x, r["geom"].centroid.y, origin_xy) for r in ref)
    cov_c = Counter(chunk_id(ref[i]["geom"].centroid.x, ref[i]["geom"].centroid.y, origin_xy)
                    for i in m["covered_ref"])
    keys = sorted(set(osm_c) | set(ref_c), key=lambda k: tuple(int(p) for p in k.split("_")))
    return [{"chunk": k, "osm": osm_c.get(k, 0), "ref": ref_c.get(k, 0), "ref_covered": cov_c.get(k, 0),
             "coverage_pct": round(100 * cov_c.get(k, 0) / ref_c[k], 1) if ref_c.get(k) else None} for k in keys]


def cell_occupancy(osm_blds: list[dict], ref: list[dict], boundary_utm, origin_xy) -> dict:
    """Okupansi sel CELL_M di dalam batas: ada bangunan OSM, ada pembanding, hanya pembanding, kosong keduanya."""
    def cells_of(geoms):
        return {(int((g.centroid.x - origin_xy[0]) // CELL_M), int((g.centroid.y - origin_xy[1]) // CELL_M))
                for g in geoms}

    minx, miny, maxx, maxy = boundary_utm.bounds
    cx0, cx1 = int((minx - origin_xy[0]) // CELL_M), int((maxx - origin_xy[0]) // CELL_M)
    cz0, cz1 = int((miny - origin_xy[1]) // CELL_M), int((maxy - origin_xy[1]) // CELL_M)
    inside = {(cx, cz) for cx in range(cx0, cx1 + 1) for cz in range(cz0, cz1 + 1)
              if boundary_utm.contains(Point(origin_xy[0] + (cx + 0.5) * CELL_M, origin_xy[1] + (cz + 0.5) * CELL_M))}
    osm_c = cells_of(b["geom"] for b in osm_blds) & inside
    ref_c = cells_of(r["geom"] for r in ref) & inside
    return {"cells": len(inside), "osm": len(osm_c), "ref": len(ref_c), "ref_only": len(ref_c - osm_c),
            "osm_only": len(osm_c - ref_c), "empty_both": len(inside - osm_c - ref_c)}


def missing_clusters(osm_blds: list[dict], ref: list[dict], origin_xy) -> list[dict]:
    """Sel CELL_M yang memuat bangunan pembanding tidak tercakup OSM, diurutkan terbanyak; dengan koordinat lokal."""
    m = match(osm_blds, ref)
    cells = Counter()
    for i, r in enumerate(ref):
        if i in m["covered_ref"]:
            continue
        c = r["geom"].centroid
        cells[(int((c.x - origin_xy[0]) // CELL_M), int((c.y - origin_xy[1]) // CELL_M))] += 1
    return [{"cell_x": cx, "cell_z": cz, "missing": n,
             "local_x_m": round((cx + 0.5) * CELL_M), "local_z_m": round((cz + 0.5) * CELL_M)}
            for (cx, cz), n in sorted(cells.items(), key=lambda kv: (-kv[1], kv[0]))]
