/**
 * Meeting-prep file utilities — shared between routes/meeting-prep.ts and sync/meeting-prep-sync.ts.
 *
 * Reads `output/meeting_prep_YYYYMMDD_HASH8.md` files and extracts the embedded
 * `meeting_prep_meta` JSON block, mapping it to the canonical `MeetingPrepMeta` schema.
 */

import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";
import { paths } from "../config.js";
import type { MeetingPrepMeta } from "../schemas/meeting-prep.js";

/** Matches meeting_prep_YYYYMMDD_HASH8.md exactly. */
export const MEETING_PREP_PATTERN = /^meeting_prep_(\d{8})_([0-9a-f]{8})\.md$/;

/** Matches the embedded ```json { ... "meeting_prep_meta": { ... } ... } ``` block. */
const MEETING_PREP_JSON_BLOCK_RE = /```json\s*\n(\{[\s\S]*?"meeting_prep_meta"[\s\S]*?\})\s*\n```/;

/** Legacy HTML-comment style (not currently used by generators but kept for compat). */
const MEETING_PREP_HTML_COMMENT_RE = /<!-- meeting_prep_meta ({[\s\S]*?}) -->/;

interface RawMeetingPrepMeta {
  readonly date?: string;
  readonly source_report?: string;
  readonly source_report_date?: string;
  readonly generation_mode?: string;
  readonly alert_down_count?: number;
  readonly s9_questions?: number;
  readonly question_count?: number;
  readonly eeat_avg?: number;
  readonly maturity?: {
    readonly strategy?: string;
    readonly process?: string;
    readonly keywords?: string;
    readonly metrics?: string;
  };
  readonly scores?: {
    readonly eeat?: {
      readonly experience?: number;
      readonly expertise?: number;
      readonly authoritativeness?: number;
      readonly trustworthiness?: number;
    };
    readonly maturity?: {
      readonly strategy?: string;
      readonly process?: string;
      readonly keywords?: string;
      readonly metrics?: string;
    };
  };
  readonly eeat_e?: number;
  readonly eeat_ex?: number;
  readonly eeat_a?: number;
  readonly eeat_t?: number;
}

function asEeatScore(raw: RawMeetingPrepMeta): MeetingPrepMeta["scores"]["eeat"] {
  // Prefer explicit canonical schema if present
  const canonical = raw.scores?.eeat;
  if (canonical) {
    return {
      experience: typeof canonical.experience === "number" ? canonical.experience : 0,
      expertise: typeof canonical.expertise === "number" ? canonical.expertise : 0,
      authoritativeness: typeof canonical.authoritativeness === "number" ? canonical.authoritativeness : 0,
      trustworthiness: typeof canonical.trustworthiness === "number" ? canonical.trustworthiness : 0,
    };
  }
  // Fallback: per-dimension shorthand fields used by claude-code generators
  if (
    typeof raw.eeat_e === "number" ||
    typeof raw.eeat_ex === "number" ||
    typeof raw.eeat_a === "number" ||
    typeof raw.eeat_t === "number"
  ) {
    return {
      experience: typeof raw.eeat_e === "number" ? raw.eeat_e : 0,
      expertise: typeof raw.eeat_ex === "number" ? raw.eeat_ex : 0,
      authoritativeness: typeof raw.eeat_a === "number" ? raw.eeat_a : 0,
      trustworthiness: typeof raw.eeat_t === "number" ? raw.eeat_t : 0,
    };
  }
  // Last resort: split eeat_avg evenly (lossy)
  const avg = typeof raw.eeat_avg === "number" ? raw.eeat_avg : 0;
  return {
    experience: avg,
    expertise: avg,
    authoritativeness: avg,
    trustworthiness: avg,
  };
}

function asMaturity(raw: RawMeetingPrepMeta): MeetingPrepMeta["scores"]["maturity"] {
  const m = raw.scores?.maturity ?? raw.maturity;
  return {
    strategy: typeof m?.strategy === "string" ? m.strategy : "L1",
    process: typeof m?.process === "string" ? m.process : "L1",
    keywords: typeof m?.keywords === "string" ? m.keywords : "L1",
    metrics: typeof m?.metrics === "string" ? m.metrics : "L1",
  };
}

function asSourceReportDate(raw: RawMeetingPrepMeta): string | undefined {
  if (typeof raw.source_report_date === "string") return raw.source_report_date;
  if (typeof raw.source_report === "string") {
    const m = raw.source_report.match(/report_(\d{8})/);
    if (m) return m[1];
  }
  return undefined;
}

/**
 * Parse meeting_prep_meta from file content.
 *
 * Supports two embedded formats:
 * 1. ```json { "meeting_prep_meta": {...} } ``` (current generators)
 * 2. <!-- meeting_prep_meta {...} --> (legacy HTML comment)
 */
export function parseMeetingPrepMeta(content: string): MeetingPrepMeta | undefined {
  let raw: RawMeetingPrepMeta | undefined;

  const jsonBlock = content.match(MEETING_PREP_JSON_BLOCK_RE);
  if (jsonBlock) {
    try {
      const wrapped = JSON.parse(jsonBlock[1]!) as { meeting_prep_meta?: RawMeetingPrepMeta };
      raw = wrapped.meeting_prep_meta;
    } catch {
      // fall through to HTML comment
    }
  }

  if (!raw) {
    const htmlComment = content.match(MEETING_PREP_HTML_COMMENT_RE);
    if (htmlComment) {
      try {
        raw = JSON.parse(htmlComment[1]!) as RawMeetingPrepMeta;
      } catch {
        return undefined;
      }
    }
  }

  if (!raw) return undefined;

  if (typeof raw.date !== "string") return undefined;

  const meta: MeetingPrepMeta = {
    date: raw.date,
    scores: {
      eeat: asEeatScore(raw),
      maturity: asMaturity(raw),
    },
    alert_down_count: typeof raw.alert_down_count === "number" ? raw.alert_down_count : 0,
    question_count:
      typeof raw.question_count === "number"
        ? raw.question_count
        : typeof raw.s9_questions === "number"
        ? raw.s9_questions
        : 0,
    generation_mode: typeof raw.generation_mode === "string" ? raw.generation_mode : "claude-code-semantic",
  };

  const sourceDate = asSourceReportDate(raw);
  return sourceDate ? { ...meta, source_report_date: sourceDate } : meta;
}

export interface MeetingPrepFile {
  readonly dateKey: string;
  readonly filename: string;
  readonly filepath: string;
  readonly size_bytes: number;
  readonly mtime: number;
}

/** List all meeting_prep_*.md files from the output directory, newest first. */
export function listMeetingPrepFiles(): readonly MeetingPrepFile[] {
  const dir = paths.outputDir;
  if (!existsSync(dir)) return [];

  return readdirSync(dir)
    .map((f) => {
      const m = MEETING_PREP_PATTERN.exec(f);
      if (!m) return null;
      const filepath = join(dir, f);
      const st = statSync(filepath);
      return {
        dateKey: `${m[1]}_${m[2]}`,
        filename: f,
        filepath,
        size_bytes: st.size,
        mtime: st.mtimeMs,
      };
    })
    .filter((x): x is MeetingPrepFile => x !== null)
    .sort((a, b) => b.mtime - a.mtime);
}

/** Read the full content + parsed meta for a meeting-prep file. */
export function readMeetingPrepFile(file: MeetingPrepFile): {
  content: string;
  meta: MeetingPrepMeta | undefined;
} {
  const content = readFileSync(file.filepath, "utf-8");
  const meta = parseMeetingPrepMeta(content);
  return { content, meta };
}
