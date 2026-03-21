/**
 * Supabase REST client — thin wrapper around fetch().
 * Does NOT depend on @supabase/supabase-js to avoid adding a new dependency.
 * Uses Supabase REST API v1 directly.
 */

import { config } from "../config.js";

export const SUPABASE_TIMEOUT_MS = 10_000;

export interface SupabaseClientConfig {
  readonly url: string;
  readonly anonKey: string;
}

async function readErrorBody(resp: Response): Promise<string> {
  try {
    const body = await resp.text();
    // Sanitize: truncate to prevent leaking internal schema details
    const safe = body ? body.slice(0, 200) : "";
    return safe ? `: ${safe}` : "";
  } catch {
    return "";
  }
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
    const body = await readErrorBody(resp);
    throw new Error(
      `Supabase RPC ${functionName} failed (${resp.status})${body}`,
    );
  }

  const data = (await resp.json()) as T[];
  return data;
}

/**
 * Query Supabase table via REST API (SELECT).
 * queryString: e.g. "?select=id,question&category=eq.SEO"
 */
export async function supabaseSelect<T>(
  table: string,
  queryString: string = "",
  timeoutMs: number = SUPABASE_TIMEOUT_MS,
): Promise<T[]> {
  const url = `${config.SUPABASE_URL}/rest/v1/${table}${queryString}`;
  const resp = await fetch(url, {
    method: "GET",
    headers: supabaseHeaders(),
    signal: AbortSignal.timeout(timeoutMs),
  });

  if (!resp.ok) {
    const body = await readErrorBody(resp);
    throw new Error(`Supabase SELECT ${table} failed (${resp.status})${body}`);
  }

  return resp.json() as Promise<T[]>;
}

/**
 * Insert or upsert rows into a Supabase table via REST API.
 * Uses service key for write access (bypasses RLS).
 */
export async function supabaseInsert<T>(
  table: string,
  rows: readonly Record<string, unknown>[],
  options: { upsert?: boolean; onConflict?: string } = {},
): Promise<T[]> {
  const url = `${config.SUPABASE_URL}/rest/v1/${table}`;
  const prefer = options.upsert
    ? "return=representation,resolution=merge-duplicates"
    : "return=representation";
  const headers: Record<string, string> = {
    ...supabaseHeaders(config.SUPABASE_SERVICE_KEY || config.SUPABASE_ANON_KEY),
    Prefer: prefer,
  };
  if (options.upsert && options.onConflict) {
    headers["Prefer"] += `,on_conflict=${options.onConflict}`;
  }
  const resp = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(rows),
    signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
  });

  if (!resp.ok) {
    const body = await readErrorBody(resp);
    throw new Error(
      `Supabase INSERT ${table} failed (${resp.status})${body}`,
    );
  }

  return resp.json() as Promise<T[]>;
}

/**
 * Delete rows from a Supabase table via REST API.
 * Uses service key for write access (bypasses RLS).
 */
export async function supabaseDelete(
  table: string,
  queryString: string,
): Promise<void> {
  const url = `${config.SUPABASE_URL}/rest/v1/${table}${queryString}`;
  const resp = await fetch(url, {
    method: "DELETE",
    headers: supabaseHeaders(
      config.SUPABASE_SERVICE_KEY || config.SUPABASE_ANON_KEY,
    ),
    signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
  });

  if (!resp.ok) {
    const body = await readErrorBody(resp);
    throw new Error(
      `Supabase DELETE ${table} failed (${resp.status})${body}`,
    );
  }
}

/**
 * Patch rows in a Supabase table via REST API (partial update).
 * Uses service key for write access (bypasses RLS).
 */
export async function supabasePatch(
  table: string,
  queryString: string,
  data: Record<string, unknown>,
): Promise<void> {
  const url = `${config.SUPABASE_URL}/rest/v1/${table}${queryString}`;
  const resp = await fetch(url, {
    method: "PATCH",
    headers: supabaseHeaders(
      config.SUPABASE_SERVICE_KEY || config.SUPABASE_ANON_KEY,
    ),
    body: JSON.stringify(data),
    signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
  });

  if (!resp.ok) {
    const body = await readErrorBody(resp);
    throw new Error(`Supabase PATCH ${table} failed (${resp.status})${body}`);
  }
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
