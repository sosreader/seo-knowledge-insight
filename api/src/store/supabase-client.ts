/**
 * Supabase REST client — thin wrapper around fetch().
 * Does NOT depend on @supabase/supabase-js to avoid adding a new dependency.
 * Uses Supabase REST API v1 directly.
 */

import { config } from "../config.js";

const SUPABASE_TIMEOUT_MS = 10_000;

export interface SupabaseClientConfig {
  readonly url: string;
  readonly anonKey: string;
}

/** Returns true when SUPABASE_URL + SUPABASE_ANON_KEY are set. */
export function hasSupabase(): boolean {
  return Boolean(config.SUPABASE_URL && config.SUPABASE_ANON_KEY);
}

/** Headers for Supabase REST API (read access). */
export function supabaseHeaders(key?: string): Record<string, string> {
  const apiKey = key ?? config.SUPABASE_ANON_KEY;
  return {
    apikey: apiKey,
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  };
}

/**
 * Call a Supabase RPC function via REST API.
 * Returns the parsed JSON response body.
 */
export async function supabaseRpc<T>(
  functionName: string,
  params: Record<string, unknown>,
): Promise<T[]> {
  const url = `${config.SUPABASE_URL}/rest/v1/rpc/${functionName}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: supabaseHeaders(),
    body: JSON.stringify(params),
    signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
  });

  if (!resp.ok) {
    throw new Error(`Supabase RPC ${functionName} failed (${resp.status})`);
  }

  const data = await resp.json() as T[];
  return data;
}

/**
 * Query Supabase table via REST API (SELECT).
 * queryString: e.g. "?select=id,question&category=eq.SEO"
 */
export async function supabaseSelect<T>(
  table: string,
  queryString: string = "",
): Promise<T[]> {
  const url = `${config.SUPABASE_URL}/rest/v1/${table}${queryString}`;
  const resp = await fetch(url, {
    method: "GET",
    headers: supabaseHeaders(),
    signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
  });

  if (!resp.ok) {
    throw new Error(`Supabase SELECT ${table} failed (${resp.status})`);
  }

  return resp.json() as Promise<T[]>;
}

/**
 * Count rows in a Supabase table.
 * Returns -1 on error.
 */
export async function supabaseCount(
  table: string,
  queryString: string = "",
): Promise<number> {
  const url = `${config.SUPABASE_URL}/rest/v1/${table}${queryString}`;
  const resp = await fetch(url, {
    method: "HEAD",
    headers: { ...supabaseHeaders(), Prefer: "count=exact" },
  });

  if (!resp.ok) return -1;
  const range = resp.headers.get("content-range") ?? "*/0";
  const total = range.split("/")[1];
  return total ? parseInt(total, 10) : -1;
}
