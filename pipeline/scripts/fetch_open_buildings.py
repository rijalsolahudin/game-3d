"""GAME-6: unduh footprint pembanding (Google Open Buildings v3 + Microsoft Global ML Buildings, gabungan VIDA)
di bbox batas, untuk audit kelengkapan bangunan OSM dan layer pelengkap (ADR-0003); tidak digabung ke data OSM.

Dijalankan dari folder pipeline/ (butuh grup dependensi opsional `buildings-ref` = duckdb):
    uv run --group buildings-ref python scripts/fetch_open_buildings.py

Membaca GeoParquet publik di source.coop lewat HTTP range (tanpa login, tidak mengunduh seluruh 16 GB).
Keluaran: data/raw/open_buildings/vida_buildings_<tanggal>.json (+ .meta.json), gitignored.
Lisensi: Google Open Buildings CC BY 4.0 / ODbL, Microsoft ML Building Footprints ODbL (lihat README).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from osm.meta import validate_meta  # noqa: E402
from osm.parse import boundary_polygon  # noqa: E402

RAW_DIR = ROOT / "data" / "raw" / "open_buildings"
BOUNDARY = ROOT / "data" / "boundary.geojson"
SCHEMA = ROOT / "schemas" / "open_buildings_meta.schema.json"
URL = ("https://data.source.coop/vida/google-microsoft-open-buildings/geoparquet/"
       "by_country/country_iso=IDN/IDN.parquet")
LICENSE = "Google Open Buildings v3: CC BY 4.0 / ODbL; Microsoft Global ML Building Footprints: ODbL"
USAGE = ("Audit kelengkapan OSM; pemakaian sebagai layer pelengkap game mengikuti ADR-0003 "
         "(keputusan pemilik produk), atribusi wajib")
SOURCE = "VIDA Google-Microsoft Open Buildings (source.coop), country_iso=IDN"


def fetch(bbox_swne) -> tuple[list[dict], str]:
    import duckdb  # dependensi opsional

    s, w, n, e = bbox_swne
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    sql = (f"select bf_source, confidence, area_in_meters, ST_AsText(geometry) as wkt "
           f"from read_parquet('{URL}') "
           f"where bbox.xmax >= {w} and bbox.xmin <= {e} and bbox.ymax >= {s} and bbox.ymin <= {n} "
           f"order by wkt")
    rows = con.execute(sql).fetchall()
    return [{"source": r[0], "confidence": r[1], "area_m2": r[2], "wkt": r[3]} for r in rows], sql


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    w, s, e, n = boundary_polygon(BOUNDARY).bounds
    bbox = (s, w, n, e)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    out = RAW_DIR / f"vida_buildings_{now.date().isoformat()}.json"
    if out.exists() and not args.force:
        print(f"{out.name} sudah ada; pakai --force", file=sys.stderr)
        return 1
    rows, sql = fetch(bbox)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    by_src: dict[str, int] = {}
    for r in rows:
        by_src[r["source"]] = by_src.get(r["source"], 0) + 1
    meta = {"downloaded_at": now.isoformat().replace("+00:00", "Z"), "download_date": now.date().isoformat(),
            "source": SOURCE, "url": URL, "bbox_swne": [round(v, 7) for v in bbox], "query": sql,
            "count": len(rows), "count_by_source": by_src, "raw_file": out.name,
            "raw_sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "license": LICENSE, "usage": USAGE}
    validate_meta(meta, SCHEMA)
    out.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"raw": out.name, "count": len(rows), "by_source": by_src}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
