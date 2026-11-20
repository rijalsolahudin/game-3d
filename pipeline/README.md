# Pipeline Data Peta - Desa Tumanggal

Python dikelola dengan `uv`. Jalankan semua perintah dari folder `pipeline/`.

```
uv sync
uv run pytest
uv run python scripts/fetch_boundary.py                  # unduh Overpass + proses (provisional, radius 1500 m)
uv run python scripts/fetch_boundary.py --radius-m 1200  # radius lain
uv run python scripts/fetch_boundary.py --offline        # proses dari raw terbaru, tanpa jaringan
uv run python scripts/fetch_boundary.py --from-geojson path/batas_resmi.geojson [--buffer-m 200]
```

Keluaran: `data/boundary.geojson`, `data/origin.json`, `data/preview/boundary.html`
(buka manual di browser; berisi label "BATAS SEMENTARA").

## Status GAME-5: batas SEMENTARA (provisional)

OSM tidak punya relation batas administratif Desa Tumanggal (dicek 2026-11-20: query
`relation["boundary"="administrative"]["name"~"Tumanggal",i]` kosong; hanya ada node
`place=village` id 1308706192, `admin_level=7`, tanpa polygon; `is_in` hanya Indonesia,
Jawa Tengah, Kab. Purbalingga). Atas keputusan pemilik produk dipakai batas sementara:

- **Lingkaran radius 1500 m** di sekitar node desa OSM `node/1308706192`
  (-7.3487136, 109.4864955), dibuat di UTM 49S (EPSG:32749) lalu dikembalikan ke EPSG:4326.
- **Buffer 200 m D1 tidak ditambahkan lagi**: lingkaran ini sudah mewakili batas + buffer.
- D1 masih berstatus usulan. Properti `boundary.geojson`: `provisional: true`,
  `method: "circle_around_osm_village_node"`, `radius_m`, `osm_node`, `retrieved_at`,
  `license: "ODbL (OSM)"`, `note` (harus diganti peta batas resmi desa).
- Luas: **7.0679 km2** (lingkaran). Luas "sebelum buffer" tidak ada (batas asli belum tersedia).

### Mengganti dengan batas resmi nanti

1. Simpan GeoJSON batas desa (Polygon/MultiPolygon, EPSG:4326) dari pemerintah desa, mis. di
   `data/raw/official/` (catat sumber, tanggal, lisensi di bagian bawah).
2. `uv run python scripts/fetch_boundary.py --from-geojson data/raw/official/batas.geojson`
   (buffer 200 m ditambahkan lewat UTM 49S; ubah dengan `--buffer-m`). Hasilnya
   `provisional: false`, `method: "official_boundary_plus_buffer"`.
3. Tinjau ulang origin dan pratinjau, minta persetujuan ulang, perbarui ARC section 2.2.
4. Pastikan origin tetap berada di dalam batas baru. Perubahan origin berarti semua
   koordinat dihitung ulang.

## Origin (usulan, provisional)

- **lat -7.3486842, lng 109.4868011** (EPSG:4326); UTM 49S 332973.86 E, 9187422.85 N.
- Sumber: OSM `way/697906351` (`highway=residential`), titik terdekat dari node desa (34 m).
- Alasan: tidak ada `amenity=townhall` atau nama "Balai Desa"/"Kantor Desa" di OSM dalam
  lingkaran, sehingga dipakai fallback jalan terdekat. Sebaiknya diganti titik depan balai
  desa begitu lokasinya diketahui.
- Detail: `data/origin.json`.

## Jalan

44 way jalan di bbox lingkaran (residential 40, tertiary 2, unclassified 1, secondary 1);
33 di antaranya beririsan dengan lingkaran dan ditampilkan di pratinjau. 8 way memotong tepi lingkaran, termasuk `Jalan Raya Selakambang`
(secondary), 2 way tertiary, dan sisanya residential/unclassified. Karena batas berupa
lingkaran buatan, jalan-jalan itu terpotong di tepi; ini wajar untuk batas sementara dan
akan hilang/bergeser saat batas resmi dipakai.

## Sumber data dan lisensi

- OpenStreetMap via Overpass API (https://overpass-api.de), diunduh 2026-11-20.
  (c) OpenStreetMap contributors, lisensi ODbL 1.0; atribusi wajib pada peta/rilis.
- Data mentah bertanggal di `data/raw/osm/` (`node_*.json`, `features_*.json`; gitignore).
- Overpass sering mengembalikan 502; skrip mengulang dengan jeda dan memakai User-Agent.

## Modul

- `geo/projection.py`: satu-satunya modul proyeksi (EPSG:4326, EPSG:32749, lokal x=timur, z=utara).
- `scripts/fetch_boundary.py`: pengambilan data, batas, origin, dan pratinjau.
- `tests/`: proyeksi dan batas/origin (provisional true, lingkaran sesuai radius, origin di dalam).
