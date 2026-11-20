"""Orkestrasi: DEM -> lattice global -> smoothing -> kuantisasi -> potong per chunk -> tulis."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import explain_validity

from geo.chunks import CHUNK_SIZE_M, chunk_bounds, format_chunk_id
from geo.projection import DEFAULT_ORIGIN_PATH, UTM_49S, LocalProjection, load_origin
from terrain import schema_check
from terrain.chunk_select import select_chunks
from terrain.config import FORMAT_VERSION, RAW_MAX, HeightmapConfig
from terrain.dem import Dem, ElevationRangeError
from terrain.smooth import gaussian_blur, kernel_radius

_OWNED_RE = re.compile(r"(index|-?\d+_-?\d+)\.(json|raw)")
_BOUNDARY_TYPES = ("Polygon", "MultiPolygon")
HEIGHT_FORMULA = "height_m = height_min_m + raw / 65535 * (height_max_m - height_min_m)"


@dataclass
class BuildResult:
    chunk_ids: list[str]
    height_min_m: float
    height_max_m: float
    total_bytes: int
    out_dir: Path


def load_boundary_local(boundary_path: Path | str, proj: LocalProjection):
    """Polygon batas (GeoJSON lon/lat) -> geometri shapely lokal, lewat modul proyeksi."""
    fc = json.loads(Path(boundary_path).read_text(encoding="utf-8"))
    local = proj.geojson_to_local(fc)
    feats = local["features"] if local.get("type") == "FeatureCollection" else [local]
    geoms = []
    for f in feats:
        raw_geom = f.get("geometry") if f.get("type") == "Feature" else f
        if not raw_geom or raw_geom.get("type") not in _BOUNDARY_TYPES:
            got = raw_geom.get("type") if raw_geom else None
            raise ValueError(f"batas harus Polygon/MultiPolygon, dapat {got!r}")
        g = shape(raw_geom)
        if g.is_empty or not g.is_valid:
            raise ValueError(f"polygon batas kosong atau tidak valid: {explain_validity(g)}")
        geoms.append(g)
    if not geoms:
        raise ValueError("batas tidak berisi geometri")
    return unary_union(geoms)


def build_global_grid(dem: Dem, proj: LocalProjection, chunks: list[tuple[int, int]], cfg: HeightmapConfig):
    """Heightmap float (m) pada lattice global untuk bbox chunk; kembalikan (array, i_min, k_min).

    Lattice: x = i * spacing, z = k * spacing, i/k bilangan bulat global; chunk (cx, cz) memakai
    i in [cx*n, (cx+1)*n] (n = resolution - 1), sehingga tepi dua chunk berbagi indeks yang sama.
    """
    n = cfg.intervals
    i_min, i_max = min(c[0] for c in chunks) * n, (max(c[0] for c in chunks) + 1) * n
    k_min, k_max = min(c[1] for c in chunks) * n, (max(c[1] for c in chunks) + 1) * n
    sigma_px = cfg.smooth_sigma_m / cfg.spacing_m
    halo = kernel_radius(sigma_px, cfg.smooth_truncate_sigmas)
    xs = np.arange(i_min - halo, i_max + halo + 1, dtype=np.float64) * cfg.spacing_m
    zs = np.arange(k_min - halo, k_max + halo + 1, dtype=np.float64) * cfg.spacing_m
    grid = dem.sample_local(proj, xs, zs, cfg.block_rows)
    lo, hi = float(grid.min()), float(grid.max())
    if lo < cfg.valid_height_min_m or hi > cfg.valid_height_max_m:
        raise ElevationRangeError(
            f"tinggi DEM {lo:.1f}..{hi:.1f} m di luar rentang wajar "
            f"{cfg.valid_height_min_m}..{cfg.valid_height_max_m} m (nodata tak bertanda?)"
        )
    grid = gaussian_blur(grid, sigma_px, cfg.smooth_truncate_sigmas)
    if halo:
        grid = grid[halo:-halo, halo:-halo]
    return grid, i_min, k_min


def _slice(grid: np.ndarray, i_min: int, k_min: int, cx: int, cz: int, n: int) -> tuple[slice, slice]:
    i0, k0 = cx * n - i_min, cz * n - k_min
    return slice(k0, k0 + n + 1), slice(i0, i0 + n + 1)


def _write_json(path: Path, obj: dict) -> int:
    data = (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return len(data)


def build_heightmaps(
    dem_path: Path | str,
    boundary_path: Path | str,
    out_dir: Path | str,
    cfg: HeightmapConfig | None = None,
    origin_path: Path | str = DEFAULT_ORIGIN_PATH,
) -> BuildResult:
    cfg = cfg or HeightmapConfig()
    out_dir = Path(out_dir)
    check_output_dir(out_dir)  # gagal cepat sebelum kerja berat
    lng, lat = load_origin(origin_path)
    proj = LocalProjection(lng, lat)
    dem = Dem(dem_path)

    chunks = select_chunks(load_boundary_local(boundary_path, proj), cfg.margin_chunks)
    n = cfg.intervals
    grid, i_min, k_min = build_global_grid(dem, proj, chunks, cfg)

    # Rentang global hanya dari sel milik chunk terpilih, ditambah padding.
    slices = {c: _slice(grid, i_min, k_min, c[0], c[1], n) for c in chunks}
    h_min = min(float(grid[s].min()) for s in slices.values()) - cfg.height_padding_m
    h_max = max(float(grid[s].max()) for s in slices.values()) + cfg.height_padding_m
    span = h_max - h_min
    raw_grid = np.rint((grid - h_min) / span * RAW_MAX).clip(0, RAW_MAX).astype("<u2")

    ox, oy = proj.origin_utm
    index = {
        "format_version": FORMAT_VERSION,
        "format": {
            "encoding": "raw_uint16", "byte_order": "little", "bits": 16,
            "row_order": "south_to_north", "column_order": "west_to_east",
            "height_formula": HEIGHT_FORMULA,
        },
        "source": {"file": Path(dem_path).name, "sha256": dem.sha256, "crs": dem.crs_name},
        "crs": UTM_49S,
        "origin": {"lng": lng, "lat": lat, "utm49s": [ox, oy]},
        "chunk_size_m": CHUNK_SIZE_M,
        "resolution": cfg.resolution,
        "sample_spacing_m": cfg.spacing_m,
        "height_min_m": h_min,
        "height_max_m": h_max,
        "height_padding_m": cfg.height_padding_m,
        "smoothing": {
            "sigma_m": cfg.smooth_sigma_m,
            "truncate_sigmas": cfg.smooth_truncate_sigmas,
            "interpolation": "bicubic_catmull_rom",
        },
        "margin_chunks": cfg.margin_chunks,
        "chunk_grid": {
            "min_cx": min(c[0] for c in chunks), "max_cx": max(c[0] for c in chunks),
            "min_cz": min(c[1] for c in chunks), "max_cz": max(c[1] for c in chunks),
        },
        "chunks": [format_chunk_id(*c) for c in chunks],
    }
    schema_check.validate(index, schema_check.load_schema("heightmap_index.schema.json"))

    chunk_schema = schema_check.load_schema("heightmap_chunk.schema.json")
    payloads: list[tuple[str, bytes, dict]] = []
    for c in chunks:
        cid = format_chunk_id(*c)
        raw = raw_grid[slices[c]]
        blob = raw.tobytes()  # little-endian, row-major, baris 0 = selatan
        part = grid[slices[c]]
        meta = {
            "format_version": FORMAT_VERSION, "id": cid, "cx": c[0], "cz": c[1],
            "bounds_local": list(chunk_bounds(*c)), "file": f"{cid}.raw",
            "sha256": hashlib.sha256(blob).hexdigest(), "resolution": cfg.resolution,
            "min_height_m": float(part.min()), "max_height_m": float(part.max()),
            "raw_min": int(raw.min()), "raw_max": int(raw.max()),
            "height_range_global_m": [h_min, h_max],
        }
        schema_check.validate(meta, chunk_schema)  # gagal -> exception sebelum ada file ditulis
        payloads.append((cid, blob, meta))

    tmp_dir = out_dir.with_name(out_dir.name + ".tmp")
    old_dir = out_dir.with_name(out_dir.name + ".old")
    for d in (tmp_dir, old_dir):
        check_output_dir(d)
        if d.exists():
            shutil.rmtree(d)
    tmp_dir.mkdir(parents=True)
    total = _write_json(tmp_dir / "index.json", index)
    for cid, blob, meta in payloads:
        (tmp_dir / f"{cid}.raw").write_bytes(blob)
        total += len(blob) + _write_json(tmp_dir / f"{cid}.json", meta)
    # Semua sukses: ganti folder lewat rename (folder lama disingkirkan dulu, lalu dihapus).
    if out_dir.exists():
        out_dir.rename(old_dir)
    tmp_dir.rename(out_dir)
    if old_dir.exists():
        shutil.rmtree(old_dir)
    return BuildResult([p[0] for p in payloads], h_min, h_max, total, out_dir)


def check_output_dir(path: Path) -> None:
    """Tolak folder keluaran yang berisi sesuatu selain output heightmap (akan terhapus saat diganti)."""
    if not path.exists():
        return
    if not path.is_dir():
        raise ValueError(f"--out bukan folder: {path}")
    names = [p.name for p in path.iterdir()]
    if not names:
        return
    foreign = [n for n in names if not _OWNED_RE.fullmatch(n)]
    index_path = path / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        schema_check.validate(index, schema_check.load_schema("heightmap_index.schema.json"))
    except (OSError, ValueError) as e:  # json.JSONDecodeError dan ValidationError turunan ValueError
        raise ValueError(f"{path} berisi file tetapi bukan output heightmap (index.json tidak valid: {e})") from e
    if foreign:
        raise ValueError(f"{path} berisi file bukan milik output heightmap: {sorted(foreign)[:5]}")
