/**
 * Mode detection — determines available features based on environment.
 */

import { config } from "../config.js";

export type SearchMode = "hybrid" | "keyword";
export type ChatMode = "rag" | "context-only" | "agent";
export type RequestMode = "agent" | "rag";

export function hasOpenAI(): boolean {
  return config.OPENAI_API_KEY.length > 0;
}

export function isAgentEnabled(): boolean {
  if (config.AGENT_ENABLED === true) return true;
  if (config.AGENT_ENABLED === false) return false;
  // "auto": enable when OpenAI key is available
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
