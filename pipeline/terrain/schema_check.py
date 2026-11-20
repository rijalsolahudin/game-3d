"""Validator subset JSON Schema untuk output heightmap.

Dipilih validator kecil sendiri (bukan dependensi jsonschema baru). Keyword didukung:
type, required, properties, items, minItems, const, enum, minimum, maximum, pattern.
Keyword lain di skema melempar SchemaError (tidak diabaikan diam-diam); skema tetap
JSON Schema 2020-12 valid sehingga bisa dipindah ke jsonschema kelak.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"

_META = {"$schema", "title", "description"}
_RULES = {"type", "required", "properties", "items", "minItems", "const", "enum", "minimum", "maximum", "pattern"}


class SchemaError(ValueError):
    """Skema memuat keyword di luar subset."""


class ValidationError(ValueError):
    """Data tidak sesuai skema."""


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


_TYPES = {
    "number": _is_num,
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
}


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def validate(data: Any, schema: dict, path: str = "$") -> None:
    unknown = set(schema) - _META - _RULES
    if unknown:
        raise SchemaError(f"{path}: keyword tidak didukung: {sorted(unknown)}")
    t = schema.get("type")
    if t is not None:
        if t not in _TYPES:
            raise SchemaError(f"{path}: type tidak didukung: {t!r}")
        if not _TYPES[t](data):
            raise ValidationError(f"{path}: harus {t}, dapat {data!r}")
    if "const" in schema and data != schema["const"]:
        raise ValidationError(f"{path}: harus {schema['const']!r}, dapat {data!r}")
    if "enum" in schema and data not in schema["enum"]:
        raise ValidationError(f"{path}: harus salah satu {schema['enum']!r}, dapat {data!r}")
    if "minimum" in schema and data < schema["minimum"]:
        raise ValidationError(f"{path}: {data} di bawah minimum {schema['minimum']}")
    if "maximum" in schema and data > schema["maximum"]:
        raise ValidationError(f"{path}: {data} di atas maksimum {schema['maximum']}")
    if "pattern" in schema and not re.fullmatch(schema["pattern"], data):
        raise ValidationError(f"{path}: {data!r} tidak cocok pola {schema['pattern']!r}")
    for key in schema.get("required", []):
        if key not in data:
            raise ValidationError(f"{path}: field wajib '{key}' tidak ada")
    for key, rule in schema.get("properties", {}).items():
        if key in data:
            validate(data[key], rule, f"{path}.{key}")
    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            raise ValidationError(f"{path}: minimal {schema['minItems']} item, dapat {len(data)}")
        if "items" in schema:
            for i, item in enumerate(data):
                validate(item, schema["items"], f"{path}[{i}]")
