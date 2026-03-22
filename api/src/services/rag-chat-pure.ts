/**
 * RAG Chat — Pure Functions (Functional Core).
 *
 * Zero I/O, zero side effects. All functions are pure and testable
 * without mocking OpenAI, Supabase, or any external service.
 */

import type { QAItem } from "../store/qa-store.js";
import type { MessageMetadata } from "../schemas/chat.js";
import { buildMaturityContext, type MaturityLevel } from "../utils/maturity.js";
import type { RetrievalQuality } from "./retrieval-gate.js";

export const SYSTEM_PROMPT = `你是一位資深 SEO 顧問，根據以下 SEO 知識庫內容回答用戶的問題。
回答時請：
1. 直接針對問題給出具體建議，不要含糊其辭
2. 引用知識庫中的案例或數字來支撐建議，在該句末尾標注來源編號（如 [1]、[2]），編號對應知識庫條目順序
3. 若知識庫沒有相關資訊，誠實說明並提供通用建議
4. 回答使用繁體中文，技術術語可以保留英文
5. 控制在 500 字以內，重點優先，不要加追問段落`;

export const AMBIGUOUS_DISCLAIMER =
  "\n\n注意：以上回答基於相似度較低的知識庫結果，建議進一步確認資訊正確性。";

export const STALENESS_THRESHOLD_MONTHS = 18;

/** Check if a source date is stale (older than threshold). */
export function isStale(sourceDate: string): boolean {
  try {
    const d = new Date(sourceDate);
    if (isNaN(d.getTime())) return false;
    const ageMonths = (Date.now() - d.getTime()) / (1000 * 60 * 60 * 24 * 30);
    return ageMonths > STALENESS_THRESHOLD_MONTHS;
  } catch {
    return false;
  }
}

/** Format retrieved hits as numbered context for the system prompt. */
export function formatContext(
  hits: ReadonlyArray<{ readonly item: QAItem; readonly score: number }>,
): string {
  return hits
    .map(({ item, score }, idx) => {
      const stalenessNote =
        !item.evergreen && isStale(item.source_date)
          ? " [注意：此建議超過 18 個月，請確認是否仍適用]"
          : "";
      return (
        `[${idx + 1}] Q: ${item.question}\n` +
        `    A: ${item.answer}${stalenessNote}\n` +
        `    (來源: ${item.source_title || item.source_date}, 相似度: ${score.toFixed(2)})`
      );
    })
    .join("\n\n");
}

/** Build the system prompt with optional maturity context and retrieval quality warning. */
export function buildSystemPrompt(
  maturityLevel: MaturityLevel | null,
  retrievalQuality: RetrievalQuality,
): string {
  let prompt = SYSTEM_PROMPT;
  if (maturityLevel) {
    prompt += `\n\n--- 客戶成熟度脈絡 ---\n${buildMaturityContext(maturityLevel)}\n--- 脈絡結束 ---`;
  }
  if (retrievalQuality === "ambiguous") {
    prompt += "\n\n注意：檢索結果的相似度偏低，回答時請格外謹慎，僅根據有把握的內容作答。";
  }
  return prompt;
}

export interface BuildMessagesParams {
  readonly systemPrompt: string;
  readonly context: string;
  readonly history: ReadonlyArray<{ readonly role: string; readonly content: string }> | null;
  readonly message: string;
}

/** Build the messages array for the LLM call. */
export function buildMessages(
  params: BuildMessagesParams,
): ReadonlyArray<{ readonly role: "system" | "user" | "assistant"; readonly content: string }> {
  const messages: Array<{ role: "system" | "user" | "assistant"; content: string }> = [
    { role: "system", content: params.systemPrompt },
  ];

  if (params.context) {
    messages.push({
      role: "system",
      content: `--- 相關 SEO 知識庫 ---\n${params.context}\n--- 知識庫結束 ---`,
    });
  }

  if (params.history) {
    for (const h of params.history) {
      messages.push({
        role: h.role as "user" | "assistant",
        content: h.content,
      });
    }
  }

  messages.push({ role: "user", content: params.message });

  return messages;
}

export interface BuildMetadataParams {
  readonly model: string;
  readonly provider: string;
  readonly embeddingModel: string;
  readonly inputTokens: number | undefined;
  readonly outputTokens: number | undefined;
  readonly totalTokens: number | undefined;
  readonly reasoningTokens: number | undefined;
  readonly durationMs: number;
  readonly retrievalCount: number;
  readonly rerankerUsed: boolean;
  readonly cacheHit: boolean;
  readonly retrievalQuality: RetrievalQuality;
  readonly citationCount: number;
}

/** Build response metadata from LLM completion stats. */
export function buildMetadata(params: BuildMetadataParams): MessageMetadata {
  return {
    model: params.model,
    provider: params.provider,
    mode: "rag",
    embedding_model: params.embeddingModel,
    input_tokens: params.inputTokens,
    output_tokens: params.outputTokens,
    total_tokens: params.totalTokens,
    reasoning_tokens: params.reasoningTokens,
    duration_ms: params.durationMs,
    retrieval_count: params.retrievalCount,
    reranker_used: params.rerankerUsed,
    cache_hit: params.cacheHit,
    retrieval_quality: params.retrievalQuality,
    citation_count: params.citationCount,
  };
}

/** Append ambiguous disclaimer to answer if retrieval quality is ambiguous. */
export function appendDisclaimer(
  answer: string,
  retrievalQuality: RetrievalQuality,
): string {
  if (retrievalQuality === "ambiguous" && answer) {
    return answer + AMBIGUOUS_DISCLAIMER;
  }
  return answer;
}
