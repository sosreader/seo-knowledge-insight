/**
 * OpenAI 相容 embedding wrapper — returns L2-normalized Float32Array.
 *
 * LLM disabled（無 OPENAI_API_KEY 且無 LLM_BASE_URL）時拋 llm_disabled（501），不打網路。
 * 有實際呼叫才記 app_llm_usage（endpoint=embedding）。
 */

import type OpenAI from "openai";
import { normalizeL2 } from "../utils/cosine-similarity.js";
import { observe } from "../utils/observability.js";
import { logLLMUsage } from "../utils/llm-usage-logger.js";
import { assertLlmEnabled, createLlmClient, llmEmbeddingModel } from "./llm-client.js";

let client: OpenAI | null = null;

function getClient(): OpenAI {
  if (!client) {
    client = createLlmClient();
  }
  return client;
}

async function getEmbeddingImpl(text: string): Promise<Float32Array> {
  assertLlmEnabled();
  const startMs = Date.now();
  const model = llmEmbeddingModel();
  const resp = await getClient().embeddings.create({
    model,
    input: text.trim(),
  });
  logLLMUsage({
    endpoint: "embedding",
    model: resp.model ?? model,
    input_tokens: resp.usage?.prompt_tokens ?? 0,
    output_tokens: 0,
    latency_ms: Date.now() - startMs,
  });
  const vec = new Float32Array(resp.data[0]!.embedding);
  return normalizeL2(vec);
}

export const getEmbedding = observe("get_embedding", getEmbeddingImpl);
