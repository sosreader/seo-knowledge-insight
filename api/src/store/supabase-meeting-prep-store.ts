/**
 * SupabaseMeetingPrepStore — Supabase-backed meeting-prep storage.
 *
 * Replaces file-based meeting-prep reading when Supabase is configured.
 * Reports stored in the `meeting_prep` table with full markdown content.
 */

import { supabaseSelect, supabaseInsert, supabaseDelete } from "./supabase-client.js";
import type {
  MeetingPrepMeta,
  MeetingPrepSummary,
  MaturityDataPoint,
} from "../schemas/meeting-prep.js";

/** date_key format: YYYYMMDD or YYYYMMDD_hash8 */
const SAFE_DATE_KEY_RE = /^\d{8}(?:_[0-9a-f]{8})?$/;

function assertSafeDateKey(dateKey: string): void {
  if (!SAFE_DATE_KEY_RE.test(dateKey)) {
    throw new Error(`Invalid date_key format: ${dateKey}`);
  }
}

interface MeetingPrepRow {
  readonly date_key: string;
  readonly filename: string;
  readonly content: string;
  readonly size_bytes: number;
  readonly meta: MeetingPrepMeta;
  readonly created_at: string;
}

export class SupabaseMeetingPrepStore {
  /** List all meeting-prep reports, newest first. */
  async list(): Promise<readonly MeetingPrepSummary[]> {
    const rows = await supabaseSelect<MeetingPrepRow>(
      "meeting_prep",
      "?select=date_key,filename,size_bytes,meta&order=date_key.desc",
    );
    return rows.map((r) => ({
      date: r.date_key,
      filename: r.filename,
      size_bytes: r.size_bytes,
      meta: r.meta,
    }));
  }

  /** List with content (for enrichment). */
  async listWithContent(): Promise<readonly (MeetingPrepSummary & { content: string })[]> {
    const rows = await supabaseSelect<MeetingPrepRow>(
      "meeting_prep",
      "?select=date_key,filename,size_bytes,meta,content&order=date_key.desc",
    );
    return rows.map((r) => ({
      date: r.date_key,
      filename: r.filename,
      size_bytes: r.size_bytes,
      meta: r.meta,
      content: r.content,
    }));
  }

  /** Get a single report by exact or fuzzy date_key match. */
  async getByDate(dateKey: string): Promise<{ summary: MeetingPrepSummary; content: string } | null> {
    assertSafeDateKey(dateKey);

    const exact = await supabaseSelect<MeetingPrepRow>(
      "meeting_prep",
      `?date_key=eq.${encodeURIComponent(dateKey)}&limit=1`,
    );
    if (exact.length > 0) {
      return this.toResult(exact[0]!);
    }

    // Fuzzy match: YYYYMMDD prefix — prefix is always 8 digits (validated by assertSafeDateKey)
    const prefix = dateKey.length === 8 ? dateKey : dateKey.split("_")[0]!;
    const fuzzy = await supabaseSelect<MeetingPrepRow>(
      "meeting_prep",
      `?date_key=like.${encodeURIComponent(prefix)}*&order=date_key.desc&limit=1`,
    );
    if (fuzzy.length === 0) return null;
    return this.toResult(fuzzy[0]!);
  }

  /** Check if a report with the given date_key exists. */
  async exists(dateKey: string): Promise<boolean> {
    assertSafeDateKey(dateKey);
    const rows = await supabaseSelect<{ date_key: string }>(
      "meeting_prep",
      `?select=date_key&date_key=eq.${encodeURIComponent(dateKey)}&limit=1`,
    );
    return rows.length > 0;
  }

  /** Save a meeting-prep report (upsert by date_key). */
  async save(dateKey: string, filename: string, content: string, meta?: MeetingPrepMeta): Promise<void> {
    assertSafeDateKey(dateKey);
    await supabaseInsert(
      "meeting_prep",
      [{
        date_key: dateKey,
        filename,
        content,
        size_bytes: Buffer.byteLength(content, "utf-8"),
        meta: meta ?? {},
      }],
      { upsert: true, onConflict: "date_key" },
    );
  }

  /** Delete a meeting-prep report by date_key. */
  async delete(dateKey: string): Promise<boolean> {
    assertSafeDateKey(dateKey);
    const exists = await this.exists(dateKey);
    if (!exists) return false;
    await supabaseDelete("meeting_prep", `?date_key=eq.${encodeURIComponent(dateKey)}`);
    return true;
  }

  /** List reports with meta for maturity trend (date ascending). */
  async listWithMeta(): Promise<readonly MaturityDataPoint[]> {
    const rows = await supabaseSelect<MeetingPrepRow>(
      "meeting_prep",
      "?select=date_key,meta&meta=not.is.null&order=date_key.asc",
    );
    return rows
      .filter((r) =>
        r.meta?.scores?.maturity !== undefined &&
        r.meta?.scores?.eeat !== undefined,
      )
      .map((r) => {
        const dateStr = r.date_key.slice(0, 8);
        const formatted = `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
        return {
          date: formatted,
          maturity: r.meta.scores.maturity,
          eeat: r.meta.scores.eeat,
          alert_down_count: r.meta.alert_down_count,
        };
      });
  }

  private toResult(r: MeetingPrepRow): { summary: MeetingPrepSummary; content: string } {
    return {
      summary: {
        date: r.date_key,
        filename: r.filename,
        size_bytes: r.size_bytes,
        meta: r.meta,
      },
      content: r.content,
    };
  }
}
