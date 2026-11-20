import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']),
  HOST: z.string().min(1),
  PORT: z.coerce.number({ error: 'wajib diisi, angka 1-65535' }).int().min(1).max(65535),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent']),
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
