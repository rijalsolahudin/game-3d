"""Rakit semua layer menjadi dict chunk (belum divalidasi/ditulis). Murni: tanpa I/O, deterministik."""
from __future__ import annotations

from collections import Counter

from export import buildings as B
from export import config as C
from export.areas import build_areas
from export.geometry import to_local_geom
from export.lines import build_lines, new_chunk_store
from geo.chunks import chunk_bounds, format_chunk_id
from osm.parse import parse_elements


def build_chunks(osm_data: dict, ref_rows, boundary_wgs, proj, tier_entries: list[dict],
                 cfg: C.ExportConfig = C.DEFAULT_CONFIG):
    """Kembalikan (chunks {id: dict}, stats Counter, notes {"skipped": Counter, "tiers_unmatched": [...]})."""
    stats: Counter = Counter()
    notes = {"skipped": Counter(), "tiers_unmatched": []}
    items, no_geom = parse_elements(osm_data)
    notes["skipped"]["osm_elements_without_geometry"] = len(no_geom)
    boundary = to_local_geom(proj, boundary_wgs)
    clip = boundary.buffer(cfg.boundary_margin_m)

    store = new_chunk_store()
    build_lines(items, proj, clip, cfg, store, stats, notes)
    build_areas(items, proj, clip, cfg, store, stats, notes)

    osm_cands, osm_geoms = B.osm_buildings(items, proj, boundary, cfg, stats, notes)
    stats["osm_buildings_total_raw"] = len(osm_geoms)
    supp = []
    if ref_rows is not None:
        stats["supp_rows"] = len(ref_rows)
        supp = B.dedupe_supplement(B.parse_supplement(ref_rows, proj, cfg, boundary, stats), osm_geoms, cfg, stats)

    tiers = {e["id"]: e for e in tier_entries}
    used: set[str] = set()
    for c in osm_cands + supp:
        chunk, rec = B.to_record(c, tiers, cfg)
        if c["id"] in tiers:
            used.add(c["id"])
        store[chunk]["buildings"].append(rec)
        stats[f"buildings_{rec['source']}"] += 1
        stats[f"buildings_tier_{rec['tier']}"] += 1
    notes["tiers_unmatched"] = sorted(set(tiers) - used)

    chunks = {}
    for (cx, cz) in sorted(store):
        data = store[(cx, cz)]
        cid = format_chunk_id(cx, cz)
        chunks[cid] = {"schema_version": C.SCHEMA_VERSION, "chunk": cid, "cx": cx, "cz": cz,
                       "bounds": list(chunk_bounds(cx, cz, cfg.chunk_size_m)),
                       **{k: sorted(data[k], key=lambda r: r["id"]) for k in ("roads", "waterways", "areas", "buildings")}}
    return chunks, stats, notes
