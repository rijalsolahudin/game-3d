# ADR-0001: Pemilihan Tech Stack

- **Status:** Diterima
- **Tanggal:** 2026-11-20
- **Task:** GAME-3

## Konteks

Game ini adalah open world 3D berbasis peta nyata Desa Tumanggal. Pemain berjalan kaki dan berkendara motor atau mobil di dunia yang dimuat bertahap per chunk. Data dunia berasal dari sumber geospasial (OpenStreetMap dan DEMNAS), dan progres pemain disimpan di cloud. Rilis awal untuk PC Windows dengan spesifikasi kelas menengah (PRD §6).

Draft awal proyek punya dua arah yang saling bertentangan. PRD menyebut Unity, Node.js/Express, dan PostgreSQL, sedangkan aturan proyek lama melarang menetapkan stack dan mengarah ke modul JavaScript dengan HUD Tailwind. Keputusan ini menyatukan keduanya.

Kebutuhan yang menentukan pilihan:

1. Fisika kendaraan yang bisa disetel, termasuk motor roda dua.
2. Streaming dunia per chunk tanpa hitch.
3. Data spasial (batas wilayah, titik landmark, footprint bangunan) yang bisa di-query.
4. Satu bahasa untuk backend dan web agar tim kecil tidak terpecah.
5. Jalur ke platform lain (mobile/konsol) kelak.

## Keputusan

| Lapisan | Pilihan | Alasan |
|---|---|---|
| Game client | **Unity 6 LTS** (C#) + **URP** | Ekosistem open world matang, terrain dan fisika bawaan, Addressables untuk streaming, dan port ke mobile relatif mudah. URP cukup ringan untuk GPU kelas menengah. |
| UI dalam game | **UI Toolkit** | Native Unity dan punya data binding runtime. Tailwind tidak bisa dipakai di dalam Unity. |
| Kendaraan | Controller arkade kustom berbasis raycast | `WheelCollider` sulit disetel untuk motor; controller kustom memberi kontrol penuh atas rasa berkendara. |
| Backend | **Node.js LTS + TypeScript strict + Fastify 5 + Zod** | Fastify lebih cepat dari Express, dan validasi Zod sekaligus menjadi tipe TypeScript dan dokumentasi OpenAPI. |
| ORM | **Drizzle** | SQL-first dan mendukung tipe geometri PostGIS. |
| Database | **PostgreSQL 17 + PostGIS** | Data relasional sekaligus query spasial (`ST_DWithin`, `ST_Contains`) untuk validasi penemuan lokasi. |
| Web pendukung | **Next.js + Tailwind CSS v4** | Hanya untuk landing page dan panel admin di Fase 3. |
| Pipeline peta | **Python (uv) + GDAL + Blender** | Ekosistem geospasial paling lengkap; Blender (Blosm) untuk impor OSM. |
| Infra | Git LFS, GitHub Actions + GameCI, Docker, Sentry | Biner besar di LFS, CI Unity yang sudah teruji, dan lingkungan lokal yang identik. |

Rincian versi dan alasan per komponen ada di `docs/technical-architecture.md` §1.

## Alternatif yang ditolak

- **Three.js / React Three Fiber (web):** ringan didistribusikan, tetapi fisika kendaraan, streaming aset besar, dan performa dunia padat jauh lebih sulit dicapai di browser. Tooling editor untuk menata dunia juga minim.
- **Unreal Engine 5:** visual terbaik dan ada Cesium, tetapi berat untuk spesifikasi minimum PRD, kurva belajar C++/Blueprint lebih curam, dan ukuran build besar. Kemiripan semi-realistis yang kita butuhkan bisa dicapai di URP.
- **Godot 4:** ringan dan open source, tetapi ekosistem open world, streaming aset, dan CI-nya belum sematang Unity.
- **Express:** sudah ada di PRD awal, tetapi tanpa validasi skema bawaan dan lebih lambat dari Fastify.
- **Prisma:** DX bagus, tetapi tipe PostGIS tidak didukung secara native sehingga query spasial harus lewat raw SQL di banyak tempat.
- **Cesium for Unity / Google Photorealistic 3D Tiles:** cakupan dan kualitas di pedesaan Indonesia rendah, dan lisensinya membatasi. Pipeline OSM offline memberi kontrol lebih besar.

## Konsekuensi

- Tim perlu menguasai dua bahasa: C# untuk game dan TypeScript untuk backend/web.
- Unity Editor wajib untuk pengembangan client; CI butuh lisensi Unity (GameCI).
- Semua HUD dibangun dengan UI Toolkit, bukan teknologi web. Tailwind hanya ada di `web/`.
- Controller kendaraan harus dibangun dan disetel sendiri; risiko ini dimitigasi dengan playtest berkala (GAME-38).
- Perubahan stack berikutnya wajib lewat ADR baru dan pembaruan `.claude/rules/tech-stack.md`.
