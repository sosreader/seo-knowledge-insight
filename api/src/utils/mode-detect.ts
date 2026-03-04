/**
 * Mode detection — determines available features based on environment.
 */

import { config } from "../config.js";

export type SearchMode = "hybrid" | "keyword";
export type ChatMode = "full" | "context-only";

export function hasOpenAI(): boolean {
  return config.OPENAI_API_KEY.length > 0;
}
