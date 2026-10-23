/**
 * LLM 開關與 OpenAI 相容 client 的單一入口。
 *
 * - 啟用條件：OPENAI_API_KEY 或 LLM_BASE_URL 任一有值。兩者皆空（rag-api 線上現況）→ disabled，
 *   呼叫端拿到 FeatureUnavailableError("llm_disabled")，error handler 轉成 501。
 * - LLM_BASE_URL 指向 OpenAI 相容端點（本機 Ollama 的 /v1）；Ollama 不驗 key，
 *   但 OpenAI SDK 要求非空 apiKey，所以用 LOCAL_LLM_PLACEHOLDER_KEY 佔位（不是憑證）。
 * - 模型名：LLM_CHAT_MODEL／LLM_EMBEDDING_MODEL 優先，空值沿用 CHAT_MODEL／OPENAI_EMBEDDING_MODEL。
 */

import OpenAI from "openai";
import { config } from "../config.js";
import { FeatureUnavailableError } from "../utils/feature-errors.js";

export const LOCAL_LLM_PLACEHOLDER_KEY = "local-llm-no-key";

const trimmed = (value: unknown): string => (typeof value === "string" ? value.trim() : "");

export function llmBaseUrl(): string {
  return trimmed(config.LLM_BASE_URL);
}

export function isLlmEnabled(): boolean {
  return trimmed(config.OPENAI_API_KEY) !== "" || llmBaseUrl() !== "";
}

export function assertLlmEnabled(): void {
  if (!isLlmEnabled()) throw new FeatureUnavailableError("llm_disabled");
}

export function llmChatModel(): string {
  return trimmed(config.LLM_CHAT_MODEL) || config.CHAT_MODEL;
}

export function llmEmbeddingModel(): string {
  return trimmed(config.LLM_EMBEDDING_MODEL) || config.OPENAI_EMBEDDING_MODEL;
}

export interface LlmClientOptions {
  readonly apiKey: string;
  readonly baseURL?: string;
}

export function llmClientOptions(): LlmClientOptions {
  const apiKey = trimmed(config.OPENAI_API_KEY) || LOCAL_LLM_PLACEHOLDER_KEY;
  const baseURL = llmBaseUrl();
  return baseURL ? { apiKey, baseURL } : { apiKey };
}

/** 建立 OpenAI 相容 client；LLM disabled 時拋 llm_disabled（不建立、不打網路）。 */
export function createLlmClient(): OpenAI {
  assertLlmEnabled();
  return new OpenAI(llmClientOptions());
}
