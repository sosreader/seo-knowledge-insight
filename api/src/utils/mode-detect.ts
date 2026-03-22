/**
 * Mode detection — determines available features based on environment.
 */

import { config } from "../config.js";

export type SearchMode = "hybrid" | "keyword";
export type ChatMode = "rag" | "context-only" | "agent";
export type RequestMode = "agent" | "rag";
export type ChatProvider = "openai" | "anthropic" | "none";

export function hasOpenAI(): boolean {
  return config.OPENAI_API_KEY.length > 0;
}

/** Check if a chat LLM is available (OpenAI or Anthropic, matching configured provider). */
export function hasChatLLM(): boolean {
  return getChatProvider() !== "none";
}

/** Resolve the effective chat LLM provider based on config + available keys. */
export function getChatProvider(): ChatProvider {
  if (config.CHAT_LLM_PROVIDER === "anthropic") {
    return config.ANTHROPIC_API_KEY.length > 0 ? "anthropic" : "none";
  }
  return hasOpenAI() ? "openai" : "none";
}

export function isAgentEnabled(): boolean {
  if (config.AGENT_ENABLED === true) return true;
  if (config.AGENT_ENABLED === false) return false;
  // "auto": enable when any chat LLM is available
  return hasChatLLM();
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
