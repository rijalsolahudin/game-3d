# Audit Data OSM - Desa Tumanggal (GAME-6)

Dihasilkan otomatis oleh `scripts/audit_osm.py` dari raw `data/raw/osm/osm_all_2026-11-20.json`; jangan edit manual.

| Item | Nilai |
|---|---|
| Tanggal unduh | 2026-11-20T21:24:45Z |
| Timestamp basis OSM (Overpass) | 2026-11-20T21:23:29Z |
| Sumber | OpenStreetMap via Overpass API (https://overpass-api.de/api/interpreter) |
| Elemen mentah | 5920 (node 5097, way 823, relation 0) |
| Batas audit | SEMENTARA (circle_around_osm_village_node, radius 1500 m), luas 7.0679 km2 |
| bbox query (S,W,N,E) | [-7.3622776, 109.4729093, -7.3351496, 109.5000818] |
| Lisensi | ODbL 1.0, (c) OpenStreetMap contributors |
| SHA-256 raw (terverifikasi) | `5abdf8a3deedd552...` |

Statistik jalan dihitung setelah clip ke batas; bangunan dihitung bila titik wakilnya di dalam batas.
Semua angka di UTM 49S (EPSG:32749) lewat `geo/projection.py`; koordinat lokal (x timur, z utara, meter) relatif
origin usulan `data/origin.json`; chunk 256 m berID `"{x}_{z}"`.

## 1. Ringkasan

- Bangunan OSM: **594** footprint, total 87957 m2 (median 110 m2); 99.8% bertipe `building=yes`.
- Jalan: **14.9 km** pada 33 way (tipe: residential, tertiary, secondary, unclassified; bernama 1 way; atribut surface 0, width 0).
- **Perkiraan bangunan yang sudah punya footprint di OSM: sekitar 30% (kisaran 28% sampai 36% menurut ambang confidence)**, dibandingkan Google Open Buildings v3 + Microsoft ML (2480 footprint, confidence >= 0.7). Artinya kira-kira 70% bangunan belum ada di OSM.
- 35% bangunan OSM berjarak > 60 m dari jalan OSM mana pun (210 bangunan).
- Tata guna lahan dan POI di OSM: landuse 0, natural 0, waterway 1, leisure 0, amenity 0, place 1.
- Kesimpulan: cakupan bangunan di bawah 80%; OSM saja **belum cukup** untuk peta yang mirip aslinya. Perlu pelengkapan sebelum masuk pipeline (bagian 7).

## 2. Statistik per kategori

| Kategori | Jumlah elemen (beririsan batas) | Rincian nilai tag |
|---|---|---|
| building | 597 | house: 1, yes: 596 |
| highway | 33 | residential: 29, secondary: 1, tertiary: 2, unclassified: 1 |
| place | 1 | village: 1 |
| waterway | 1 | river: 1 |

Kategori yang diekspor tetapi kosong dalam batas: natural, landuse, leisure, amenity, barrier, man_made, shop, tourism, historic, office.

### Panjang jalan per tipe (di dalam batas)

| highway | Way | Panjang (km) |
|---|---|---|
| residential | 29 | 8.226 |
| tertiary | 2 | 3.541 |
| secondary | 1 | 2.331 |
| unclassified | 1 | 0.768 |
| **total** | 33 | **14.866** |

Waterway: river 1.235 km.

### Bangunan

- Jumlah 594, luas footprint total 87957 m2 (8.80 ha), median 110 m2.
- Tipe `building=`: house 1, yes 593.
- Bertag `name`: 0; bertag `addr:*`: 0 (NFR-07: nama/alamat tidak dicantumkan di laporan; bangunan pribadi berlabel generik).
- Bertag `building:levels`: 0; `roof:shape`: 0.
- Footprint < 8 m2 (janggal): 2 (way/1000872258, way/1000872285).

### Sebaran bangunan OSM per chunk 256 m

Tabel lengkap gabungan dengan pembanding ada di bagian 3. Ringkas: 57 chunk berisi bangunan OSM; terpadat: `-2_3` (49), `0_-4` (41), `2_-4` (38), `3_-5` (33), `3_-4` (30).

## 3. Perkiraan kelengkapan footprint bangunan

**Metode.** Tidak ada survei lapangan, sehingga dipakai proxy otomatis: footprint OSM dibandingkan dengan
footprint hasil deteksi citra satelit (Google Open Buildings v3 + Microsoft Global ML Building Footprints, gabungan VIDA di
source.coop; diunduh 2026-11-20, 4000 footprint di bbox sebelum filter). Pada audit ini pembanding hanya
dibandingkan dan tidak digabung ke data OSM. Lisensi: Google Open Buildings v3: CC BY 4.0 / ODbL; Microsoft Global ML Building Footprints: ODbL. Google v3 dipakai pada confidence >= 0.7
(rekomendasi Google; Microsoft tidak punya skor). Dua footprint dianggap bangunan yang sama bila irisan >= 30% dari
luas yang terkecil. Baris pembanding divalidasi satu per satu: 0 dari 4000 baris ditolak karena tidak valid.

| Metrik | Nilai |
|---|---|
| Footprint OSM (dalam batas) | 594 |
| Footprint pembanding (dalam batas, filter confidence) | 2480 (microsoft 49, google 2431) |
| Pembanding yang tertutup footprint OSM | 735 |
| **Cakupan OSM terhadap pembanding (jumlah)** | **29.6%** |
| Cakupan berdasar luas | 35.1% (221939 m2 pembanding, 143978 m2 belum ada di OSM) |
| Footprint OSM yang terkonfirmasi pembanding | 509 (85.7% dari footprint OSM) |
| Footprint OSM tanpa pasangan pembanding | 85 |
| Estimasi alternatif total bangunan (Lincoln-Petersen) | 2894 (OSM = 21%) |

Estimasi alternatif Lincoln-Petersen (n_osm x n_ref / cocok) mengasumsikan dua sumber saling bebas; asumsi itu
cenderung optimistis karena bangunan yang sulit dideteksi citra juga cenderung belum dipetakan di OSM. Ia dicantumkan
sebagai pembanding, bukan batas bawah.

Sensitivitas terhadap ambang confidence Google:


| Ambang confidence | Footprint pembanding | Cakupan OSM (%) | Estimasi alternatif (LP) |
|---|---|---|---|
| 0.65 | 2897 | 28.3 | 3278 |
| 0.7 | 2480 | 29.6 | 2894 |
| 0.75 | 1949 | 31.3 | 2427 |
| 0.8 | 1264 | 35.5 | 1925 |
| 0.9 | 92 | 31.5 | 1822 |

**Cara membaca dan batasan.** Cakupan jumlah tidak sama dengan cakupan sebenarnya: (a) pembanding punya
false positive (atap seng, gudang, kandang, bayangan) dan memecah satu bangunan menjadi beberapa footprint, yang menaikkan
penyebut; (b) pencocokan memakai irisan terhadap luas yang terkecil, sehingga satu bangunan OSM bisa menutup beberapa
footprint pembanding yang terpecah dan menaikkan hitungan "tertutup" (jumlah tertutup bisa melebihi jumlah footprint OSM);
(c) bangunan kecil/tertutup pohon luput dari pembanding. Cakupan menurut ambang confidence berkisar 28% sampai 36%,
artinya sekitar 64% sampai 72% bangunan belum ada di OSM. Angka pasti baru bisa didapat dari
survei/pencocokan manual pada sampel chunk.


### Per chunk 256 m (OSM vs pembanding)

Chunk bertanda `!` = cakupan < 30% dengan >= 20 footprint pembanding (prioritas pelengkapan). Kolom "Tertutup OSM" menghitung footprint pembanding (lihat catatan (b)).

| Chunk | OSM | Pembanding | Tertutup OSM | Cakupan % | Prioritas |
|---|---|---|---|---|---|
| `-6_0` | 0 | 25 | 0 | 0.0 | ! |
| `-6_1` | 7 | 10 | 6 | 60.0 |  |
| `-6_2` | 4 | 4 | 2 | 50.0 |  |
| `-5_-4` | 9 | 58 | 13 | 22.4 | ! |
| `-5_-3` | 7 | 31 | 12 | 38.7 |  |
| `-5_-2` | 0 | 6 | 0 | 0.0 |  |
| `-5_0` | 0 | 2 | 0 | 0.0 |  |
| `-5_2` | 1 | 5 | 0 | 0.0 |  |
| `-5_3` | 0 | 1 | 0 | 0.0 |  |
| `-4_-5` | 0 | 3 | 0 | 0.0 |  |
| `-4_-4` | 9 | 152 | 27 | 17.8 | ! |
| `-4_-3` | 12 | 92 | 20 | 21.7 | ! |
| `-4_0` | 2 | 1 | 1 | 100.0 |  |
| `-4_2` | 16 | 13 | 11 | 84.6 |  |
| `-4_3` | 7 | 6 | 5 | 83.3 |  |
| `-4_4` | 0 | 1 | 0 | 0.0 |  |
| `-3_-6` | 0 | 27 | 0 | 0.0 | ! |
| `-3_-5` | 0 | 8 | 0 | 0.0 |  |
| `-3_-4` | 1 | 182 | 1 | 0.5 | ! |
| `-3_-3` | 6 | 52 | 7 | 13.5 | ! |
| `-3_-2` | 1 | 8 | 1 | 12.5 |  |
| `-3_-1` | 1 | 2 | 1 | 50.0 |  |
| `-3_0` | 4 | 5 | 5 | 100.0 |  |
| `-3_2` | 11 | 12 | 7 | 58.3 |  |
| `-3_3` | 13 | 16 | 12 | 75.0 |  |
| `-2_-6` | 0 | 28 | 0 | 0.0 | ! |
| `-2_-5` | 0 | 45 | 0 | 0.0 | ! |
| `-2_-4` | 2 | 92 | 2 | 2.2 | ! |
| `-2_-3` | 24 | 126 | 35 | 27.8 | ! |
| `-2_-2` | 2 | 15 | 1 | 6.7 |  |
| `-2_1` | 0 | 2 | 0 | 0.0 |  |
| `-2_2` | 8 | 20 | 7 | 35.0 |  |
| `-2_3` | 49 | 55 | 37 | 67.3 |  |
| `-1_-5` | 0 | 6 | 0 | 0.0 |  |
| `-1_-4` | 23 | 74 | 44 | 59.5 |  |
| `-1_-3` | 17 | 34 | 23 | 67.6 |  |
| `-1_-1` | 6 | 14 | 7 | 50.0 |  |
| `-1_0` | 9 | 25 | 16 | 64.0 |  |
| `-1_1` | 2 | 2 | 2 | 100.0 |  |
| `-1_2` | 12 | 56 | 13 | 23.2 | ! |
| `-1_3` | 0 | 26 | 0 | 0.0 | ! |
| `-1_4` | 0 | 1 | 0 | 0.0 |  |
| `-1_5` | 13 | 18 | 11 | 61.1 |  |
| `0_-6` | 0 | 12 | 0 | 0.0 |  |
| `0_-5` | 0 | 11 | 0 | 0.0 |  |
| `0_-4` | 41 | 92 | 60 | 65.2 |  |
| `0_-3` | 19 | 32 | 26 | 81.2 |  |
| `0_-2` | 2 | 2 | 2 | 100.0 |  |
| `0_-1` | 1 | 1 | 1 | 100.0 |  |
| `0_0` | 1 | 5 | 1 | 20.0 |  |
| `0_1` | 2 | 16 | 1 | 6.2 |  |
| `0_2` | 0 | 30 | 0 | 0.0 | ! |
| `0_3` | 10 | 42 | 8 | 19.0 | ! |
| `0_4` | 1 | 16 | 0 | 0.0 |  |
| `0_5` | 0 | 1 | 0 | 0.0 |  |
| `1_-6` | 0 | 22 | 0 | 0.0 | ! |
| `1_-5` | 0 | 11 | 0 | 0.0 |  |
| `1_-4` | 28 | 82 | 31 | 37.8 |  |
| `1_-3` | 3 | 7 | 4 | 57.1 |  |
| `1_1` | 0 | 9 | 0 | 0.0 |  |
| `1_2` | 6 | 14 | 8 | 57.1 |  |
| `1_3` | 15 | 45 | 19 | 42.2 |  |
| `1_4` | 0 | 1 | 0 | 0.0 |  |
| `1_5` | 1 | 0 | 0 | - |  |
| `2_-5` | 5 | 20 | 4 | 20.0 | ! |
| `2_-4` | 38 | 93 | 49 | 52.7 |  |
| `2_-3` | 10 | 20 | 16 | 80.0 |  |
| `2_-1` | 0 | 6 | 0 | 0.0 |  |
| `2_2` | 10 | 26 | 18 | 69.2 |  |
| `2_3` | 3 | 2 | 2 | 100.0 |  |
| `2_4` | 1 | 1 | 1 | 100.0 |  |
| `3_-5` | 33 | 106 | 31 | 29.2 | ! |
| `3_-4` | 30 | 109 | 38 | 34.9 |  |
| `3_-3` | 12 | 59 | 33 | 55.9 |  |
| `3_-2` | 0 | 1 | 0 | 0.0 |  |
| `3_-1` | 0 | 1 | 0 | 0.0 |  |
| `3_0` | 8 | 26 | 11 | 42.3 |  |
| `3_1` | 1 | 4 | 3 | 75.0 |  |
| `3_4` | 0 | 1 | 0 | 0.0 |  |
| `4_-4` | 19 | 89 | 25 | 28.1 | ! |
| `4_-3` | 0 | 47 | 0 | 0.0 | ! |
| `4_-2` | 0 | 13 | 0 | 0.0 |  |
| `4_-1` | 3 | 6 | 4 | 66.7 |  |
| `4_0` | 5 | 5 | 2 | 40.0 |  |
| `4_1` | 8 | 19 | 8 | 42.1 |  |
| `4_2` | 0 | 1 | 0 | 0.0 |  |
| `5_-3` | 0 | 2 | 0 | 0.0 |  |
| `5_-2` | 0 | 11 | 0 | 0.0 |  |

## 4. Jalan dan gang: hilang atau janggal

- Way jalan: 33; komponen terhubung: **2** (25 way / 8.909 km, 8 way / 5.958 km; panjang di dalam batas).
  - Komponen terpisah (way/697721232; 8 way, tipe residential 6, tertiary 2) berjarak 567.9 m dari jaringan utama tanpa simpul bersama: ruas penghubung kemungkinan belum dipetakan, atau terhubung lewat bagian di luar batas buatan.
- Nama: 1 dari 33 way bernama; tanpa nama: residential 29, unclassified 1, tertiary 2.
- Atribut (jumlah way yang punya): `surface` 0, `width` 0, `lanes` 0, `oneway` 0, `maxspeed` 0.
- Tipe `highway` yang tidak ada di OSM dalam batas: `path`, `track`, `footway`, `service`, `steps`, `cycleway` (gang kecil/jalan setapak/akses kebun berkurang pemetaannya).
- **210 bangunan OSM (35.4%) > 60 m dari jalan OSM terdekat**: akses ke rumah-rumah ini tidak terpetakan.
- Persilangan jalan tanpa simpul (bukan jembatan/terowongan): 0.

### Dead-end (18) dan kandidat celah (2)

Dead-end = ujung way yang tidak dipakai way lain, di dalam batas (di luar 40 m dari tepi), tanpa jalan lain dalam 30 m. Kandidat celah = ujung yang berada <= 30 m dari jalan lain tetapi tidak berbagi simpul (seharusnya tersambung). Koordinat lokal (x timur, z utara) relatif origin.

| Way | highway | Panjang way (m) | Ujung (x, z) m | Catatan |
|---|---|---|---|---|
| way/628209989 | residential | 34.9 | (-501, -989) | - |
| way/697702321 | residential | 211.5 | (-346, -597) | - |
| way/697702321 | residential | 211.5 | (-547, -628) | - |
| way/697702322 | residential | 757.5 | (-500, -521) | - |
| way/697702323 | residential | 590.4 | (-1039, -624) | - |
| way/697702357 | residential | 48.9 | (-847, -989) | - |
| way/697721232 | residential | 291.0 | (1071, 383) | - |
| way/697721233 | residential | 507.1 | (560, 743) | - |
| way/697721234 | residential | 373.3 | (151, 1089) | - |
| way/697721256 | residential | 102.2 | (1000, -797) | - |
| way/697721257 | residential | 399.6 | (918, -608) | - |
| way/697906351 | residential | 750.3 | (-23, -130) | - |
| way/962514379 | residential | 181.0 | (-781, -764) | - |
| way/962519704 | residential | 279.4 | (670, 594) | - |
| way/962520913 | residential | 81.4 | (380, -859) | - |
| way/1377775603 | residential | 157.7 | (2, -997) | - |
| way/1377775604 | residential | 114.3 | (-137, -1019) | - |
| way/1377780521 | residential | 472.3 | (-337, -1371) | - |
| way/628209991 | residential | 17.8 | (-477, -1258) | celah 17.2 m ke way/628209993 |
| way/697702324 | residential | 47.2 | (-639, -803) | celah 25.1 m ke way/697702325 |

Dead-end pada jalan permukiman pedesaan sebagian wajar (gang buntu). Yang mencurigakan adalah way lebih panjang dari 200 m yang berhenti di tengah area: 11 dead-end, way/1377780521, way/697702321, way/697702322, way/697702323, way/697721232, way/697721233, way/697721234, way/697721257, way/697906351, way/962519704, serta kandidat celah di atas.

## 5. Area mencurigakan (tanpa bangunan OSM padahal ada bangunan)

Sel 64 m x 64 m di dalam batas: total 1723; berisi bangunan OSM 215; berisi bangunan pembanding 475; **hanya pembanding (OSM kosong) 267**; kosong di keduanya 1241 (kemungkinan sawah/kebun/hutan/sungai, wajar tanpa bangunan).

Klaster sel dengan bangunan pembanding tidak tercakup OSM terbanyak (sepuluh teratas dari 420 sel):

| Pusat sel (x, z) m dari origin | Footprint pembanding belum di OSM |
|---|---|
| (-800, -800) | 30 |
| (-736, -800) | 29 |
| (-672, -800) | 23 |
| (-544, -800) | 19 |
| (-928, -800) | 17 |
| (-480, -736) | 17 |
| (-672, -864) | 16 |
| (864, -1120) | 16 |
| (-864, -672) | 15 |
| (-608, -864) | 15 |

Chunk dengan cakupan < 30% dan >= 20 footprint pembanding: 20 chunk (`-6_0`, `-5_-4`, `-4_-4`, `-4_-3`, `-3_-6`, `-3_-4`, `-3_-3`, `-2_-6`, `-2_-5`, `-2_-4`, `-2_-3`, `-1_2`, `-1_3`, `0_2`, `0_3`, `1_-6`, `2_-5`, `3_-5`, `4_-4`, `4_-3`). Footprint pembanding yang belum tertutup OSM: 1745.

## 6. Yang hilang untuk kemiripan visual

Per kategori, nilai tag lazim di desa Jawa yang tidak ada satu pun di OSM (dalam batas):

| Kategori | Jumlah elemen | Nilai tag yang tidak ada |
|---|---|---|
| landuse | 0 | farmland, orchard, meadow, forest, residential, grass |
| natural | 0 | water, wood, tree_row, tree, scrub, wetland |
| waterway | 1 | stream, canal, ditch, drain |
| leisure | 0 | pitch, park, garden |
| amenity | 0 | place_of_worship, school, townhall, marketplace, grave_yard |
| place | 1 | hamlet, isolated_dwelling, locality |

Dampak (hanya kategori yang kosong atau kurang):

- **Tata guna lahan (`landuse`: sawah, kebun, hutan, pekarangan)**: nol di OSM; tidak ada tekstur/zonasi lahan; luasan harus diturunkan dari citra referensi atau digitasi.
- **Alam (`natural`: air, hutan/bambu, semak, pohon)**: nol di OSM; tidak ada vegetasi/badan air terpetakan; pohon perlu penebaran procedural.
- **Rekreasi (`leisure`: lapangan, taman)**: nol di OSM; lapangan/taman harus dicari lewat survei.
- **Fasilitas (`amenity`: masjid, sekolah, balai desa, pasar, makam)**: nol di OSM; landmark dan POI Tier A harus dikumpulkan lewat survei lapangan.
- **Waterway**: 1 elemen (river 1); tidak ada: stream, canal, ditch, drain; saluran kecil/irigasi perlu dilengkapi.
- **Nama tempat**: `place` hanya village 1; tidak ada: hamlet, isolated_dwelling, locality.
- **Atribut bangunan**: tidak ada `building:levels` maupun `roof:shape`; tinggi dan atap harus ditebak.

## 7. Rekomendasi

**Perlu pelengkapan/digitasi sebelum data masuk pipeline? YA.**

Prioritas (tinggi ke rendah):

1. **Bangunan (P0).** Cakupan ~30%: lengkapi footprint untuk tier C (procedural dari footprint). 1745 footprint pembanding belum ada di OSM. Keputusan pemilik produk: footprint Google/Microsoft dipakai sebagai layer pelengkap di game (ADR-0003, PR docs #14); simpan sebagai layer sumber terpisah dengan jejak sumber dan lisensi, dedup terhadap OSM, dan bersihkan false positive (atap/gudang), footprint terpecah, dan bentuk tidak kotak. Impor ke OSM (RapiD/MapWithAI) bersifat opsional dan harus mengikuti panduan impor OSM.
2. **Jalan dan gang (P0).** Fokus: akses ke 210 bangunan yang jauh dari jalan, 1 komponen jaringan terpisah, 2 kandidat celah, dan dead-end panjang (bagian 4). Digitasi dari survei, Mapillary (CC BY-SA, perlu atribusi dan berbagi-serupa), dan tracing **hanya dari layer imagery yang disetujui editor OSM** (lisensinya mengizinkan tracing untuk OSM); citra lain dilarang untuk tracing dan, sesuai NFR-06, citra berlisensi terbatas hanya referensi modeling, bukan tekstur. Beri `name` bila diketahui dari pemerintah desa (nama jalan umum, bukan nama pribadi), serta `surface` dan `width`.
3. **Landuse dan alam (P1).** Digitasi poligon sawah, kebun, hutan/bambu, dan pekarangan (`landuse=farmland/orchard/forest/residential`, `natural=wood/scrub`) dengan aturan citra yang sama seperti jalan; tanpa ini lahan tidak punya zonasi.
4. **Sungai kecil dan irigasi (P1).** Tambah `waterway=stream/ditch/canal`; lebar kira-kira dari DEM dan survei.
5. **Landmark dan POI Tier A (P1).** Survei lapangan (masjid, balai desa, sekolah, makam, lapangan, warung): titik GPS dan foto di `pipeline/data/reference/<slug>/` tanpa data pribadi (NFR-07). Balai desa juga menentukan origin final.
6. **Atribut bangunan (P2).** `building:levels`, tipe atap, material hanya untuk Tier A/B; Tier C cukup default per kluster.
7. **Batas resmi (P0, di luar task ini).** Audit memakai batas sementara; ulangi `fetch_osm.py` dan `audit_osm.py` setelah batas resmi tersedia.

Semua citra satelit/foto hanya referensi modeling (NFR-06); survei lapangan adalah sumber utama landmark dan POI.

## 8. Atribusi, lisensi, privasi

- Data OSM (c) OpenStreetMap contributors, lisensi ODbL 1.0. Teks kredit untuk game dan rilis:
  **"Map data (c) OpenStreetMap contributors, available under the Open Database License (https://www.openstreetmap.org/copyright)."**
  Turunan database OSM (footprint, jalan hasil olahan) harus tetap diberi atribusi dan berbagi-serupa sesuai ODbL
  (NFR-06). Dicatat juga di `pipeline/README.md`.
- Pembanding (VIDA gabungan): Google Open Buildings v3 (CC BY 4.0 / ODbL) dan Microsoft Global ML Building Footprints (ODbL).
  Dipakai di audit ini; pemakaian sebagai layer pelengkap game mengikuti ADR-0003 dan wajib diberi atribusi sesuai lisensi masing-masing.
- Privasi (NFR-07): laporan tidak memuat nama pemilik atau alamat; tag `name`/`addr:*` pada bangunan diabaikan
  (0 bernama, 0 beralamat pada data saat ini).

## 9. Reproduksi

```
uv run python scripts/fetch_osm.py                                   # raw OSM + metadata (jaringan)
uv run --group buildings-ref python scripts/fetch_open_buildings.py  # pembanding (opsional, jaringan)
uv run python scripts/audit_osm.py                                   # tulis laporan ini (tanpa jaringan)
```
