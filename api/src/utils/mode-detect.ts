/**
 * Mode detection — determines available features based on environment.
 */

import { config } from "../config.js";

export type SearchMode = "hybrid" | "keyword";
export type ChatMode = "full" | "context-only";

export function hasOpenAI(): boolean {
  return config.OPENAI_API_KEY.length > 0;
}

export function isAgentEnabled(): boolean {
  if (config.AGENT_ENABLED === true) return true;
  if (config.AGENT_ENABLED === false) return false;
  // "auto": enable when OpenAI key is available
  return hasOpenAI();
}
