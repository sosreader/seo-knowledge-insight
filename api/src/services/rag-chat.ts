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
import type { MaturityLevel } from "../utils/maturity.js";
import {
  formatContext,
  buildSystemPrompt,
  buildMessages,
  buildMetadata,
  appendDisclaimer,
} from "./rag-chat-pure.js";


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

  // 4. Build context + messages (pure functions)
  const context = formatContext(finalHits);
  const systemPrompt = buildSystemPrompt(maturityLevel, retrievalQuality);
  const messages = buildMessages({ systemPrompt, context, history, message });

  // 5. Call GPT (max_completion_tokens for reasoning models like gpt-5.x)
  const resp = await getOpenAI().chat.completions.create({
    model: config.CHAT_MODEL,
    messages: messages as Array<{ role: "system" | "user" | "assistant"; content: string }>,
    temperature: 0.3,
    max_completion_tokens: 2000,
  });

  const rawAnswer = resp.choices[0]?.message?.content ?? "";
  const sources = finalHits.map(({ item, score }) => itemToSource(item, score));

  // 5a. Append disclaimer for ambiguous retrieval
  const answer = appendDisclaimer(rawAnswer, retrievalQuality);

  // 5b. Validate inline citations
  const { citationCount } = validateCitations(answer, sources.length);

  // Online scoring (safe no-op when Laminar not initialized)
  await scoreRagResponse(answer, sources);

  const usage = resp.usage;
  const metadata = buildMetadata({
    model: resp.model ?? config.CHAT_MODEL,
    embeddingModel: config.OPENAI_EMBEDDING_MODEL,
    inputTokens: usage?.prompt_tokens,
    outputTokens: usage?.completion_tokens,
    totalTokens: usage?.total_tokens,
    reasoningTokens: (usage as unknown as Record<string, unknown>)?.completion_tokens_details
      ? ((usage as unknown as Record<string, unknown>).completion_tokens_details as Record<string, number>)?.reasoning_tokens
      : undefined,
    durationMs: Date.now() - startMs,
    retrievalCount: finalHits.length,
    rerankerUsed: rerankerUsed,
    cacheHit: false,
    retrievalQuality: retrievalQuality,
    citationCount: citationCount,
  });

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
