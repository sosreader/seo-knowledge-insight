/**
 * Anthropic RAG Chat Streaming — SSE stream via Claude streaming API.
 *
 * Parallel implementation to rag-chat-stream.ts (OpenAI).
 * Uses Anthropic's messages.stream() helper.
 */

import { config } from "../config.js";
import { qaStore, type QAItem } from "../store/qa-store.js";
import { itemToSource } from "../schemas/chat.js";
import { evaluateRetrievalQuality, validateCitations } from "./retrieval-gate.js";
import { recordMiss } from "../store/learning-store.js";
import { logLLMUsage } from "../utils/llm-usage-logger.js";
import { hasOpenAI } from "../utils/mode-detect.js";
import type { MaturityLevel } from "../utils/maturity.js";
import type { StreamCallbacks } from "./rag-chat-stream.js";
import {
  formatContext,
  AMBIGUOUS_DISCLAIMER,
} from "./rag-chat-pure.js";
import { buildAnthropicSystem, buildAnthropicMessages } from "./anthropic-chat-pure.js";

/** Retrieve hits: hybrid or keyword-only. */
async function retrieveHits(message: string, retrieveK: number) {
  if (hasOpenAI()) {
    const { getEmbedding } = await import("./embedding.js");
    const queryVec = await getEmbedding(message);
    return qaStore.hybridSearch(message, queryVec, retrieveK);
  }
  return qaStore.keywordSearch(message, retrieveK);
}

export async function anthropicRagChatStream(
  message: string,
  history: ReadonlyArray<{ role: string; content: string }> | null,
  callbacks: StreamCallbacks,
  maturityLevel: MaturityLevel | null = null,
): Promise<void> {
  const startMs = Date.now();

  try {
    // 1. Retrieve
    const retrieveK = config.ANTHROPIC_API_KEY ? config.CHAT_CONTEXT_K * 3 : config.CHAT_CONTEXT_K;
    const hits = await retrieveHits(message, retrieveK);

    // 1b. Re-ranking
    const { rerank } = await import("./reranker.js");
    const rerankerUsed = !!config.ANTHROPIC_API_KEY;
    const finalHits = rerankerUsed
      ? await rerank(message, hits as Array<{ item: QAItem; score: number }>, config.CHAT_CONTEXT_K)
      : hits.slice(0, config.CHAT_CONTEXT_K);

    const sources = finalHits.map(({ item, score }) => itemToSource(item, score));

    // 2. Quality gate
    const retrievalQuality = evaluateRetrievalQuality(finalHits);
    await callbacks.onSources(sources);

    if (retrievalQuality === "incorrect") {
      const topScore = finalHits.length > 0 ? finalHits[0].score : 0;
      recordMiss({ query: message, top_score: topScore, context: "anthropic-rag-chat-stream" });
      await callbacks.onMetadata({
        mode: "context-only",
        duration_ms: Date.now() - startMs,
        retrieval_count: finalHits.length,
        reranker_used: rerankerUsed,
        retrieval_quality: "incorrect",
      });
      await callbacks.onDone();
      return;
    }

    // 3. Build context + system
    const context = formatContext(finalHits);
    const system = buildAnthropicSystem(maturityLevel, retrievalQuality, context);
    const messages = buildAnthropicMessages(history, message);

    // 4. Stream Claude response
    const { default: Anthropic } = await import("@anthropic-ai/sdk");
    const client = new Anthropic({ apiKey: config.ANTHROPIC_API_KEY });

    const stream = client.messages.stream({
      model: config.CHAT_ANTHROPIC_MODEL,
      max_tokens: 2000,
      system,
      messages,
      temperature: 0.3,
    });

    let fullAnswer = "";

    for await (const event of stream) {
      if (
        event.type === "content_block_delta" &&
        event.delta.type === "text_delta"
      ) {
        fullAnswer += event.delta.text;
        await callbacks.onToken(event.delta.text);
      }
    }

    // 5. Final message for usage
    const finalMsg = await stream.finalMessage();
    const inputTokens = finalMsg.usage.input_tokens;
    const outputTokens = finalMsg.usage.output_tokens;
    const modelName = finalMsg.model;

    // 6. Post-processing
    const { citationCount } = validateCitations(fullAnswer, sources.length);

    if (retrievalQuality === "ambiguous" && fullAnswer) {
      await callbacks.onToken(AMBIGUOUS_DISCLAIMER);
    }

    logLLMUsage({
      endpoint: "/api/v1/chat/stream",
      model: modelName,
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      latency_ms: Date.now() - startMs,
    });

    const embeddingModel = hasOpenAI() ? config.OPENAI_EMBEDDING_MODEL : "none";

    await callbacks.onMetadata({
      model: modelName,
      provider: "anthropic",
      mode: "rag",
      embedding_model: embeddingModel,
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      total_tokens: inputTokens + outputTokens,
      duration_ms: Date.now() - startMs,
      retrieval_count: finalHits.length,
      reranker_used: rerankerUsed,
      retrieval_quality: retrievalQuality,
      citation_count: citationCount,
    });

    await callbacks.onDone();
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    await callbacks.onError(msg);
  }
}
