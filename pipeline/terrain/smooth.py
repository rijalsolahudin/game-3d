"""Filter Gaussian separabel pada grid global (dijalankan sebelum dipotong per chunk)."""
from __future__ import annotations

import math

import numpy as np


def kernel_radius(sigma_px: float, truncate: float) -> int:
    return math.ceil(truncate * sigma_px) if sigma_px > 0 else 0


def _gaussian_kernel(sigma_px: float, radius: int) -> np.ndarray:
    k = np.arange(-radius, radius + 1, dtype=np.float64)
    w = np.exp(-0.5 * (k / sigma_px) ** 2)
    return w / w.sum()


def _blur_axis(a: np.ndarray, kernel: np.ndarray, axis: int) -> np.ndarray:
    radius = (len(kernel) - 1) // 2
    pad = [(0, 0), (0, 0)]
    pad[axis] = (radius, radius)
    p = np.pad(a, pad, mode="edge")
    n = a.shape[axis]
    out = np.zeros_like(a)
    for i, w in enumerate(kernel):
        sl = [slice(None), slice(None)]
        sl[axis] = slice(i, i + n)
        out += w * p[tuple(sl)]
    return out


def gaussian_blur(a: np.ndarray, sigma_px: float, truncate: float) -> np.ndarray:
    """Gaussian 2D separabel; sigma_px = 0 mengembalikan salinan tanpa perubahan."""
    if sigma_px <= 0:
        return a.copy()
    kernel = _gaussian_kernel(sigma_px, kernel_radius(sigma_px, truncate))
    return _blur_axis(_blur_axis(a, kernel, 0), kernel, 1)
