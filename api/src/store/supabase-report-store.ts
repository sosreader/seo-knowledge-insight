/**
 * SupabaseReportStore — Supabase-backed report storage.
 *
 * Replaces file-based report reading/writing when Supabase is configured.
 * Reports are stored in the `reports` table with full markdown content.
 */

import { supabaseSelect, supabaseInsert, supabasePatch } from "./supabase-client.js";
import type { ReportSummary, ReportMeta } from "../schemas/report.js";

interface ReportRow {
  readonly id: number;
  readonly date_key: string;
  readonly filename: string;
  readonly content: string;
  readonly size_bytes: number;
  readonly meta: ReportMeta | null;
  readonly created_at: string;
}

export class SupabaseReportStore {
  /** List all reports, newest first. */
  async list(): Promise<readonly ReportSummary[]> {
    const rows = await supabaseSelect<ReportRow>(
      "reports",
      "?select=date_key,filename,size_bytes,meta&order=date_key.desc",
    );
    return rows.map((r) => ({
      date: r.date_key,
      filename: r.filename,
      size_bytes: r.size_bytes,
      meta: r.meta ?? undefined,
    }));
  }

  /** Get a single report by date_key. */
  async getByDate(dateKey: string): Promise<{ summary: ReportSummary; content: string } | null> {
    const rows = await supabaseSelect<ReportRow>(
      "reports",
      `?date_key=eq.${encodeURIComponent(dateKey)}&limit=1`,
    );
    if (rows.length === 0) return null;
    const r = rows[0]!;
    return {
      summary: {
        date: r.date_key,
        filename: r.filename,
        size_bytes: r.size_bytes,
        meta: r.meta ?? undefined,
      },
      content: r.content,
    };
  }

  /** Check if a report with the given date_key exists. */
  async exists(dateKey: string): Promise<boolean> {
    const rows = await supabaseSelect<{ date_key: string }>(
      "reports",
      `?select=date_key&date_key=eq.${encodeURIComponent(dateKey)}&limit=1`,
    );
    return rows.length > 0;
  }

  /** Save a report (upsert by date_key). */
  async save(dateKey: string, content: string, meta?: ReportMeta): Promise<void> {
    const filename = `report_${dateKey}.md`;
    await supabaseInsert(
      "reports",
      [{
        date_key: dateKey,
        filename,
        content,
        size_bytes: Buffer.byteLength(content, "utf-8"),
        meta: meta ?? null,
      }],
      { upsert: true, onConflict: "date_key" },
    );
  }

  /** Soft-delete a report by date_key (sets deleted_at). */
  async delete(dateKey: string): Promise<boolean> {
    const exists = await this.exists(dateKey);
    if (!exists) return false;
    await supabasePatch(
      "reports",
      `?date_key=eq.${encodeURIComponent(dateKey)}`,
      { deleted_at: new Date().toISOString() },
    );
    return true;
  }
}
