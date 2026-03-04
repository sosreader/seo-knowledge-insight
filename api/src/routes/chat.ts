import { Hono } from "hono";
import { chatRequestSchema } from "../schemas/chat.js";
import { ok, fail } from "../schemas/api-response.js";
import { ragChat } from "../services/rag-chat.js";

export const chatRoute = new Hono();

chatRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = chatRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { message, history } = parsed.data;
  const historyDicts = history.map((h) => ({ role: h.role, content: h.content }));

  const result = await ragChat(message, historyDicts.length > 0 ? historyDicts : null);

  return c.json(ok({ answer: result.answer, sources: result.sources }));
});
