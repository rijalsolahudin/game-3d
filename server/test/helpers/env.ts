import { parseEnv, type Env } from '../../src/lib/env.js';

/** Env dasar untuk test. Tambahkan variabel wajib baru (mis. DATABASE_URL) di sini saja. */
export const BASE_TEST_ENV: Record<string, string> = {
  NODE_ENV: 'test',
  HOST: '127.0.0.1',
  PORT: '3000',
  LOG_LEVEL: 'silent',
};

export function testEnv(extra: Record<string, string> = {}): Env {
  return parseEnv({ ...BASE_TEST_ENV, ...extra });
}
