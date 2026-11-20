import { isIP } from 'node:net';
import { z } from 'zod';

function isIpOrCidr(v: string): boolean {
  const [ip, prefix, ...rest] = v.split('/');
  if (rest.length > 0 || ip === undefined) return false;
  const family = isIP(ip);
  if (family === 0) return false;
  if (prefix === undefined) return true;
  const max = family === 4 ? 32 : 128;
  return /^\d{1,3}$/.test(prefix) && Number(prefix) <= max;
}

const TRUST_PROXY_KEYWORDS = new Set(['loopback', 'linklocal', 'uniquelocal']);

/**
 * false (default) | daftar IP/CIDR/keyword (loopback, linklocal, uniquelocal) proxy tepercaya.
 * `true` ditolak. Hop count (angka) juga ditolak: Fastify 5.12 membuat trustProxy numerik
 * "fail closed" (tidak pernah mempercayai proxy), jadi angka tidak berguna dan menyesatkan.
 */
const trustProxySchema = z
  .string()
  .default('false')
  .transform((raw, ctx): false | string[] => {
    const v = raw.trim();
    if (v === '' || v === 'false') return false;
    const items = v.split(',').map((x) => x.trim());
    if (items.every((x) => isIpOrCidr(x) || TRUST_PROXY_KEYWORDS.has(x))) return items;
    ctx.addIssue({
      code: 'custom',
      message: 'harus false atau daftar IP/CIDR proxy dipisah koma (angka dan "true" ditolak)',
    });
    return z.NEVER;
  });

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']),
  HOST: z.string().min(1),
  PORT: z.coerce.number({ error: 'wajib diisi, angka 1-65535' }).int().min(1).max(65535),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent']),
  RATE_LIMIT_AUTH_MAX: z.coerce.number().int().min(1).default(10),
  RATE_LIMIT_AUTH_WINDOW_MS: z.coerce.number().int().min(1000).default(60_000),
  TRUST_PROXY: trustProxySchema,
  CORS_ORIGINS: z
    .string()
    .default('')
    .transform((v) =>
      v
        .split(',')
        .map((o) => o.trim())
        .filter((o) => o.length > 0),
    ),
});

export type Env = z.infer<typeof envSchema>;

export class EnvError extends Error {}

export function parseEnv(source: Record<string, string | undefined> = process.env): Env {
  const result = envSchema.safeParse(source);
  if (!result.success) {
    const lines = result.error.issues.map((i) => `  - ${i.path.join('.')}: ${i.message}`);
    throw new EnvError(
      `Konfigurasi environment tidak valid. Perbaiki variabel berikut (lihat .env.example):\n${lines.join('\n')}`,
    );
  }
  return result.data;
}
