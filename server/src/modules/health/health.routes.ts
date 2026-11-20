import type { FastifyPluginAsyncZod } from 'fastify-type-provider-zod';
import { healthResponseSchema } from './health.schema.js';

export const healthRoutes: FastifyPluginAsyncZod = async (app) => {
  app.get(
    '/health',
    {
      schema: {
        tags: ['health'],
        summary: 'Cek status server',
        response: { 200: healthResponseSchema },
      },
    },
    async () => ({ status: 'ok' as const, uptime: process.uptime() }),
  );
};
