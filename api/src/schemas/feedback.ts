import { z } from "zod";

export const feedbackRequestSchema = z.object({
  query: z.string().min(1).max(500),
  qa_id: z.string().regex(/^[0-9a-f]{16}$/),
  feedback: z.enum(["helpful", "not_relevant"]),
  top_score: z.number().optional(),
});

export type FeedbackRequest = z.infer<typeof feedbackRequestSchema>;
