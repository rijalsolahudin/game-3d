"""Muat dan validasi masukan ekspor: raw OSM + pembanding (cek sha256 lewat meta loader GAME-6), batas, origin, tiers."""
from __future__ import annotations

import json
from pathlib import Path

from export.schema import load_tiers
from geo.projection import default_projection
from osm.audit import REF_SCHEMA
from osm.meta import load_meta, sha256_file
from osm.parse import RawFormatError, boundary_polygon, load_raw

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def newest(folder: Path, prefix: str) -> Path | None:
    files = sorted(f for f in folder.glob(f"{prefix}_*.json") if not f.name.endswith(".meta.json"))
    return files[-1] if files else None


def _boundary_props(path: Path) -> dict:
    """Properti fitur kind=boundary (sudah lolos boundary_polygon)."""
    fc = json.loads(path.read_text(encoding="utf-8"))
    return next(f["properties"] for f in fc["features"] if f["properties"].get("kind") == "boundary")


def load_inputs(data_dir: Path = DATA, use_supplement: bool = True) -> dict:
    """Kembalikan dict masukan. MetaError/TiersError/RawFormatError bila masukan tidak valid; FileNotFoundError bila hilang."""
    raw_osm = newest(data_dir / "raw" / "osm", "osm_all")
    if raw_osm is None:
        raise FileNotFoundError("raw OSM belum ada; jalankan scripts/fetch_osm.py")
    osm_meta = load_meta(raw_osm)
    osm_data = load_raw(raw_osm)
    inputs = [{"name": "osm_raw", "file": raw_osm.name, "sha256": osm_meta["raw_sha256"]}]
    dates = {"osm": osm_meta["download_date"]}

    ref_rows = None
    raw_ref = newest(data_dir / "raw" / "open_buildings", "vida_buildings") if use_supplement else None
    if raw_ref is not None:
        ref_meta = load_meta(raw_ref, REF_SCHEMA)
        ref_rows = json.loads(raw_ref.read_text(encoding="utf-8"))
        if not isinstance(ref_rows, list):
            raise ValueError(f"{raw_ref.name} harus berupa list baris")
        inputs.append({"name": "open_buildings_raw", "file": raw_ref.name, "sha256": ref_meta["raw_sha256"]})
        dates["google"] = dates["microsoft"] = ref_meta["download_date"]

    boundary_path, origin_path, tiers_path = data_dir / "boundary.geojson", data_dir / "origin.json", data_dir / "tiers.json"
    try:  # divalidasi dulu (tepat satu fitur kind=boundary, polygon valid) sebelum properti dibaca
        boundary = boundary_polygon(boundary_path)
    except (KeyError, TypeError, IndexError) as e:
        raise RawFormatError(f"{boundary_path.name} bukan GeoJSON batas yang valid: {e!r}") from e
    props = _boundary_props(boundary_path)
    proj = default_projection(origin_path)  # divalidasi terhadap origin.schema.json
    origin = json.loads(origin_path.read_text(encoding="utf-8"))
    tier_entries = load_tiers(tiers_path)
    for name, p in (("boundary", boundary_path), ("origin", origin_path), ("tiers", tiers_path)):
        inputs.append({"name": name, "file": p.name, "sha256": sha256_file(p)})
    meta = {
        "inputs": inputs, "download_dates": dates,
        "origin": {"lat": origin["lat"], "lng": origin["lng"], "provisional": bool(origin.get("provisional"))},
        "boundary": {"provisional": bool(props.get("provisional")), **({"method": props["method"]} if "method" in props else {})},
    }
    return {"osm_data": osm_data, "ref_rows": ref_rows, "boundary": boundary, "proj": proj,
            "tier_entries": tier_entries, "meta": meta}
