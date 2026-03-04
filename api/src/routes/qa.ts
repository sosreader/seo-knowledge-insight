import { Hono } from "hono";
import { qaIdPattern, qaListParamsSchema } from "../schemas/qa.js";
import { ok, fail } from "../schemas/api-response.js";
import { qaStore, type QAItem } from "../store/qa-store.js";

export const qaRoute = new Hono();

function toSchema(item: QAItem) {
  return {
    id: item.id,
    seq: item.seq,
    question: item.question,
    answer: item.answer,
    keywords: item.keywords,
    confidence: item.confidence,
    category: item.category,
    difficulty: item.difficulty,
    evergreen: item.evergreen,
    source_title: item.source_title,
    source_date: item.source_date,
    is_merged: item.is_merged,
    notion_url: item.notion_url,
  };
}

qaRoute.get("/categories", (c) => {
  return c.json(ok({ categories: qaStore.categories() }));
});

qaRoute.get("/:item_id", (c) => {
  const itemId = c.req.param("item_id");
  if (!qaIdPattern.test(itemId)) {
    return c.json(fail("Invalid QA ID format"), 400);
  }
  const item = qaStore.getById(itemId);
  if (!item) {
    return c.json(fail(`QA id=${itemId} not found`), 404);
  }
  return c.json(ok(toSchema(item)));
});

qaRoute.get("/", (c) => {
  const parsed = qaListParamsSchema.safeParse({
    category: c.req.query("category"),
    keyword: c.req.query("keyword"),
    difficulty: c.req.query("difficulty"),
    evergreen: c.req.query("evergreen"),
    limit: c.req.query("limit"),
    offset: c.req.query("offset"),
  });

  if (!parsed.success) {
    return c.json(fail("Invalid query parameters"), 400);
  }

  const { limit, offset, ...filters } = parsed.data;
  const { items, total } = qaStore.listQa({ ...filters, limit, offset });

  return c.json(
    ok({
      items: items.map(toSchema),
      total,
      offset,
      limit,
    }),
  );
});
