# Kode error API

Semua error memakai format tunggal. Sumber konstanta: `src/lib/errors.ts`.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request tidak valid",
    "details": [{ "path": "email", "message": "..." }]
  }
}
```

`details` hanya ada pada `VALIDATION_ERROR`. Error 5xx tidak pernah menyertakan stack trace atau pesan asli (hanya dicatat di log server). Error 4xx bawaan Fastify yang tidak dikenal dipetakan ke kode generik.

| Status | Code                     | Arti                                                                      |
| ------ | ------------------------ | ------------------------------------------------------------------------- |
| 400    | `VALIDATION_ERROR`       | Body/query/params gagal validasi Zod; lihat `details`                     |
| 400    | `INVALID_JSON`           | Body JSON rusak atau kosong                                               |
| 400    | `BAD_REQUEST`            | 400 umum (mis. Content-Length tidak sesuai)                               |
| 401    | `UNAUTHORIZED`           | Token tidak ada/tidak valid/kedaluwarsa                                   |
| 403    | `FORBIDDEN`              | Terautentikasi tetapi tidak berhak                                        |
| 404    | `NOT_FOUND`              | Rute atau sumber tidak ditemukan                                          |
| 405    | `METHOD_NOT_ALLOWED`     | Metode HTTP tidak diizinkan untuk rute ini                                |
| 408    | `REQUEST_TIMEOUT`        | Request melewati batas waktu                                              |
| 4xx    | `CLIENT_ERROR`           | 4xx lain yang tak dikenal (406, 414, 431, ...); status asli dipertahankan |
| 409    | `CONFLICT`               | Konflik keadaan (mis. email sudah terdaftar)                              |
| 413    | `PAYLOAD_TOO_LARGE`      | Body melebihi batas                                                       |
| 415    | `UNSUPPORTED_MEDIA_TYPE` | Content-Type tidak didukung                                               |
| 429    | `RATE_LIMITED`           | Melebihi rate limit (auth: 10 req/menit/IP, dapat diatur lewat env)       |
| 500    | `INTERNAL_ERROR`         | Kesalahan tak terduga di server                                           |

Melempar error dari kode aplikasi:
`throw new AppError(401, ERROR_CODES.UNAUTHORIZED, 'Token tidak valid')`.

Memasang rate limit di modul auth: satu counter per IP dibagi seluruh route `/v1/auth/*`.
Pasang sekali di scope plugin `/v1/auth`, jangan per route:

```ts
export const authRoutes: FastifyPluginAsyncZod = async (app) => {
  app.addHook('onRequest', app.authRateLimitHook);
  // ...semua route auth
};
// app.register(authRoutes, { prefix: '/v1/auth' })
```

IP client bergantung pada env `TRUST_PROXY` (default `false`, XFF diabaikan). Di belakang proxy set daftar IP/CIDR proxy (atau keyword `loopback`/`linklocal`/`uniquelocal`); `true` dan angka hop ditolak (Fastify 5.12 menganggap trustProxy numerik tidak pernah mempercayai proxy).

Catatan 4xx tak dikenal: status asli dipertahankan, pesan internal Fastify tidak diteruskan, kode `CLIENT_ERROR` (kecuali yang ada di tabel).
