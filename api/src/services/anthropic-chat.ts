/**
 * Anthropic RAG Chat — hybrid search + Claude completion.
 *
 * Parallel implementation to rag-chat.ts (OpenAI).
 * When OpenAI key is unavailable, falls back to keyword-only search.
 */

import { config } from "../config.js";
import { qaStore, type QAItem } from "../store/qa-store.js";
import { itemToSource, type ChatResponse } from "../schemas/chat.js";
import { observe } from "../utils/observability.js";
import { scoreRagResponse } from "../utils/laminar-scoring.js";
import { normalizeQuery, hashQuery, lookupCache, saveCache } from "./response-cache.js";
import { logLLMUsage } from "../utils/llm-usage-logger.js";
import { evaluateRetrievalQuality, validateCitations, type RetrievalQuality } from "./retrieval-gate.js";
import { recordMiss } from "../store/learning-store.js";
import { hasOpenAI } from "../utils/mode-detect.js";
import type { MaturityLevel } from "../utils/maturity.js";
import {
  formatContext,
  buildMetadata,
  appendDisclaimer,
} from "./rag-chat-pure.js";
import { buildAnthropicSystem, buildAnthropicMessages } from "./anthropic-chat-pure.js";

/** Retrieve hits: hybrid search when OpenAI available, keyword-only otherwise. */
async function retrieveHits(message: string, retrieveK: number) {
  if (hasOpenAI()) {
    const { getEmbedding } = await import("./embedding.js");
    const queryVec = await getEmbedding(message);
    return qaStore.hybridSearch(message, queryVec, retrieveK);
  }
  return qaStore.keywordSearch(message, retrieveK);
}

export async function anthropicRagChat(
  message: string,
  history: ReadonlyArray<{ role: string; content: string }> | null = null,
  maturityLevel: MaturityLevel | null = null,
): Promise<ChatResponse> {
  const startMs = Date.now();

  // 0. Cache lookup
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

  // 1. Retrieve (hybrid or keyword-only)
  const retrieveK = config.ANTHROPIC_API_KEY ? config.CHAT_CONTEXT_K * 3 : config.CHAT_CONTEXT_K;
  const hits = await retrieveHits(message, retrieveK);

  // 1b. Re-ranking
  const { rerank } = await import("./reranker.js");
  const rerankerUsed = !!config.ANTHROPIC_API_KEY;
  const finalHits = rerankerUsed
    ? await rerank(message, hits as Array<{ item: QAItem; score: number }>, config.CHAT_CONTEXT_K)
    : hits.slice(0, config.CHAT_CONTEXT_K);

  // 2. Retrieval quality gate
  const retrievalQuality: RetrievalQuality = evaluateRetrievalQuality(finalHits);

  if (retrievalQuality === "incorrect") {
    const topScore = finalHits.length > 0 ? finalHits[0].score : 0;
    recordMiss({ query: message, top_score: topScore, context: "anthropic-rag-chat" });
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

  // 3. Build context + system prompt
  const context = formatContext(finalHits);
  const system = buildAnthropicSystem(maturityLevel, retrievalQuality, context);
  const messages = buildAnthropicMessages(history, message);

  // 4. Call Claude
  const { default: Anthropic } = await import("@anthropic-ai/sdk");
  const client = new Anthropic({ apiKey: config.ANTHROPIC_API_KEY });

  const resp = await client.messages.create({
    model: config.CHAT_ANTHROPIC_MODEL,
    max_tokens: 2000,
    system,
    messages,
    temperature: 0.3,
  });

  const rawAnswer = resp.content[0]?.type === "text" ? resp.content[0].text : "";
  const sources = finalHits.map(({ item, score }) => itemToSource(item, score));

  const answer = appendDisclaimer(rawAnswer, retrievalQuality);
  const { citationCount } = validateCitations(answer, sources.length);

  await scoreRagResponse(answer, sources);

  const embeddingModel = hasOpenAI() ? config.OPENAI_EMBEDDING_MODEL : "none";
  const metadata = buildMetadata({
    model: resp.model,
    provider: "anthropic",
    embeddingModel,
    inputTokens: resp.usage.input_tokens,
    outputTokens: resp.usage.output_tokens,
    totalTokens: resp.usage.input_tokens + resp.usage.output_tokens,
    reasoningTokens: undefined,
    durationMs: Date.now() - startMs,
    retrievalCount: finalHits.length,
    rerankerUsed,
    cacheHit: false,
    retrievalQuality,
    citationCount,
  });

  logLLMUsage({
    endpoint: "/api/v1/chat",
    model: resp.model,
    input_tokens: resp.usage.input_tokens,
    output_tokens: resp.usage.output_tokens,
    latency_ms: Date.now() - startMs,
  });

  const result: ChatResponse = { answer, sources, mode: "rag", metadata };

  // Cache (first message only)
  if ((!history || history.length === 0) && !maturityLevel) {
    const normalized = normalizeQuery(message);
    const qHash = hashQuery(normalized);
    saveCache(message, qHash, result as unknown as Record<string, unknown>);
  }

  return result;
}

export const anthropicRagChatObserved = observe("anthropic_rag_chat", anthropicRagChat);
