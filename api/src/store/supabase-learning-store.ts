/**
 * SupabaseLearningStore — Supabase-backed append-only log for feedback + search misses.
 *
 * Drop-in replacement for file-based learning-store.ts when SUPABASE_URL is set.
 */

import { supabaseHeaders } from "./supabase-client.js";
import { config } from "../config.js";

const SUPABASE_TIMEOUT_MS = 10_000;

export async function recordFeedbackSupabase(params: {
  query: string;
  qa_id: string;
  feedback: string;
  top_score?: number;
}): Promise<void> {
  const resp = await fetch(
    `${config.SUPABASE_URL}/rest/v1/learnings`,
    {
      method: "POST",
      headers: { ...supabaseHeaders(), Prefer: "return=minimal" },
      body: JSON.stringify({
        type: "feedback",
        query: params.query,
        qa_id: params.qa_id,
        feedback: params.feedback,
        top_score: params.top_score ?? null,
      }),
      signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
    },
  );

  if (!resp.ok) {
    console.warn(`Failed to record feedback to Supabase (${resp.status})`);
  }
}

export async function recordMissSupabase(params: {
  query: string;
  top_score: number;
  context: string;
}): Promise<void> {
  const resp = await fetch(
    `${config.SUPABASE_URL}/rest/v1/learnings`,
    {
      method: "POST",
      headers: { ...supabaseHeaders(), Prefer: "return=minimal" },
      body: JSON.stringify({
        type: "miss",
        query: params.query,
        top_score: params.top_score,
        context: params.context,
      }),
      signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
    },
  );

  if (!resp.ok) {
    console.warn(`Failed to record miss to Supabase (${resp.status})`);
  }
}
