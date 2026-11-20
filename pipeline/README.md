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
- `scripts/fetch_dem_copernicus.py`: unduh DEM sementara Copernicus GLO-30 + cek cakupan (GAME-52).
- `geo/chunks.py`: ID chunk `"{x}_{z}"` (256 m) dan bounds.
- `schemas/origin.schema.json`: skema `data/origin.json`.
- `tests/`: proyeksi dan batas/origin (provisional true, lingkaran sesuai radius, origin di dalam);
  `test_dem_copernicus.py` (pemilihan tile, cakupan, idempotensi; tanpa jaringan).

## DEM sementara: Copernicus GLO-30 (GAME-52)

```
uv run python scripts/fetch_dem_copernicus.py               # unduh tile + cek cakupan
uv run python scripts/fetch_dem_copernicus.py --check-only  # verifikasi file lokal, tanpa jaringan
```

- Pengganti sementara DEMNAS (GAME-7, butuh login manual di situs BIG); keputusan 2026-11-21 (ARC 1.4).
  Akan digantikan DEMNAS begitu file itu ada.
- Sumber: AWS Open Data `copernicus-dem-30m` (HTTPS publik, tanpa kredensial), COG 1 arc-second
  (~30 m), EPSG:4326. Tile `Copernicus_DSM_COG_10_S08_00_E109_00_DEM` (dinamai dari pojok kiri-bawah
  nominal: lintang -8..-7, bujur 109..110; grid asli bergeser setengah piksel, bounds raster
  bujur 108,99986..109,99986 dan lintang -7,99986..-6,99986, sehingga lon 109,9999 sudah masuk tile E110), 37.366.881 byte (35,6 MiB), sha256
  `5da4c2e5f8cb559a322700d6d3a318b0c331992043118be21e7c5c21a155c003`.
- Diunduh 2026-11-20 21:27 UTC (2026-11-21 WIB). Disimpan apa adanya di `data/raw/dem/copernicus/`
  (gitignore) bersama `dem_copernicus.json` (URL, waktu unduh, ukuran, sha256, ETag).
  Tanpa reproyeksi/potong: itu GAME-16.
- Skrip memeriksa bounds raster mencakup polygon batas dan tidak ada nodata di piksel yang
  disentuh polygon; bila gagal keluar dengan kode 1 dan pesan jelas. Menjalankan ulang tidak
  mengunduh lagi bila ukuran dan sha256 cocok dengan metadata. Unduhan ditulis ke `.part` lalu di-rename.
- Ketinggian di dalam batas sementara (7691 piksel): min 98,00 m, max 247,18 m, mean 184,30 m.
- Lisensi: Copernicus DEM licence, gratis untuk publik; atribusi wajib (EULA ada di bucket,
  `INFO/eula_F.pdf`; teks atribusi di bawah diverifikasi dari sana). Masukkan ke kredit game:
  "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by
  the European Union and ESA; all rights reserved".
- **Catatan untuk GAME-16: ini DSM, bukan DTM.** Nilai mencakup tinggi pohon dan bangunan, jadi
  terrain bisa sedikit bergelombang atau terangkat di area pohon lebat/permukiman. Resolusi ~30 m
  juga jauh lebih kasar dari DEMNAS (~8 m): pertimbangkan penghalusan dan jangan anggap detail
  kecil sebagai nyata.

## Proyeksi koordinat (GAME-15)

`geo/projection.py` adalah satu-satunya sumber konversi lon/lat -> koordinat game. Konvensi:
**x = timur, z = utara, 1 unit = 1 m, (0, 0) = origin** (`data/origin.json`, divalidasi terhadap
`schemas/origin.schema.json`). Lokal = UTM 49S (EPSG:32749) dikurangi UTM origin, jadi jarak lokal
adalah jarak grid UTM (skala ~0.999945 terhadap jarak geodesik di Tumanggal; arah grid berbeda
~0.19 derajat dari azimut sejati karena konvergensi meridian).

```python
from geo.projection import default_projection
from geo.chunks import chunk_id, chunk_bounds

p = default_projection()                  # origin dari data/origin.json
x, z = p.to_local(lon, lat)               # titik tunggal
xs, zs = p.to_local_array(lons, lats)     # array numpy
lon, lat = p.to_lonlat(x, z)              # konversi balik (round-trip < 1 mm)
local_fc = p.geojson_to_local(fc)         # Feature/FeatureCollection/geometri apa pun -> [x, z]
ll_fc = p.geojson_to_lonlat(local_fc)     # kebalikannya

chunk_id(x, z)             # "{cx}_{cz}", chunk 256 m, floor division ("-1_-1" untuk x=z=-0.1)
chunk_bounds("0_0")        # (min_x, min_z, max_x, max_z) = (0, 0, 256, 256); batas atas eksklusif
```

Untuk shapely/raster tersedia `transformer_to_utm()` / `transformer_to_wgs()` (UTM absolut) dan
`LocalProjection.origin_utm` untuk menggeser. Elevasi (nilai ke-3 posisi GeoJSON) dipertahankan.
Titik kontrol di `tests/test_local_projection.py`: node OSM nyata (Overpass, 2026-11-21, ODbL)
dibandingkan dengan `pyproj.Geod` (jarak dan azimut geodesik, dikoreksi faktor skala dan konvergensi
meridian dari `Proj.get_factors`); selisih < 0,5 m.

## GAME-6: data OSM dan audit

```
uv run python scripts/fetch_osm.py                                   # Overpass -> data/raw/osm/osm_all_<tanggal>.json + .meta.json
uv run python scripts/fetch_osm.py --check                           # validasi raw + metadata terbaru (tanpa jaringan)
uv run --group buildings-ref python scripts/fetch_open_buildings.py  # pembanding footprint (opsional) -> data/raw/open_buildings/
uv run python scripts/audit_osm.py                                   # tulis docs/osm-audit.md (tanpa jaringan, deterministik)
```

- Raw OSM: semua `highway, waterway, natural, landuse, leisure, amenity, building, barrier, man_made, place, shop, tourism,
  historic, office` (node/way/relation) dalam bbox batas, `out geom` + node referensi way. Metadata (tanggal unduh, query,
  jumlah elemen, timestamp basis OSM, SHA-256) divalidasi terhadap `schemas/osm_raw_meta.schema.json`. Clip ke batas dilakukan saat audit.
- Pembanding footprint: Google Open Buildings v3 + Microsoft Global ML Building Footprints (gabungan VIDA, source.coop,
  `.../geoparquet/by_country/country_iso=IDN/IDN.parquet`, dibaca lewat HTTP range, tanpa login), **diunduh 2026-11-20**
  ke `data/raw/open_buildings/`. Lisensi: Google Open Buildings v3 CC BY 4.0 / ODbL, Microsoft ODbL. Dipakai untuk audit dan
  sebagai layer pelengkap game (keputusan pemilik produk, ADR-0003); jangan digabung diam-diam ke data OSM, catat sumbernya.
  Skema metadata: `schemas/open_buildings_meta.schema.json`. Grup dependensi opsional `buildings-ref` (duckdb>=2.0,<3).
  Teks atribusi pembanding untuk kredit: "Building footprints: Google Open Buildings v3 (CC BY 4.0) and Microsoft Global ML
  Building Footprints (ODbL), via VIDA Google-Microsoft Open Buildings."
- Metadata raw (OSM dan pembanding) divalidasi terhadap skema dan sha256 raw dicocokkan sebelum audit.
- Laporan: [`docs/osm-audit.md`](docs/osm-audit.md) (data diunduh 2026-11-20).
- Modul: `osm/{query,parse,meta,geom,stats,network,completeness,audit,report}.py`; test `tests/test_osm.py`.
- `osm/geom.chunk_id` memakai rumus chunk domain.md (floor(m/256)); selaraskan ke modul bersama di `geo/` bila sudah ada.

### Atribusi OSM (ODbL), wajib di kredit game dan rilis

> Map data (c) OpenStreetMap contributors, available under the Open Database License (https://www.openstreetmap.org/copyright).

Turunan database OSM (footprint, jaringan jalan hasil olahan) wajib diberi atribusi dan dibagikan serupa sesuai ODbL (NFR-06).
Unduhan GAME-6: Overpass API, 2026-11-20, basis OSM 2026-11-20T21:23:29Z.
