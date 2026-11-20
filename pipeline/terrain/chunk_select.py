"""Pemilihan chunk yang beririsan dengan polygon batas (koordinat lokal) + margin."""
from __future__ import annotations

import math

from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

from geo.chunks import CHUNK_SIZE_M, chunk_bounds


def select_chunks(boundary_local: BaseGeometry, margin_chunks: int) -> list[tuple[int, int]]:
    """Daftar (cx, cz) terurut: chunk beririsan dengan batas, dilebarkan margin kotak (Chebyshev)."""
    if boundary_local.is_empty:
        raise ValueError("polygon batas kosong")
    min_x, min_z, max_x, max_z = boundary_local.bounds
    hit: set[tuple[int, int]] = set()
    for cx in range(math.floor(min_x / CHUNK_SIZE_M), math.floor(max_x / CHUNK_SIZE_M) + 1):
        for cz in range(math.floor(min_z / CHUNK_SIZE_M), math.floor(max_z / CHUNK_SIZE_M) + 1):
            if boundary_local.intersects(box(*chunk_bounds(cx, cz))):
                hit.add((cx, cz))
    sel = {
        (cx + dx, cz + dz)
        for cx, cz in hit
        for dx in range(-margin_chunks, margin_chunks + 1)
        for dz in range(-margin_chunks, margin_chunks + 1)
    }
    return sorted(sel)
