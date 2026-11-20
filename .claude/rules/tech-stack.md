# Tech Stack & Struktur Repo

## Stack (terkunci)

| Lapisan | Stack |
|---|---|
| Game client | Unity 6 LTS, C#, URP, Addressables, Input System, Cinemachine 3, UI Toolkit, Splines |
| Backend | Node.js LTS, TypeScript strict, Fastify 5, Zod, Drizzle ORM, pnpm |
| Database | PostgreSQL 17+ dengan PostGIS |
| Web pendukung (Fase 3) | Next.js + Tailwind CSS v4 |
| Pipeline peta | Python 3 (uv), GDAL, Blender, OSM + DEMNAS |
| Infra | Git LFS, GitHub Actions + GameCI, Docker, Sentry |

- **Dilarang** menambah framework, ORM, database, atau package mayor baru tanpa ADR baru di `docs/adr/` dan pembaruan tabel ini serta `docs/technical-architecture.md` §1.
- **Tailwind hanya untuk `web/`.** HUD/menu game WAJIB UI Toolkit (UXML + USS). Jangan pernah menyarankan Tailwind, HTML, atau Three.js untuk client game.
- Jangan naikkan versi mayor Unity/Node/package dalam PR fitur. Versi dikunci di `ProjectVersion.txt`, `packages-lock.json`, `.nvmrc`, dan `pnpm-lock.yaml`.

## Struktur repository

```
CLAUDE.md
.claude/       rules/, skills/
docs/          PRD, arsitektur, roadmap, adr/
client/        proyek Unity, kode di Assets/_Project/Scripts/{Core,World,Player,Vehicles,Exploration,Save,Net,UI}
server/        Fastify: src/modules/{auth,me,worlds,sync}, src/db, src/plugins, test/
pipeline/      skrip data peta; data/raw di-gitignore
web/           Next.js + Tailwind v4 (Fase 3)
```

Detail lengkap: `docs/technical-architecture.md` §6. Jangan membuat folder top-level baru tanpa memperbarui dokumen itu.
