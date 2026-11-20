# Manajemen Task (Ergonio)

Project: `stackinnov/game-3d` (slug `game-3d`, key `GAME`). Satu checklist di `docs/roadmap.md` = satu task Ergonio. Alur langkah demi langkah ada di skill **`ergonio-workflow`**; file ini memuat aturan yang selalu berlaku.

| Konsep | Di Ergonio | Nilai |
|---|---|---|
| Fase roadmap | **Milestone** | `Fase 0 — Persiapan`, `Fase 1 — Foundation & Vertical Slice`, `Fase 2 — Extended Features`, `Fase 3 — Polish & Rilis` |
| Sub-bagian roadmap (0.1, 1.3, …) | Custom field **Epic** (select) | mis. `1.5 Kendaraan` |
| Label tugas (`[Client]`, `[Server]`, …) | Custom field **Area** (select) | `Produk, Client, Server, Data, Art, UI, Web, Ops, QA` |
| Estimasi | **Story Points** (angka) | Fibonacci 1, 2, 3, 5, 8, 13. Lebih dari 13 dipecah jadi subtask |
| Iterasi kerja | **Sprint** (iteration, 2 minggu, mulai 2026-11-23) | `Sprint 1`, `Sprint 2`, … |

- Status: `Backlog` (belum dijadwalkan) → `To Do` (masuk sprint) → `In Progress` → `In Review` (PR terbuka) → `Done` (PR merge + DoD terpenuhi).
- Tidak ada perubahan kode, aset, atau dokumen tanpa task. Status dipindah saat itu juga, bukan di akhir sesi.
- Setiap task WAJIB punya Milestone, Epic, dan Area. Ketergantungan dicatat dengan link `blocks`/`blocked_by`.
- Judul task = teks checklist roadmap tanpa prefix label.
- Deskripsi WAJIB ditulis dalam bahasa yang mengalir dan manusiawi, dengan bagian **Latar belakang, Yang dikerjakan, Acceptance criteria, Definition of Done, Referensi** (template di skill `ergonio-workflow`).
- Task baru di luar roadmap: tambahkan dulu ke `docs/roadmap.md`, baru buat task-nya.
