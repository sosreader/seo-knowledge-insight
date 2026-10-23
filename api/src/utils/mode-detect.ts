/**
 * Mode detection — determines available features based on environment.
 */

import { config } from "../config.js";
import { isLlmEnabled } from "../services/llm-client.js";

export type SearchMode = "hybrid" | "keyword";
export type ChatMode = "rag" | "context-only" | "agent";
export type RequestMode = "agent" | "rag";

/** OpenAI 相容 LLM 可用（OPENAI_API_KEY 或 LLM_BASE_URL）。名稱沿用，語意見 services/llm-client.ts。 */
export function hasOpenAI(): boolean {
  return isLlmEnabled();
}

export function isAgentEnabled(): boolean {
  if (config.AGENT_ENABLED === true) return true;
  if (config.AGENT_ENABLED === false) return false;
  // "auto": enable when an OpenAI-compatible LLM is available
  return hasOpenAI();
}

/**
 * Resolve effective chat mode with three-layer priority:
 * 1. Request-level mode (highest)
 * 2. Server-level AGENT_ENABLED
 * 3. auto fallback
 */
export function resolveMode(requestMode?: RequestMode): "agent" | "rag" {
  if (requestMode) return requestMode;
  return isAgentEnabled() ? "agent" : "rag";
}
