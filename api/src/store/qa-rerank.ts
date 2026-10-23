/**
 * QA 混合檢索的重排邏輯（純函式，無 I/O）。
 *
 * 自 supabase-qa-store.ts 原樣抽出，給 PgQAStore 使用；排序公式、權重、欄位推導一律不變，
 * 換資料庫不換檢索品質（品質調整另案在 S2.6 量測後再做）。
 */

import { computeKeywordBoostSingle } from "../utils/keyword-boost.js";
import type { QAItem } from "./qa-store.js";
import {
  categoryDiversityBoost,
  matchedQueryTerms,
  novelQueryTermBoost,
  queryTerms,
} from "./query-term-utils.js";
import {
  asList,
  tokenize,
  inferQueryLabels,
  questionSignature,
  QUERY_CATEGORY_HINTS,
  QUERY_INTENT_HINTS,
  QUERY_SCENARIO_HINTS,
} from "./search-engine.js";

/** match_qa_items() 回傳的列（VW 0011 的 RETURNS TABLE，欄位與 Supabase 版相同）。 */
export interface MatchRow {
  id: string;
  seq: number;
  question: string;
  answer: string;
  keywords: string[];
  confidence: number;
  category: string;
  difficulty: string;
  evergreen: boolean;
  source_title: string;
  source_date: string;
  source_type: string;
  source_collection: string;
  source_url: string;
  is_merged: boolean;
  extraction_model: string | null;
  maturity_relevance: string | null;
  synonyms: string[];
  freshness_score: number;
  search_hit_count: number;
  primary_category?: string | null;
  categories?: string[] | null;
  intent_labels?: string[] | null;
  scenario_tags?: string[] | null;
  serving_tier?: string | null;
  retrieval_phrases?: string[] | null;
  retrieval_surface_text?: string | null;
  content_granularity?: string | null;
  evidence_scope?: string[] | null;
  booster_target_queries?: string[] | null;
  hard_negative_terms?: string[] | null;
  similarity: number;
}

/**
 * 啟動時 SELECT app_qa_item 撈到的 row。
 *
 * 不含 primary_category 等 extended retrieval 欄位：VW app_qa_item 雖然有這些欄（0011 照 Supabase
 * live DDL），但 Supabase 時期的檢索一律由 category／keywords 推導（見 rowToQAItem），
 * 這次只換資料庫、刻意維持同一套排序輸入；要改用真欄位另案量測（S2.6）。
 */
export interface QARow {
  id: string;
  seq: number;
  question: string;
  answer: string;
  keywords: string[];
  confidence: number;
  category: string;
  difficulty: string;
  evergreen: boolean;
  source_title: string;
  source_date: string;
  source_type: string;
  source_collection: string;
  source_url: string;
  is_merged: boolean;
  extraction_model: string | null;
  maturity_relevance: string | null;
  synonyms: string[];
  freshness_score: number;
  search_hit_count: number;
}

export const OVER_RETRIEVE_FACTOR = 3;
export const KW_BOOST_CONFIG = { boost: 0.1, maxHits: 3, partial: 0.05 } as const;
export const SEMANTIC_WEIGHT = 0.7;
const SYNONYM_BOOST = 0.05;

/** startup select 用的欄位；刻意不含 extended retrieval 欄位，理由見 QARow 註解。 */
export const SELECT_COLUMNS = [
  "id",
  "seq",
  "question",
  "answer",
  "keywords",
  "confidence",
  "category",
  "difficulty",
  "evergreen",
  "source_title",
  "source_date",
  "source_type",
  "source_collection",
  "source_url",
  "is_merged",
  "extraction_model",
  "maturity_relevance",
  "synonyms",
  "freshness_score",
  "search_hit_count",
] as const;


/**
 * 建構 QAItem。extended retrieval 欄位（primary_category 等）在 live schema
 * 不存在，一律用 category / keywords 推導預設值，不再假裝這些欄位可能存在。
 * row 也接受 MatchRow（RPC 路徑）——MatchRow 是 QARow 的超集，結構相容。
 */
export function rowToQAItem(row: QARow): QAItem {
  return {
    id: row.id,
    seq: row.seq,
    question: row.question,
    answer: row.answer,
    keywords: row.keywords ?? [],
    confidence: row.confidence ?? 0,
    category: row.category ?? "",
    difficulty: row.difficulty ?? "",
    evergreen: row.evergreen ?? false,
    source_title: row.source_title ?? "",
    source_date: row.source_date ?? "",
    is_merged: row.is_merged ?? false,
    synonyms: row.synonyms ?? [],
    freshness_score: row.freshness_score ?? 1.0,
    search_hit_count: row.search_hit_count ?? 0,
    notion_url: "",
    source_type: row.source_type ?? "meeting",
    source_collection: row.source_collection ?? "seo-meetings",
    source_url: row.source_url ?? "",
    extraction_model: row.extraction_model ?? undefined,
    maturity_relevance:
      (row.maturity_relevance as "L1" | "L2" | "L3" | "L4") ?? undefined,
    primary_category: row.category ?? "",
    categories: row.category ? [row.category] : [],
    intent_labels: [],
    scenario_tags: [],
    serving_tier: "canonical",
    retrieval_phrases: row.keywords ?? [],
    retrieval_surface_text: [row.question, row.answer, ...(row.keywords ?? [])]
      .filter(Boolean)
      .join("\n"),
    content_granularity: undefined,
    evidence_scope: [],
    booster_target_queries: [],
    hard_negative_terms: [],
  };
}

export function computeSynonymBonus(
  query: string,
  synonyms: readonly string[],
): number {
  if (!synonyms || synonyms.length === 0) return 0;
  const queryLower = query.toLowerCase();
  for (const syn of synonyms) {
    const synLower = syn.toLowerCase();
    if (queryLower.includes(synLower) || synLower.includes(queryLower)) {
      return SYNONYM_BOOST;
    }
  }
  return 0;
}

// asList, tokenize, inferQueryLabels, QUERY_*_HINTS imported from search-engine.ts

export function metadataScore(query: string, item: QAItem): number {
  const queryLower = query.toLowerCase();
  const terms = queryTerms(query);
  const queryTokens = tokenize(query);
  const surfaceTokens = tokenize(item.retrieval_surface_text ?? "");
  const queryCategories = inferQueryLabels(query, QUERY_CATEGORY_HINTS);
  const queryIntents = inferQueryLabels(query, QUERY_INTENT_HINTS);
  const queryScenarios = inferQueryLabels(query, QUERY_SCENARIO_HINTS);
  const itemCategories = new Set(asList(item.categories));
  const itemIntents = new Set(asList(item.intent_labels));
  const itemScenarios = new Set(asList(item.scenario_tags));

  const phraseBoost =
    computeKeywordBoostSingle(
      query,
      item.retrieval_phrases ?? [],
      KW_BOOST_CONFIG,
    ) * 2.0;
  const surfaceBoost =
    [...queryTokens].filter((token) => surfaceTokens.has(token)).length * 0.03;
  const categoryBoost =
    [...queryCategories].filter((label) => itemCategories.has(label)).length *
    0.08;
  const intentBoost =
    [...queryIntents].filter((label) => itemIntents.has(label)).length * 0.06;
  const scenarioBoost =
    [...queryScenarios].filter((label) => itemScenarios.has(label)).length *
    0.05;
  const exactTermBoost =
    matchedQueryTerms(item.retrieval_surface_text ?? "", terms).size * 0.04;
  const tier = (item.serving_tier ?? "canonical").toLowerCase();
  const targetedBooster = asList(item.booster_target_queries).some((target) =>
    queryLower.includes(target.toLowerCase()),
  );
  const tierScore =
    tier === "booster"
      ? targetedBooster
        ? 0.05
        : -0.08
      : tier === "supporting"
        ? 0.02
        : 0.08;
  const hardNegativePenalty = asList(item.hard_negative_terms).some((term) =>
    queryLower.includes(term.toLowerCase()),
  )
    ? -0.05
    : 0;

  return (
    phraseBoost +
    surfaceBoost +
    categoryBoost +
    intentBoost +
    scenarioBoost +
    exactTermBoost +
    tierScore +
    hardNegativePenalty
  );
}

export function itemMatchesCategory(item: QAItem, category: string | null): boolean {
  if (!category) return true;
  const categories = asList(item.categories);
  return categories.length > 0
    ? categories.includes(category)
    : item.category === category;
}

// questionSignature imported from search-engine.ts

export function rerankResults(
  results: ReadonlyArray<{ item: QAItem; score: number }>,
  topK: number,
  query: string,
): ReadonlyArray<{ item: QAItem; score: number }> {
  const candidates = [...results];
  const selected: Array<{ item: QAItem; score: number }> = [];
  const terms = queryTerms(query);
  const queryCategories = inferQueryLabels(query, QUERY_CATEGORY_HINTS);

  while (candidates.length > 0 && selected.length < topK) {
    const selectedSigs = new Set(
      selected.map((result) => questionSignature(result.item.question)),
    );
    const selectedCategories = new Set(
      selected.flatMap((result) => asList(result.item.categories)),
    );
    const selectedIntents = new Set(
      selected.flatMap((result) => asList(result.item.intent_labels)),
    );
    const selectedTerms = new Set(
      selected.flatMap((result) => [
        ...matchedQueryTerms(result.item.retrieval_surface_text ?? "", terms),
      ]),
    );

    let bestIndex = 0;
    let bestScore = Number.NEGATIVE_INFINITY;
    for (let index = 0; index < candidates.length; index += 1) {
      const candidate = candidates[index]!;
      let adjusted = candidate.score;
      if (selectedSigs.has(questionSignature(candidate.item.question)))
        adjusted -= 0.25;
      const categories = asList(candidate.item.categories);
      const uncoveredQueryCategories = categories.filter(
        (category) =>
          queryCategories.has(category) && !selectedCategories.has(category),
      ).length;
      adjusted += categoryDiversityBoost(uncoveredQueryCategories);
      const intents = asList(candidate.item.intent_labels);
      if (
        intents.length > 0 &&
        intents.every((intent) => !selectedIntents.has(intent))
      )
        adjusted += 0.04;
      const candidateTerms = matchedQueryTerms(
        candidate.item.retrieval_surface_text ?? "",
        terms,
      );
      const novelTerms = [...candidateTerms].filter(
        (term) => !selectedTerms.has(term),
      ).length;
      adjusted += novelQueryTermBoost(novelTerms, terms.length);
      if (adjusted > bestScore) {
        bestScore = adjusted;
        bestIndex = index;
      }
    }
    if (!Number.isFinite(bestScore)) break;
    selected.push({ item: candidates[bestIndex]!.item, score: bestScore });
    candidates.splice(bestIndex, 1);
  }
  return selected;
}

