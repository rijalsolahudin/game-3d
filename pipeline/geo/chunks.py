"""Helper chunk dunia: koordinat lokal (meter) -> ID chunk "{x}_{z}" dan bounds.

Chunk 256 m; floor division sehingga koordinat negatif jatuh ke chunk negatif
(mis. x = -0.1 -> chunk -1). Sumber aturan: domain.md (koordinat).
"""
from __future__ import annotations

import re

CHUNK_SIZE_M = 256

# Integer kanonik: tanpa "-0" dan tanpa nol di depan; fullmatch menolak newline di akhir.
_INT = r"(0|-?[1-9][0-9]*)"
_ID_RE = re.compile(rf"{_INT}_{_INT}")


def chunk_coords(x: float, z: float, size: int = CHUNK_SIZE_M) -> tuple[int, int]:
    """Indeks chunk (cx, cz) yang memuat titik lokal (x, z)."""
    return int(x // size), int(z // size)


def format_chunk_id(cx: int, cz: int) -> str:
    return f"{cx}_{cz}"


def chunk_id(x: float, z: float, size: int = CHUNK_SIZE_M) -> str:
    """ID chunk `"{cx}_{cz}"` untuk titik lokal (x, z)."""
    return format_chunk_id(*chunk_coords(x, z, size))


def parse_chunk_id(cid: str) -> tuple[int, int]:
    m = _ID_RE.fullmatch(cid)
    if not m:
        raise ValueError(f"chunk ID tidak valid: {cid!r} (format \"{{x}}_{{z}}\")")
    return int(m.group(1)), int(m.group(2))


def chunk_bounds(
    cid_or_cx: str | int, cz: int | None = None, size: int = CHUNK_SIZE_M
) -> tuple[float, float, float, float]:
    """Bounds chunk (min_x, min_z, max_x, max_z) dalam meter lokal.

    Terima ID string `"{x}_{z}"` atau pasangan indeks (cx, cz).
    Batas bawah inklusif, batas atas eksklusif (milik chunk tetangga).
    """
    if isinstance(cid_or_cx, str):
        cx, cz = parse_chunk_id(cid_or_cx)
    else:
        if cz is None:
            raise ValueError("cz wajib bila cx diberikan sebagai integer")
        cx = cid_or_cx
    return float(cx * size), float(cz * size), float((cx + 1) * size), float((cz + 1) * size)
