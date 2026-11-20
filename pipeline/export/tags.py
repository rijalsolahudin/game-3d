"""Parsing dan sanitasi tag OSM. Privasi (NFR-07): hanya nilai generik yang lolos; tidak ada nama/alamat bangunan."""
from __future__ import annotations

import re

_METERS = re.compile(r"\s*(\d+(?:[.,]\d+)?)\s*(?:m|meter|metre|metres|meters)?\s*", re.IGNORECASE)
_LEVELS = re.compile(r"\s*(\d{1,3})(?:\.0+)?\s*")
# Pola/batas ini diduplikasi di schemas/chunk.schema.json (JSON tidak bisa impor); test_schema_constants menjaganya sama.
SLUG_PATTERN = r"[a-z0-9_]{1,40}"
SURFACE_PATTERN = r"[a-z0-9_:;]{1,60}"
_SLUG = re.compile(SLUG_PATTERN)
_SURFACE = re.compile(SURFACE_PATTERN)
_LAYER = re.compile(r"\s*(-?\d{1,3})\s*")
MAX_NAME_LEN = 100


def parse_meters(value, lo: float, hi: float) -> float | None:
    """'4', '4.5 m', '4,5' -> float dalam [lo, hi]; selain itu None."""
    if not isinstance(value, str):
        return None
    m = _METERS.fullmatch(value)
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    return v if lo <= v <= hi else None


def parse_levels(value) -> int | None:
    if not isinstance(value, str):
        return None
    m = _LEVELS.fullmatch(value)
    if not m:
        return None
    n = int(m.group(1))
    return n if n >= 1 else None


def parse_layer(value) -> int | None:
    if not isinstance(value, str):
        return None
    m = _LAYER.fullmatch(value)
    return int(m.group(1)) if m else None


def slug(value) -> str | None:
    """Nilai tag sederhana (huruf kecil/angka/_) atau None."""
    return value if isinstance(value, str) and _SLUG.fullmatch(value) else None


def surface(value) -> str | None:
    return value if isinstance(value, str) and _SURFACE.fullmatch(value) else None


def flag(value) -> bool:
    """bridge/tunnel: true bila ada dan bukan 'no'."""
    return isinstance(value, str) and value != "no"


def safe_name(value) -> str | None:
    """Nama jalan publik: teks tanpa karakter kontrol, dipangkas spasi; None bila tak layak."""
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v or len(v) > MAX_NAME_LEN or any(ord(c) < 32 or ord(c) == 127 for c in v):
        return None
    return v


def road_base_kind(kind: str) -> str:
    return kind[: -len("_link")] if kind.endswith("_link") else kind
