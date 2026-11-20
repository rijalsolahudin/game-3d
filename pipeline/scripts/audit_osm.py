"""GAME-6: audit data OSM -> pipeline/docs/osm-audit.md (deterministik; tanpa jaringan).

Dijalankan dari folder pipeline/:
    uv run python scripts/audit_osm.py              # pakai raw OSM terbaru (+ pembanding bila ada)
    uv run python scripts/audit_osm.py --json       # cetak hasil mentah audit sebagai JSON (debug)

Masukan: data/raw/osm/osm_all_*.json(+meta), data/raw/open_buildings/vida_buildings_*.json (opsional),
data/boundary.geojson, data/origin.json. Data (c) OpenStreetMap contributors, ODbL.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from osm.audit import run  # noqa: E402
from osm.completeness import ReferenceFormatError  # noqa: E402
from osm.meta import MetaError  # noqa: E402
from osm.report import render  # noqa: E402

RAW_OSM = ROOT / "data" / "raw" / "osm"
RAW_REF = ROOT / "data" / "raw" / "open_buildings"
OUT = ROOT / "docs" / "osm-audit.md"


def newest(folder: Path, prefix: str) -> Path | None:
    files = sorted(f for f in folder.glob(f"{prefix}_*.json") if not f.name.endswith(".meta.json"))
    return files[-1] if files else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    raw = newest(RAW_OSM, "osm_all")
    if raw is None:
        print("raw OSM belum ada; jalankan scripts/fetch_osm.py", file=sys.stderr)
        return 1
    ref = newest(RAW_REF, "vida_buildings")
    try:
        res = run(raw, ROOT / "data" / "boundary.geojson", ROOT / "data" / "origin.json", ref)
    except (MetaError, ReferenceFormatError) as e:
        print(f"audit dibatalkan: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(res), encoding="utf-8")
    print(f"ditulis {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
