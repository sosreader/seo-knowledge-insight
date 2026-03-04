/**
 * Reranker — Claude haiku re-ranks search candidates.
 *
 * Strategy: over-retrieve topK*3 → send to Claude haiku → return top-K.
 * Falls back to original ordering on error or when Anthropic key unavailable.
 *
 * Phase 3 of RAG improvement plan.
 */

import { config } from "../config.js";
import type { QAItem } from "../store/qa-store.js";

interface RerankCandidate {
  readonly stable_id: string;
  readonly question: string;
  readonly category: string;
  readonly score: number;
}

interface RerankResult {
  readonly stable_id: string;
  readonly rank: number;
  readonly reason: string;
}

/**
 * Rerank candidates using Claude haiku.
 * Returns reranked QAItems (top-K).
 */
export async function rerank(
  query: string,
  candidates: ReadonlyArray<{ item: QAItem; score: number }>,
  topK: number,
): Promise<ReadonlyArray<{ item: QAItem; score: number }>> {
  if (candidates.length === 0) return candidates;
  if (candidates.length <= topK) return candidates;

  // Require Anthropic API key
  if (!config.ANTHROPIC_API_KEY) {
    return candidates.slice(0, topK);
  }

  const candidateList: RerankCandidate[] = candidates.map((c) => ({
    stable_id: c.item.id,
    question: c.item.question.slice(0, 150),
    category: c.item.category,
    score: c.score,
  }));

  const prompt = buildRerankPrompt(query, candidateList, topK);

  try {
    const ranked = await callClaude(prompt, topK);
    if (!ranked || ranked.length === 0) {
      return candidates.slice(0, topK);
    }

    // Reorder candidates according to reranked order
    const idToCandidate = new Map(candidates.map((c) => [c.item.id, c]));
    const reranked = ranked
      .map((r) => idToCandidate.get(r.stable_id))
      .filter((c): c is { item: QAItem; score: number } => c !== undefined);

    // Append any candidates not in reranked list (safety net)
    const rankedIds = new Set(ranked.map((r) => r.stable_id));
    const remaining = candidates.filter((c) => !rankedIds.has(c.item.id));
    return [...reranked, ...remaining].slice(0, topK);
  } catch (err) {
    console.error("[reranker] Error during reranking, using original order:", err);
    return candidates.slice(0, topK);
  }
}

function buildRerankPrompt(
  query: string,
  candidates: RerankCandidate[],
  topK: number,
): string {
  const candidateXml = candidates
    .map(
      (c, i) =>
        `<candidate id="${i + 1}" stable_id="${c.stable_id}">
  <question>${c.question}</question>
  <category>${c.category}</category>
  <initial_score>${c.score.toFixed(4)}</initial_score>
</candidate>`,
    )
    .join("\n");

  return `你是一位 SEO 知識檢索的排名評估員。

使用者查詢：<query>${query}</query>

以下是候選 Q&A（按初始分數排序）：
<candidates>
${candidateXml}
</candidates>

請評估每個候選項目與查詢的相關性，選出最相關的 ${topK} 個，按相關度排序。

輸出 JSON 陣列，格式如下（只輸出 JSON，不要額外解釋）：
[
  {"stable_id": "xxx", "rank": 1, "reason": "最相關原因（10字內）"},
  {"stable_id": "yyy", "rank": 2, "reason": "相關原因"}
]

要求：
- 只回傳最相關的 ${topK} 個
- stable_id 必須來自候選清單
- 以繁體中文描述 reason`;
}

async function callClaude(prompt: string, topK: number): Promise<RerankResult[] | null> {
  // Dynamic import to avoid loading SDK when not needed
  const { default: Anthropic } = await import("@anthropic-ai/sdk").catch(() => ({ default: null }));
  if (!Anthropic) {
    console.warn("[reranker] @anthropic-ai/sdk not installed");
    return null;
  }

  const client = new Anthropic({ apiKey: config.ANTHROPIC_API_KEY });
  const resp = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 512,
    messages: [{ role: "user", content: prompt }],
  });

  const content = resp.content[0];
  if (!content || content.type !== "text") return null;

  const text = content.text.trim();

  // Extract JSON from response (Claude sometimes adds backticks)
  const jsonMatch = text.match(/\[[\s\S]*\]/);
  if (!jsonMatch) return null;

  const parsed = JSON.parse(jsonMatch[0]);
  if (!Array.isArray(parsed)) return null;

  return parsed
    .filter(
      (item): item is RerankResult =>
        typeof item === "object" &&
        typeof item.stable_id === "string" &&
        typeof item.rank === "number",
    )
    .sort((a, b) => a.rank - b.rank)
    .slice(0, topK);
}
