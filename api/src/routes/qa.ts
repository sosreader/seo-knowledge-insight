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
    source_type: item.source_type,
    source_collection: item.source_collection,
    source_url: item.source_url,
    extraction_model: item.extraction_model ?? null,
    maturity_relevance: item.maturity_relevance ?? null,
    primary_category: item.primary_category ?? item.category,
    categories: item.categories ?? [item.category],
    intent_labels: item.intent_labels ?? [],
    scenario_tags: item.scenario_tags ?? [],
    serving_tier: item.serving_tier ?? "canonical",
    evidence_scope: item.evidence_scope ?? [],
    freshness_score: item.freshness_score,
  };
}

qaRoute.get("/categories", (c) => {
  return c.json(ok({ categories: qaStore.categories() }));
});

qaRoute.get("/collections", (c) => {
  return c.json(ok({ collections: qaStore.collections() }));
});

qaRoute.get("/:item_id", (c) => {
  const itemId = c.req.param("item_id");

  // Support both hex stable_id and integer seq
  let item;
  const seqNum = Number(itemId);
  if (Number.isInteger(seqNum) && seqNum > 0) {
    item = qaStore.getBySeq(seqNum);
  } else if (qaIdPattern.test(itemId)) {
    item = qaStore.getById(itemId);
  } else {
    return c.json(fail("Invalid QA ID format"), 400);
  }

  if (!item) {
    return c.json(fail(`QA id=${itemId} not found`), 404);
  }
  return c.json(ok(toSchema(item)));
});

qaRoute.get("/", (c) => {
  const parsed = qaListParamsSchema.safeParse({
    category: c.req.query("category"),
    primary_category: c.req.query("primary_category"),
    keyword: c.req.query("keyword"),
    difficulty: c.req.query("difficulty"),
    evergreen: c.req.query("evergreen"),
    source_type: c.req.query("source_type"),
    source_collection: c.req.query("source_collection"),
    extraction_model: c.req.query("extraction_model"),
    maturity_relevance: c.req.query("maturity_relevance"),
    intent_label: c.req.query("intent_label"),
    scenario_tag: c.req.query("scenario_tag"),
    serving_tier: c.req.query("serving_tier"),
    evidence_scope: c.req.query("evidence_scope"),
    sort_by: c.req.query("sort_by"),
    sort_order: c.req.query("sort_order"),
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
