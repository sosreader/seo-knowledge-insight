/**
 * Retrieval Quality Gate — rule-based 3-tier threshold.
 *
 * Corrective RAG (CRAG) inspired: evaluate retrieval quality
 * BEFORE sending context to LLM, to prevent hallucinations
 * from low-quality search results.
 */

export type RetrievalQuality = "correct" | "ambiguous" | "incorrect";

const CORRECT_THRESHOLD = 0.6;
const AMBIGUOUS_THRESHOLD = 0.4;

/**
 * Evaluate retrieval quality based on top-1 score.
 *
 * - correct: topScore >= 0.6 — high-confidence match
 * - ambiguous: 0.4 <= topScore < 0.6 — uncertain, add disclaimer
 * - incorrect: topScore < 0.4 — no good match, fallback to context-only
 */
export function evaluateRetrievalQuality(
  hits: ReadonlyArray<{ readonly score: number }>,
): RetrievalQuality {
  if (hits.length === 0) return "incorrect";

  const topScore = hits[0].score;
  if (topScore >= CORRECT_THRESHOLD) return "correct";
  if (topScore >= AMBIGUOUS_THRESHOLD) return "ambiguous";
  return "incorrect";
}

/**
 * Validate inline citations [N] in the answer.
 * Returns count of unique valid citations and any out-of-range refs.
 */
export function validateCitations(
  answer: string,
  sourceCount: number,
): { readonly citationCount: number; readonly invalidRefs: readonly number[] } {
  const refs = [...answer.matchAll(/\[(\d+)\]/g)].map((m) =>
    parseInt(m[1], 10),
  );
  const uniqueRefs = [...new Set(refs)];
  const invalidRefs = uniqueRefs.filter((n) => n < 1 || n > sourceCount);
  return {
    citationCount: uniqueRefs.length - invalidRefs.length,
    invalidRefs,
  };
}
