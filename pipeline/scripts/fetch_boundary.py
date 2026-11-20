"""GAME-5: batas Desa Tumanggal + titik origin.

Dijalankan dari folder pipeline/:
    uv run python scripts/fetch_boundary.py                       # mode provisional (lingkaran 1500 m)
    uv run python scripts/fetch_boundary.py --radius-m 1200
    uv run python scripts/fetch_boundary.py --offline             # pakai raw terbaru, tanpa jaringan
    uv run python scripts/fetch_boundary.py --from-geojson path/batas_resmi.geojson [--buffer-m 200]

Mode provisional: OSM tidak punya relation batas Desa Tumanggal, jadi dipakai lingkaran
berjari-jari --radius-m di sekitar node desa OSM. Lingkaran sudah mewakili batas + buffer D1
(tidak ada buffer tambahan). Ganti dengan batas resmi lewat --from-geojson.

Keluaran: data/boundary.geojson, data/origin.json, data/preview/boundary.html
Data (c) OpenStreetMap contributors, ODbL.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import warnings

import httpx
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import nearest_points, transform, unary_union

warnings.filterwarnings("ignore", message=".*shapely.ops.transform.*")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from geo.projection import (  # noqa: E402
    lonlat_to_utm,
    transformer_to_utm,
    transformer_to_wgs,
)

RAW_DIR = ROOT / "data" / "raw" / "osm"
OUT_BOUNDARY = ROOT / "data" / "boundary.geojson"
OUT_ORIGIN = ROOT / "data" / "origin.json"
OUT_PREVIEW = ROOT / "data" / "preview" / "boundary.html"

VILLAGE_NODE = 1308706192
DEFAULT_RADIUS_M = 1500.0
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
]  # mirror lain (kumi.systems, private.coffee) timeout dari lingkungan ini; tambahkan bila perlu
UA = {"User-Agent": "game-3d-pipeline/0.1 (GAME-5 boundary fetch)"}
LICENSE = "ODbL (OSM)"
REPLACE_NOTE = (
    "BATAS SEMENTARA: harus diganti dengan peta batas resmi Desa Tumanggal "
    "dari pemerintah desa (jalankan dengan --from-geojson)."
)
# kelas jalan yang dihitung "jalan utama" / kandidat origin (tertiary ke atas + residential/unclassified)
ROAD_CLASSES = "motorway|trunk|primary|secondary|tertiary|unclassified|residential"
ROAD_LINKS = "|".join(c + "_link" for c in ("motorway", "trunk", "primary", "secondary", "tertiary"))


def overpass(query: str, attempts: int = 5) -> dict:
    last = None
    for i in range(attempts):
        for url in ENDPOINTS:
            try:
                r = httpx.post(url, data={"data": query}, headers=UA,
                               timeout=httpx.Timeout(90, connect=15))
                if r.status_code == 200 and r.text.lstrip().startswith("{"):
                    return r.json()
                last = f"{url}: HTTP {r.status_code}"
            except httpx.HTTPError as e:
                last = f"{url}: {e!r}"
            print("retry:", last, file=sys.stderr)
        time.sleep(min(10 * 2**i, 60))
    raise RuntimeError(f"Overpass gagal: {last}")


def save_raw(name: str, data: dict, today: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    p = RAW_DIR / f"{name}_{today}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")
    return p


def latest_raw(name: str) -> Path:
    files = sorted(RAW_DIR.glob(f"{name}_*.json"))
    if not files:
        raise FileNotFoundError(f"tidak ada raw {name}_*.json; jalankan tanpa --offline")
    return files[-1]


def to_utm(geom):
    return transform(transformer_to_utm().transform, geom)


def to_wgs(geom):
    return transform(transformer_to_wgs().transform, geom)


def area_km2(geom_wgs) -> float:
    return to_utm(geom_wgs).area / 1e6


def circle_wgs(lon: float, lat: float, radius_m: float):
    """Lingkaran di UTM 49S (meter), dikembalikan ke EPSG:4326."""
    x, y = lonlat_to_utm(lon, lat)
    return to_wgs(Point(x, y).buffer(radius_m, quad_segs=64))


def way_line(e) -> LineString:
    return LineString([(p["lon"], p["lat"]) for p in e["geometry"]])


def road_ways(elements):
    return [e for e in elements if e["type"] == "way" and e.get("geometry") and "highway" in e.get("tags", {})]


def choose_origin(poly, village_ll, elements):
    """Balai/Kantor Desa di dalam batas; fallback titik di jalan terdekat dari node desa."""
    cands = []
    for e in elements:
        t = e.get("tags", {})
        name = t.get("name", "")
        if "highway" in t:
            continue
        if "lat" in e:
            c = e
        elif e.get("geometry"):
            cc = way_line(e).centroid if len(e["geometry"]) > 1 else Point(e["geometry"][0]["lon"], e["geometry"][0]["lat"])
            c = {"lat": cc.y, "lon": cc.x}
        else:
            continue
        is_hall = t.get("amenity") == "townhall" or any(
            k in name.lower() for k in ("balai desa", "kantor desa", "kantor kepala desa"))
        if is_hall and poly.contains(Point(c["lon"], c["lat"])):
            d = Point(*lonlat_to_utm(c["lon"], c["lat"])).distance(Point(*lonlat_to_utm(*village_ll)))
            cands.append((0 if "tumanggal" in name.lower() else 1, d, e["type"], e["id"], c["lat"], c["lon"], name))
    if cands:
        cands.sort()
        _, _, typ, eid, lat, lon, name = cands[0]
        return dict(lat=lat, lng=lon, source=f"OSM {typ}/{eid}", name=name or None,
                    reason="Balai/Kantor Desa di dalam batas; titik mudah dikenali untuk spawn.")
    roads = [e for e in road_ways(elements) if e["tags"]["highway"] in ROAD_CLASSES.split("|")
             or e["tags"]["highway"] in ROAD_LINKS.split("|")]
    if not roads:
        raise RuntimeError("tidak ada balai desa maupun jalan; origin tidak bisa ditentukan")
    village_utm = Point(*lonlat_to_utm(*village_ll))
    best = None
    for e in roads:
        line = to_utm(way_line(e))
        p = nearest_points(line, village_utm)[0]
        d = p.distance(village_utm)
        if best is None or (d, e["id"]) < (best[0], best[1]):
            best = (d, e["id"], p, e["tags"])
    d, wid, p, tags = best
    lon, lat = transformer_to_wgs().transform(p.x, p.y)
    return dict(lat=lat, lng=lon, source=f"OSM way/{wid} (highway={tags['highway']}) terdekat dari node desa",
                name=tags.get("name"),
                reason=(f"Balai/Kantor Desa tidak ditemukan di OSM dalam batas; dipakai titik di jalan "
                        f"terdekat ({d:.0f} m) dari node desa."))


def feature(geom, props):
    return {"type": "Feature", "properties": props, "geometry": mapping(geom)}


def round_geom(geom, nd=7):
    from shapely import set_precision
    return set_precision(geom, 10 ** -nd)


def edge_cut_roads(poly, elements):
    """Jalan (kelas utama) yang memotong tepi batas: nama, kelas, dan apakah tembus keluar."""
    out = []
    edge = poly.boundary
    for e in road_ways(elements):
        if e["tags"]["highway"] not in ROAD_CLASSES.split("|"):
            continue
        line = way_line(e)
        if line.intersects(edge):
            out.append({"id": e["id"], "name": e["tags"].get("name"), "highway": e["tags"]["highway"]})
    return sorted(out, key=lambda r: r["id"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius-m", type=float, default=DEFAULT_RADIUS_M, help="radius lingkaran provisional")
    ap.add_argument("--from-geojson", type=Path, help="batas resmi (Polygon/MultiPolygon EPSG:4326)")
    ap.add_argument("--buffer-m", type=float, default=200.0, help="buffer untuk --from-geojson (D1)")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    today = dt.date.today().isoformat()

    # --- node desa (selalu dipakai sebagai acuan lokasi) ---
    if args.offline:
        node_p = latest_raw("node")
        node_res = json.loads(node_p.read_text(encoding="utf-8"))
        fetched = node_p.stem.split("_")[-1]
    else:
        node_res = overpass(f"[out:json][timeout:60];node({VILLAGE_NODE});out;")
        save_raw("node", node_res, today)
        fetched = today
    node = node_res["elements"][0]
    if node["id"] != VILLAGE_NODE or node["tags"].get("name") != "Tumanggal":
        raise RuntimeError("node desa tidak sesuai")
    vlat, vlon = node["lat"], node["lon"]

    # --- poligon ---
    base = {"source": "OpenStreetMap via Overpass API", "retrieved_at": fetched, "license": LICENSE,
            "crs": "EPSG:4326", "osm_node": VILLAGE_NODE}
    if args.from_geojson:
        gj = json.loads(args.from_geojson.read_text(encoding="utf-8"))
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        official = unary_union([shape(f["geometry"]) for f in feats])
        if not official.is_valid:
            official = official.buffer(0)
        poly = to_wgs(to_utm(official).buffer(args.buffer_m, quad_segs=16))
        props = {**base, "provisional": False, "method": "official_boundary_plus_buffer",
                 "buffer_m": args.buffer_m, "boundary_file": args.from_geojson.name,
                 "area_original_km2": round(area_km2(official), 4)}
    else:
        poly = circle_wgs(vlon, vlat, args.radius_m)
        props = {**base, "provisional": True, "method": "circle_around_osm_village_node",
                 "radius_m": args.radius_m, "buffer_m": 0,
                 "note": REPLACE_NOTE + " Lingkaran sudah mewakili batas + buffer D1 (tidak ada buffer tambahan)."}
    poly = round_geom(poly)
    area = area_km2(poly)
    props["area_km2"] = round(area, 4)

    fc = {"type": "FeatureCollection", "name": "boundary",
          "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
          "features": [feature(poly, {**props, "kind": "boundary"})]}

    # --- fitur OSM dalam batas ---
    if args.offline:
        feats_res = json.loads(latest_raw("features").read_text(encoding="utf-8"))
    else:
        # bbox poligon + filter setelahnya; cukup "around" dengan jarak sudut terjauh
        w, s, e, n = poly.bounds
        bbox = f"{s},{w},{n},{e}"
        feats_res = overpass(
            f'[out:json][timeout:90];('
            f'nwr["amenity"="townhall"]({bbox});'
            f'nwr["name"~"balai desa|kantor desa",i]({bbox});'
            f'way["highway"~"^({ROAD_CLASSES}|{ROAD_LINKS})$"]({bbox});'
            f');out tags geom;')
        save_raw("features", feats_res, today)
    elements = feats_res["elements"]
    in_roads = [e for e in road_ways(elements) if way_line(e).intersects(poly)]

    org = choose_origin(poly, (vlon, vlat), elements)
    org.update(lat=round(org["lat"], 7), lng=round(org["lng"], 7))
    org.update(crs="EPSG:4326", license=LICENSE,
               retrieved_at=fetched, provisional=True,
               utm49s=[round(v, 2) for v in lonlat_to_utm(org["lng"], org["lat"])],
               status="usulan - menunggu persetujuan pemilik produk")
    if not poly.contains(Point(org["lng"], org["lat"])):
        raise RuntimeError("origin di luar batas")

    cut = edge_cut_roads(poly, elements)
    OUT_BOUNDARY.parent.mkdir(parents=True, exist_ok=True)
    OUT_BOUNDARY.write_text(json.dumps(fc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_ORIGIN.write_text(json.dumps(org, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    roads = [{"name": e["tags"].get("name"), "highway": e["tags"]["highway"],
              "coords": [[round(p["lat"], 6), round(p["lon"], 6)] for p in e["geometry"]]} for e in in_roads]
    write_preview(fc, org, (vlat, vlon), roads, props["provisional"])

    print(json.dumps({"area_km2": round(area, 4), "origin": org, "roads_intersecting": len(in_roads),
                      "roads_crossing_edge": cut}, ensure_ascii=False, indent=1))
    return 0


def write_preview(fc, org, village, roads, provisional) -> None:
    OUT_PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    label = "BATAS SEMENTARA (lingkaran di sekitar node desa OSM)" if provisional else "Batas desa + buffer"
    data = {"fc": fc, "origin": {k: org.get(k) for k in ("lat", "lng", "name", "source")},
            "village": {"lat": village[0], "lng": village[1]}, "roads": roads}
    html = f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><title>Batas Desa Tumanggal - pratinjau</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#map{{height:100%;margin:0}}
.box{{position:absolute;z-index:1000;top:10px;right:10px;background:#fff;padding:8px 12px;font:13px sans-serif;border-radius:4px;max-width:320px}}
.warn{{color:#fff;background:#c00;padding:2px 6px;font-weight:bold}}</style>
</head><body><div id="map"></div>
<div class="box"><span class="warn">{label}</span><br>
<span style="color:#d33">&#9632;</span> batas &nbsp; <span style="color:#555">&#9632;</span> jalan OSM ({len(roads)})<br>
<span style="color:#27c">&#9679;</span> node desa OSM &nbsp; <span style="color:#fc0">&#9679;</span> origin {org['lat']}, {org['lng']}<br>
Harus diganti peta batas resmi desa.</div>
<script>
const D = {json.dumps(data, ensure_ascii=False)};
const map = L.map('map');
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors (ODbL)'}}).addTo(map);
const layer = L.geoJSON(D.fc, {{style: {{color:'#d33',weight:3,fillOpacity:0.05}}}}).addTo(map);
D.roads.forEach(r => L.polyline(r.coords, {{color:'#555',weight:3}}).bindTooltip((r.name||'(tanpa nama)')+' ['+r.highway+']').addTo(map));
L.circleMarker([D.village.lat, D.village.lng], {{radius:7,color:'#27c',fillColor:'#27c',fillOpacity:1}}).addTo(map).bindPopup('Node desa OSM 1308706192');
L.circleMarker([D.origin.lat, D.origin.lng], {{radius:9,color:'#000',fillColor:'#fc0',fillOpacity:1}}).addTo(map)
  .bindPopup('Origin (usulan): '+D.origin.lat+', '+D.origin.lng+'<br>'+(D.origin.name||'')+'<br>'+D.origin.source);
map.fitBounds(layer.getBounds());
</script></body></html>
"""
    OUT_PREVIEW.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
