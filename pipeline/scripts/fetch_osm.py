"""GAME-6: unduh SEMUA data OSM relevan dalam batas desa (bbox batas; clip dilakukan saat audit).

Dijalankan dari folder pipeline/:
    uv run python scripts/fetch_osm.py            # unduh dari Overpass -> data/raw/osm/osm_all_<tanggal>.json (+ .meta.json)
    uv run python scripts/fetch_osm.py --check    # validasi raw + meta terbaru tanpa jaringan

Data mentah read-only setelah ditulis (tidak ditimpa bila file bertanggal sama sudah ada, kecuali --force).
Data (c) OpenStreetMap contributors, ODbL 1.0.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from osm.meta import build_meta, load_meta  # noqa: E402
from osm.parse import boundary_polygon, validate_raw  # noqa: E402
from osm.query import build_query  # noqa: E402

RAW_DIR = ROOT / "data" / "raw" / "osm"
BOUNDARY = ROOT / "data" / "boundary.geojson"
ENDPOINT = "https://overpass-api.de/api/interpreter"
UA = {"User-Agent": "game-3d-pipeline/0.1 (GAME-6 OSM audit)"}
ATTEMPTS = 5
BACKOFF_BASE_S = 10
BACKOFF_MAX_S = 60
HTTP_TIMEOUT = httpx.Timeout(300, connect=15)


def overpass(query: str) -> dict:
    last = None
    for i in range(ATTEMPTS):
        try:
            r = httpx.post(ENDPOINT, data={"data": query}, headers=UA, timeout=HTTP_TIMEOUT)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                return r.json()
            last = f"HTTP {r.status_code}"
        except httpx.HTTPError as e:
            last = repr(e)
        print("retry:", last, file=sys.stderr)
        time.sleep(min(BACKOFF_BASE_S * 2**i, BACKOFF_MAX_S))
    raise RuntimeError(f"Overpass gagal: {last}")


def canonical(data: dict) -> dict:
    """Urutkan elemen (type,id) supaya file deterministik untuk respons yang sama."""
    order = {"node": 0, "way": 1, "relation": 2}
    out = dict(data)
    out["elements"] = sorted(data["elements"], key=lambda e: (order[e["type"]], e["id"]))
    return out


def latest(suffix: str) -> Path:
    files = sorted(RAW_DIR.glob(f"osm_all_*{suffix}"))
    files = [f for f in files if (suffix != ".json" or not f.name.endswith(".meta.json"))]
    if not files:
        raise FileNotFoundError("belum ada raw osm_all_*; jalankan tanpa --check")
    return files[-1]


def check() -> int:
    raw = latest(".json")
    validate_raw(json.loads(raw.read_text(encoding="utf-8")))
    load_meta(raw)  # skema + sha256
    print(f"OK: {raw.name} + {raw.with_suffix('.meta.json').name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validasi raw+meta terbaru, tanpa jaringan")
    ap.add_argument("--force", action="store_true", help="timpa file bertanggal sama")
    args = ap.parse_args()
    if args.check:
        return check()

    fc = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    provisional = bool(fc["features"][0]["properties"].get("provisional"))
    w, s, e, n = boundary_polygon(BOUNDARY).bounds
    bbox = (s, w, n, e)
    query = build_query(bbox)

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    raw_p = RAW_DIR / f"osm_all_{now.date().isoformat()}.json"
    if raw_p.exists() and not args.force:
        print(f"{raw_p.name} sudah ada; pakai --force untuk menimpa", file=sys.stderr)
        return 1

    data = canonical(overpass(query))
    validate_raw(data)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_p.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")
    meta = build_meta(data=data, raw_file=raw_p, endpoint=ENDPOINT, query=query, bbox_swne=bbox,
                      downloaded_at=now.isoformat().replace("+00:00", "Z"), provisional=provisional)
    raw_p.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"raw": raw_p.name, "counts": meta["element_counts"],
                      "osm_base": meta["osm_base_timestamp"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
