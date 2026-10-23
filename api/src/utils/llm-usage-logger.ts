/**
 * LLM usage logger — fire-and-forget 寫入 vocus-warehouse `app_llm_usage`。
 *
 * Records token usage, latency, and model per LLM call.
 * 非 PG 模式直接 no-op；寫入失敗不影響主流程。
 */

import { hasPg } from "../store/pg-client.js";
import { insertLLMUsage } from "../store/pg-llm-usage-store.js";

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
  if (!hasPg()) return;

  insertLLMUsage({
    endpoint: entry.endpoint,
    model: entry.model,
    input_tokens: entry.input_tokens,
    output_tokens: entry.output_tokens,
    latency_ms: entry.latency_ms,
  }).catch(() => {
    // Usage logging failures must never crash the main path
  });
}
