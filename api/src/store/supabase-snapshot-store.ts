/**
 * SupabaseSnapshotStore — Supabase-backed metrics snapshot storage.
 */

import { supabaseSelect, supabaseInsert, supabaseDelete } from "./supabase-client.js";
import type { MetricsSnapshotMeta, MetricsSnapshot } from "../schemas/pipeline.js";

interface SnapshotRow {
  readonly id: string;
  readonly label: string;
  readonly source: string;
  readonly tab: string;
  readonly weeks: number;
  readonly metrics: Record<string, unknown>;
  readonly created_at: string;
}

export class SupabaseSnapshotStore {
  async list(): Promise<readonly MetricsSnapshotMeta[]> {
    const rows = await supabaseSelect<Omit<SnapshotRow, "metrics">>(
      "metrics_snapshots",
      "?select=id,label,source,tab,weeks,created_at&order=created_at.desc",
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
    const rows = await supabaseSelect<SnapshotRow>(
      "metrics_snapshots",
      `?id=eq.${encodeURIComponent(id)}&limit=1`,
    );
    if (rows.length === 0) return null;
    const r = rows[0]!;
    return {
      id: r.id,
      created_at: r.created_at,
      label: r.label,
      source: r.source,
      tab: r.tab,
      weeks: r.weeks,
      metrics: r.metrics,
    };
  }

  async save(snapshot: MetricsSnapshot): Promise<void> {
    await supabaseInsert(
      "metrics_snapshots",
      [{
        id: snapshot.id,
        label: snapshot.label,
        source: snapshot.source,
        tab: snapshot.tab,
        weeks: snapshot.weeks,
        metrics: snapshot.metrics,
        created_at: snapshot.created_at,
      }],
      { upsert: true, onConflict: "id" },
    );
  }

  async delete(id: string): Promise<boolean> {
    const existing = await this.getById(id);
    if (!existing) return false;
    await supabaseDelete("metrics_snapshots", `?id=eq.${encodeURIComponent(id)}`);
    return true;
  }
}
