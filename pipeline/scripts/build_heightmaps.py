"""GAME-16: heightmap RAW 16-bit per chunk 256 m dari DEM.

Dijalankan dari folder pipeline/:
    uv run python scripts/build_heightmaps.py
    uv run python scripts/build_heightmaps.py --dem data/raw/dem/copernicus/X.tif --no-smooth
    uv run python scripts/build_heightmaps.py --resolution 513 --margin-chunks 2

Output ke data/out/heightmaps/ (gitignore): index.json, <id>.raw, <id>.json.
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from terrain.build import build_heightmaps
from terrain.config import HeightmapConfig
from terrain.dem import CoverageError
from terrain.schema_check import ValidationError

DEM_DIR = ROOT / "data" / "raw" / "dem" / "copernicus"
BOUNDARY = ROOT / "data" / "boundary.geojson"
OUT_DIR = ROOT / "data" / "out" / "heightmaps"


def default_dem() -> Path:
    tifs = sorted(DEM_DIR.glob("*.tif"))
    if len(tifs) != 1:
        sys.exit(f"butuh tepat satu .tif di {DEM_DIR} (ada {len(tifs)}); pakai --dem")
    return tifs[0]


def main() -> int:
    d = HeightmapConfig()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dem", type=Path, help="GeoTIFF DEM (default: satu-satunya .tif di data/raw/dem/copernicus)")
    ap.add_argument("--boundary", type=Path, default=BOUNDARY)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--resolution", type=int, default=d.resolution, help="sampel per sisi, (2^n)+1")
    ap.add_argument("--margin-chunks", type=int, default=d.margin_chunks)
    ap.add_argument("--height-padding-m", type=float, default=d.height_padding_m)
    ap.add_argument("--smooth-sigma-m", type=float, default=d.smooth_sigma_m)
    ap.add_argument("--no-smooth", action="store_true", help="matikan Gaussian (sigma 0)")
    a = ap.parse_args()

    cfg = replace(
        d,
        resolution=a.resolution,
        margin_chunks=a.margin_chunks,
        height_padding_m=a.height_padding_m,
        smooth_sigma_m=0.0 if a.no_smooth else a.smooth_sigma_m,
    )
    t0 = time.perf_counter()
    try:
        r = build_heightmaps(a.dem or default_dem(), a.boundary, a.out, cfg)
    except (CoverageError, ValidationError, ValueError) as e:
        print(f"GAGAL: {e}", file=sys.stderr)
        return 1
    print(
        f"{len(r.chunk_ids)} chunk -> {r.out_dir}; tinggi global {r.height_min_m:.2f}..{r.height_max_m:.2f} m; "
        f"{r.total_bytes / 1e6:.1f} MB; {time.perf_counter() - t0:.1f} s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
