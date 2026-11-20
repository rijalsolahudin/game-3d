---
name: ergonio-workflow
description: Wajib dipakai setiap kali mengerjakan, merencanakan, atau melaporkan pekerjaan di repo game-3d — mengambil task dari Ergonio (project stackinnov/game-3d), memindah status, mencatat progres lewat komentar, membuat task baru sesuai format, dan menutup task setelah DoD terpenuhi. Trigger: "kerjakan", "lanjut", "task berikutnya", "GAME-<n>", "update progress", "sprint", "apa yang harus dikerjakan", atau mulai mengubah kode/aset/dokumen proyek.
---

# Ergonio Workflow — game-3d

Project Ergonio: slug `game-3d`, key `GAME`. Semua pekerjaan di repo ini WAJIB tercatat di sana. Pemetaan field ada di `.claude/rules/ergonio.md`.

## Aturan inti

1. **Tidak ada pekerjaan tanpa task.** Sebelum mengubah kode, aset, atau dokumen, pastikan ada task Ergonio-nya. Bila belum ada → tambahkan ke `docs/roadmap.md` lalu buat task (lihat "Membuat task").
2. **Status selalu mencerminkan kenyataan.** Pindahkan status saat itu juga, bukan di akhir sesi.
3. **Progres dicatat sebagai komentar**, bukan dengan menimpa deskripsi. Progres % mengikuti status otomatis — jangan mencoba mengaturnya.
4. **Selalu pakai UUID task** (dari `queryTasks`/`getTask`) untuk `updateTask`/`createComment`. Nomor task bisa bentrok antar project; bila hanya tahu nomor, `getTask` dulu dan pastikan `projectId` = game-3d.
5. Semua aksi tulis Ergonio butuh persetujuan user — kelompokkan perubahan agar tidak membanjiri approval.

## Alur per sesi

### 1. Mulai sesi — cek task
- `queryTasks(projectId:"game-3d", status:["prog","review"])` → lanjutkan yang sudah berjalan lebih dulu.
- Bila kosong atau user minta task baru: `queryTasks(projectId:"game-3d", status:"todo")`, lalu `status:"backlog"`. Pilih berdasarkan urutan Epic (`0.1` → `3.4`), prioritas (`crit` > `high` > …), dan pastikan tidak ada link `blocked_by` yang belum Done (`getTask`).
- Bila user menyebut `GAME-<n>`, `getTask` task itu.
- Sampaikan ke user task yang akan dikerjakan (nomor + judul) sebelum mulai.

### 2. Mulai kerja
- `getTask` → baca latar belakang, acceptance criteria, DoD, dan referensi dokumen. Bila deskripsi belum sesuai template, perbaiki dulu sebelum mulai. Baca bagian dokumen yang dirujuk (`PRD`, `ARC`, `.claude/rules/`).
- `updateTask(status:"prog")` dan isi Sprint aktif bila kosong.
- Branch: `feat|fix|chore|docs/GAME-<n>-<slug-pendek>`.
- Task > 13 story points atau terlalu luas → `createSubtasks` dulu (maks 10 judul).

### 3. Selama kerja — update progres
Tulis komentar (`createComment`) pada momen ini:
- Setelah menyelesaikan bagian berarti (mis. satu modul, satu subtask).
- Saat menemukan keputusan yang belum ada di dokumen, atau perubahan scope.
- Saat terblokir → komentar penyebabnya, `linkTasks(type:"blocked_by")` ke task penghalang bila ada, dan beri tahu user.
- Di akhir sesi bila task belum selesai.

Format komentar:
```
**Progres:** <apa yang sudah selesai>
**Berikutnya:** <langkah selanjutnya>
**Catatan/Blocker:** <opsional>
**Bukti:** <file/commit/hasil test>
```

### 4. Review
- Setelah PR dibuka / pekerjaan siap ditinjau → `updateTask(status:"review")` + komentar berisi link PR, ringkasan perubahan, dan hasil verifikasi (bagian Testing di rule area terkait).

### 5. Selesai
Pindah ke `done` HANYA bila:
- Semua **Acceptance criteria** dan **Definition of Done** di deskripsi tercentang dan terverifikasi (test lulus, build jalan, dsb.). Centang butirnya lewat `updateTask(description)`.
- Checklist terkait di `docs/roadmap.md` sudah dicentang `[x]`.
- Komentar penutup berisi bukti.
Bila ada sisa pekerjaan → buat task lanjutan, jangan menutup task setengah jadi.

### 6. Akhir sesi
Laporkan ke user: task yang disentuh, status terbaru, dan apa yang tersisa.

## Kerja paralel (subagent)

Aturan lengkap: `.claude/rules/parallel-agents.md`. Pakai saat user minta beberapa task dikerjakan sekaligus, atau ada beberapa task siap di Area berbeda.

1. **Pilih task siap:** `queryTasks(projectId:"game-3d", status:["todo","backlog"])`, lalu `getTask` tiap kandidat untuk memastikan semua `blocked_by` sudah Done. Pilih paling banyak satu task Client/UI, ditambah task Server dan Data yang tidak saling bergantung.
2. **Konfirmasi ke user:** sebutkan task mana ke agent mana sebelum mulai.
3. **Tandai mulai:** `updateTask(status:"prog")` untuk semua task terpilih dalam satu batch.
4. **Kirim ke subagent:** satu `Agent` call per task, dijalankan dalam satu pesan agar paralel, dengan `subagent_type` sesuai Area (`unity-dev` / `server-dev` / `pipeline-dev`) dan `isolation: "worktree"`. Prompt berisi nomor task, judul, dan deskripsi lengkap dari `getTask`.
5. **Catat progres:** saat laporan subagent masuk, tulis komentar progres dari laporannya (format Progres/Berikutnya/Catatan/Bukti).
6. **Review:** jalankan `reviewer` dengan nomor task, deskripsi, dan daftar perubahan. Bila `changes-requested`, kirim temuan kembali ke subagent yang sama (`SendMessage`), lalu review ulang.
7. **Integrasi:** gabungkan hasil worktree, jalankan verifikasi akhir, buka PR, lalu `updateTask(status:"review")` + komentar link PR.
8. **Blocked/partial:** bila subagent melapor `blocked` atau `partial`, komentari penyebabnya, tambahkan link `blocked_by` bila ada task penghalang, dan kembalikan status ke `todo`.

## Membuat task

Setiap task WAJIB lengkap:

| Field | Aturan |
|---|---|
| `title` | Teks checklist roadmap tanpa prefix `[Area]`, kalimat perintah. |
| `milestone` | `Fase 0 — Persiapan` / `Fase 1 — Foundation & Vertical Slice` / `Fase 2 — Extended Features` / `Fase 3 — Polish & Rilis` |
| `Epic` | Sub-bagian roadmap, mis. `1.5 Kendaraan` (cek opsi dengan `listFields`). |
| `Area` | `Produk, Client, Server, Data, Art, UI, Web, Ops, QA` |
| `Story Points` | Fibonacci 1–13. |
| `priority` | `crit` blocker rilis/keputusan · `high` jalur kritis · `medium` normal · `low` nice-to-have |
| `status` | `null` (→ Backlog) kecuali diminta lain. |

### Deskripsi task (WAJIB)

Deskripsi ditulis untuk manusia: bahasa Indonesia yang mengalir dan enak dibaca, seperti menjelaskan ke rekan satu tim. Hindari daftar kata kunci tanpa kalimat, singkatan yang tidak dijelaskan, atau kalimat potongan. Orang yang baru bergabung harus paham *kenapa* task ini ada dan *kapan* task ini dianggap selesai hanya dari membaca deskripsinya.

Template:
```
## Latar belakang
<1–2 paragraf: masalah atau kebutuhan apa yang dijawab task ini, kenapa
penting sekarang, dan bagaimana kaitannya dengan task lain.>

## Yang dikerjakan
<paragraf singkat tentang pendekatannya, boleh diikuti poin-poin untuk
langkah konkret. Sebut batasan penting (apa yang TIDAK termasuk).>

## Acceptance criteria
- [ ] <perilaku/hasil yang bisa diamati dan diuji, ditulis sebagai kalimat utuh>
- [ ] <…>

## Definition of Done
- [ ] Semua acceptance criteria terpenuhi dan sudah dicek langsung
- [ ] <test/verifikasi spesifik task ini lulus, mis. test EditMode X, `pnpm test`>
- [ ] Kode/aset mengikuti `.claude/rules/` dan sudah di-review (PR merge)
- [ ] Checklist terkait di `docs/roadmap.md` dicentang
- [ ] Komentar penutup di task berisi bukti (link PR, hasil test, screenshot)

**Referensi:** <PRD §x · ARC §x · Dx · task terkait GAME-n>
```

Aturan penulisan:
- **Acceptance criteria** = apa yang harus benar dari sisi hasil/perilaku, spesifik untuk task ini, terukur (angka, kondisi, skenario). Minimal 2 butir.
- **Definition of Done** = standar kualitas sebelum task boleh ditutup. Butir umum di atas selalu ada; tambahkan butir khusus task bila perlu.
- Untuk task non-kode (survei, izin, playtest), sesuaikan DoD dengan bukti yang relevan (notulen, foto, laporan), bukan PR.

Sebelum membuat, cek duplikat dengan `searchTasks`. Epic baru → tambah opsi lewat `updateField` (sertakan seluruh daftar opsi lama) dan sub-bagian baru di roadmap.

## Status

| Key | Label | Arti |
|---|---|---|
| `backlog` | Backlog | Belum dijadwalkan |
| `todo` | To Do | Masuk sprint aktif |
| `prog` | In Progress | Sedang dikerjakan (batasi ≤ 2 per orang) |
| `review` | In Review | PR terbuka / menunggu verifikasi |
| `done` | Done | DoD terpenuhi |

## Laporan cepat

- "Progres sprint / project?" → `getProjectStats(projectId:"game-3d")`.
- "Apa yang selesai minggu ini?" → `queryTasks(projectId:"game-3d", completedSince:"this week")`.
- Per epic → `queryTasks(projectId:"game-3d", customField:"Epic", customFieldValue:"<epic>")`.
