import { Hono } from "hono";
import { searchRequestSchema } from "../schemas/search.js";
import { ok, fail } from "../schemas/api-response.js";
import { getEmbedding } from "../services/embedding.js";
import { qaStore } from "../store/qa-store.js";

export const searchRoute = new Hono();

searchRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = searchRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { query, top_k, category } = parsed.data;

  const embedding = await getEmbedding(query);
  const hits = qaStore.hybridSearch(query, embedding, top_k, category ?? null);

  const results = hits.map(({ item, score }) => ({
    id: item.id,
    question: item.question,
    answer: item.answer,
    keywords: item.keywords,
    category: item.category,
    difficulty: item.difficulty,
    evergreen: item.evergreen,
    source_title: item.source_title,
    source_date: item.source_date,
    score: Math.round(score * 10000) / 10000,
  }));

  return c.json(ok({ results, total: results.length }));
});
