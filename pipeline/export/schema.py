"""Validasi output/masukan ekspor terhadap schemas/*.schema.json (JSON Schema Draft 2020-12, paket jsonschema)."""
from __future__ import annotations

import json
import math
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
MAX_ERRORS = 10
MAX_MESSAGE_LEN = 200


@cache
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _non_finite(obj, path: str = "") -> list[str]:
    """Lokasi nilai NaN/Infinity (JSON Schema `number` tidak menolaknya, JSON standar tidak mengizinkannya)."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return [f"{path or '/'}: nilai tidak finit ({obj})"]
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.extend(_non_finite(v, f"{path}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(_non_finite(v, f"{path}/{i}"))
    return found


def errors(name: str, data) -> list[str]:
    """Daftar pesan galat (maks MAX_ERRORS, terurut); kosong berarti valid. NaN/Inf ditolak."""
    errs = sorted(_validator(name).iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path])
    msgs = [f"/{'/'.join(str(p) for p in e.absolute_path)}: {e.message[:MAX_MESSAGE_LEN]}" for e in errs]
    return (msgs + _non_finite(data))[:MAX_ERRORS]


class TiersError(ValueError):
    """tiers.json tidak valid."""


def load_tiers(path: Path) -> list[dict]:
    """Baca dan validasi data/tiers.json; kembalikan entries. TiersError bila tidak valid atau id ganda."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errs = errors("tiers", data)
    if errs:
        raise TiersError("; ".join(errs))
    ids = [e["id"] for e in data["entries"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise TiersError(f"id ganda di tiers.json: {dup}")
    return data["entries"]
