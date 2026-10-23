/**
 * app_learning 寫入（回饋與 search miss，append-only）。
 * warehouse_rag 有 SELECT／INSERT／UPDATE，無 DELETE；表無 deleted_at。
 * 回饋：呼叫端 await 並回傳讀回的列（錯誤交給 error handler → 503／504）。
 * miss：fire-and-forget（learning-store.ts 接住錯誤）。
 */

import { isoColumn, pgQuery } from "./pg-client.js";

const INSERT_SQL = `INSERT INTO app_learning (type, query, qa_id, feedback, top_score, context)
  VALUES ($1, $2, $3, $4, $5, $6)`;

/** 寫入後讀回的回饋列（RETURNING）；id 是 bigint，pg 以字串回傳。 */
export interface StoredFeedback {
  readonly id: string;
  readonly query: string;
  readonly qa_id: string;
  readonly feedback: string;
  readonly top_score: number | null;
  readonly created_at: string;
}

const FEEDBACK_RETURNING = ` RETURNING id::text AS id, query, qa_id, feedback, top_score, ${isoColumn("created_at")}`;

export async function recordFeedbackPg(params: {
  readonly query: string;
  readonly qa_id: string;
  readonly feedback: string;
  readonly top_score?: number;
}): Promise<StoredFeedback> {
  const rows = await pgQuery<StoredFeedback>(INSERT_SQL + FEEDBACK_RETURNING, [
    "feedback",
    params.query,
    params.qa_id,
    params.feedback,
    params.top_score ?? null,
    null,
  ]);
  return rows[0]!;
}

export async function recordMissPg(params: {
  readonly query: string;
  readonly top_score: number;
  readonly context: string;
}): Promise<void> {
  await pgQuery(INSERT_SQL, ["miss", params.query, null, null, params.top_score, params.context]);
}
