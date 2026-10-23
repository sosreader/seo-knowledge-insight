import { Hono } from "hono";
import { searchRequestSchema, type SearchModeParam } from "../schemas/search.js";
import { ok, fail } from "../schemas/api-response.js";
import { getEmbedding } from "../services/embedding.js";
import { qaStore, type QAItem } from "../store/qa-store.js";
import { QUERY_CATEGORY_HINTS } from "../store/search-engine.js";
import { PgQAStore } from "../store/pg-qa-store.js";
import type { SearchMode } from "../utils/mode-detect.js";
import { isLlmEnabled } from "../services/llm-client.js";
import { featureUnavailableBody } from "../utils/feature-errors.js";
import { applyMaturityBoost, parseMaturityLevel, type MaturityLevel } from "../utils/maturity.js";

/** Fire-and-forget: increment search_hit_count for matched IDs. */
const trackHits = (
  hits: ReadonlyArray<{ item: QAItem; score: number }>,
): void => {
  if (qaStore instanceof PgQAStore && hits.length > 0) {
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
    if (extraction_model && item.extraction_model !== extraction_model)
      return false;
    if (
      primary_category &&
      (item.primary_category ?? item.category) !== primary_category
    )
      return false;
    if (intent_label && !(item.intent_labels ?? []).includes(intent_label))
      return false;
    if (scenario_tag && !(item.scenario_tags ?? []).includes(scenario_tag))
      return false;
    if (serving_tier && (item.serving_tier ?? "canonical") !== serving_tier)
      return false;
    if (evidence_scope && !(item.evidence_scope ?? []).includes(evidence_scope))
      return false;
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

type Hit = { item: QAItem; score: number };

const mapResults = (query: string, hits: ReadonlyArray<Hit>) => {
  const queryCategories = inferQueryCategories(query);
  const usedQueryCategories = new Set<string>();

  return hits.map(({ item, score }, index) => {
    const allCategories = item.categories ?? [item.category];
    const matchedCategories = allCategories.filter((category) =>
      queryCategories.has(category),
    );
    const primaryCategory = item.primary_category ?? item.category;
    const preferredCategory =
      index === 0
        ? primaryCategory
        : (matchedCategories.find(
            (category) => !usedQueryCategories.has(category),
          ) ??
          matchedCategories[0] ??
          primaryCategory);
    if (queryCategories.has(preferredCategory))
      usedQueryCategories.add(preferredCategory);

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
      extraction_provenance: item.extraction_provenance ?? null,
      maturity_relevance: item.maturity_relevance ?? null,
      score: Math.round(score * 10000) / 10000,
    };
  });
};

interface SearchPlan {
  readonly query: string;
  readonly topK: number;
  readonly retrievalTopK: number;
  readonly category: string | null;
  readonly filters: MetadataFilters;
  readonly maturityLevel: MaturityLevel | null;
}

/** 檢索後共用：metadata 過濾 → 成熟度加權 → 命中計數（≤200 id，fire-and-forget）。 */
const finalizeHits = (plan: SearchPlan, hits: ReadonlyArray<Hit>): ReadonlyArray<Hit> => {
  const filteredHits = filterHitsByMetadata(hits, plan.filters).slice(0, plan.topK);
  const boostedHits = applyMaturityBoost(filteredHits, plan.maturityLevel).slice(0, plan.topK);
  trackHits(boostedHits);
  return boostedHits;
};

const isFallbackStatus = (err: unknown): boolean => {
  const status = (err as { status?: number }).status;
  return status === 401 || status === 403 || status === 429;
};

/** hybrid（semantic 同路徑）：OpenAI 相容端點驗證／額度錯誤時回 null，由呼叫端退 keyword。 */
const runVectorSearch = async (plan: SearchPlan): Promise<ReadonlyArray<Hit> | null> => {
  try {
    const embedding = await getEmbedding(plan.query);
    const hits = await qaStore.hybridSearch(plan.query, embedding, plan.retrievalTopK, plan.category);
    return finalizeHits(plan, hits);
  } catch (err: unknown) {
    if (!isFallbackStatus(err)) throw err;
    console.warn(`LLM API error (${(err as { status?: number }).status}), falling back to keyword search`);
    return null;
  }
};

const runKeywordSearch = (plan: SearchPlan): ReadonlyArray<Hit> =>
  finalizeHits(plan, qaStore.keywordSearch(plan.query, plan.retrievalTopK, plan.category));

/** 明確要求向量模式但 LLM 關閉 → 501；未指定模式 → LLM 可用走 hybrid，否則 keyword。 */
const wantsVector = (mode: SearchModeParam | undefined, llmEnabled: boolean): boolean =>
  mode === undefined ? llmEnabled : mode !== "keyword";

searchRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = searchRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { query, top_k, category, maturity_level, mode, ...filters } = parsed.data;
  const llmEnabled = isLlmEnabled();
  const vector = wantsVector(mode, llmEnabled);

  if (vector && !llmEnabled) {
    return c.json(featureUnavailableBody("llm_disabled"), 501);
  }

  const hasPostFilter = Object.values(filters).some(Boolean);
  const plan: SearchPlan = {
    query,
    topK: top_k,
    retrievalTopK: hasPostFilter ? top_k * MODEL_FILTER_OVERFETCH : top_k,
    category: category ?? null,
    filters,
    maturityLevel: parseMaturityLevel(maturity_level),
  };

  const vectorHits = vector ? await runVectorSearch(plan) : null;
  const effectiveMode: SearchMode = vectorHits ? "hybrid" : "keyword";
  const results = mapResults(query, vectorHits ?? runKeywordSearch(plan));
  const llmDisabled = !llmEnabled;

  return c.json(
    ok(
      { results, total: results.length, mode: effectiveMode, llm_disabled: llmDisabled },
      { mode: effectiveMode, llm_disabled: llmDisabled },
    ),
  );
});
