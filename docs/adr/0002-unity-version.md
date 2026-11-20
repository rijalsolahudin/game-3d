# ADR-0002: Versi Editor Unity Sementara (6.6 → 6.7 LTS)

- **Status:** Diterima
- **Tanggal:** 2026-11-20
- **Task:** GAME-10
- **Mengubah:** ADR-0001 (baris "Game client: Unity 6 LTS")

## Konteks

ADR-0001 menetapkan Unity 6 **LTS**. Saat proyek Unity dibuat (GAME-10), editor yang terpasang di mesin pengembang adalah **6000.6.10f1 (Unity 6.6)**. Ternyata 6.6 bukan rilis LTS. Unity Hub mencatatnya di stream *Supported*, bukan LTS (`isLTS: null`).

Per 2026-11-20:

- LTS yang berlaku adalah **Unity 6.3 LTS** (`6000.3.x`), didukung sekitar sampai akhir 2027.
- **Unity 6.7 LTS** diperkirakan rilis kuartal 4 2026, tetapi tanggalnya belum dipastikan Unity.
- 6.6 hanya menerima perbaikan sampai 6.7 rilis.

Proyek Unity masih kosong: hanya struktur folder, asmdef, aset URP bawaan, dan test sederhana.

## Keputusan

Pemilik produk memutuskan:

1. **Sementara** memakai Unity **6000.6.10f1**. Versi ini dikunci di `client/ProjectSettings/ProjectVersion.txt`.
2. **Upgrade ke Unity 6.7 LTS** begitu rilis. Upgrade dibuat sebagai task tersendiri di Ergonio.
3. Setelah upgrade, aturan "Unity 6 LTS" di `.claude/rules/tech-stack.md` berlaku penuh lagi tanpa pengecualian.

## Alternatif yang ditolak

- **Turun ke 6.3 LTS sekarang:** paling sesuai aturan, tetapi butuh unduhan editor baru (~6 GB) dan pembuatan ulang proyek, sementara beberapa bulan lagi tetap harus upgrade ke 6.7 LTS. Unity juga tidak mendukung downgrade proyek, jadi `ProjectSettings` dan `packages-lock.json` harus dihasilkan ulang.
- **Tetap di 6.6 seterusnya:** 6.6 berhenti didukung saat 6.7 rilis, dan tidak cocok untuk game yang akan dirawat bertahun-tahun.

## Konsekuensi

- Selama di 6.6, versi paket (URP 17.6.x, Input System 1.20.x, dll.) mengikuti 6.6.
- CI GameCI (GAME-14) memakai image editor `6000.6.10f1`, dan perlu diperbarui saat upgrade.
- Upgrade 6.6 → 6.7 diperkirakan murah selama proyek masih kecil. Makin lama ditunda, makin besar risikonya, jadi upgrade dikerjakan **sebelum Fase 1 selesai** bila 6.7 LTS sudah tersedia.
- Bila 6.7 LTS molor melewati Q1 2027, keputusan ini ditinjau ulang. Opsinya pindah ke 6.3 LTS.
