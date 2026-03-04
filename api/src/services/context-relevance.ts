/**
 * Context Relevance — NVIDIA-style semantic evaluation metric.
 *
 * Measures how relevant the retrieved Q&A contexts are to the user query.
 * No ground truth required: only needs query + retrieved_contexts.
 *
 * Score: 0-1 (0 = irrelevant, 0.5 = partial, 1 = fully relevant)
 * LLM judge: Anthropic Claude haiku (dynamic import, same pattern as reranker.ts)
 * Falls back to freshness_score heuristic when API key is unavailable.
 */

import { config } from "../config.js";
import type { QAItem } from "../store/qa-store.js";

export interface ContextRelevanceResult {
  readonly score: number;
  readonly reason: string;
  readonly per_context: ReadonlyArray<{ readonly id: string; readonly score: number }>;
}

interface ClaudeJudgeResponse {
  overall_score: number;
  reason: string;
  per_context: Array<{ id: string; score: number }>;
}

/**
 * Evaluate how relevant retrieved contexts are for the given query.
 * Falls back to heuristic scoring when Anthropic API key is absent.
 */
export async function contextRelevance(
  query: string,
  contexts: ReadonlyArray<QAItem>,
): Promise<ContextRelevanceResult> {
  if (contexts.length === 0) {
    return { score: 0, reason: "No contexts retrieved", per_context: [] };
  }

  if (!config.ANTHROPIC_API_KEY) {
    return fallbackScore(contexts);
  }

  try {
    return await callClaude(query, contexts);
  } catch (err) {
    console.error("[context-relevance] Claude call failed, using heuristic fallback:", err);
    return fallbackScore(contexts);
  }
}

/** Heuristic fallback: use freshness_score as relevance proxy when LLM unavailable. */
function fallbackScore(contexts: ReadonlyArray<QAItem>): ContextRelevanceResult {
  const per_context = contexts.map((c) => ({
    id: c.id,
    score: Math.min(1, Math.max(0, c.freshness_score ?? 0.5)),
  }));
  const avgScore = per_context.reduce((sum, c) => sum + c.score, 0) / per_context.length;
  return {
    score: Math.round(avgScore * 100) / 100,
    reason: "Fallback: LLM unavailable, using freshness_score heuristic",
    per_context,
  };
}

async function callClaude(
  query: string,
  contexts: ReadonlyArray<QAItem>,
): Promise<ContextRelevanceResult> {
  // Dynamic import to avoid loading SDK when not needed
  const { default: Anthropic } = await import("@anthropic-ai/sdk").catch(() => ({ default: null }));
  if (!Anthropic) {
    console.warn("[context-relevance] @anthropic-ai/sdk not installed, using fallback");
    return fallbackScore(contexts);
  }

  const client = new Anthropic({ apiKey: config.ANTHROPIC_API_KEY });
  const prompt = buildPrompt(query, contexts);

  const resp = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 512,
    messages: [{ role: "user", content: prompt }],
  });

  const content = resp.content[0];
  if (!content || content.type !== "text") {
    return fallbackScore(contexts);
  }

  const text = content.text.trim();

  // Extract JSON object from response (Claude may add extra text or backticks)
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    return fallbackScore(contexts);
  }

  let parsed: ClaudeJudgeResponse;
  try {
    parsed = JSON.parse(jsonMatch[0]);
  } catch {
    return fallbackScore(contexts);
  }

  if (typeof parsed.overall_score !== "number") {
    return fallbackScore(contexts);
  }

  return {
    score: Math.min(1, Math.max(0, parsed.overall_score)),
    reason: typeof parsed.reason === "string" ? parsed.reason : "",
    per_context: Array.isArray(parsed.per_context)
      ? parsed.per_context
          .filter((c): c is { id: string; score: number } =>
            typeof c === "object" && typeof c.id === "string" && typeof c.score === "number",
          )
          .map((c) => ({ id: c.id, score: Math.min(1, Math.max(0, c.score)) }))
      : [],
  };
}

/** Escape characters that could break XML prompt structure. */
function escapeXml(text: string): string {
  return text.replace(/[<>&"']/g, (c) => {
    switch (c) {
      case "<": return "&lt;";
      case ">": return "&gt;";
      case "&": return "&amp;";
      case '"': return "&quot;";
      case "'": return "&apos;";
      default: return c;
    }
  });
}

function buildPrompt(query: string, contexts: ReadonlyArray<QAItem>): string {
  const safeQuery = escapeXml(query);
  const contextXml = contexts
    .map(
      (c, i) =>
        `<context id="${i + 1}" stable_id="${c.id}">
  <question>${escapeXml(c.question.slice(0, 200))}</question>
  <category>${escapeXml(c.category)}</category>
</context>`,
    )
    .join("\n");

  return `你是一位 SEO 知識檢索品質評估員，評估「檢索到的 Q&A 片段與使用者查詢的語意相關性」。

使用者查詢：<query>${safeQuery}</query>

檢索到的 Q&A 片段：
<contexts>
${contextXml}
</contexts>

請評估每個片段與查詢的語意相關程度：
- 1.0 = 完全相關（直接回答查詢）
- 0.5 = 部分相關（有關聯但不直接）
- 0.0 = 完全不相關

輸出 JSON（只輸出 JSON，不要額外說明）：
{
  "overall_score": 0.82,
  "reason": "整體評估原因（30字內）",
  "per_context": [
    {"id": "stable_id_here", "score": 0.9}
  ]
}

要求：
- overall_score 為所有片段相關性的加權平均（0-1）
- id 使用 stable_id（context 標籤的 stable_id 屬性）
- reason 以繁體中文描述
- 所有分數必須在 0-1 之間`;
}
