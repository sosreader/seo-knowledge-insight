import { z } from "zod";

export const feedbackCategorySchema = z.enum([
  "wrong_answer",
  "missing_info",
  "wrong_source",
  "outdated",
  "too_basic",
  "too_advanced",
]);

export const feedbackRequestSchema = z.object({
  query: z.string().min(1).max(500),
  qa_id: z.string().regex(/^[0-9a-f]{16}$/),
  feedback: z.enum(["helpful", "not_relevant"]),
  feedback_category: feedbackCategorySchema.optional(),
  top_score: z.number().optional(),
});

export type FeedbackRequest = z.infer<typeof feedbackRequestSchema>;
export type FeedbackCategory = z.infer<typeof feedbackCategorySchema>;
