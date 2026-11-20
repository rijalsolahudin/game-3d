# Open World Real Map — Desa Tumanggal

Game eksplorasi 3D open world berbasis peta nyata Desa Tumanggal, Kec. Pengadegan, Kab. Purbalingga.

## Struktur

| Folder | Isi |
|---|---|
| `client/` | Proyek Unity 6 LTS (game) |
| `server/` | Backend Fastify + TypeScript |
| `pipeline/` | Skrip data peta (OSM, DEMNAS → Unity) |
| `web/` | Landing & panel admin (Fase 3) |
| `docs/` | PRD, arsitektur, roadmap, ADR |
| `.claude/` | Rules, skills, dan subagent untuk Claude Code |

Dokumen utama: [PRD](docs/product-requirements.md) · [Arsitektur](docs/technical-architecture.md) · [Roadmap](docs/roadmap.md)

## Clone

Repo ini memakai **Git LFS** untuk model 3D, tekstur, audio, dan raster peta. Pasang Git LFS sebelum clone:

```bash
git lfs install
git clone <url-repo>
```

Bila sudah terlanjur clone tanpa LFS, jalankan `git lfs pull`.

Data mentah pipeline (`pipeline/data/raw/`) tidak disimpan di repo. Cara mengunduhnya ada di `pipeline/README.md`.

## Database lokal

Backend memakai PostgreSQL 17 + PostGIS 3.5 yang dijalankan lewat Docker.

```bash
cp .env.example .env      # lalu ganti POSTGRES_PASSWORD
docker compose up -d db
```

Database tersedia di `localhost:5433` (port bisa diubah lewat `POSTGRES_PORT` di `.env`). Default-nya 5433 agar tidak bentrok dengan PostgreSQL lain yang mungkin sudah jalan di 5432. Data tersimpan di volume `game-3d_db-data`, jadi tidak hilang saat container dimatikan. Untuk menghapus data sepenuhnya: `docker compose down -v`.
