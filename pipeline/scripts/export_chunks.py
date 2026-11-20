"""GAME-17: ekspor jalan, air, landuse, bangunan, dan tier ke JSON per chunk.

Dijalankan dari folder pipeline/:
    uv run python scripts/export_chunks.py                  # -> data/out/chunks/{id}.json + index.json
    uv run python scripts/export_chunks.py --no-supplement  # hanya OSM (tanpa Google/Microsoft)

Masukan: data/raw/osm (+meta), data/raw/open_buildings (+meta, opsional), data/boundary.geojson,
data/origin.json, data/tiers.json. Laporan: data/out/export_report.json. Kode keluar 1 bila ada data tidak valid.
Data (c) OpenStreetMap contributors (ODbL); Google Open Buildings v3 (CC BY 4.0); Microsoft ML Building Footprints (ODbL).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from export.assemble import build_chunks  # noqa: E402
from export.config import ExportConfig  # noqa: E402
from export.inputs import DATA, load_inputs  # noqa: E402
from export.schema import TiersError  # noqa: E402
from export.writer import OutputDirError, write_export  # noqa: E402
from osm.meta import MetaError  # noqa: E402
from osm.parse import RawFormatError  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-supplement", action="store_true", help="abaikan footprint Google/Microsoft")
    ap.add_argument("--out", type=Path, default=DATA / "out" / "chunks")
    ap.add_argument("--report", type=Path, default=DATA / "out" / "export_report.json")
    args = ap.parse_args()
    cfg = ExportConfig()
    try:
        inp = load_inputs(use_supplement=not args.no_supplement)
    except (MetaError, TiersError, RawFormatError, OSError, ValueError) as e:
        print(f"ekspor dibatalkan: {e}", file=sys.stderr)
        return 1
    chunks, stats, notes = build_chunks(inp["osm_data"], inp["ref_rows"], inp["boundary"], inp["proj"],
                                        inp["tier_entries"], cfg)
    try:
        report = write_export(chunks, stats, notes, args.out, args.report, inp["meta"], cfg)
    except OutputDirError as e:
        print(f"ekspor dibatalkan: {e}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if not report["ok"]:
        print("ekspor GAGAL validasi skema; lihat invalid_chunks/index_errors di laporan", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
