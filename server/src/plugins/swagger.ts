import fp from 'fastify-plugin';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import { jsonSchemaTransform } from 'fastify-type-provider-zod';

export const swaggerPlugin = fp(async (app) => {
  await app.register(swagger, {
    openapi: {
      openapi: '3.1.0',
      info: { title: 'Desa Tumanggal API', version: '0.1.0' },
      servers: [{ url: '/' }],
    },
    transform: jsonSchemaTransform,
  });
  await app.register(swaggerUi, { routePrefix: '/docs' });
});
