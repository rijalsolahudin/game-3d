# Product Roadmap

**Produk:** Open World Real Map — Desa Tumanggal
**Status:** Draft v2 · **Terakhir diperbarui:** 2026-11-20
**Dokumen terkait:** [product-requirements.md](product-requirements.md) · [technical-architecture.md](technical-architecture.md) · [../CLAUDE.md](../CLAUDE.md)

**Label tugas:** `[Client]` Unity · `[Server]` backend · `[Data]` pipeline peta · `[Art]` aset 3D · `[UI]` HUD/menu (UI Toolkit) · `[Web]` Next.js + Tailwind · `[Ops]` CI/infra · `[QA]` pengujian
**Referensi:** `PRD §x` = product-requirements.md, `ARC §x` = technical-architecture.md, `Dx` = keputusan produk PRD §2.

Setiap milestone selesai bila **semua checklist tercentang dan Definition of Done (DoD) terpenuhi**.

---

## FASE 0 — Persiapan

### 0.1 Keputusan & Repo
- [ ] Pemilik produk mengonfirmasi atau merevisi keputusan D1–D8 (PRD §2)
- [x] `[Ops]` Inisialisasi monorepo sesuai ARC §6, Git LFS (`.gitattributes`), `.gitignore` Unity + Node
- [x] `[Ops]` ADR-0001 "Pemilihan Tech Stack" di `docs/adr/`
- [x] `[Ops]` `docker-compose.yml` dengan `postgis/postgis` untuk pengembangan lokal

### 0.2 Survei & Data Mentah
- [x] `[Data]` Tentukan polygon batas Desa Tumanggal + buffer (D1) dan titik origin
- [ ] `[Data]` Ganti batas sementara (lingkaran 1,5 km) dengan batas administratif resmi desa + buffer 200 m
- [x] `[Data]` Unduh data OSM wilayah, audit kelengkapan jalan & footprint bangunan
- [ ] `[Data]` Unduh DEMNAS untuk area cakupan
- [x] `[Data]` Unduh DEM sementara Copernicus GLO-30 (30 m) untuk area cakupan, dipakai sampai DEMNAS tersedia
- [ ] `[Data]` Digitasi manual di OSM: gang, jalan setapak, sawah/kebun, dan irigasi, sesuai prioritas `pipeline/docs/osm-audit.md` (ADR-0003)
- [ ] `[Data]` Survei lapangan: foto referensi landmark Tier A, daftar bangunan Tier B di jalan utama
- [ ] `[Data]` Izin/sosialisasi ke pemerintah desa (PRD NFR-07)

**DoD:** keputusan D1–D8 tercatat, data mentah tersimpan di `pipeline/data/raw/`, daftar landmark Tier A final.

---

## FASE 1 — Foundation & Core (Vertical Slice)

### 1.1 Fondasi Client
- [x] `[Client]` Proyek Unity 6 LTS + URP, struktur `Assets/_Project/` dan `.asmdef` per modul (ARC §2.3)
- [ ] `[Client]` Upgrade editor ke Unity 6.7 LTS begitu rilis, sebelum Fase 1 selesai (ADR-0002)
- [x] `[Client]` Paket: Addressables, Input System, Cinemachine, Splines, UI Toolkit, Newtonsoft Json, Test Framework
- [x] `[Client]` Scene `Boot` → `Menu` → `World`, state machine game di `Game.Core`
- [x] `[Client]` Event bus + konfigurasi berbasis ScriptableObject (tanpa angka ajaib)
- [ ] `[Ops]` CI GameCI: test EditMode + build Windows otomatis per PR

### 1.2 Pipeline Peta → Unity
- [x] `[Data]` Skrip proyeksi OSM/DEM → UTM 49S → koordinat lokal (ARC §2.2)
- [ ] `[Data]` Generator heightmap per tile 256 m dari DEM (Copernicus sementara, lalu DEMNAS)
- [ ] `[Data]` Ekspor jalan sebagai spline (JSON) + footprint bangunan + metadata tier
- [ ] `[Client]` Importer Editor: membuat terrain tile, spline jalan, dan placeholder bangunan dari output pipeline
- [ ] `[Client]` Addressables group per chunk, world streamer 2 ring + ring LOD (ARC §2.2)
- [ ] `[Client]` Batas dunia (dinding tak terlihat + kabut) sesuai D1

### 1.3 Karakter Faceless
- [ ] `[Art]` Model karakter humanoid faceless (tanpa hidung/mulut/telinga/alis), rig Humanoid
- [ ] `[Art]` Shader/mesh mata `FacelessEyes`: iris, pupil, highlight (D4)
- [x] `[Client]` Controller third-person: jalan, lari, lompat, kamera Cinemachine
- [ ] `[Client]` Animator: idle, walk, run, jump, enter/exit vehicle
- [ ] `[Client]` Kedip acak + arah pandang (look-at) ke POI terdekat
- [ ] `[QA]` Test EditMode: aturan faceless (prefab karakter tidak memiliki slot fitur wajah lain)

### 1.4 Bangunan & Lingkungan
- [ ] `[Art]` 5 landmark Tier A pertama (dengan LOD0–2)
- [ ] `[Art]` Modular kit Tier B (dinding, atap genteng, jendela, teras)
- [ ] `[Client]` Generator procedural Tier C dari footprint (tinggi + atap sesuai tipe)
- [ ] `[Client]` Collider sederhana (box/convex) untuk semua bangunan
- [ ] `[Art]` Vegetasi: sawah, kelapa, bambu, semak (GPU instancing)
- [ ] `[Client]` Pencahayaan: matahari, skybox, fog, Adaptive Probe Volumes

### 1.5 Kendaraan
- [ ] `[Client]` `VehicleController` dasar: suspensi raycast, akselerasi, rem, kemudi (config ScriptableObject)
- [ ] `[Client]` `MotorcycleController`: lean visual, stabilisasi otomatis
- [ ] `[Client]` `CarController`
- [ ] `[Client]` Enter/exit kendaraan, kamera kendaraan, kendaraan tetap di tempat saat ditinggal
- [ ] `[Art]` Model motor bebek & mobil (LOD0–2)
- [ ] `[QA]` Playtest rasa berkendara (minimal 5 orang), catat tuning

### 1.6 Backend Dasar
- [x] `[Server]` Fastify + TS strict + Zod + Swagger + Pino, struktur `modules/` (ARC §6)
- [ ] `[Server]` Skema Drizzle + migrasi semua tabel ARC §5, seed dunia Tumanggal & `vehicle_models`
- [ ] `[Server]` Auth: register, login, refresh rotasi, logout (Argon2id, JWT)
- [ ] `[Server]` `GET /me`, `GET /me/save`, `GET /worlds/:slug`
- [x] `[Server]` Rate limit, CORS, helmet, format error standar
- [ ] `[QA]` Integration test Vitest + Testcontainers untuk auth & save
- [ ] `[Ops]` CI server: lint, typecheck, test

### 1.7 Integrasi Client ↔ Server
- [ ] `[Client]` `ApiClient` (timeout, retry eksponensial, refresh token otomatis)
- [ ] `[Client]` Penyimpanan refresh token aman (Windows Credential Manager / DPAPI)
- [ ] `[UI]` Layar login/registrasi (UI Toolkit)
- [ ] `[Client]` Save lokal + merge dengan cloud berdasarkan `revision`
- [ ] `[Client]` Starter motor diberikan sesuai D5

**DoD Fase 1:** pemain bisa login, spawn di Tumanggal, berjalan & naik motor di area ≥ 1 km² yang di-stream per chunk, 5 landmark Tier A terlihat, posisi tersimpan dan dipulihkan setelah restart, ≥ 60 FPS pada spesifikasi minimum.

---

## FASE 2 — Extended Features

### 2.1 Aktivitas Eksplorasi (D6)
- [ ] `[Server]` Seed `pois` & `collectibles` dari pipeline
- [ ] `[Server]` `POST /me/sync` idempoten: `checkpoint`, `discover`, `collect`, `photo` + validasi radius PostGIS
- [ ] `[Server]` Aturan unlock mobil (≥ 50% Tier A) di server
- [ ] `[Client]` Sistem penemuan lokasi (trigger radius) + notifikasi
- [ ] `[Client]` Interaksi landmark: panel info
- [ ] `[Client]` Koleksi item tersebar
- [ ] `[Client]` Foto mode (kamera bebas, sembunyikan HUD, simpan screenshot)
- [ ] `[Client]` Antrean sinkron offline + kirim ulang
- [ ] `[UI]` Panel progres eksplorasi (penemuan & koleksi)

### 2.2 Navigasi
- [ ] `[Client]` Render peta top-down per chunk (offline, dari data pipeline)
- [ ] `[UI]` Minimap HUD (posisi pemain, kendaraan, POI yang ditemukan)
- [ ] `[UI]` World map interaktif: zoom, pan, penanda
- [ ] `[Client]` Waypoint + penunjuk arah di HUD

### 2.3 Konten Lengkap MVP
- [ ] `[Art]` Seluruh landmark Tier A (±10–20)
- [ ] `[Art]` Seluruh bangunan Tier B di jalan utama
- [ ] `[Data]` Seluruh cakupan D1 ter-stream
- [ ] `[Client]` Pengaturan grafis (preset, resolusi, FOV) & remap kontrol (FR-12)

**DoD Fase 2:** seluruh area D1 dapat dijelajah, semua aktivitas D6 berjalan dan tersinkron, mobil terbuka sesuai aturan, world map & minimap berfungsi.

---

## FASE 3 — Polish & Rilis

### 3.1 Optimasi
- [ ] `[Client]` Audit budget performa ARC §7 (Profiler + Memory Profiler) di spesifikasi minimum
- [ ] `[Client]` LOD & occlusion culling, kompresi tekstur, atlas Tier C
- [ ] `[Client]` Hilangkan GC alloc di jalur update; tidak ada hitch > 100 ms saat streaming
- [ ] `[Ops]` Hosting Addressables di CDN + remote catalog

### 3.2 Ketahanan & Kualitas
- [ ] `[Client]` Fallback aset gagal dimuat (placeholder + retry), state error yang jelas
- [ ] `[Client]` Sentry Unity SDK (crash & exception)
- [ ] `[Server]` Sentry Node SDK, backup DB harian, health check
- [ ] `[QA]` Test end-to-end: login → spawn → motor → penemuan → unlock mobil → world map → keluar → lanjut
- [ ] `[QA]` Playtest warga lokal (metrik PRD §1.4)
- [ ] `[UI]` Polish HUD & menu, aksesibilitas (NFR-09), kredit + atribusi OSM (NFR-06)

### 3.3 Web Pendukung
- [ ] `[Web]` Next.js + Tailwind v4: landing page & halaman unduhan
- [ ] `[Web]` Panel admin: kelola deskripsi POI (auth admin terpisah)

### 3.4 Rilis
- [ ] `[Ops]` Build produksi Windows, signing, versioning SemVer
- [ ] `[Ops]` Deploy backend container + DB terkelola
- [ ] `[Ops]` Rilis playtest di itch.io, lalu halaman Steam

**DoD Fase 3:** metrik PRD §1.4 tercapai pada playtest, crash-free ≥ 99%, build rilis terdistribusi.

---

## Setelah MVP (Backlog)

- Perluasan wilayah ke desa tetangga di Kec. Pengadegan (+ floating origin).
- NPC faceless dengan rutinitas harian.
- Siklus siang–malam & cuaca (FR-13).
- Port Android.
- Multiplayer (memerlukan revisi arsitektur & aturan auth di `.claude/rules/server.md` terlebih dahulu).
