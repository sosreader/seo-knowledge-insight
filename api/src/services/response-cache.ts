/**
 * Exact-match response cache — sha256(normalizedQuery) as key.
 *
 * 存在 vocus-warehouse `app_response_cache`（warehouse_rag 有 SELECT／INSERT／UPDATE／DELETE，
 * 以 query_hash upsert）。非 PG 模式（本機檔案模式）直接 no-op；任何 DB 錯誤都不影響主流程。
 */

import { createHash } from "node:crypto";
import { hasPg, pgQuery } from "../store/pg-client.js";
import { scoreEvent } from "../utils/laminar-scoring.js";

const UPSERT_SQL = `INSERT INTO app_response_cache (query_hash, query_text, response, expires_at, hit_count)
  VALUES ($1, $2, $3::jsonb, $4::timestamptz, 0)
  ON CONFLICT (query_hash) DO UPDATE SET
    query_text = EXCLUDED.query_text, response = EXCLUDED.response,
    expires_at = EXCLUDED.expires_at, hit_count = 0`;

export function normalizeQuery(query: string): string {
  return query.toLowerCase().trim().replace(/\s+/g, " ");
}

export function hashQuery(normalized: string): string {
  return createHash("sha256").update(normalized).digest("hex");
}

interface CachedRow {
  readonly response: Record<string, unknown>;
}

/**
 * Look up a cached response by query hash.
 * Returns null on miss, error, or when not in PG mode.
 */
export async function lookupCache(
  queryHash: string,
): Promise<Record<string, unknown> | null> {
  if (!hasPg()) return null;

  try {
    const rows = await pgQuery<CachedRow>(
      "SELECT response FROM app_response_cache WHERE query_hash = $1 AND expires_at > now() LIMIT 1",
      [queryHash],
    );

    const hit = rows.length > 0;
    await scoreEvent("cache_hit", hit ? 1 : 0);
    return hit ? rows[0]!.response : null;
  } catch {
    // Cache failures must never crash the main path
    return null;
  }
}

/**
 * Save a response to cache. Upserts on query_hash conflict.
 */
export async function saveCache(
  queryText: string,
  queryHash: string,
  response: Record<string, unknown>,
  ttlHours: number = 2,
): Promise<void> {
  if (!hasPg()) return;

  const expiresAt = new Date(
    Date.now() + ttlHours * 60 * 60 * 1000,
  ).toISOString();

  try {
    await pgQuery(UPSERT_SQL, [queryHash, queryText, JSON.stringify(response), expiresAt]);
  } catch {
    // Cache save failures must never crash the main path
  }
}
