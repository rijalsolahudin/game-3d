"""Metadata unduhan OSM mentah: pembuatan dan validasi terhadap schemas/osm_raw_meta.schema.json."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "osm_raw_meta.schema.json"
LICENSE = "ODbL 1.0"
ATTRIBUTION = "(c) OpenStreetMap contributors"
SOURCE = "OpenStreetMap via Overpass API"
_PY_TYPES = {"string": str, "object": dict, "array": list, "boolean": bool, "integer": int, "number": (int, float)}


class MetaError(ValueError):
    """Metadata tidak sesuai skema."""


def validate_meta(meta: dict, schema_path: Path = SCHEMA_PATH) -> None:
    """Validasi subset JSON Schema (required + type properti) tanpa dependensi tambahan."""
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = [f"field wajib hilang: {k}" for k in schema["required"] if k not in meta]
    for k, spec in schema["properties"].items():
        if k not in meta:
            continue
        v = meta[k]
        wrong_bool = isinstance(v, bool) and spec["type"] in ("integer", "number")  # bool subclass int
        if wrong_bool or not isinstance(v, _PY_TYPES[spec["type"]]):
            errors.append(f"tipe salah: {k} harus {spec['type']}")
    if errors:
        raise MetaError("; ".join(errors))


def load_meta(raw_path: Path, schema_path: Path = SCHEMA_PATH) -> dict:
    """Baca `<raw>.meta.json`, validasi skema, dan cocokkan sha256 dengan file raw. MetaError bila gagal."""
    raw_path = Path(raw_path)
    meta_path = raw_path.with_suffix(".meta.json")
    if not meta_path.exists():
        raise MetaError(f"metadata {meta_path.name} tidak ada untuk {raw_path.name}; "
                        "unduh ulang dengan skrip fetch yang sesuai (metadata ditulis bersama raw)")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise MetaError(f"{meta_path.name} bukan JSON valid: {e}") from e
    validate_meta(meta, schema_path)
    if meta["raw_sha256"] != sha256_file(raw_path):
        raise MetaError(f"sha256 {raw_path.name} tidak cocok dengan {meta_path.name}; raw berubah setelah diunduh")
    return meta


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def element_counts(data: dict) -> dict:
    c = Counter(e["type"] for e in data["elements"])
    tagged = Counter(e["type"] for e in data["elements"] if e.get("tags"))
    return {"total": len(data["elements"]), **{t: c.get(t, 0) for t in ("node", "way", "relation")},
            "tagged": {t: tagged.get(t, 0) for t in ("node", "way", "relation")}}


def build_meta(*, data: dict, raw_file: Path, endpoint: str, query: str, bbox_swne, downloaded_at: str,
               provisional: bool) -> dict:
    meta = {
        "downloaded_at": downloaded_at,
        "download_date": downloaded_at[:10],
        "source": SOURCE,
        "endpoint": endpoint,
        "query": query,
        "bbox_swne": [round(v, 7) for v in bbox_swne],
        "osm_base_timestamp": data.get("osm3s", {}).get("timestamp_osm_base", ""),
        "element_counts": element_counts(data),
        "raw_file": Path(raw_file).name,
        "raw_sha256": sha256_file(raw_file),
        "boundary_provisional": provisional,
        "license": LICENSE,
        "attribution": ATTRIBUTION,
    }
    validate_meta(meta)
    return meta
