/**
 * Online scoring — attach evaluation scores to the current Laminar span.
 *
 * Ported from Python utils/laminar_scoring.py.  All functions are safe
 * to call when Laminar is not initialized — they silently skip.
 */

import { isLaminarInitialized } from "./observability.js";

/**
 * Attach a named numeric score to the current Laminar span.
 */
export async function scoreEvent(name: string, value: number): Promise<void> {
  if (!isLaminarInitialized()) return;
  try {
    const { Laminar } = await import("@lmnr-ai/lmnr");
    Laminar.event({ name, attributes: { value } });
  } catch {
    // Scoring failures must never crash the main path.
  }
}

interface SourceLike {
  readonly score?: number;
}

/**
 * Attach rule-based online scores to the current rag_chat span.
 *
 * Evaluators (no extra LLM call):
 *   answer_length    — 1.0 if answer > 50 chars, else 0.0
 *   has_sources      — 1.0 if >= 1 source retrieved, else 0.0
 *   top_source_score — cosine similarity of best source (0–1)
 *   source_count     — sources.length / 5, capped at 1.0
 */
export async function scoreRagResponse(
  answer: string | null,
  sources: readonly SourceLike[],
): Promise<void> {
  const text = answer ?? "";
  const events: Promise<void>[] = [
    scoreEvent("answer_length", text.trim().length > 50 ? 1 : 0),
    scoreEvent("has_sources", sources.length > 0 ? 1 : 0),
  ];

  if (sources.length > 0) {
    const topScore = sources[0]?.score ?? 0;
    events.push(scoreEvent("top_source_score", topScore));
    events.push(scoreEvent("source_count", Math.min(sources.length / 5, 1)));
  }

  await Promise.all(events);
}
