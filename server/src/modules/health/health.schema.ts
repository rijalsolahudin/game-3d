import { z } from 'zod';

export const healthResponseSchema = z.object({
  status: z.literal('ok'),
  uptime: z.number().describe('Detik sejak server menyala'),
});

export type HealthResponse = z.infer<typeof healthResponseSchema>;
