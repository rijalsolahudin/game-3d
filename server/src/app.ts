import Fastify, { type FastifyInstance } from 'fastify';
import { serializerCompiler, validatorCompiler } from 'fastify-type-provider-zod';
import type { Env } from './lib/env.js';
import { errorHandlerPlugin } from './plugins/error-handler.js';
import { swaggerPlugin } from './plugins/swagger.js';
import { healthRoutes } from './modules/health/health.routes.js';

export async function buildApp(env: Env): Promise<FastifyInstance> {
  const app = Fastify({
    logger: {
      level: env.LOG_LEVEL,
      ...(env.NODE_ENV === 'development' && {
        transport: { target: 'pino-pretty', options: { translateTime: 'HH:MM:ss' } },
      }),
    },
  });

  app.setValidatorCompiler(validatorCompiler);
  app.setSerializerCompiler(serializerCompiler);

  await app.register(errorHandlerPlugin);
  await app.register(swaggerPlugin);
  await app.register(healthRoutes, { prefix: '/v1' });

  return app;
}
