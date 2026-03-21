/**
 * Keyword boost scoring — 4-layer matching algorithm.
 *
 * Translated from Python utils/search_engine.py compute_keyword_boost().
 *
 * Matching layers (priority order):
 *   1. Exact: keyword appears in query
 *   2. Token forward: query token appears in keyword
 *   3. Token reverse: keyword token appears in query
 *   4. Bigram weak hit: first 2 chars of keyword in query (partial score)
 */

export interface KeywordBoostConfig {
  readonly boost: number;
  readonly maxHits: number;
  readonly partial: number;
}

const DEFAULT_CONFIG: KeywordBoostConfig = {
  boost: 0.1,
  maxHits: 3,
  partial: 0.05,
};

function tokenize(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .split(/\s+/)
      .filter((t) => t.length >= 2),
  );
}

/**
 * Compute keyword boost for a single (query, qa) pair.
 */
export function computeKeywordBoostSingle(
  query: string,
  keywords: readonly string[],
  cfg: KeywordBoostConfig = DEFAULT_CONFIG,
): number {
  const queryLower = query.toLowerCase();
  const queryTokens = tokenize(query);

  let totalHits = 0;
  for (const kw of keywords) {
    const kwLower = kw.toLowerCase();
    const kwTokens = tokenize(kw);

    if (kwLower.length > 0 && queryLower.includes(kwLower)) {
      totalHits += 2.0;
    } else if ([...queryTokens].some((t) => kwLower.includes(t))) {
      totalHits += 1;
    } else if ([...kwTokens].some((t) => queryLower.includes(t))) {
      totalHits += 1;
    } else if (kwLower.length >= 2 && queryLower.includes(kwLower.slice(0, 2))) {
      totalHits += cfg.boost > 0 ? cfg.partial / cfg.boost : 0;
    }
  }

  if (totalHits <= 0) return 0;
  return cfg.boost * Math.min(totalHits, cfg.maxHits);
}

export interface QAPairForKeyword {
  readonly keywords: readonly string[];
}

/**
 * Compute keyword boost matrix (queries x qa_pairs).
 * Returns flat Float32Array of shape [queries.length * qaPairs.length].
 */
export function computeKeywordBoostMatrix(
  queries: readonly string[],
  qaPairs: readonly QAPairForKeyword[],
  cfg: KeywordBoostConfig = DEFAULT_CONFIG,
): Float32Array {
  const nQ = queries.length;
  const nQA = qaPairs.length;
  const matrix = new Float32Array(nQ * nQA);

  for (let qi = 0; qi < nQ; qi++) {
    const offset = qi * nQA;
    for (let ji = 0; ji < nQA; ji++) {
      matrix[offset + ji] = computeKeywordBoostSingle(queries[qi]!, qaPairs[ji]!.keywords, cfg);
    }
  }

  return matrix;
}
