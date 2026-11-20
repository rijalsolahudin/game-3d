import fp from 'fastify-plugin';
import type { FastifyError } from 'fastify';
import {
  hasZodFastifySchemaValidationErrors,
  isResponseSerializationError,
} from 'fastify-type-provider-zod';
import {
  AppError,
  ERROR_CODES,
  FASTIFY_ERROR_MAP,
  GENERIC_4XX,
  type ErrorDetail,
} from '../lib/errors.js';

const INTERNAL = { code: ERROR_CODES.INTERNAL_ERROR, message: 'Terjadi kesalahan pada server' };
// 4xx lain (406, 414, 431, ...): status asli dipertahankan, kode netral yang tidak menyiratkan 400.
const GENERIC_CLIENT_ERROR = {
  code: ERROR_CODES.CLIENT_ERROR,
  message: 'Request tidak dapat diproses',
};

function toPath(instancePath: string): string {
  return instancePath.replace(/^\//, '').replaceAll('/', '.');
}

export const errorHandlerPlugin = fp(async (app) => {
  app.setNotFoundHandler((_req, reply) => {
    void reply
      .status(404)
      .send({ error: { code: ERROR_CODES.NOT_FOUND, message: 'Rute tidak ditemukan' } });
  });

  app.setErrorHandler((err: FastifyError | AppError, req, reply) => {
    if (hasZodFastifySchemaValidationErrors(err)) {
      const details: ErrorDetail[] = err.validation.map((v) => ({
        path: toPath(v.instancePath),
        message: v.message ?? 'Nilai tidak valid',
      }));
      return reply.status(400).send({
        error: { code: ERROR_CODES.VALIDATION_ERROR, message: 'Request tidak valid', details },
      });
    }
    if (isResponseSerializationError(err)) {
      req.log.error({ err }, 'response tidak sesuai skema');
      return reply.status(500).send({ error: INTERNAL });
    }
    if (err instanceof AppError) {
      if (err.statusCode >= 500) {
        req.log.error({ err }, 'app error 5xx');
        return reply.status(500).send({ error: INTERNAL });
      }
      return reply.status(err.statusCode).send({
        error: {
          code: err.code,
          message: err.message,
          ...(err.details && { details: err.details }),
        },
      });
    }
    const status =
      typeof err.statusCode === 'number' && err.statusCode >= 400 ? err.statusCode : 500;
    if (status >= 500) {
      req.log.error({ err }, 'unhandled error');
      return reply.status(500).send({ error: INTERNAL });
    }
    const mapped = err.code ? FASTIFY_ERROR_MAP[err.code] : undefined;
    if (mapped) {
      return reply
        .status(mapped.status)
        .send({ error: { code: mapped.code, message: mapped.message } });
    }
    // 4xx tak dikenal: kode & pesan generik, pesan internal tidak diteruskan.
    const generic = GENERIC_4XX[status] ?? GENERIC_CLIENT_ERROR;
    return reply.status(status).send({ error: { code: generic.code, message: generic.message } });
  });
});
