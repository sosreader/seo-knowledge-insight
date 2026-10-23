/**
 * app_llm_usage（LLM 呼叫記帳）。warehouse_rag 只有 SELECT／INSERT（append-only）；表無 deleted_at。
 */

import { isoColumn, pgQuery } from "./pg-client.js";

export interface LLMUsageRow {
  readonly endpoint: string;
  readonly model: string;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly latency_ms: number;
  readonly created_at: string;
}

export interface LLMUsageInsert {
  readonly endpoint: string;
  readonly model: string;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly latency_ms: number;
}

export async function insertLLMUsage(entry: LLMUsageInsert): Promise<void> {
  await pgQuery(
    `INSERT INTO app_llm_usage (endpoint, model, input_tokens, output_tokens, latency_ms)
      VALUES ($1, $2, $3, $4, $5)`,
    [entry.endpoint, entry.model, entry.input_tokens, entry.output_tokens, entry.latency_ms],
  );
}

/** since 之後的記帳，新到舊，最多 limit 筆（與 Supabase 版 /pipeline/llm-usage 相同）。 */
export async function listLLMUsageSince(sinceIso: string, limit: number): Promise<readonly LLMUsageRow[]> {
  return pgQuery<LLMUsageRow>(
    `SELECT endpoint, model, input_tokens, output_tokens, latency_ms, ${isoColumn("created_at")}
       FROM app_llm_usage
      WHERE created_at >= $1::timestamptz
      ORDER BY created_at DESC
      LIMIT $2`,
    [sinceIso, limit],
  );
}
