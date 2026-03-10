/**
 * Exact-match response cache — sha256(normalizedQuery) as key.
 *
 * Uses Supabase `response_cache` table. Gracefully no-ops when
 * Supabase is not configured.
 */

import { createHash } from "node:crypto";
import { hasSupabase, supabaseSelect, supabaseInsert } from "../store/supabase-client.js";
import { scoreEvent } from "../utils/laminar-scoring.js";

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
 * Returns null on miss, error, or when Supabase is unavailable.
 */
export async function lookupCache(
  queryHash: string,
): Promise<Record<string, unknown> | null> {
  if (!hasSupabase()) return null;

  try {
    const now = new Date().toISOString();
    const rows = await supabaseSelect<CachedRow>(
      "response_cache",
      `?query_hash=eq.${queryHash}&expires_at=gt.${now}&select=response&limit=1`,
    );

    const hit = rows.length > 0;
    await scoreEvent("cache_hit", hit ? 1 : 0);
    return hit ? rows[0].response : null;
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
  if (!hasSupabase()) return;

  const expiresAt = new Date(
    Date.now() + ttlHours * 60 * 60 * 1000,
  ).toISOString();

  try {
    await supabaseInsert("response_cache", [
      {
        query_hash: queryHash,
        query_text: queryText,
        response,
        expires_at: expiresAt,
        hit_count: 0,
      },
    ], { upsert: true, onConflict: "query_hash" });
  } catch {
    // Cache save failures must never crash the main path
  }
}
