/**
 * PgSnapshotStore — 指標快照（app_metrics_snapshot）。
 *
 * 有 deleted_at（VW 無 RLS）：每個 SELECT 明寫 deleted_at IS NULL；刪除為軟刪除。
 * save 以 id upsert 並把 deleted_at 清回 NULL（與 Supabase 版相同語意：重存即復活）。
 */

import { isoColumn, pgQuery } from "./pg-client.js";
import type { MetricsSnapshotMeta, MetricsSnapshot } from "../schemas/pipeline.js";

interface SnapshotRow {
  readonly id: string;
  readonly label: string;
  readonly source: string;
  readonly tab: string;
  readonly weeks: number;
  readonly metrics: Record<string, unknown>;
  readonly maturity: Record<string, string> | null;
  readonly created_at: string;
}

const META_COLUMNS = `id, label, source, tab, weeks, ${isoColumn("created_at")}`;

const UPSERT_SQL = `INSERT INTO app_metrics_snapshot
    (id, label, source, tab, weeks, metrics, maturity, created_at, deleted_at)
  VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, COALESCE($8::timestamptz, now()), NULL)
  ON CONFLICT (id) DO UPDATE SET
    label = EXCLUDED.label, source = EXCLUDED.source, tab = EXCLUDED.tab, weeks = EXCLUDED.weeks,
    metrics = EXCLUDED.metrics, maturity = EXCLUDED.maturity, created_at = EXCLUDED.created_at,
    deleted_at = NULL`;

export class PgSnapshotStore {
  async list(): Promise<readonly MetricsSnapshotMeta[]> {
    const rows = await pgQuery<Omit<SnapshotRow, "metrics" | "maturity">>(
      `SELECT ${META_COLUMNS} FROM app_metrics_snapshot
        WHERE deleted_at IS NULL ORDER BY created_at DESC`,
    );
    return rows.map((r) => ({
      id: r.id,
      created_at: r.created_at,
      label: r.label,
      source: r.source,
      tab: r.tab,
      weeks: r.weeks,
    }));
  }

  async getById(id: string): Promise<MetricsSnapshot | null> {
    const rows = await pgQuery<SnapshotRow>(
      `SELECT ${META_COLUMNS}, metrics, maturity FROM app_metrics_snapshot
        WHERE id = $1 AND deleted_at IS NULL LIMIT 1`,
      [id],
    );
    const r = rows[0];
    if (!r) return null;
    return {
      id: r.id,
      created_at: r.created_at,
      label: r.label,
      source: r.source,
      tab: r.tab,
      weeks: r.weeks,
      metrics: r.metrics,
      ...(r.maturity ? { maturity: r.maturity } : {}),
    };
  }

  async save(snapshot: MetricsSnapshot): Promise<void> {
    await pgQuery(UPSERT_SQL, [
      snapshot.id,
      snapshot.label,
      snapshot.source,
      snapshot.tab,
      snapshot.weeks,
      JSON.stringify(snapshot.metrics),
      snapshot.maturity ? JSON.stringify(snapshot.maturity) : null,
      snapshot.created_at || null,
    ]);
  }

  /** 軟刪除；已刪或不存在回 false。 */
  async delete(id: string): Promise<boolean> {
    const rows = await pgQuery<{ id: string }>(
      `UPDATE app_metrics_snapshot SET deleted_at = now()
        WHERE id = $1 AND deleted_at IS NULL RETURNING id`,
      [id],
    );
    return rows.length > 0;
  }
}
