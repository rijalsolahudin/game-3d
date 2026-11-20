---
paths:
  - "pipeline/**"
---

# Aturan Pipeline Data Peta

- Python 3 dikelola dengan `uv` (`pyproject.toml` + `uv.lock`); GDAL/pyproj untuk proyeksi, Blender (+ Blosm) untuk modeling.
- Semua konversi koordinat lewat satu modul proyeksi bersama (UTM 49S / EPSG:32749 → koordinat lokal relatif origin). Dilarang menghitung proyeksi sendiri di skrip lain.
- `pipeline/data/raw/` berisi data mentah apa adanya dan di-gitignore; catat sumber, tanggal unduh, dan lisensi di `pipeline/README.md`.
- Output (heightmap, JSON per chunk) WAJIB lolos validasi skema di `pipeline/schemas/` sebelum ditulis; data tidak valid dilaporkan, bukan dibuang diam-diam.
- Skrip harus deterministik dan idempoten: input sama → output identik.
- Output per chunk memakai ID `"{x}_{z}"` (chunk 256 m); tepi heightmap antar chunk harus identik (tanpa seam).
- Referensi foto survei di `pipeline/data/reference/<slug>/`; tanpa nama pemilik atau data pribadi warga.
- Test dengan pytest untuk proyeksi, validasi skema, dan penyambungan antar chunk.
