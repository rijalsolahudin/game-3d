# ADR-0003: Footprint Bangunan Pelengkap (Google/Microsoft) dan DuckDB di Pipeline

- **Status:** Diterima
- **Tanggal:** 2026-11-21
- **Task:** GAME-6 (audit), GAME-17 (ekspor)
- **Menambah:** ADR-0001 (stack pipeline peta)

## Konteks

Audit OSM (GAME-6, `pipeline/docs/osm-audit.md`) di dalam batas sementara menemukan:

- OSM baru memuat **594** footprint bangunan.
- Data pembanding Google Open Buildings v3 dan Microsoft Global ML Building Footprints memuat sekitar **2480** footprint di area yang sama. Jadi OSM baru mencakup sekitar **30%** (kisaran 21–36%).
- Gang, jalan setapak, landuse (sawah, kebun), irigasi, dan POI tidak ada sama sekali di OSM.

Target produk adalah dunia yang mirip aslinya. Dengan hanya 30% bangunan, sebagian besar desa akan tampak kosong.

Data Google dan Microsoft tersedia gabungan (dataset VIDA di source.coop) dalam format GeoParquet. File ini terlalu besar untuk diunduh utuh, sehingga perlu dibaca sebagian lewat HTTP range request. DuckDB (dengan ekstensi `spatial` dan `httpfs`) bisa melakukannya tanpa login dan tanpa server.

## Keputusan

Pemilik produk memutuskan pada 2026-11-21:

1. **Bangunan dilengkapi dari Google Open Buildings v3 dan Microsoft ML Building Footprints.** Footprint OSM tetap menjadi sumber utama. Footprint pelengkap hanya dipakai bila tidak tumpang tindih dengan OSM (dedup). Data pelengkap disimpan sebagai **layer terpisah** di pipeline dan **tidak diimpor ke OSM**. Setiap bangunan membawa atribut `source` (`osm` / `google` / `microsoft`). False positive dibersihkan dengan ambang confidence dan luas minimum yang diatur di config pipeline.
2. **Gang, jalan setapak, sawah, kebun, dan irigasi didigitasi manual di OSM** oleh tim, memakai editor iD/JOSM. Tracing hanya boleh di atas citra yang lisensinya mengizinkan tracing untuk OSM (layer yang disetujui di editor OSM). Pipeline kemudian mengambilnya lewat unduhan OSM biasa.
3. **DuckDB** ditambahkan ke pipeline, **hanya** sebagai dependensi grup opsional `buildings-ref` di `pipeline/pyproject.toml`, untuk membaca GeoParquet jarak jauh. DuckDB tidak dipakai di server maupun client, dan bukan pengganti PostgreSQL.

## Tambahan 2026-11-21: jalan penghubung otomatis

Digitasi manual di OSM ternyata terlalu sulit bagi tim saat ini. Contohnya, Jl. Pagersari Tumanggal di dunia nyata menyambung ke Jl. Raya Tumanggal, tetapi di OSM ruas itu terputus. Pemilik produk memutuskan:

1. Pipeline membuat **jalan penghubung otomatis** (`source: generated`):
   - Ujung jalan buntu yang dekat dengan jalan lain disambung lewat jalur paling landai di terrain.
   - Kelompok bangunan yang jauh dari jalan diberi gang ke jalan terdekat.
2. Jalan generated hanyalah perkiraan, bukan hasil tracing citra, sehingga tidak ada masalah lisensi citra. Jalan ini otomatis tidak dibuat lagi bila data OSM di lokasi itu sudah tersedia (digitasi GAME-54 tetap terbuka bila ada relawan).
3. Bangunan Google Open Buildings diatribusikan dengan opsi lisensi **ODbL**, sama dengan OSM dan Microsoft.

## Lisensi dan atribusi

- Google Open Buildings v3: CC BY 4.0 atau ODbL (dual license); proyek ini memakai opsi **ODbL**.
- Microsoft Global ML Building Footprints: ODbL.
- OSM: ODbL.

Game adalah *Produced Work* menurut ODbL, jadi cukup atribusi di kredit. Teks atribusi ketiganya wajib ada di kredit game (PRD NFR-06) dan di `pipeline/README.md`.

## Alternatif yang ditolak

- **OSM saja:** sekitar 70% bangunan hilang, sehingga tidak memenuhi target kemiripan.
- **Digitasi seluruh bangunan manual di OSM:** paling rapi, tetapi butuh puluhan jam kerja manusia untuk sekitar 1700 bangunan.
- **Mengunduh file GeoParquet utuh tanpa DuckDB:** ukurannya per negara mencapai gigabyte, dan tetap butuh pustaka pembaca Parquet. Menulis pembaca range request sendiri lebih rapuh.

## Konsekuensi

- GAME-17 mengekspor bangunan dari dua sumber dengan atribut `source`, dan skema JSON-nya mencatat field itu.
- Audit dan ekspor perlu dijalankan ulang setelah digitasi manual dan setelah batas resmi tersedia (GAME-53).
- DuckDB dikunci di `uv.lock`. Upgrade mayor DuckDB mengikuti aturan tech-stack (PR terpisah).
