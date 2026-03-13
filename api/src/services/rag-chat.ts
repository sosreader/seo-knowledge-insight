/**
 * RAG Chat — embedding query + GPT completion.
 *
 * Translated from Python app/core/chat.py
 */

import OpenAI from "openai";
import { config } from "../config.js";
import { getEmbedding } from "./embedding.js";
import { qaStore, type QAItem } from "../store/qa-store.js";
import { itemToSource, type ChatResponse, type MessageMetadata } from "../schemas/chat.js";
import { observe } from "../utils/observability.js";
import { scoreRagResponse } from "../utils/laminar-scoring.js";
import { normalizeQuery, hashQuery, lookupCache, saveCache } from "./response-cache.js";
import { logLLMUsage } from "../utils/llm-usage-logger.js";
import { evaluateRetrievalQuality, validateCitations, type RetrievalQuality } from "./retrieval-gate.js";
import { recordMiss } from "../store/learning-store.js";
import { buildMaturityContext, type MaturityLevel } from "../utils/maturity.js";

const SYSTEM_PROMPT = `你是一位資深 SEO 顧問，根據以下 SEO 知識庫內容回答用戶的問題。
回答時請：
1. 直接針對問題給出具體建議，不要含糊其辭
2. 引用知識庫中的案例或數字來支撐建議，在該句末尾標注來源編號（如 [1]、[2]），編號對應知識庫條目順序
3. 若知識庫沒有相關資訊，誠實說明並提供通用建議
4. 回答使用繁體中文，技術術語可以保留英文
5. 控制在 500 字以內，重點優先，不要加追問段落`;

const AMBIGUOUS_DISCLAIMER =
  "\n\n注意：以上回答基於相似度較低的知識庫結果，建議進一步確認資訊正確性。";

const STALENESS_THRESHOLD_MONTHS = 18;

function isStale(sourceDate: string): boolean {
  try {
    const d = new Date(sourceDate);
    if (isNaN(d.getTime())) return false;
    const ageMonths = (Date.now() - d.getTime()) / (1000 * 60 * 60 * 24 * 30);
    return ageMonths > STALENESS_THRESHOLD_MONTHS;
  } catch {
    return false;
  }
}

function formatContext(hits: ReadonlyArray<{ item: QAItem; score: number }>): string {
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


let openaiClient: OpenAI | null = null;
function getOpenAI(): OpenAI {
  if (!openaiClient) {
    openaiClient = new OpenAI({ apiKey: config.OPENAI_API_KEY });
  }
  return openaiClient;
}

export async function ragChat(
  message: string,
  history: ReadonlyArray<{ role: string; content: string }> | null = null,
  maturityLevel: MaturityLevel | null = null,
): Promise<ChatResponse> {
  const startMs = Date.now();

  // 0. Cache lookup (only for first message without history, skip when maturity-aware)
  if ((!history || history.length === 0) && !maturityLevel) {
    const normalized = normalizeQuery(message);
    const qHash = hashQuery(normalized);
    const cached = await lookupCache(qHash);
    if (cached) {
      const cachedResp = cached as unknown as ChatResponse;
      return {
        ...cachedResp,
        metadata: { ...cachedResp.metadata, cache_hit: true, duration_ms: Date.now() - startMs },
      };
    }
  }

  // 1. Embed user question
  const queryVec = await getEmbedding(message);

  // 2. Hybrid search (over-retrieve for reranker)
  const retrieveK = config.ANTHROPIC_API_KEY ? config.CHAT_CONTEXT_K * 3 : config.CHAT_CONTEXT_K;
  const hits = await qaStore.hybridSearch(message, queryVec, retrieveK);

  // 2b. Re-ranking (Phase 3)
  const { rerank } = await import("./reranker.js");
  const rerankerUsed = !!config.ANTHROPIC_API_KEY;
  const finalHits = rerankerUsed
    ? await rerank(message, hits as Array<{ item: QAItem; score: number }>, config.CHAT_CONTEXT_K)
    : hits.slice(0, config.CHAT_CONTEXT_K);

  // 3. Retrieval quality gate (CRAG-inspired)
  const retrievalQuality: RetrievalQuality = evaluateRetrievalQuality(finalHits);

  // 3a. Incorrect — no good match, return context-only without LLM call
  if (retrievalQuality === "incorrect") {
    const topScore = finalHits.length > 0 ? finalHits[0].score : 0;
    recordMiss({ query: message, top_score: topScore, context: "rag-chat" });
    const sources = finalHits.map(({ item, score }) => itemToSource(item, score));
    return {
      answer: null,
      sources,
      mode: "context-only",
      metadata: {
        mode: "context-only",
        duration_ms: Date.now() - startMs,
        retrieval_count: finalHits.length,
        reranker_used: rerankerUsed,
        retrieval_quality: "incorrect",
      },
    };
  }

  // 4. Build context
  const context = formatContext(finalHits);

  // 5. Assemble messages
  let systemPrompt = SYSTEM_PROMPT;
  if (maturityLevel) {
    systemPrompt += `\n\n--- 客戶成熟度脈絡 ---\n${buildMaturityContext(maturityLevel)}\n--- 脈絡結束 ---`;
  }
  if (retrievalQuality === "ambiguous") {
    systemPrompt += "\n\n注意：檢索結果的相似度偏低，回答時請格外謹慎，僅根據有把握的內容作答。";
  }

  const messages: Array<{ role: "system" | "user" | "assistant"; content: string }> = [
    { role: "system", content: systemPrompt },
  ];

  if (context) {
    messages.push({
      role: "system",
      content: `--- 相關 SEO 知識庫 ---\n${context}\n--- 知識庫結束 ---`,
    });
  }

  if (history) {
    for (const h of history) {
      messages.push({
        role: h.role as "user" | "assistant",
        content: h.content,
      });
    }
  }

  messages.push({ role: "user", content: message });

  // 6. Call GPT (max_completion_tokens for reasoning models like gpt-5.x)
  const resp = await getOpenAI().chat.completions.create({
    model: config.CHAT_MODEL,
    messages,
    temperature: 0.3,
    max_completion_tokens: 2000,
  });

  let answer = resp.choices[0]?.message?.content ?? "";
  const sources = finalHits.map(({ item, score }) => itemToSource(item, score));

  // 6a. Append disclaimer for ambiguous retrieval
  if (retrievalQuality === "ambiguous" && answer) {
    answer = answer + AMBIGUOUS_DISCLAIMER;
  }

  // 6b. Validate inline citations
  const { citationCount } = validateCitations(answer, sources.length);

  // Online scoring (safe no-op when Laminar not initialized)
  await scoreRagResponse(answer, sources);

  const usage = resp.usage;
  const metadata: MessageMetadata = {
    model: resp.model ?? config.CHAT_MODEL,
    provider: "openai",
    mode: "rag",
    embedding_model: config.OPENAI_EMBEDDING_MODEL,
    input_tokens: usage?.prompt_tokens,
    output_tokens: usage?.completion_tokens,
    total_tokens: usage?.total_tokens,
    reasoning_tokens: (usage as unknown as Record<string, unknown>)?.completion_tokens_details
      ? ((usage as unknown as Record<string, unknown>).completion_tokens_details as Record<string, number>)?.reasoning_tokens
      : undefined,
    duration_ms: Date.now() - startMs,
    retrieval_count: finalHits.length,
    reranker_used: rerankerUsed,
    cache_hit: false,
    retrieval_quality: retrievalQuality,
    citation_count: citationCount,
  };

  // Log LLM usage (fire-and-forget)
  logLLMUsage({
    endpoint: "/api/v1/chat",
    model: resp.model ?? config.CHAT_MODEL,
    input_tokens: usage?.prompt_tokens ?? 0,
    output_tokens: usage?.completion_tokens ?? 0,
    latency_ms: Date.now() - startMs,
  });

  const result: ChatResponse = { answer, sources, mode: "rag", metadata };

  // Save to cache (first message only, skip when maturity-aware, fire-and-forget)
  if ((!history || history.length === 0) && !maturityLevel) {
    const normalized = normalizeQuery(message);
    const qHash = hashQuery(normalized);
    saveCache(message, qHash, result as unknown as Record<string, unknown>);
  }

  return result;
}

/** Observed version — wraps ragChat as a Laminar span. */
export const ragChatObserved = observe("rag_chat", ragChat);
