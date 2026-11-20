import fp from 'fastify-plugin';
import type { FastifyError } from 'fastify';
import {
  hasZodFastifySchemaValidationErrors,
  isResponseSerializationError,
} from 'fastify-type-provider-zod';

export const errorHandlerPlugin = fp(async (app) => {
  app.setNotFoundHandler((_req, reply) => {
    void reply.status(404).send({ error: { code: 'NOT_FOUND', message: 'Rute tidak ditemukan' } });
  });

  app.setErrorHandler((err: FastifyError, req, reply) => {
    if (hasZodFastifySchemaValidationErrors(err)) {
      return reply.status(400).send({
        error: { code: 'VALIDATION_ERROR', message: 'Request tidak valid' },
      });
    }
    if (isResponseSerializationError(err)) {
      req.log.error({ err }, 'response tidak sesuai skema');
      return reply.status(500).send({
        error: { code: 'INTERNAL_ERROR', message: 'Terjadi kesalahan pada server' },
      });
    }
    const status =
      typeof err.statusCode === 'number' && err.statusCode >= 400 ? err.statusCode : 500;
    if (status >= 500) {
      req.log.error({ err }, 'unhandled error');
      return reply.status(500).send({
        error: { code: 'INTERNAL_ERROR', message: 'Terjadi kesalahan pada server' },
      });
    }
    return reply
      .status(status)
      .send({ error: { code: err.code ?? 'BAD_REQUEST', message: err.message } });
  });
});
