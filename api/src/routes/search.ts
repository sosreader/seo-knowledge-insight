import { Hono } from "hono";
import { searchRequestSchema } from "../schemas/search.js";
import { ok, fail } from "../schemas/api-response.js";
import { getEmbedding } from "../services/embedding.js";
import { qaStore, type QAItem } from "../store/qa-store.js";
import { SupabaseQAStore } from "../store/supabase-qa-store.js";
import { hasOpenAI, type SearchMode } from "../utils/mode-detect.js";
import { applyMaturityBoost, parseMaturityLevel } from "../utils/maturity.js";

/** Fire-and-forget: increment search_hit_count for matched IDs. */
const trackHits = (
  hits: ReadonlyArray<{ item: QAItem; score: number }>,
): void => {
  if (qaStore instanceof SupabaseQAStore && hits.length > 0) {
    const hitIds = hits.map((h) => h.item.id);
    qaStore.incrementSearchHitCount(hitIds).catch((err) => {
      console.warn("trackHits failed (non-fatal):", err);
    });
  }
};

export const searchRoute = new Hono();

const filterHitsByModel = (
  hits: ReadonlyArray<{ item: QAItem; score: number }>,
  extractionModel?: string,
): ReadonlyArray<{ item: QAItem; score: number }> => {
  if (!extractionModel) {
    return hits;
  }
  return hits.filter(({ item }) => item.extraction_model === extractionModel);
};

searchRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = searchRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { query, top_k, category, extraction_model, maturity_level } =
    parsed.data;
  const maturityLevel = parseMaturityLevel(maturity_level);

  const mapResults = (hits: ReadonlyArray<{ item: QAItem; score: number }>) =>
    hits.map(({ item, score }) => ({
      id: item.id,
      question: item.question,
      answer: item.answer,
      keywords: item.keywords,
      category: item.category,
      difficulty: item.difficulty,
      evergreen: item.evergreen,
      source_title: item.source_title,
      source_date: item.source_date,
      source_type: item.source_type,
      source_collection: item.source_collection,
      source_url: item.source_url,
      extraction_model: item.extraction_model ?? null,
      maturity_relevance: item.maturity_relevance ?? null,
      score: Math.round(score * 10000) / 10000,
    }));

  if (hasOpenAI()) {
    try {
      const embedding = await getEmbedding(query);
      const hits = await qaStore.hybridSearch(
        query,
        embedding,
        top_k,
        category ?? null,
      );
      const filteredHits = filterHitsByModel(hits, extraction_model);
      const boostedHits = applyMaturityBoost(filteredHits, maturityLevel);
      trackHits(boostedHits);
      const results = mapResults(boostedHits);
      return c.json(
        ok({ results, total: results.length, mode: "hybrid" as SearchMode }),
      );
    } catch (err: unknown) {
      const status = (err as { status?: number }).status;
      if (status === 401 || status === 403 || status === 429) {
        console.warn(
          `OpenAI API error (${status}), falling back to keyword search`,
        );
        // Fall through to keyword search below
      } else {
        throw err;
      }
    }
  }

  // Native TypeScript keyword search — in-memory, no OpenAI required
  const hits = qaStore.keywordSearch(query, top_k, category ?? null);
  const filteredHits = filterHitsByModel(hits, extraction_model);
  const boostedHits = applyMaturityBoost(filteredHits, maturityLevel);
  trackHits(boostedHits);
  const results = mapResults(boostedHits);
  return c.json(
    ok({ results, total: results.length, mode: "keyword" as SearchMode }),
  );
});
