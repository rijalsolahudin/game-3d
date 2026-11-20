"""Parsing respons Overpass mentah ke geometri shapely (EPSG:4326), klasifikasi, dan clip ke batas."""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape
from shapely.ops import polygonize, unary_union

# kategori sesuai task GAME-6 (+ POI tambahan)
CATEGORIES: tuple[str, ...] = (
    "highway", "waterway", "natural", "landuse", "leisure", "amenity", "building",
    "barrier", "man_made", "place", "shop", "tourism", "historic", "office",
)
# way tertutup dengan tag ini dianggap area
_AREA_KEYS = ("building", "landuse", "leisure", "amenity", "man_made", "historic", "tourism", "shop", "office")
_LINEAR_NATURAL = {"tree_row", "cliff", "ridge", "valley", "arete"}


class RawFormatError(ValueError):
    """Respons Overpass tidak sesuai format yang diharapkan."""


def load_raw(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_raw(data)
    return data


def validate_raw(data: dict) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
        raise RawFormatError("raw OSM harus objek dengan 'elements' berupa list")
    for e in data["elements"]:
        if not isinstance(e, dict) or e.get("type") not in ("node", "way", "relation") \
                or not isinstance(e.get("id"), int):
            raise RawFormatError(f"elemen tidak valid: {str(e)[:80]}")
        if e["type"] == "node" and not ("lat" in e and "lon" in e):
            raise RawFormatError(f"node {e['id']} tanpa koordinat")


def categories_of(tags: dict) -> list[str]:
    return [c for c in CATEGORIES if c in tags]


def is_area_way(tags: dict, closed: bool) -> bool:
    if not closed:
        return False
    if tags.get("area") == "yes":
        return True
    if tags.get("area") == "no":
        return False
    if "building" in tags or "landuse" in tags:
        return True
    if "highway" in tags or "waterway" in tags or "barrier" in tags:
        return False
    if tags.get("natural") in _LINEAR_NATURAL:
        return False
    return "natural" in tags or any(k in tags for k in _AREA_KEYS)


def _coords(geom_list) -> list[tuple[float, float]]:
    return [(p["lon"], p["lat"]) for p in geom_list]


def multipolygon_geometry(e: dict):
    """Rakit multipolygon dari anggota outer/inner relation; None bila gagal dirakit."""
    outers, inners = [], []
    for m in e.get("members", []):
        if m.get("type") != "way" or not m.get("geometry") or len(m["geometry"]) < 2:
            continue
        line = LineString(_coords(m["geometry"]))
        (inners if m.get("role") == "inner" else outers).append(line)
    if not outers:
        return None
    outer_polys = list(polygonize(unary_union(outers)))
    if not outer_polys:
        return None
    result = unary_union(outer_polys)
    if inners:
        holes = list(polygonize(unary_union(inners)))
        if holes:
            result = result.difference(unary_union(holes))
    if result.is_empty:
        return None
    return result if result.is_valid else result.buffer(0)


def element_geometry(e: dict):
    """Geometri EPSG:4326 elemen, atau None (geometri tidak lengkap/tak bisa dirakit)."""
    t = e["type"]
    if t == "node":
        return Point(e["lon"], e["lat"])
    if t == "way":
        g = e.get("geometry")
        if not g or len(g) < 2:
            return None
        pts = _coords(g)
        closed = pts[0] == pts[-1] and len(pts) >= 4
        if is_area_way(e.get("tags", {}), closed):
            poly = Polygon(pts)
            return poly if poly.is_valid else poly.buffer(0)
        return LineString(pts)
    if e.get("tags", {}).get("type") in ("multipolygon", "boundary"):
        return multipolygon_geometry(e)
    return None


def parse_elements(data: dict) -> tuple[list[dict], list[dict]]:
    """Elemen bertag -> (items, skipped). item = {type,id,tags,cats,geom,nodes}, terurut (type,id)."""
    items, skipped = [], []
    for e in sorted(data["elements"], key=lambda x: (x["type"], x["id"])):
        tags = e.get("tags")
        if not tags:
            continue  # node referensi tanpa tag
        cats = categories_of(tags)
        if not cats:
            continue
        g = element_geometry(e)
        if g is None or g.is_empty:
            skipped.append({"type": e["type"], "id": e["id"], "cats": cats})
            continue
        items.append({"type": e["type"], "id": e["id"], "tags": tags, "cats": cats, "geom": g,
                      "nodes": e.get("nodes", [])})
    return items, skipped


def clip_to_boundary(items: list[dict], boundary) -> list[dict]:
    """Item yang beririsan dengan batas (EPSG:4326). `inside` = titik wakil item berada di dalam batas."""
    kept = []
    for it in items:
        g = it["geom"]
        if not g.intersects(boundary):
            continue
        rep = g.representative_point() if g.geom_type in ("Polygon", "MultiPolygon") else g.centroid
        kept.append({**it, "inside": bool(boundary.contains(rep))})
    return kept


def boundary_polygon(path: Path):
    fc = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = [f for f in fc["features"] if f["properties"].get("kind") == "boundary"]
    if len(feats) != 1:
        raise RawFormatError("boundary.geojson harus memuat tepat satu fitur kind=boundary")
    geom = shape(feats[0]["geometry"])
    if not isinstance(geom, (Polygon, MultiPolygon)) or not geom.is_valid:
        raise RawFormatError("batas bukan polygon valid")
    return geom
