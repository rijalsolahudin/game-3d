"""Jalan (highway) dan aliran air (waterway) -> potongan polyline per chunk dengan ujung bersama identik."""
from __future__ import annotations

from collections import Counter, defaultdict

import shapely
from shapely.geometry import LineString

from export import config as C
from export import tags as T
from export.geometry import polyline_length, rnd, split_polyline, to_local_geom


def osm_ref(item: dict) -> str:
    return f"{item['type']}/{item['id']}"


def _line_parts(line: LineString, clip) -> list[LineString]:
    """Bagian garis di dalam `clip` (batas + margin); garis utuh dipertahankan apa adanya."""
    if clip.contains(line):
        return [line]
    inter = line.intersection(clip)
    return [g for g in shapely.get_parts(inter) if isinstance(g, LineString) and g.length > 0]


def _emit(item, kind, width, extra, line, clip, cfg, out, stats, layer):
    ref = osm_ref(item)
    parts = _line_parts(line, clip)
    if not parts:
        stats[f"{layer}_outside_boundary"] += 1
        return
    seq = 0
    for part in parts:
        pieces = split_polyline(list(part.coords), cfg.chunk_size_m, cfg.coord_decimals)
        for i, pc in enumerate(pieces):
            rec = {"id": f"{ref}#{seq}", "osm_id": ref, "seq": seq,
                   "continues_prev": i > 0, "continues_next": i < len(pieces) - 1,
                   "kind": kind, "width_m": width, **extra,
                   "points": [[x, z] for x, z in pc["points"]]}
            out[pc["chunk"]][layer].append(rec)
            stats[f"{layer}_km_{kind}"] += polyline_length(pc["points"]) / 1000
            stats[f"{layer}_pieces"] += 1
            seq += 1
    stats[f"{layer}_ways"] += 1


def build_lines(items: list[dict], proj, clip, cfg: C.ExportConfig, out: dict, stats: Counter, notes: dict) -> None:
    """Isi out[(cx,cz)]["roads"/"waterways"]; hitung statistik dan catatan (alasan yang dilewati/ditolak)."""
    for item in items:
        tg, geom = item["tags"], item["geom"]
        for key, layer in (("highway", "roads"), ("waterway", "waterways")):
            if key not in tg:
                continue
            kind = T.slug(tg[key])
            if kind is None:
                notes["skipped"][f"{layer}_invalid_kind"] += 1
                continue
            if geom.geom_type != "LineString":
                notes["skipped"][f"{layer}_non_line"] += 1  # node (halte, penyeberangan) atau area=yes
                continue
            if layer == "roads" and kind in C.ROAD_EXCLUDED_KINDS:
                notes["skipped"][f"roads_excluded_{kind}"] += 1
                continue
            if layer == "roads":
                default = C.ROAD_WIDTH_M.get(T.road_base_kind(kind), C.ROAD_WIDTH_FALLBACK_M)
            else:
                default = C.WATERWAY_WIDTH_M.get(kind, C.WATERWAY_WIDTH_FALLBACK_M)
            width = default
            if "width" in tg:
                w = T.parse_meters(tg["width"], cfg.width_min_m, cfg.width_max_m)
                if w is None:
                    notes["skipped"][f"{layer}_width_tag_invalid_default_used"] += 1
                else:
                    width = w
            extra: dict = {}
            if layer == "roads" and (s := T.surface(tg.get("surface"))):
                extra["surface"] = s
            if (n := T.safe_name(tg.get("name"))):
                extra["name"] = n  # hanya jalan/sungai (publik); bangunan tidak pernah membawa nama
            if T.flag(tg.get("bridge")):
                extra["bridge"] = True
            if T.flag(tg.get("tunnel")):
                extra["tunnel"] = True
            if (lay := T.parse_layer(tg.get("layer"))) is not None:
                extra["layer"] = lay
            local = to_local_geom(proj, geom)
            _emit(item, kind, rnd(width, 2), extra, local, clip, cfg, out, stats, layer)


def new_chunk_store():
    return defaultdict(lambda: {"roads": [], "waterways": [], "areas": [], "buildings": []})
