import { buildApp } from './app.js';
import { EnvError, parseEnv } from './lib/env.js';

async function main(): Promise<void> {
  const env = parseEnv();
  const app = await buildApp(env);
  const shutdown = (): void => {
    void app.close().then(() => process.exit(0));
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
  await app.listen({ host: env.HOST, port: env.PORT });
}

main().catch((err: unknown) => {
  if (err instanceof EnvError) {
    console.error(err.message);
  } else {
    console.error(err);
  }
  process.exit(1);
});
