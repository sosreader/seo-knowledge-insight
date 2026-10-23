/**
 * app_learning 寫入（回饋與 search miss，append-only）。
 * warehouse_rag 有 SELECT／INSERT／UPDATE，無 DELETE；表無 deleted_at。
 * 呼叫端（learning-store.ts）以 fire-and-forget 呼叫並接住錯誤。
 */

import { pgQuery } from "./pg-client.js";

const INSERT_SQL = `INSERT INTO app_learning (type, query, qa_id, feedback, top_score, context)
  VALUES ($1, $2, $3, $4, $5, $6)`;

export async function recordFeedbackPg(params: {
  readonly query: string;
  readonly qa_id: string;
  readonly feedback: string;
  readonly top_score?: number;
}): Promise<void> {
  await pgQuery(INSERT_SQL, [
    "feedback",
    params.query,
    params.qa_id,
    params.feedback,
    params.top_score ?? null,
    null,
  ]);
}

export async function recordMissPg(params: {
  readonly query: string;
  readonly top_score: number;
  readonly context: string;
}): Promise<void> {
  await pgQuery(INSERT_SQL, ["miss", params.query, null, null, params.top_score, params.context]);
}
