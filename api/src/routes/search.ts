import { Hono } from "hono";
import { searchRequestSchema } from "../schemas/search.js";
import { ok, fail } from "../schemas/api-response.js";
import { getEmbedding } from "../services/embedding.js";
import { qaStore, type QAItem } from "../store/qa-store.js";
import { QUERY_CATEGORY_HINTS } from "../store/search-engine.js";
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

const MODEL_FILTER_OVERFETCH = 3;

interface MetadataFilters {
  readonly extraction_model?: string;
  readonly primary_category?: string;
  readonly intent_label?: string;
  readonly scenario_tag?: string;
  readonly serving_tier?: string;
  readonly evidence_scope?: string;
}

const filterHitsByMetadata = (
  hits: ReadonlyArray<{ item: QAItem; score: number }>,
  filters: MetadataFilters,
): ReadonlyArray<{ item: QAItem; score: number }> => {
  const {
    extraction_model,
    primary_category,
    intent_label,
    scenario_tag,
    serving_tier,
    evidence_scope,
  } = filters;

  return hits.filter(({ item }) => {
    if (extraction_model && item.extraction_model !== extraction_model) return false;
    if (primary_category && (item.primary_category ?? item.category) !== primary_category) return false;
    if (intent_label && !(item.intent_labels ?? []).includes(intent_label)) return false;
    if (scenario_tag && !(item.scenario_tags ?? []).includes(scenario_tag)) return false;
    if (serving_tier && (item.serving_tier ?? "canonical") !== serving_tier) return false;
    if (evidence_scope && !(item.evidence_scope ?? []).includes(evidence_scope)) return false;
    return true;
  });
};

const inferQueryCategories = (query: string): ReadonlySet<string> => {
  const queryLower = query.toLowerCase();
  const labels = new Set<string>();
  for (const [label, hints] of Object.entries(QUERY_CATEGORY_HINTS)) {
    if (hints.some((hint) => queryLower.includes(hint))) labels.add(label);
  }
  return labels;
};

searchRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = searchRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const {
    query,
    top_k,
    category,
    primary_category,
    extraction_model,
    maturity_level,
    intent_label,
    scenario_tag,
    serving_tier,
    evidence_scope,
  } =
    parsed.data;
  const maturityLevel = parseMaturityLevel(maturity_level);

  const mapResults = (hits: ReadonlyArray<{ item: QAItem; score: number }>) => {
    const queryCategories = inferQueryCategories(query);
    const usedQueryCategories = new Set<string>();

    return hits.map(({ item, score }, index) => {
      const allCategories = item.categories ?? [item.category];
      const matchedCategories = allCategories.filter((category) => queryCategories.has(category));
      const primaryCategory = item.primary_category ?? item.category;
      const preferredCategory =
        index === 0
          ? primaryCategory
          : matchedCategories.find((category) => !usedQueryCategories.has(category)) ??
            matchedCategories[0] ??
            primaryCategory;
      if (queryCategories.has(preferredCategory)) usedQueryCategories.add(preferredCategory);

      return {
        id: item.id,
        question: item.question,
        answer: item.answer,
        keywords: item.keywords,
        category: item.category,
        primary_category: primaryCategory,
        categories: [preferredCategory],
        all_categories: allCategories,
        intent_labels: item.intent_labels ?? [],
        scenario_tags: item.scenario_tags ?? [],
        serving_tier: item.serving_tier ?? "canonical",
        evidence_scope: item.evidence_scope ?? [],
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
      };
    });
  };

  if (hasOpenAI()) {
    try {
      const embedding = await getEmbedding(query);
      const retrievalTopK = extraction_model ? top_k * MODEL_FILTER_OVERFETCH : top_k;
      const hits = await qaStore.hybridSearch(
        query,
        embedding,
        retrievalTopK,
        category ?? null,
      );
      const filteredHits = filterHitsByMetadata(hits, {
        extraction_model,
        primary_category,
        intent_label,
        scenario_tag,
        serving_tier,
        evidence_scope,
      }).slice(0, top_k);
      const boostedHits = applyMaturityBoost(filteredHits, maturityLevel).slice(0, top_k);
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
  const retrievalTopK = extraction_model ? top_k * MODEL_FILTER_OVERFETCH : top_k;
  const hits = qaStore.keywordSearch(query, retrievalTopK, category ?? null);
  const filteredHits = filterHitsByMetadata(hits, {
    extraction_model,
    primary_category,
    intent_label,
    scenario_tag,
    serving_tier,
    evidence_scope,
  }).slice(0, top_k);
  const boostedHits = applyMaturityBoost(filteredHits, maturityLevel).slice(0, top_k);
  trackHits(boostedHits);
  const results = mapResults(boostedHits);
  return c.json(
    ok({ results, total: results.length, mode: "keyword" as SearchMode }),
  );
});
