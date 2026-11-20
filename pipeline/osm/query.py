"""Pembuatan query Overpass untuk semua data OSM relevan dalam bbox batas."""
from __future__ import annotations

# Kunci tag OSM yang diekspor (nwr = node, way, relation).
TAG_KEYS: tuple[str, ...] = (
    "highway", "waterway", "natural", "landuse", "leisure", "amenity", "building",
    "barrier", "man_made", "place", "shop", "tourism", "historic", "office",
)
TIMEOUT_S = 240


def build_query(bbox_swne: tuple[float, float, float, float]) -> str:
    """bbox_swne = (selatan, barat, utara, timur) dalam derajat. Hasil `out geom` + node referensi way."""
    s, w, n, e = bbox_swne
    bbox = f"{s:.7f},{w:.7f},{n:.7f},{e:.7f}"
    stmts = "".join(f'nwr["{k}"]({bbox});' for k in TAG_KEYS)
    return (
        f"[out:json][timeout:{TIMEOUT_S}];"
        f"({stmts})->.a;"
        ".a out geom;"
        "node(w.a);out skel qt;"
    )
