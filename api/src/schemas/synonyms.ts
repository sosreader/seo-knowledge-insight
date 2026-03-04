import { z } from "zod";

/**
 * Synonym term regex: word chars + CJK + hyphen + plus + space.
 * Does NOT allow '/' or '..' to prevent path traversal.
 */
const TERM_REGEX = /^[\w\u4e00-\u9fff\-+\s]{1,100}$/;

export const synonymTermSchema = z
  .string()
  .min(1, "Term must not be empty")
  .max(100, "Term must be at most 100 characters")
  .refine((v) => TERM_REGEX.test(v), {
    message: "Term contains invalid characters (no '/' or '..')",
  })
  .refine((v) => !v.includes(".."), {
    message: "Term must not contain path traversal",
  });

export const synonymListSchema = z
  .array(z.string().min(1).max(200))
  .min(1, "Synonyms list must not be empty")
  .max(50, "Synonyms list must have at most 50 items");

export const createSynonymSchema = z.object({
  term: synonymTermSchema,
  synonyms: synonymListSchema,
});

export const updateSynonymSchema = z.object({
  synonyms: synonymListSchema,
});

export type CreateSynonymRequest = z.infer<typeof createSynonymSchema>;
export type UpdateSynonymRequest = z.infer<typeof updateSynonymSchema>;
