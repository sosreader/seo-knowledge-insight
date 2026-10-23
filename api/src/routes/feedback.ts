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

  const { query, qa_id, feedback, feedback_category, top_score } = parsed.data;

  // PG 模式 await 寫入並以 RETURNING 讀回；DB 不可用 → error handler 回 503／504（不再靜默吞掉）
  const saved = await recordFeedback({ query, qa_id, feedback, feedback_category, top_score });

  return c.json(
    ok({
      recorded: true,
      id: saved.id,
      created_at: saved.created_at,
      qa_id: saved.qa_id,
      feedback: saved.feedback,
      feedback_category,
    }),
  );
});
