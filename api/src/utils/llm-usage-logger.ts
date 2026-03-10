/**
 * LLM usage logger — fire-and-forget write to Supabase `llm_usage` table.
 *
 * Records token usage, latency, and model per LLM call.
 * Gracefully no-ops when Supabase is unavailable.
 */

import { hasSupabase, supabaseInsert } from "../store/supabase-client.js";

export interface LLMUsageEntry {
  readonly endpoint: string;
  readonly model: string;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly latency_ms: number;
}

/**
 * Log a single LLM API call. Fire-and-forget — does not block the response.
 */
export function logLLMUsage(entry: LLMUsageEntry): void {
  if (!hasSupabase()) return;

  supabaseInsert("llm_usage", [
    {
      endpoint: entry.endpoint,
      model: entry.model,
      input_tokens: entry.input_tokens,
      output_tokens: entry.output_tokens,
      latency_ms: entry.latency_ms,
    },
  ]).catch(() => {
    // Usage logging failures must never crash the main path
  });
}
