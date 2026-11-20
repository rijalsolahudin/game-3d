---
paths:
  - "web/**"
---

# Aturan Web (Fase 3)

- Next.js (App Router) + TypeScript strict.
- Tailwind CSS v4 CSS-first: `@import "tailwindcss";` + `@theme` di `web/src/app/globals.css`. Dilarang `tailwind.config.js` gaya v3.
- Dilarang `style=""` inline kecuali nilai dinamis runtime.
- Web hanya mengonsumsi API `/v1` yang sama dengan game; tidak mengakses database langsung.
- Panel admin wajib login dengan peran `admin` (lihat `server.md`).
