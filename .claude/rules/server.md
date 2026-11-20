---
paths:
  - "server/**"
---

# Aturan Server / TypeScript

## Struktur & konvensi
- Per modul: `*.routes.ts`, `*.schema.ts` (Zod), `*.service.ts` (logika), `*.repository.ts` (Drizzle). Route tidak boleh query DB langsung.
- File `kebab-case.ts`; tipe/class `PascalCase`; fungsi/variabel `camelCase`; konstanta `UPPER_SNAKE_CASE`.
- TypeScript `strict: true`, dilarang `any` (pakai `unknown` + narrowing).
- Env var divalidasi Zod saat boot; server berhenti bila ada yang kurang.
- Semua endpoint di bawah `/v1`, request & response divalidasi Zod dan terdokumentasi otomatis ke OpenAPI.
- Format error tunggal: `{ "error": { "code", "message", "details"? } }` lewat error handler global. `details` hanya untuk `VALIDATION_ERROR` (path + pesan, tanpa nilai input). Kode error hanya dari `src/lib/errors.ts` dan didokumentasikan di `server/docs/error-codes.md`. Stack trace dan pesan internal tidak boleh bocor di production.

## Autentikasi & otorisasi
- Password: Argon2id. Access token: JWT 15 menit. Refresh token: 30 hari, rotasi, disimpan ter-hash, deteksi reuse per `family_id` (reuse → cabut seluruh family).
- Semua endpoint selain `/v1/auth/*` dan `/v1/health` wajib JWT. Ambil `userId` dari token, **jangan pernah** dari body/params.
- Rate limit endpoint auth 10 req/menit/IP, satu counter bersama untuk seluruh `/v1/auth/*` (hook di scope plugin auth, bukan config per route). Jangan set `trustProxy: true` tanpa batas; pakai env `TRUST_PROXY`.
- Panel admin web memakai peran `admin` terpisah; jangan menambah peran lain tanpa memperbarui file ini.

## Database & query
- Akses DB hanya lewat Drizzle di `*.repository.ts`. Raw SQL hanya via template `sql\`\`` Drizzle dengan parameter binding, dilarang interpolasi string.
- Setiap perubahan skema = migrasi drizzle-kit baru; jangan mengedit migrasi yang sudah di-merge.
- Konvensi: tabel `snake_case` jamak, PK `uuid` (UUIDv7), waktu `timestamptz` UTC, geometri PostGIS SRID 4326 dengan index GiST.
- Tidak ada N+1; pilih kolom seperlunya.
- Operasi multi-tabel (mis. penemuan + unlock kendaraan) dalam satu transaksi.
- Event sinkron idempoten lewat `sync_events.id` dengan `ON CONFLICT DO NOTHING`.
- Skema acuan: `docs/technical-architecture.md` §5. Perubahan skema WAJIB memperbarui ER diagram di sana.

## Testing
- Vitest; integration test memakai Testcontainers (PostgreSQL+PostGIS asli), bukan mock DB.
- Setiap endpoint baru punya minimal satu test sukses dan satu test gagal validasi/otorisasi.
- Sebelum menyatakan selesai: `pnpm lint && pnpm typecheck && pnpm test`.
