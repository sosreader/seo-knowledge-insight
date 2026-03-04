import { Hono } from "hono";
import { feedbackRequestSchema } from "../schemas/feedback.js";
import { ok, fail } from "../schemas/api-response.js";
import { recordFeedback } from "../store/learning-store.js";

export const feedbackRoute = new Hono();

feedbackRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = feedbackRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { query, qa_id, feedback, top_score } = parsed.data;

  recordFeedback({ query, qa_id, feedback, top_score });

  return c.json(
    ok({
      recorded: true,
      qa_id,
      feedback,
    }),
  );
});
