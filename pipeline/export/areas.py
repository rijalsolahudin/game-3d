"""Polygon landuse/natural/leisure/air -> potongan per chunk (dipotong tepat di batas chunk)."""
from __future__ import annotations

from collections import Counter

from export import config as C
from export import tags as T
from export.geometry import (
    flatten_polygons,
    rings_of,
    rnd,
    split_polygon,
    to_local_geom,
)
from export.lines import osm_ref


def area_class(tg: dict) -> tuple[str, str] | None:
    """(kategori, kind) atau None bila bukan area yang diekspor."""
    if tg.get("natural") == C.WATER_NATURAL:
        return "water", C.WATER_NATURAL
    if tg.get("waterway") == C.WATER_WATERWAY:
        return "water", C.WATER_WATERWAY
    for key in C.AREA_KEYS:
        if key in tg:
            kind = T.slug(tg[key])
            return (key, kind) if kind else None
    return None


def build_areas(items: list[dict], proj, clip, cfg: C.ExportConfig, out: dict, stats: Counter, notes: dict) -> None:
    for item in items:
        tg, geom = item["tags"], item["geom"]
        if "building" in tg:
            continue
        has_area_tag = any(k in tg for k in C.AREA_KEYS) or tg.get("waterway") == C.WATER_WATERWAY
        if not has_area_tag:
            continue
        cls = area_class(tg)
        if cls is None:
            notes["skipped"]["areas_invalid_kind"] += 1
            continue
        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            notes["skipped"]["areas_non_polygon"] += 1  # node/garis (tree_row, pohon tunggal)
            continue
        local = to_local_geom(proj, geom).intersection(clip)
        parts = flatten_polygons(local)
        if not parts:
            stats["areas_outside_boundary"] += 1
            continue
        ref, seq = osm_ref(item), 0
        for poly in parts:
            pieces, dropped = split_polygon(poly, cfg.chunk_size_m, cfg.coord_decimals, cfg.min_piece_area_m2)
            notes["skipped"]["areas_sliver_dropped"] += dropped
            for chunk, p in pieces:
                out[chunk]["areas"].append({
                    "id": f"{ref}#{seq}", "osm_id": ref, "part": seq, "category": cls[0], "kind": cls[1],
                    "area_m2": rnd(p.area, 2), "rings": rings_of(p, cfg.coord_decimals)})
                stats[f"areas_{cls[0]}_{cls[1]}"] += 1
                seq += 1
