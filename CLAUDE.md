# Open World Real Map — Desa Tumanggal

Game eksplorasi 3D open world berbasis peta nyata Desa Tumanggal (Kec. Pengadegan, Kab. Purbalingga). Karakter **faceless** (hanya sepasang mata), kendaraan **motor & mobil**, aktivitas penemuan lokasi. Platform awal: **PC Windows**, single-player dengan cloud save.

## Dokumen

- [docs/product-requirements.md](docs/product-requirements.md): apa & mengapa (fitur, keputusan produk D1–D8, NFR)
- [docs/technical-architecture.md](docs/technical-architecture.md): tech stack, arsitektur, API, skema DB
- [docs/roadmap.md](docs/roadmap.md): urutan kerja & Definition of Done per fase

Bila ada konflik, urutan prioritas: **`.claude/rules/` → technical-architecture.md → product-requirements.md → roadmap.md**.

## Aturan proyek

Aturan dipecah per topik di `.claude/rules/` dan WAJIB dipatuhi:

| File | Berlaku untuk |
|---|---|
| `tech-stack.md` | selalu: stack terkunci & struktur repo |
| `general.md` | selalu: keamanan, performa, kerapian, testing, git |
| `domain.md` | selalu: faceless, kendaraan, koordinat, cakupan, lisensi |
| `ergonio.md` | selalu: manajemen task |
| `parallel-agents.md` | selalu: kerja paralel dengan subagent |
| `unity.md` | `client/**` |
| `server.md` | `server/**` |
| `pipeline.md` | `pipeline/**` |
| `web.md` | `web/**` |

## Manajemen task

Setiap sesi kerja WAJIB mengikuti skill **`ergonio-workflow`**: cek task Ergonio di awal, set `In Progress` saat mulai, komentar progres selama kerja, `In Review` saat PR siap, `Done` hanya setelah acceptance criteria & DoD terverifikasi. Tidak ada perubahan kode, aset, atau dokumen tanpa task.

Subagent di `.claude/agents/`: `unity-dev` (opus), `server-dev` (sonnet), `pipeline-dev` (sonnet), `reviewer` (opus, read-only). Hanya agent utama yang mengubah Ergonio.
