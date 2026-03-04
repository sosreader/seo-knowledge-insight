import { z } from "zod";

export const qaIdPattern = /^[0-9a-f]{16}$/;

export const qaListParamsSchema = z.object({
  category: z.string().optional(),
  keyword: z.string().max(100).optional(),
  difficulty: z.string().regex(/^(基礎|進階)$/).optional(),
  evergreen: z
    .enum(["true", "false"])
    .transform((v) => v === "true")
    .optional(),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  offset: z.coerce.number().int().min(0).default(0),
});

export type QAListParams = z.infer<typeof qaListParamsSchema>;
