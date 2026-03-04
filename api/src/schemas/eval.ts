import { z } from "zod";

// --- Request schemas ---

export const evalSampleRequestSchema = z.object({
  size: z.number().int().positive().default(20),
  seed: z.number().int().default(42),
  with_golden: z.boolean().default(false),
});

export const evalRetrievalRequestSchema = z.object({
  top_k: z.number().int().positive().default(5),
  use_enriched: z.boolean().default(false),
});

/**
 * eval-save: input must be a safe filename (no path components).
 * Regex: alphanumeric, dots, hyphens, underscores, ending in .json
 */
const SAFE_FILENAME = /^[a-zA-Z0-9._-]+\.json$/;

export const evalSaveRequestSchema = z.object({
  input: z
    .string()
    .min(1)
    .refine((v) => SAFE_FILENAME.test(v), {
      message: "input must be a .json filename (no path separators)",
    })
    .refine((v) => !v.includes(".."), {
      message: "input must not contain path traversal",
    }),
  extraction_engine: z.enum(["claude-code", "gpt-5", "gpt-5-mini"]).default("claude-code"),
  update_baseline: z.boolean().default(false),
});

export type EvalSampleRequest = z.infer<typeof evalSampleRequestSchema>;
export type EvalRetrievalRequest = z.infer<typeof evalRetrievalRequestSchema>;
export type EvalSaveRequest = z.infer<typeof evalSaveRequestSchema>;
