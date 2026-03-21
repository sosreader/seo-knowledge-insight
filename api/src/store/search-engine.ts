/**
 * SearchEngine — Hybrid Search (semantic + keyword boost + synonym + freshness).
 *
 * Translated from Python utils/search_engine.py SearchEngine class.
 *
 * Formula:
 *   base = semantic_weight * cosine_sim + keyword_boost + synonym_bonus
 *   final_score = base * freshness_score
 */

import {
  normalizeL2,
  normalizeRows,
  matrixDotVector,
} from "../utils/cosine-similarity.js";
import {
  computeKeywordBoostSingle,
  computeKeywordBoostMatrix,
  type KeywordBoostConfig,
} from "../utils/keyword-boost.js";
import {
  categoryDiversityBoost,
  matchedQueryTerms,
  novelQueryTermBoost,
  queryTerms,
} from "./query-term-utils.js";

export interface QADict {
  readonly id: string;
  readonly question: string;
  readonly answer: string;
  readonly keywords: readonly string[];
  readonly category: string;
  readonly primary_category?: string;
  readonly categories?: readonly string[];
  readonly intent_labels?: readonly string[];
  readonly scenario_tags?: readonly string[];
  readonly serving_tier?: string;
  readonly retrieval_phrases?: readonly string[];
  readonly retrieval_surface_text?: string;
  readonly booster_target_queries?: readonly string[];
  readonly hard_negative_terms?: readonly string[];
  readonly _enrichment?: {
    readonly synonyms?: readonly string[];
    readonly freshness_score?: number;
  };
}

export interface SearchResult {
  readonly qa: QADict;
  readonly score: number;
}

export interface SearchEngineConfig {
  readonly semanticWeight: number;
  readonly synonymBoost: number;
  readonly kwBoost: KeywordBoostConfig;
  readonly overRetrieveFactor: number; // Phase 3: over-retrieve multiplier (default 3)
}

const DEFAULT_CONFIG: SearchEngineConfig = {
  semanticWeight: 0.7,
  synonymBoost: 0.05,
  kwBoost: { boost: 0.1, maxHits: 3, partial: 0.05 },
  overRetrieveFactor: 3,
};

const MAX_QUERY_TOKENS = 100;
const MAX_METADATA_TEXT_LENGTH = 2000;

export const QUERY_INTENT_HINTS: Readonly<Record<string, readonly string[]>> = {
  diagnosis: ["異常", "下滑", "原因", "診斷", "why", "根因"],
  "root-cause": ["root cause", "根因", "canonical", "waf", "衝突"],
  implementation: ["如何", "修正", "設定", "實作", "schema", "標記"],
  measurement: [
    "ga",
    "ga4",
    "gsc",
    "ctr",
    "曝光",
    "點擊",
    "追蹤",
    "kpi",
    "ratio",
    "share",
    "佔比",
  ],
  reporting: ["報表", "週報", "監測", "趨勢"],
  "platform-decision": ["平台", "策略", "路徑", "作者"],
};

export const QUERY_SCENARIO_HINTS: Readonly<Record<string, readonly string[]>> = {
  discover: ["discover", "探索"],
  "google-news": ["google news", "news", "新聞"],
  "faq-rich-result": ["faq", "rich result", "搜尋外觀"],
  "ga4-attribution": ["ga4", "歸因", "unassigned"],
  "author-page": ["/user", "作者頁", "author"],
  "image-seo": ["image", "圖片", "alt", "縮圖"],
  "core-web-vitals": [
    "core web vitals",
    "cwv",
    "lcp",
    "cls",
    "行動版",
    "手機體驗",
  ],
  "video-seo": ["videoobject", "video appearance", "影片", "video"],
  "sitemap-api": ["sitemap", "url inspection", "inspection api", "cms api"],
  "ai-referral-traffic": [
    "chatgpt",
    "perplexity",
    "gemini",
    "ai 流量",
    "流量佔比",
  ],
};

export const QUERY_CATEGORY_HINTS: Readonly<Record<string, readonly string[]>> =
  {
    技術SEO: [
      "schema",
      "結構化資料",
      "core web vitals",
      "lcp",
      "cls",
      "ttfb",
      "amp",
      "videoobject",
      "video appearance",
      "sitemap",
      "url inspection",
      "inspection api",
      "mobile seo",
      "行動版",
      "手機",
      "json-ld",
      "key moments",
      "image pack",
      "圖片搜尋",
    ],
    索引與檢索: ["索引", "coverage", "googlebot", "canonical", "檢索未索引"],
    搜尋表現分析: [
      "ctr",
      "曝光",
      "點擊",
      "serp",
      "search console",
      "kpi",
      "品牌",
      "非品牌",
      "brand",
      "non-brand",
      "轉換率",
      "可見度",
    ],
    GA與數據追蹤: [
      "ga",
      "ga4",
      "追蹤",
      "歸因",
      "direct",
      "chatgpt",
      "perplexity",
      "gemini",
      "ratio",
      "share",
      "佔比",
    ],
    Discover與AMP: ["discover", "amp", "news", "max-image-preview"],
    內容策略: ["內容", "文章", "eeat", "供給", "更新", "意圖"],
    連結策略: ["連結", "內部連結", "錨點", "反向連結", "錨文本"],
    平台策略: ["平台", "作者", "/user", "路徑", "cms", "創作者", "自訂網域"],
    演算法與趨勢: [
      "演算法",
      "趨勢",
      "ai",
      "gemini",
      "perplexity",
      "chatgpt",
      "ai overview",
      "ai search",
      "llm",
    ],
  };

export function asList(
  value: readonly string[] | string | null | undefined,
): readonly string[] {
  if (Array.isArray(value)) return value.filter(Boolean);
  if (typeof value === "string" && value.trim().length > 0)
    return [value.trim()];
  return [];
}

function qaCategories(
  qa: Pick<QADict, "categories" | "primary_category" | "category">,
): readonly string[] {
  const categories = asList(qa.categories);
  if (categories.length > 0) return categories;
  const primary = qa.primary_category ?? qa.category;
  return primary ? [primary] : [];
}

function qaIntents(qa: Pick<QADict, "intent_labels">): readonly string[] {
  return asList(qa.intent_labels);
}

export function questionSignature(question: string): string {
  return question
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff]+/g, "")
    .slice(0, 120);
}

export function tokenize(text: string): Set<string> {
  const tokens = text
    .slice(0, MAX_METADATA_TEXT_LENGTH)
    .toLowerCase()
    .split(/\s+/)
    .filter((token) => token.length >= 2)
    .slice(0, MAX_QUERY_TOKENS);
  return new Set(tokens);
}

export function inferQueryLabels(
  query: string,
  hintMap: Readonly<Record<string, readonly string[]>>,
): ReadonlySet<string> {
  const queryLower = query.toLowerCase();
  const labels = new Set<string>();
  for (const [label, hints] of Object.entries(hintMap)) {
    if (hints.some((hint) => queryLower.includes(hint))) {
      labels.add(label);
    }
  }
  return labels;
}

function intersectionSize(
  left: ReadonlySet<string>,
  right: ReadonlySet<string>,
): number {
  let hits = 0;
  for (const item of left) {
    if (right.has(item)) hits += 1;
  }
  return hits;
}

function servingTierPrior(query: string, qa: QADict): number {
  const tier = (qa.serving_tier ?? "canonical").toLowerCase();
  if (tier === "booster") {
    const targets = asList(qa.booster_target_queries);
    const isTargeted = targets.some((target) =>
      query.toLowerCase().includes(target.toLowerCase()),
    );
    return isTargeted ? 0.05 : -0.08;
  }
  if (tier === "supporting") return 0.02;
  return 0.08;
}

function metadataFeatureScore(query: string, qa: QADict): number {
  const terms = queryTerms(query);
  const queryTokens = tokenize(query);
  const surfaceTokens = tokenize(qa.retrieval_surface_text ?? "");
  const queryCategories = inferQueryLabels(query, QUERY_CATEGORY_HINTS);
  const queryIntents = inferQueryLabels(query, QUERY_INTENT_HINTS);
  const queryScenarios = inferQueryLabels(query, QUERY_SCENARIO_HINTS);

  const phraseBoost =
    computeKeywordBoostSingle(
      query,
      asList(qa.retrieval_phrases),
      DEFAULT_CONFIG.kwBoost,
    ) * 2.0;
  const surfaceBoost = intersectionSize(queryTokens, surfaceTokens) * 0.03;
  const categoryBoost =
    intersectionSize(queryCategories, new Set(qaCategories(qa))) * 0.08;
  const intentBoost =
    intersectionSize(queryIntents, new Set(qaIntents(qa))) * 0.06;
  const scenarioBoost =
    intersectionSize(queryScenarios, new Set(asList(qa.scenario_tags))) * 0.05;
  const exactTermBoost =
    matchedQueryTerms(qa.retrieval_surface_text ?? "", terms).size * 0.04;
  const hardNegativePenalty = asList(qa.hard_negative_terms).some((term) =>
    query.toLowerCase().includes(term.toLowerCase()),
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
    servingTierPrior(query, qa) +
    hardNegativePenalty
  );
}

function matchesCategoryFilter(qa: QADict, category: string | null): boolean {
  if (!category) return true;
  return qaCategories(qa).includes(category);
}

function rerankCandidates(
  results: readonly SearchResult[],
  topK: number,
  query: string,
): readonly SearchResult[] {
  const candidates = [...results];
  const selected: SearchResult[] = [];
  const terms = queryTerms(query);
  const queryCategories = inferQueryLabels(query, QUERY_CATEGORY_HINTS);

  while (candidates.length > 0 && selected.length < topK) {
    const selectedSigs = new Set(
      selected.map((item) => questionSignature(item.qa.question)),
    );
    const selectedCategories = new Set(
      selected.flatMap((item) => qaCategories(item.qa)),
    );
    const selectedIntents = new Set(
      selected.flatMap((item) => qaIntents(item.qa)),
    );
    const selectedTerms = new Set(
      selected.flatMap((item) => [
        ...matchedQueryTerms(item.qa.retrieval_surface_text ?? "", terms),
      ]),
    );

    let bestIndex = 0;
    let bestScore = Number.NEGATIVE_INFINITY;

    for (let index = 0; index < candidates.length; index += 1) {
      const candidate = candidates[index]!;
      let adjustedScore = candidate.score;
      const signature = questionSignature(candidate.qa.question);
      if (selectedSigs.has(signature)) adjustedScore -= 0.25;

      const categories = qaCategories(candidate.qa);
      const uncoveredQueryCategories = categories.filter(
        (category) =>
          queryCategories.has(category) && !selectedCategories.has(category),
      ).length;
      adjustedScore += categoryDiversityBoost(uncoveredQueryCategories);

      const intents = qaIntents(candidate.qa);
      if (
        intents.length > 0 &&
        intents.every((intent) => !selectedIntents.has(intent))
      ) {
        adjustedScore += 0.04;
      }

      const candidateTerms = matchedQueryTerms(
        candidate.qa.retrieval_surface_text ?? "",
        terms,
      );
      const novelTerms = [...candidateTerms].filter(
        (term) => !selectedTerms.has(term),
      ).length;
      adjustedScore += novelQueryTermBoost(novelTerms, terms.length);

      if (adjustedScore > bestScore) {
        bestScore = adjustedScore;
        bestIndex = index;
      }
    }

    if (!Number.isFinite(bestScore)) break;
    selected.push({ qa: candidates[bestIndex]!.qa, score: bestScore });
    candidates.splice(bestIndex, 1);
  }

  return selected;
}

export class SearchEngine {
  private readonly qaPairs: readonly QADict[];
  private readonly embNorm: Float32Array; // flat [N x dim], L2-normalized
  private readonly rows: number;
  private readonly cols: number;
  private readonly config: SearchEngineConfig;

  // Pre-computed enrichment vectors (length N)
  private readonly synonymBoostVec: Float32Array;
  private readonly freshnessVec: Float32Array;

  constructor(
    qaPairs: readonly QADict[],
    embeddings: Float32Array,
    embeddingDim: number,
    config: Partial<SearchEngineConfig> = {},
  ) {
    const rows = qaPairs.length;
    if (rows * embeddingDim !== embeddings.length) {
      throw new Error(
        `qaPairs (${rows}) * embeddingDim (${embeddingDim}) !== embeddings length (${embeddings.length})`,
      );
    }

    this.qaPairs = qaPairs;
    this.rows = rows;
    this.cols = embeddingDim;
    this.config = { ...DEFAULT_CONFIG, ...config };

    // L2-normalize embedding rows
    this.embNorm = normalizeRows(embeddings, rows, embeddingDim);

    // Pre-compute synonym boost vector
    this.synonymBoostVec = new Float32Array(rows);
    for (let i = 0; i < rows; i++) {
      const synonyms = qaPairs[i]!._enrichment?.synonyms;
      this.synonymBoostVec[i] =
        synonyms && synonyms.length > 0 ? this.config.synonymBoost : 0;
    }

    // Pre-compute freshness vector
    this.freshnessVec = new Float32Array(rows);
    for (let i = 0; i < rows; i++) {
      this.freshnessVec[i] = qaPairs[i]!._enrichment?.freshness_score ?? 1.0;
    }
  }

  /**
   * Single-query hybrid search.
   */
  search(
    query: string,
    queryEmbedding: Float32Array,
    topK: number = 5,
    category: string | null = null,
    minScore: number = 0.2,
  ): readonly SearchResult[] {
    const scores = this.hybridScores(query, queryEmbedding);

    // Category mask
    if (category) {
      for (let i = 0; i < this.rows; i++) {
        if (!matchesCategoryFilter(this.qaPairs[i]!, category)) {
          scores[i] = -1;
        }
      }
    }

    // Get top-K indices
    const indices = topKIndices(scores, topK * this.config.overRetrieveFactor);

    const results: SearchResult[] = [];
    for (const idx of indices) {
      if (scores[idx]! >= minScore) {
        results.push({ qa: this.qaPairs[idx]!, score: scores[idx]! });
      }
    }
    return rerankCandidates(results, topK, query);
  }

  /**
   * Compute hybrid scores for a single query. Returns Float32Array of shape [N].
   */
  private hybridScores(query: string, queryEmb: Float32Array): Float32Array {
    const qNorm = normalizeL2(queryEmb);
    const semanticScores = matrixDotVector(
      this.embNorm,
      qNorm,
      this.rows,
      this.cols,
    );

    const scores = new Float32Array(this.rows);
    for (let i = 0; i < this.rows; i++) {
      const kwBoost = computeKeywordBoostSingle(
        query,
        this.qaPairs[i]!.keywords,
        this.config.kwBoost,
      );

      const synonymBonus = this.computeSynonymBonusSingle(query, i);
      const featureScore = metadataFeatureScore(query, this.qaPairs[i]!);

      const base =
        semanticScores[i]! * this.config.semanticWeight +
        kwBoost +
        synonymBonus +
        featureScore;

      scores[i] = base * this.freshnessVec[i]!;
    }
    return scores;
  }

  /**
   * Compute synonym bonus for a single (query, qa_index) pair.
   */
  private computeSynonymBonusSingle(query: string, qaIdx: number): number {
    const synonyms = this.qaPairs[qaIdx]!._enrichment?.synonyms;
    if (!synonyms || synonyms.length === 0) return 0;

    const queryLower = query.toLowerCase();
    for (const syn of synonyms) {
      const synLower = syn.toLowerCase();
      if (queryLower.includes(synLower) || synLower.includes(queryLower)) {
        return this.config.synonymBoost;
      }
    }
    return 0;
  }

  /**
   * Over-retrieve for re-ranking: returns topK * overRetrieveFactor candidates.
   * Used by Phase 3 reranker.
   */
  searchOverRetrieve(
    query: string,
    queryEmbedding: Float32Array,
    topK: number = 5,
    category: string | null = null,
    minScore: number = 0.1,
  ): readonly SearchResult[] {
    return this.search(
      query,
      queryEmbedding,
      topK * this.config.overRetrieveFactor,
      category,
      minScore,
    );
  }

  /**
   * Keyword-only search (no embedding required).
   * Reuses keyword boost + synonym + freshness, skipping semantic scores.
   */
  keywordOnlySearch(
    query: string,
    topK: number = 5,
    category: string | null = null,
    minScore: number = 0.01,
  ): readonly SearchResult[] {
    const scores = new Float32Array(this.rows);
    for (let i = 0; i < this.rows; i++) {
      const kwBoost = computeKeywordBoostSingle(
        query,
        this.qaPairs[i]!.keywords,
        this.config.kwBoost,
      );
      const synonymBonus = this.computeSynonymBonusSingle(query, i);
      const featureScore = metadataFeatureScore(query, this.qaPairs[i]!);
      scores[i] =
        (kwBoost + synonymBonus + featureScore) * this.freshnessVec[i]!;
    }

    if (category) {
      for (let i = 0; i < this.rows; i++) {
        if (!matchesCategoryFilter(this.qaPairs[i]!, category)) {
          scores[i] = -1;
        }
      }
    }

    const indices = topKIndices(scores, topK * this.config.overRetrieveFactor);
    const results = indices
      .filter((idx) => scores[idx]! >= minScore)
      .map((idx) => ({ qa: this.qaPairs[idx]!, score: scores[idx]! }));
    return rerankCandidates(results, topK, query);
  }
}

/**
 * Get indices of top-K highest values in a Float32Array, sorted descending.
 */
export function topKIndices(arr: Float32Array, k: number): number[] {
  const indexed: Array<{ idx: number; val: number }> = [];
  for (let i = 0; i < arr.length; i++) {
    indexed.push({ idx: i, val: arr[i]! });
  }
  indexed.sort((a, b) => b.val - a.val);
  return indexed.slice(0, k).map((x) => x.idx);
}
