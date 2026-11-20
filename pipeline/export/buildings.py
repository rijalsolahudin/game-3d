"""Footprint bangunan: OSM (utama) + Google/Microsoft (pelengkap, dedup), tinggi, tier. Tanpa nama/alamat (NFR-07)."""
from __future__ import annotations

import hashlib
import math
from collections import Counter

import shapely
from shapely import wkt
from shapely.geometry import Polygon
from shapely.strtree import STRtree

from export import config as C
from export import tags as T
from export.geometry import flatten_polygons, rings_of, rnd, to_local_geom
from export.lines import osm_ref

SUPP_SOURCES = ("google", "microsoft")
OVERLAP_KINDS = ("centroid", "ratio", "area")
SUPP_REJECT_REASONS = ("invalid_row", "invalid_geometry", "outside_boundary", "low_confidence", "too_small",
                       "too_large", "bad_shape",
                       *(f"overlap_{t}_{k}" for t in ("osm", "supplementary") for k in OVERLAP_KINDS))


def _clean(poly: Polygon, decimals: int) -> list[Polygon]:
    return [p for p in flatten_polygons(shapely.set_precision(poly, 10.0 ** -decimals)) if p.area > 0]


def osm_buildings(items, proj, boundary, cfg: C.ExportConfig, stats: Counter, notes: dict):
    """Bangunan OSM. Kembalian: (kandidat di dalam batas, SEMUA footprint OSM lokal untuk uji overlap)."""
    kept, all_geoms = [], []
    for item in items:
        tg = item["tags"]
        if "building" not in tg:
            continue
        if tg["building"] == "no":
            notes["skipped"]["buildings_tag_no"] += 1
            continue
        if item["geom"].geom_type not in ("Polygon", "MultiPolygon"):
            notes["skipped"]["buildings_non_polygon"] += 1
            continue
        parts = _clean(to_local_geom(proj, item["geom"]), cfg.coord_decimals)
        base = f"osm-{item['type']}-{item['id']}"
        for i, poly in enumerate(parts):
            all_geoms.append(poly)
            c = poly.centroid
            if not boundary.contains(c):
                stats["osm_outside_boundary"] += 1
                continue
            kept.append({"id": base if len(parts) == 1 else f"{base}-{i}", "source": "osm",
                         "osm_id": osm_ref(item), "kind": T.slug(tg["building"]) or "yes",
                         "tags": tg, "geom": poly})
    return kept, all_geoms


def parse_supplement(rows, proj, cfg: C.ExportConfig, boundary, stats: Counter):
    """Validasi + filter baris Google/Microsoft; tolak dengan alasan (dihitung). Kembalian: kandidat terurut."""
    rej = stats
    cands = []
    for r in rows:
        src = r.get("source") if isinstance(r, dict) else None
        text = r.get("wkt") if isinstance(r, dict) else None
        conf = r.get("confidence") if isinstance(r, dict) else None
        conf_ok = conf is None or (isinstance(conf, (int, float)) and not isinstance(conf, bool) and conf == conf)
        if src not in SUPP_SOURCES or not isinstance(text, str) or not conf_ok or (src == "google" and conf is None):
            rej["supp_rejected_invalid_row"] += 1
            continue
        try:
            g = wkt.loads(text)
        except Exception:  # shapely.errors.GEOSException / WKT tidak terbaca
            rej["supp_rejected_invalid_geometry"] += 1
            continue
        if g.geom_type != "Polygon" or g.is_empty:
            rej["supp_rejected_invalid_geometry"] += 1
            continue
        if not g.is_valid:
            g = g.buffer(0)
        polys = _clean(to_local_geom(proj, g), cfg.coord_decimals) if not g.is_empty else []
        if len(polys) != 1:
            rej["supp_rejected_invalid_geometry"] += 1
            continue
        poly = polys[0]
        if not boundary.contains(poly.centroid):  # pertama: statistik penolakan lain hanya mewakili desa
            reason = "outside_boundary"
        elif src == "google" and conf < cfg.google_min_confidence:
            reason = "low_confidence"
        elif poly.area < cfg.supp_min_area_m2:
            reason = "too_small"
        elif poly.area > cfg.supp_max_area_m2:
            reason = "too_large"
        elif not _shape_ok(poly, cfg):
            reason = "bad_shape"
        else:
            reason = None
        if reason:
            rej[f"supp_rejected_{reason}"] += 1
            continue
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:C.ID_HASH_LEN]
        cands.append({"id": f"{src}-{digest}", "source": src, "osm_id": None, "kind": "yes", "tags": {},
                      "confidence": conf, "geom": poly})
    cands.sort(key=lambda c: (c["source"] != "google", -(c["confidence"] or 0.0), c["id"]))
    return cands


def _shape_ok(poly: Polygon, cfg: C.ExportConfig) -> bool:
    rect = shapely.minimum_rotated_rectangle(poly)
    if rect.geom_type != "Polygon" or rect.area <= 0:
        return False
    pts = list(rect.exterior.coords)
    s1, s2 = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])
    if min(s1, s2) <= 0:
        return False
    return poly.area / rect.area >= cfg.supp_min_rectangularity and max(s1, s2) / min(s1, s2) <= cfg.supp_max_aspect


def overlap_kind(a: Polygon, b: Polygon, cfg: C.ExportConfig) -> str | None:
    """Alasan a dan b dianggap bangunan yang sama/saling tembus, atau None.

    centroid: centroid salah satunya di dalam yang lain; ratio: irisan / luas terkecil >= ambang;
    area: luas irisan absolut >= ambang (m2).
    """
    inter = a.intersection(b).area
    if inter <= 0:
        return None
    if b.contains(a.centroid) or a.contains(b.centroid):
        return "centroid"
    if inter / min(a.area, b.area) >= cfg.overlap_ratio_max:
        return "ratio"
    if inter >= cfg.overlap_area_max_m2:
        return "area"
    return None


def _first_overlap(g: Polygon, others, indices, cfg: C.ExportConfig) -> str | None:
    for j in sorted(int(i) for i in indices):
        kind = overlap_kind(g, others[j], cfg)
        if kind:
            return kind
    return None


def dedupe_supplement(cands, osm_geoms, cfg: C.ExportConfig, stats: Counter) -> list[dict]:
    """Buang kandidat yang tumpang tindih OSM, lalu antar-pelengkap (urutan deterministik: Google dulu)."""
    osm_tree = STRtree(osm_geoms) if osm_geoms else None
    geoms = [c["geom"] for c in cands]
    cand_tree = STRtree(geoms) if cands else None
    accepted: set[int] = set()
    for i, c in enumerate(cands):
        g = c["geom"]
        kind = _first_overlap(g, osm_geoms, osm_tree.query(g), cfg) if osm_tree is not None else None
        if kind:
            stats[f"supp_rejected_overlap_osm_{kind}"] += 1
            continue
        kind = _first_overlap(g, geoms, [j for j in cand_tree.query(g) if int(j) in accepted], cfg)
        if kind:
            stats[f"supp_rejected_overlap_supplementary_{kind}"] += 1
            continue
        accepted.add(i)
        stats[f"supp_accepted_{c['source']}"] += 1
    return [cands[i] for i in sorted(accepted)]


def height_of(tags: dict, kind: str, area: float, cfg: C.ExportConfig) -> tuple[float, str, int | None]:
    """(tinggi m, sumber, levels). Tag height > building:levels x lantai > default tipe > default luas."""
    levels = T.parse_levels(tags.get("building:levels"))
    h = T.parse_meters(tags.get("height"), cfg.height_min_m, cfg.height_max_m)
    if h is not None:
        return h, "tag_height", levels
    if levels is not None:
        return min(max(levels * cfg.floor_height_m, cfg.height_min_m), cfg.height_max_m), "tag_levels", levels
    if kind in C.HEIGHT_BY_KIND_M:
        return C.HEIGHT_BY_KIND_M[kind], "default_kind", None
    for upper, hh in C.HEIGHT_BY_AREA_M:
        if area <= upper:
            return hh, "default_area", None
    return C.HEIGHT_LARGE_M, "default_area", None


def to_record(c: dict, tiers: dict, cfg: C.ExportConfig) -> tuple[tuple[int, int], dict]:
    """Kandidat -> (chunk, record JSON). Chunk = tempat centroid (bangunan tidak dipotong/diduplikasi)."""
    from geo.chunks import chunk_coords

    d = cfg.coord_decimals
    poly = c["geom"]
    cen = poly.centroid
    centroid = [rnd(cen.x, d), rnd(cen.y, d)]
    h, hsrc, levels = height_of(c["tags"], c["kind"], poly.area, cfg)
    entry = tiers.get(c["id"])
    rec = {"id": c["id"], "source": c["source"]}
    if c["osm_id"]:
        rec["osm_id"] = c["osm_id"]
    if c.get("confidence") is not None:
        rec["confidence"] = c["confidence"]
    rec.update({"kind": c["kind"], "tier": entry["tier"] if entry else cfg.default_tier,
                "height_m": rnd(h, 2), "height_source": hsrc, "levels": levels,
                "centroid": centroid, "area_m2": rnd(poly.area, 2), "footprint": rings_of(poly, d)})
    if entry and entry.get("landmark"):
        rec["landmark"] = entry["landmark"]
    return chunk_coords(centroid[0], centroid[1], cfg.chunk_size_m), rec
