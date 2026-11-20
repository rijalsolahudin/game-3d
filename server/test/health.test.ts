import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { buildApp } from '../src/app.js';
import { parseEnv } from '../src/lib/env.js';

describe('GET /v1/health', () => {
  let app: FastifyInstance;

  beforeAll(async () => {
    app = await buildApp(
      parseEnv({ NODE_ENV: 'test', HOST: '127.0.0.1', PORT: '3000', LOG_LEVEL: 'silent' }),
    );
    await app.ready();
  });
  afterAll(async () => {
    await app.close();
  });

  it('mengembalikan status ok', async () => {
    const res = await app.inject({ method: 'GET', url: '/v1/health' });
    expect(res.statusCode).toBe(200);
    expect(res.json()).toMatchObject({ status: 'ok' });
  });

  it('rute tak dikenal memakai format error tunggal', async () => {
    const res = await app.inject({ method: 'GET', url: '/v1/nope' });
    expect(res.statusCode).toBe(404);
    expect(res.json()).toEqual({ error: { code: 'NOT_FOUND', message: 'Rute tidak ditemukan' } });
  });
});

describe('parseEnv', () => {
  it('menolak bila variabel wajib kosong', () => {
    expect(() => parseEnv({})).toThrow(/NODE_ENV/);
  });
});
