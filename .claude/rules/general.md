# Aturan Umum

## Keamanan
- Validasi SEMUA input eksternal: request API, file pipeline/peta, dan save lokal memakai skema eksplisit. Tolak data yang tidak sesuai skema.
- Tidak ada secret di repo. Pakai env var, `.env` di-gitignore, sediakan `.env.example`. Client game tidak boleh menyimpan secret apa pun, hanya URL API publik.
- Server tidak mempercayai client untuk data persisten: penemuan lokasi, koleksi, dan unlock kendaraan divalidasi atau dihitung di server.
- Teks dari server atau pemain yang ditampilkan di UI tidak boleh diinterpretasikan sebagai rich text/markup/HTML.

## Performa
- Budget acuan: `docs/technical-architecture.md` §7. Fitur baru tidak boleh melewatinya.
- Hindari kerja berulang yang mahal di jalur panas (per frame / per request); cache hasil yang bisa di-cache.

## Kerapian kode
- Satu file = satu tanggung jawab (satu class/sistem/modul).
- Semua konstanta tuning (kecepatan, radius, interval, batas) di config. Dilarang angka ajaib.
- Hapus kode mati, log debug, dan aset tak terpakai sebelum commit.

## Testing & verifikasi
- Setiap perubahan perilaku disertai test yang relevan (detail per area di `unity.md`, `server.md`, `pipeline.md`).
- Sebelum menyatakan tugas selesai, jalankan verifikasi area yang disentuh dan laporkan hasilnya apa adanya.

## Git & alur kerja
- Branch: `feat/…`, `fix/…`, `chore/…`, `docs/…` dengan nomor task, mis. `feat/GAME-12-vehicle-controller`. Commit: Conventional Commits.
- Satu PR = satu tujuan. Perubahan aturan atau arsitektur lewat PR `docs/…` terpisah, tidak diselipkan di PR fitur.
- Biner (model, tekstur, audio, raster peta) WAJIB lewat Git LFS.
- Kerjakan sesuai urutan `docs/roadmap.md` dan centang checklist di sana saat tugas selesai.
- Bila menemukan keputusan yang belum ada di dokumen, **tanyakan** atau catat sebagai usulan di PRD §2. Jangan mengarang aturan baru diam-diam.
