# Kerja Paralel dengan Subagent

Subagent ada di `.claude/agents/`. Agent utama berperan sebagai orkestrator.

| Agent | Model | Area Ergonio | Folder |
|---|---|---|---|
| `unity-dev` | opus | Client, UI | `client/**` |
| `server-dev` | sonnet | Server | `server/**` |
| `pipeline-dev` | sonnet | Data (skrip) | `pipeline/**` |
| `reviewer` | opus | semua (read-only) | — |

Area Produk, Art, dan Data lapangan (survei, izin, modeling) dikerjakan manusia, bukan subagent.

## Aturan
- **Satu subagent = satu task.** Agent utama mengirim nomor task beserta deskripsi lengkap (latar belakang, acceptance criteria, DoD).
- **Hanya task yang siap:** semua link `blocked_by` sudah Done. Cek dengan `getTask` sebelum menugaskan.
- **Isolasi:** subagent yang mengubah file dijalankan dengan `isolation: "worktree"` agar tidak bentrok dengan pekerjaan lain.
- **Maksimal satu subagent di `client/**` pada satu waktu.** Scene/prefab Unity sulit di-merge, dan satu proyek Unity tidak bisa dibuka dua editor. `server-dev` dan `pipeline-dev` boleh paralel dengan `unity-dev` dan satu sama lain.
- **Ergonio hanya diubah oleh agent utama.** Subagent melapor; agent utama memindah status, menulis komentar progres, dan mencentang criteria. Ini mencegah status dobel dan mengumpulkan persetujuan user.
- **Review sebelum In Review:** setelah subagent dev selesai, jalankan `reviewer` atas hasilnya. Task baru boleh ke `In Review` bila verdict `approve`, atau temuan sudah diperbaiki.
- **Integrasi:** agent utama yang menggabungkan hasil worktree, menyelesaikan konflik, dan menjalankan verifikasi akhir sebelum PR.
- Bila subagent melaporkan keputusan baru atau perubahan dokumen yang dibutuhkan, agent utama mencatatnya (PRD §2 / ARC) sebelum task ditutup.

Alur langkah demi langkah ada di skill `ergonio-workflow`, bagian "Kerja paralel".
