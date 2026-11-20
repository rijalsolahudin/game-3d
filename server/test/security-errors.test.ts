import { afterEach, describe, expect, it } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { buildApp } from '../src/app.js';
import { AppError, ERROR_CODES } from '../src/lib/errors.js';
import { parseEnv } from '../src/lib/env.js';
import { BASE_TEST_ENV, testEnv } from './helpers/env.js';

let app: FastifyInstance;

async function make(extra: Record<string, string> = {}): Promise<FastifyInstance> {
  app = await buildApp(testEnv(extra));
  // Meniru modul auth: satu scope /v1/auth dengan hook rate limit bersama.
  const instance = app;
  await app.register(
    async (scope) => {
      scope.addHook('onRequest', instance.authRateLimitHook);
      scope.get('/login', async () => ({ ok: true }));
      scope.get('/register', async () => ({ ok: true }));
    },
    { prefix: '/v1/auth' },
  );
  app.post(
    '/v1/dummy/validate',
    { schema: { body: z.object({ email: z.email(), age: z.number() }) } },
    async () => ({ ok: true }),
  );
  app.get('/v1/dummy/401', async () => {
    throw new AppError(401, ERROR_CODES.UNAUTHORIZED, 'Token tidak valid');
  });
  app.get('/v1/dummy/500', async () => {
    throw new Error('rahasia: password db = hunter2');
  });
  app.get('/v1/dummy/418', async () => {
    throw Object.assign(new Error('pesan internal'), { statusCode: 418, code: 'X_INTERNAL' });
  });
  await app.ready();
  return app;
}

async function hit(url: string, headers: Record<string, string> = {}): Promise<number> {
  const res = await app.inject({ method: 'GET', url, headers });
  return res.statusCode;
}

afterEach(async () => {
  await app.close();
});

describe('rate limit auth', () => {
  it('satu counter bersama: 6 ke /login + 4 ke /register lolos, request ke-11 mendapat 429', async () => {
    await make();
    for (let i = 0; i < 6; i++) expect(await hit('/v1/auth/login')).toBe(200);
    for (let i = 0; i < 4; i++) expect(await hit('/v1/auth/register')).toBe(200);
    const res = await app.inject({ method: 'GET', url: '/v1/auth/register' });
    expect(res.statusCode).toBe(429);
    expect(res.json().error.code).toBe('RATE_LIMITED');
    expect(typeof res.json().error.message).toBe('string');
    // route lain di scope yang sama juga ikut terblokir
    expect(await hit('/v1/auth/login')).toBe(429);
  });

  it('endpoint non-auth tidak dibatasi', async () => {
    await make();
    for (let i = 0; i < 15; i++) expect(await hit('/v1/health')).toBe(200);
  });

  it('default (TRUST_PROXY=false): X-Forwarded-For diabaikan, satu counter', async () => {
    await make({ RATE_LIMIT_AUTH_MAX: '2' });
    expect(await hit('/v1/auth/login', { 'x-forwarded-for': '1.1.1.1' })).toBe(200);
    expect(await hit('/v1/auth/login', { 'x-forwarded-for': '2.2.2.2' })).toBe(200);
    expect(await hit('/v1/auth/login', { 'x-forwarded-for': '3.3.3.3' })).toBe(429);
  });

  it('TRUST_PROXY=127.0.0.1: X-Forwarded-For berbeda punya counter terpisah', async () => {
    await make({ RATE_LIMIT_AUTH_MAX: '2', TRUST_PROXY: '127.0.0.1' });
    expect(await hit('/v1/auth/login', { 'x-forwarded-for': '1.1.1.1' })).toBe(200);
    expect(await hit('/v1/auth/login', { 'x-forwarded-for': '1.1.1.1' })).toBe(200);
    expect(await hit('/v1/auth/login', { 'x-forwarded-for': '1.1.1.1' })).toBe(429);
    expect(await hit('/v1/auth/login', { 'x-forwarded-for': '2.2.2.2' })).toBe(200);
  });
});

describe('format error', () => {
  it('400 validasi menyertakan details per field', async () => {
    await make();
    const res = await app.inject({
      method: 'POST',
      url: '/v1/dummy/validate',
      payload: { email: 'bukan-email', age: 'x' },
    });
    expect(res.statusCode).toBe(400);
    const { error } = res.json();
    expect(error.code).toBe('VALIDATION_ERROR');
    const paths = error.details.map((d: { path: string }) => d.path);
    expect(paths).toEqual(expect.arrayContaining(['email', 'age']));
  });

  it('JSON rusak -> INVALID_JSON tanpa pesan internal Fastify', async () => {
    await make();
    const res = await app.inject({
      method: 'POST',
      url: '/v1/dummy/validate',
      headers: { 'content-type': 'application/json' },
      payload: '{rusak',
    });
    expect(res.statusCode).toBe(400);
    expect(res.json()).toEqual({
      error: { code: 'INVALID_JSON', message: 'Body JSON tidak valid' },
    });
  });

  it('content-type tidak didukung -> 415 UNSUPPORTED_MEDIA_TYPE', async () => {
    await make();
    const res = await app.inject({
      method: 'POST',
      url: '/v1/dummy/validate',
      headers: { 'content-type': 'application/xml' },
      payload: '<a/>',
    });
    expect(res.statusCode).toBe(415);
    expect(res.json().error.code).toBe('UNSUPPORTED_MEDIA_TYPE');
  });

  it('401 dari route', async () => {
    await make();
    const res = await app.inject({ method: 'GET', url: '/v1/dummy/401' });
    expect(res.statusCode).toBe(401);
    expect(res.json()).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Token tidak valid' },
    });
  });

  it('404 rute tak dikenal', async () => {
    await make();
    const res = await app.inject({ method: 'GET', url: '/v1/tidak-ada' });
    expect(res.statusCode).toBe(404);
    expect(res.json().error.code).toBe('NOT_FOUND');
  });

  it('4xx tak dikenal: status asli, kode netral CLIENT_ERROR, pesan internal tidak bocor', async () => {
    await make();
    const res = await app.inject({ method: 'GET', url: '/v1/dummy/418' });
    expect(res.statusCode).toBe(418);
    expect(res.json()).toEqual({
      error: { code: 'CLIENT_ERROR', message: 'Request tidak dapat diproses' },
    });
  });

  it('500 di production tidak membocorkan pesan asli/stack', async () => {
    await make({ NODE_ENV: 'production' });
    const res = await app.inject({ method: 'GET', url: '/v1/dummy/500' });
    expect(res.statusCode).toBe(500);
    expect(res.json()).toEqual({
      error: { code: 'INTERNAL_ERROR', message: 'Terjadi kesalahan pada server' },
    });
    expect(res.body).not.toMatch(/hunter2|stack|\.ts:/);
  });
});

describe('helmet, cors, swagger', () => {
  it('header keamanan helmet muncul', async () => {
    await make();
    const res = await app.inject({ method: 'GET', url: '/v1/health' });
    expect(res.headers['x-content-type-options']).toBe('nosniff');
    expect(res.headers['content-security-policy']).toBeDefined();
  });

  it('CORS: origin tidak terdaftar ditolak, terdaftar diizinkan', async () => {
    await make({ CORS_ORIGINS: 'https://admin.example.com' });
    const ok = await app.inject({
      method: 'GET',
      url: '/v1/health',
      headers: { origin: 'https://admin.example.com' },
    });
    expect(ok.headers['access-control-allow-origin']).toBe('https://admin.example.com');
    const no = await app.inject({
      method: 'GET',
      url: '/v1/health',
      headers: { origin: 'https://evil.example.com' },
    });
    expect(no.headers['access-control-allow-origin']).toBeUndefined();
  });

  it('development: /docs dan initializer 200, CSP tanpa unsafe-inline di script-src', async () => {
    await make({ NODE_ENV: 'development' });
    const docs = await app.inject({ method: 'GET', url: '/docs/' });
    expect(docs.statusCode).toBe(200);
    const init = await app.inject({ method: 'GET', url: '/docs/static/swagger-initializer.js' });
    expect(init.statusCode).toBe(200);
    const csp = String(docs.headers['content-security-policy']);
    expect(csp).not.toMatch(/script-src[^;]*unsafe-inline/);
    expect(csp).not.toContain('upgrade-insecure-requests');
  });

  it('production: CSP default helmet dan /docs mati', async () => {
    await make({ NODE_ENV: 'production' });
    const res = await app.inject({ method: 'GET', url: '/docs/' });
    expect(res.statusCode).toBe(404);
    const health = await app.inject({ method: 'GET', url: '/v1/health' });
    expect(String(health.headers['content-security-policy'])).toContain(
      'upgrade-insecure-requests',
    );
  });
});

describe('parseEnv rate limit, CORS, TRUST_PROXY', () => {
  it('default dan parsing daftar dipisah koma', () => {
    expect(parseEnv(BASE_TEST_ENV).CORS_ORIGINS).toEqual([]);
    expect(
      parseEnv({ ...BASE_TEST_ENV, CORS_ORIGINS: 'http://a.com, http://b.com' }).CORS_ORIGINS,
    ).toEqual(['http://a.com', 'http://b.com']);
    expect(parseEnv(BASE_TEST_ENV).RATE_LIMIT_AUTH_MAX).toBe(10);
  });

  it('TRUST_PROXY: default false, keyword, daftar IP/CIDR; true/sembarang ditolak', () => {
    expect(parseEnv(BASE_TEST_ENV).TRUST_PROXY).toBe(false);
    expect(parseEnv({ ...BASE_TEST_ENV, TRUST_PROXY: 'loopback' }).TRUST_PROXY).toEqual([
      'loopback',
    ]);
    expect(
      parseEnv({ ...BASE_TEST_ENV, TRUST_PROXY: '10.0.0.0/8, 192.168.1.1' }).TRUST_PROXY,
    ).toEqual(['10.0.0.0/8', '192.168.1.1']);
    expect(() => parseEnv({ ...BASE_TEST_ENV, TRUST_PROXY: 'true' })).toThrow(/TRUST_PROXY/);
    expect(() => parseEnv({ ...BASE_TEST_ENV, TRUST_PROXY: '1' })).toThrow(/TRUST_PROXY/);
    expect(() => parseEnv({ ...BASE_TEST_ENV, TRUST_PROXY: '10.0.0.0/99' })).toThrow(/TRUST_PROXY/);
  });
});
