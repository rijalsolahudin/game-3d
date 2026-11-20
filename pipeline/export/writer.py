"""Validasi skema, index.json, laporan ringkasan, dan penulisan atomik output ekspor (byte-identik bila input sama)."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from export import buildings as B
from export import config as C
from export import schema

_CHUNK_FILE = re.compile(r"(0|-?[1-9][0-9]*)_(0|-?[1-9][0-9]*)\.json")
INDEX_NAME = "index.json"


class OutputDirError(ValueError):
    """Folder keluaran berisi file yang bukan milik ekspor ini; tidak ditimpa."""


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"


def _km(stats: Counter, prefix: str) -> dict:
    return {k[len(prefix):]: round(v, 3) for k, v in sorted(stats.items()) if k.startswith(prefix)}


def build_index(files: dict, stats: Counter, meta: dict, cfg: C.ExportConfig) -> dict:
    """files: {chunk_id: (chunk dict, bytes, sha256)}."""
    entries = []
    for cid, (ch, nbytes, digest) in files.items():
        entries.append({"id": cid, "cx": ch["cx"], "cz": ch["cz"], "file": f"{cid}.json", "bytes": nbytes,
                        "sha256": digest, "counts": {k: len(ch[k]) for k in ("roads", "waterways", "areas", "buildings")}})
    chunks = [ch for ch, _, _ in files.values()]
    by_source = Counter(b["source"] for ch in chunks for b in ch["buildings"])
    by_tier = Counter(b["tier"] for ch in chunks for b in ch["buildings"])
    road_km = sum(v for k, v in stats.items() if k.startswith("roads_km_"))
    sources = []
    for sid, info in C.SOURCE_INFO.items():
        s = {"id": sid, **info, "used_buildings": by_source.get(sid, 0)}
        if sid in meta["download_dates"]:
            s["download_date"] = meta["download_dates"][sid]
        sources.append(s)
    return {
        "schema_version": C.SCHEMA_VERSION, "chunk_size_m": cfg.chunk_size_m,
        "coordinate_system": C.COORDINATE_SYSTEM,
        "origin": meta["origin"], "boundary": meta["boundary"], "sources": sources, "inputs": meta["inputs"],
        "config": cfg.as_dict(),
        "totals": {"chunks": len(entries), "road_pieces": sum(len(c["roads"]) for c in chunks),
                   "road_km": round(road_km, 3), "waterway_pieces": sum(len(c["waterways"]) for c in chunks),
                   "areas": sum(len(c["areas"]) for c in chunks), "buildings": sum(by_source.values()),
                   "buildings_by_source": dict(sorted(by_source.items())), "buildings_by_tier": dict(sorted(by_tier.items()))},
        "chunks": entries,
    }


def build_report(stats: Counter, notes: dict, invalid: dict, index_errors: list, total_bytes: int) -> dict:
    supp = {"rows": stats.get("supp_rows", 0),
            "accepted": {s: stats.get(f"supp_accepted_{s}", 0) for s in B.SUPP_SOURCES},
            "rejected": {r: stats.get(f"supp_rejected_{r}", 0) for r in B.SUPP_REJECT_REASONS}}
    return {
        "ok": not invalid and not index_errors,
        "invalid_chunks": invalid, "index_errors": index_errors,
        "road_km_by_kind": _km(stats, "roads_km_"), "waterway_km_by_kind": _km(stats, "waterways_km_"),
        "road_ways": stats.get("roads_ways", 0), "waterway_ways": stats.get("waterways_ways", 0),
        "outside_boundary": {k: v for k, v in sorted(stats.items()) if k.endswith("_outside_boundary")},
        "areas": {k[len(C.AREA_STAT_PREFIX):]: v for k, v in sorted(stats.items()) if k.startswith(C.AREA_STAT_PREFIX) and not k.endswith("_boundary")},
        "buildings": {"osm_in_raw": stats.get("osm_buildings_total_raw", 0), "osm_exported": stats.get("buildings_osm", 0),
                      "google_exported": stats.get("buildings_google", 0),
                      "microsoft_exported": stats.get("buildings_microsoft", 0),
                      "tier": {t: stats.get(f"buildings_tier_{t}", 0) for t in ("A", "B", "C")},
                      "supplement": supp},
        "skipped": dict(sorted(notes["skipped"].items())),
        "tiers_unmatched": notes["tiers_unmatched"],
        "output_bytes": total_bytes,
    }


def check_out_dir(out_dir: Path) -> None:
    """OutputDirError bila folder ada, tidak kosong, dan bukan hasil ekspor ini (index.json sah + hanya file chunk)."""
    if not out_dir.exists():
        return
    if not out_dir.is_dir():
        raise OutputDirError(f"{out_dir} bukan folder")
    entries = list(out_dir.iterdir())
    if not entries:
        return
    try:
        idx = json.loads((out_dir / INDEX_NAME).read_text(encoding="utf-8"))
        mine = idx["schema_version"] == C.SCHEMA_VERSION and idx["coordinate_system"] == C.COORDINATE_SYSTEM
    except (OSError, ValueError, KeyError, TypeError):
        mine = False
    foreign = sorted(e.name for e in entries if e.name != INDEX_NAME and not _CHUNK_FILE.fullmatch(e.name))
    if not mine or foreign:
        raise OutputDirError(f"{out_dir} bukan folder hasil ekspor chunk (index.json sah tidak ada atau ada file asing "
                             f"{foreign[:5]}); pilih --out lain atau kosongkan folder itu")


def write_export(chunks: dict, stats: Counter, notes: dict, out_dir: Path, report_path: Path, meta: dict,
                 cfg: C.ExportConfig = C.DEFAULT_CONFIG) -> dict:
    """Validasi lalu tulis. Chunk yang tidak lolos skema TIDAK ditulis dan dilaporkan; laporan selalu ditulis.

    Output ditulis ke folder sementara `<out>.new` lalu menggantikan `<out>` (chunk basi ikut hilang).
    Folder `<out>` yang berisi file asing ditolak (OutputDirError) sebelum apa pun ditulis.
    """
    out_dir, report_path = Path(out_dir), Path(report_path)
    check_out_dir(out_dir)
    invalid, files = {}, {}
    for cid, ch in chunks.items():
        errs = schema.errors("chunk", ch)
        if errs:
            invalid[cid] = errs
            continue
        files[cid] = (ch, dumps(ch))
    hashed = {cid: (ch, len(t.encode("utf-8")), hashlib.sha256(t.encode("utf-8")).hexdigest())
              for cid, (ch, t) in files.items()}
    index = build_index(hashed, stats, meta, cfg)
    index_errors = schema.errors("index", index)
    report = build_report(stats, notes, invalid, index_errors, sum(n for _, n, _ in hashed.values()))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if not index_errors:
        _replace_dir(out_dir, {f"{cid}.json": t for cid, (_, t) in files.items()} | {INDEX_NAME: dumps(index)})
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    return report


def _replace_dir(out_dir: Path, contents: dict[str, str]) -> None:
    new, old = (out_dir.with_name(out_dir.name + suffix) for suffix in (".new", ".old"))
    for tmp in (new, old):
        shutil.rmtree(tmp, ignore_errors=True)
    new.mkdir(parents=True)
    for name, text in contents.items():
        (new / name).write_text(text, encoding="utf-8")
    if out_dir.exists():
        out_dir.rename(old)
    new.rename(out_dir)
    shutil.rmtree(old, ignore_errors=True)
