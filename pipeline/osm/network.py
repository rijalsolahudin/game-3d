"""Audit jaringan jalan: konektivitas, dead-end, celah (endpoint dekat jalan lain tanpa simpul), persilangan tanpa simpul."""
from __future__ import annotations

from collections import Counter

from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

from osm.geom import project

GAP_MAX_M = 30.0        # endpoint dead-end yang <= jarak ini dari jalan lain = kandidat ruas terputus
EDGE_MARGIN_M = 40.0    # endpoint di dalam jarak ini dari tepi batas diabaikan (terpotong batas buatan)
SNAP_TOL_M = 0.5        # persilangan di dekat simpul bersama dianggap tersambung
# tipe yang dianggap jaringan kendaraan (untuk dead-end/gap); path/footway/steps diaudit terpisah
VEHICLE_HIGHWAYS = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
                    "service", "track", "living_street", "road"}


def _is_vehicle(tags: dict) -> bool:
    h = tags["highway"]
    return h in VEHICLE_HIGHWAYS or (h.endswith("_link") and h.split("_")[0] in VEHICLE_HIGHWAYS)


def road_items(items: list[dict]) -> list[dict]:
    return [i for i in items if "highway" in i["tags"] and i["geom"].geom_type == "LineString"]


def components(roads: list[dict]) -> list[list[dict]]:
    """Komponen terhubung berdasar simpul OSM bersama (union-find)."""
    parent = list(range(len(roads)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    owner: dict[int, int] = {}
    for idx, r in enumerate(roads):
        for nid in r["nodes"]:
            if nid in owner:
                parent[find(idx)] = find(owner[nid])
            else:
                owner[nid] = idx
    groups: dict[int, list[dict]] = {}
    for idx, r in enumerate(roads):
        groups.setdefault(find(idx), []).append(r)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]["id"]))


def _fmt(r: dict) -> str:
    return f"way/{r['id']}"


def analyze(roads: list[dict], boundary_utm) -> dict:
    """Kembalikan dict temuan; geometri road di EPSG:4326 diproyeksikan di sini."""
    inner = boundary_utm.buffer(-EDGE_MARGIN_M)
    utm = [project(r["geom"]) for r in roads]
    node_deg: Counter = Counter()
    for r in roads:
        node_deg.update(set(r["nodes"]))
    tree = STRtree(utm)

    dead_ends, gaps = [], []
    for idx, r in enumerate(roads):
        ids = r["nodes"]
        if not ids or ids[0] == ids[-1] or not _is_vehicle(r["tags"]):
            continue
        for nid, pt in ((ids[0], Point(utm[idx].coords[0])), (ids[-1], Point(utm[idx].coords[-1]))):
            if node_deg[nid] != 1 or not inner.contains(pt):
                continue
            near = [j for j in tree.query(pt.buffer(GAP_MAX_M)) if j != idx]
            dists = sorted((d, roads[j]["id"]) for j in near if (d := utm[j].distance(pt)) <= GAP_MAX_M)
            rec = {"way": _fmt(r), "highway": r["tags"]["highway"], "named": "name" in r["tags"],
                   "len_m": round(utm[idx].length, 1), "x": round(pt.x, 1), "y": round(pt.y, 1)}
            if dists:
                rec.update(gap_m=round(dists[0][0], 1), near_way=f"way/{dists[0][1]}")
                gaps.append(rec)
            else:
                dead_ends.append(rec)

    crossings = []
    for idx, r in enumerate(roads):
        if r["tags"].get("bridge") or r["tags"].get("tunnel") or not _is_vehicle(r["tags"]):
            continue
        for j in tree.query(utm[idx]):
            if j <= idx:
                continue
            o = roads[j]
            if o["tags"].get("bridge") or o["tags"].get("tunnel") or not _is_vehicle(o["tags"]):
                continue
            if r["tags"].get("layer") != o["tags"].get("layer"):
                continue
            if set(r["nodes"]) & set(o["nodes"]):
                continue
            inter = utm[idx].intersection(utm[j])
            if not inter.is_empty and inter.geom_type == "Point" and inner.contains(inter):
                crossings.append({"a": _fmt(r), "b": _fmt(o), "x": round(inter.x, 1), "y": round(inter.y, 1)})

    comps = components(roads)
    comp_info = []
    main_geom = unary_union([project(r["geom"]) for r in comps[0]]) if comps else None
    for k, c in enumerate(comps):
        km = sum(project(r["geom"]).intersection(boundary_utm).length for r in c) / 1000
        info = {"ways": len(c), "km": round(km, 3), "sample": _fmt(c[0]),
                "types": dict(sorted(Counter(r["tags"]["highway"] for r in c).items()))}
        if k > 0:  # jarak terdekat ke komponen utama: kecil berarti kemungkinan simpul tidak tersambung
            info["min_dist_to_main_m"] = round(unary_union([project(r["geom"]) for r in c]).distance(main_geom), 1)
        comp_info.append(info)
    unnamed = Counter()
    named = Counter()
    for r in roads:
        (named if "name" in r["tags"] else unnamed)[r["tags"]["highway"]] += 1
    attrs = {k: sum(1 for r in roads if k in r["tags"]) for k in ("surface", "width", "lanes", "oneway", "maxspeed")}
    return {"roads": len(roads), "components": comp_info, "dead_ends": dead_ends, "gaps": gaps,
            "crossings": crossings, "named": dict(named), "unnamed": dict(unnamed), "attrs": attrs}
