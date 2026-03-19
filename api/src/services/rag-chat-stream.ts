/**
 * RAG Chat Streaming — SSE stream wrapper around ragChat pipeline.
 *
 * Reuses the same retrieval + quality gate logic from rag-chat.ts,
 * but streams the GPT response token-by-token via OpenAI streaming API.
 */

import OpenAI from "openai";
import { config } from "../config.js";
import { getEmbedding } from "./embedding.js";
import { qaStore, type QAItem } from "../store/qa-store.js";
import { itemToSource, type SourceItem, type MessageMetadata } from "../schemas/chat.js";
import { evaluateRetrievalQuality, validateCitations } from "./retrieval-gate.js";
import { recordMiss } from "../store/learning-store.js";
import { logLLMUsage } from "../utils/llm-usage-logger.js";
import type { MaturityLevel } from "../utils/maturity.js";
import {
  formatContext,
  buildSystemPrompt,
  buildMessages,
  AMBIGUOUS_DISCLAIMER,
} from "./rag-chat-pure.js";

let openaiClient: OpenAI | null = null;
function getOpenAI(): OpenAI {
  if (!openaiClient) {
    openaiClient = new OpenAI({ apiKey: config.OPENAI_API_KEY });
  }
  return openaiClient;
}

export interface StreamCallbacks {
  readonly onSources: (sources: readonly SourceItem[]) => Promise<void>;
  readonly onToken: (token: string) => Promise<void>;
  readonly onMetadata: (metadata: MessageMetadata) => Promise<void>;
  readonly onDone: () => Promise<void>;
  readonly onError: (error: string) => Promise<void>;
}

/**
 * Stream RAG chat response via callbacks.
 *
 * Flow: retrieve → quality gate → stream GPT tokens → metadata
 */
export async function ragChatStream(
  message: string,
  history: ReadonlyArray<{ role: string; content: string }> | null,
  callbacks: StreamCallbacks,
  maturityLevel: MaturityLevel | null = null,
): Promise<void> {
  const startMs = Date.now();

  try {
    // 1. Embed user question
    const queryVec = await getEmbedding(message);

    // 2. Hybrid search
    const retrieveK = config.ANTHROPIC_API_KEY ? config.CHAT_CONTEXT_K * 3 : config.CHAT_CONTEXT_K;
    const hits = await qaStore.hybridSearch(message, queryVec, retrieveK);

    // 2b. Re-ranking
    const { rerank } = await import("./reranker.js");
    const rerankerUsed = !!config.ANTHROPIC_API_KEY;
    const finalHits = rerankerUsed
      ? await rerank(message, hits as Array<{ item: QAItem; score: number }>, config.CHAT_CONTEXT_K)
      : hits.slice(0, config.CHAT_CONTEXT_K);

    const sources = finalHits.map(({ item, score }) => itemToSource(item, score));

    // 3. Quality gate
    const retrievalQuality = evaluateRetrievalQuality(finalHits);

    // Emit sources early so client can render them while waiting for tokens
    await callbacks.onSources(sources);

    // 3a. Incorrect — no good match
    if (retrievalQuality === "incorrect") {
      const topScore = finalHits.length > 0 ? finalHits[0].score : 0;
      recordMiss({ query: message, top_score: topScore, context: "rag-chat-stream" });
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

    // 4. Build context + messages (pure functions)
    const context = formatContext(finalHits);
    const systemPrompt = buildSystemPrompt(maturityLevel, retrievalQuality);
    const messages = buildMessages({ systemPrompt, context, history, message });

    // 5. Stream GPT response
    const stream = await getOpenAI().chat.completions.create({
      model: config.CHAT_MODEL,
      messages: messages as Array<{ role: "system" | "user" | "assistant"; content: string }>,
      temperature: 0.3,
      max_completion_tokens: 2000,
      stream: true,
      stream_options: { include_usage: true },
    });

    let fullAnswer = "";
    let inputTokens = 0;
    let outputTokens = 0;
    let modelName = config.CHAT_MODEL;

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content;
      if (delta) {
        fullAnswer += delta;
        await callbacks.onToken(delta);
      }

      // Usage comes in the final chunk
      if (chunk.usage) {
        inputTokens = chunk.usage.prompt_tokens ?? 0;
        outputTokens = chunk.usage.completion_tokens ?? 0;
      }
      if (chunk.model) {
        modelName = chunk.model;
      }
    }

    // 6. Post-processing
    const { citationCount } = validateCitations(fullAnswer, sources.length);

    // Ambiguous disclaimer (appended as final token)
    if (retrievalQuality === "ambiguous" && fullAnswer) {
      await callbacks.onToken(AMBIGUOUS_DISCLAIMER);
    }

    // Log LLM usage (fire-and-forget)
    logLLMUsage({
      endpoint: "/api/v1/chat/stream",
      model: modelName,
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      latency_ms: Date.now() - startMs,
    });

    await callbacks.onMetadata({
      model: modelName,
      provider: "openai",
      mode: "rag",
      embedding_model: config.OPENAI_EMBEDDING_MODEL,
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
