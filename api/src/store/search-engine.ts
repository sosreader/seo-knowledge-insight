/**
 * SearchEngine — Hybrid Search (semantic + keyword boost + synonym + freshness).
 *
 * Translated from Python utils/search_engine.py SearchEngine class.
 *
 * Formula:
 *   base = semantic_weight * cosine_sim + keyword_boost + synonym_bonus
 *   final_score = base * freshness_score
 */

import { normalizeL2, normalizeRows, matrixDotVector } from "../utils/cosine-similarity.js";
import {
  computeKeywordBoostSingle,
  computeKeywordBoostMatrix,
  type KeywordBoostConfig,
} from "../utils/keyword-boost.js";

export interface QADict {
  readonly id: string;
  readonly question: string;
  readonly answer: string;
  readonly keywords: readonly string[];
  readonly category: string;
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
}

const DEFAULT_CONFIG: SearchEngineConfig = {
  semanticWeight: 0.7,
  synonymBoost: 0.05,
  kwBoost: { boost: 0.1, maxHits: 3, partial: 0.05 },
};

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
      this.synonymBoostVec[i] = synonyms && synonyms.length > 0 ? this.config.synonymBoost : 0;
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
        if (this.qaPairs[i]!.category !== category) {
          scores[i] = -1;
        }
      }
    }

    // Get top-K indices
    const indices = topKIndices(scores, topK);

    const results: SearchResult[] = [];
    for (const idx of indices) {
      if (scores[idx]! >= minScore) {
        results.push({ qa: this.qaPairs[idx]!, score: scores[idx]! });
      }
    }
    return results;
  }

  /**
   * Compute hybrid scores for a single query. Returns Float32Array of shape [N].
   */
  private hybridScores(query: string, queryEmb: Float32Array): Float32Array {
    const qNorm = normalizeL2(queryEmb);
    const semanticScores = matrixDotVector(this.embNorm, qNorm, this.rows, this.cols);

    const scores = new Float32Array(this.rows);
    for (let i = 0; i < this.rows; i++) {
      const kwBoost = computeKeywordBoostSingle(
        query,
        this.qaPairs[i]!.keywords,
        this.config.kwBoost,
      );

      const synonymBonus = this.computeSynonymBonusSingle(query, i);

      const base =
        semanticScores[i]! * this.config.semanticWeight + kwBoost + synonymBonus;

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
}

/**
 * Get indices of top-K highest values in a Float32Array, sorted descending.
 */
function topKIndices(arr: Float32Array, k: number): number[] {
  const indexed: Array<{ idx: number; val: number }> = [];
  for (let i = 0; i < arr.length; i++) {
    indexed.push({ idx: i, val: arr[i]! });
  }
  indexed.sort((a, b) => b.val - a.val);
  return indexed.slice(0, k).map((x) => x.idx);
}
