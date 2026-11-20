import fp from 'fastify-plugin';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import type { onRequestAsyncHookHandler } from 'fastify';
import type { Env } from '../lib/env.js';
import { AppError, ERROR_CODES } from '../lib/errors.js';

declare module 'fastify' {
  interface FastifyInstance {
    /**
     * Hook rate limit bersama untuk seluruh endpoint auth (satu counter per IP,
     * dibuat sekali). Pasang di scope plugin `/v1/auth`:
     * `app.addHook('onRequest', app.authRateLimitHook)`.
     * Batas dari env RATE_LIMIT_AUTH_MAX / RATE_LIMIT_AUTH_WINDOW_MS.
     */
    authRateLimitHook: onRequestAsyncHookHandler;
  }
}

export const securityPlugin = fp<{ env: Env }>(async (app, { env }) => {
  const isProd = env.NODE_ENV === 'production';

  await app.register(helmet, {
    // Production memakai CSP default helmet. Di luar production, hanya dilonggarkan
    // seperlunya agar swagger-ui (diaktifkan hanya di luar production) bisa dibuka.
    contentSecurityPolicy: isProd
      ? undefined
      : {
          directives: {
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", 'data:', 'validator.swagger.io'],
            'upgrade-insecure-requests': null,
          },
        },
  });

  await app.register(cors, {
    // Daftar kosong = tidak mengizinkan origin silang.
    origin: env.CORS_ORIGINS.length > 0 ? env.CORS_ORIGINS : false,
  });

  await app.register(rateLimit, {
    global: false,
    errorResponseBuilder: (_req, ctx) =>
      new AppError(
        429,
        ERROR_CODES.RATE_LIMITED,
        `Terlalu banyak request, coba lagi dalam ${Math.ceil(ctx.ttl / 1000)} detik`,
      ),
  });

  app.decorate(
    'authRateLimitHook',
    app.rateLimit({ max: env.RATE_LIMIT_AUTH_MAX, timeWindow: env.RATE_LIMIT_AUTH_WINDOW_MS }),
  );
});
