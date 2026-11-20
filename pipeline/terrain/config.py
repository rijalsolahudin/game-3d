"""Konfigurasi heightmap. Semua parameter tuning ada di sini (tanpa angka ajaib di modul lain)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from geo.chunks import CHUNK_SIZE_M

FORMAT_VERSION = 1
RAW_MAX = 65535  # nilai maksimum uint16


@dataclass(frozen=True)
class HeightmapConfig:
    # (2^n)+1 sampel per sisi chunk; 257 -> 1 m/piksel pada chunk 256 m.
    resolution: int = 257
    # Chunk tambahan di sekeliling chunk yang beririsan dengan batas (kabut/horizon).
    margin_chunks: int = 1
    # Padding rentang tinggi global (m) di bawah min dan di atas max.
    height_padding_m: float = 1.0
    # Gaussian ringan (sigma dalam meter); 0 = smoothing mati.
    smooth_sigma_m: float = 12.0
    # Kernel Gaussian dipotong pada kelipatan sigma ini.
    smooth_truncate_sigmas: float = 3.0
    # Rentang tinggi wajar (m) untuk sampel DEM; di luar ini dianggap data rusak (nodata tak bertanda).
    valid_height_min_m: float = -500.0
    valid_height_max_m: float = 9000.0
    # Jumlah baris lattice per blok saat sampling (batas memori).
    block_rows: int = 256

    def __post_init__(self) -> None:
        n = self.resolution - 1
        if self.resolution < 3 or n & (n - 1):
            raise ValueError(f"resolution harus (2^n)+1 dan >= 3, dapat {self.resolution}")
        if self.margin_chunks < 0 or self.smooth_sigma_m < 0 or self.height_padding_m < 0:
            raise ValueError("margin_chunks, smooth_sigma_m, height_padding_m tidak boleh negatif")

    @property
    def intervals(self) -> int:
        """Jumlah interval sampel per sisi chunk (resolution - 1)."""
        return self.resolution - 1

    @property
    def spacing_m(self) -> float:
        return CHUNK_SIZE_M / self.intervals

    def as_dict(self) -> dict:
        return asdict(self)
