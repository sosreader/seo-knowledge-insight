import { Hono } from "hono";
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import { paths } from "../config.js";
import { readTail } from "../utils/report-file.js";
import { meetingPrepStore } from "../store/store-registry.js";
import type {
  MeetingPrepMeta,
  MeetingPrepSummary,
  MaturityDataPoint,
  MaturityTrendResponse,
  MaturityTrendSummary,
} from "../schemas/meeting-prep.js";

/** Matches meeting_prep_YYYYMMDD_<hash8>.md */
const MEETING_PREP_PATTERN = /^meeting_prep_(\d{8})_([0-9a-f]{8})\.md$/;

const MEETING_PREP_META_RE = /<!-- meeting_prep_meta ({[\s\S]*?}) -->/;

const DATE_RE = /^\d{8}(?:_[0-9a-f]{8})?$/;

/** Extract source report date from content header: 來源：`output/report_XXXXXXXX_XXXXXXXX.md` */
const SOURCE_REPORT_RE = /來源：`?output\/report_([0-9a-zA-Z_]+)\.md`?/;

function parseSourceReportDate(content: string): string | undefined {
  const m = SOURCE_REPORT_RE.exec(content);
  return m?.[1] ?? undefined;
}

/** Parse meeting_prep_meta JSON with field-by-field validation. */
function parseMeetingPrepMeta(content: string): MeetingPrepMeta | undefined {
  const m = content.match(MEETING_PREP_META_RE);
  if (!m) return undefined;
  try {
    const raw = JSON.parse(m[1]) as Record<string, unknown>;
    if (typeof raw.date !== "string") return undefined;
    if (typeof raw.generation_mode !== "string") return undefined;

    const scores = raw.scores as Record<string, unknown> | undefined;
    if (!scores || typeof scores !== "object") return undefined;

    const eeat = scores.eeat as Record<string, unknown> | undefined;
    const maturity = scores.maturity as Record<string, unknown> | undefined;
    if (!eeat || !maturity) return undefined;

    return {
      date: raw.date,
      scores: {
        eeat: {
          experience: typeof eeat.experience === "number" ? eeat.experience : 0,
          expertise: typeof eeat.expertise === "number" ? eeat.expertise : 0,
          authoritativeness: typeof eeat.authoritativeness === "number" ? eeat.authoritativeness : 0,
          trustworthiness: typeof eeat.trustworthiness === "number" ? eeat.trustworthiness : 0,
        },
        maturity: {
          strategy: typeof maturity.strategy === "string" ? maturity.strategy : "L1",
          process: typeof maturity.process === "string" ? maturity.process : "L1",
          keywords: typeof maturity.keywords === "string" ? maturity.keywords : "L1",
          metrics: typeof maturity.metrics === "string" ? maturity.metrics : "L1",
        },
      },
      alert_down_count: typeof raw.alert_down_count === "number" ? raw.alert_down_count : 0,
      question_count: typeof raw.question_count === "number" ? raw.question_count : 0,
      generation_mode: raw.generation_mode,
      ...(typeof raw.source_report_date === "string"
        ? { source_report_date: raw.source_report_date }
        : {}),
    };
  } catch {
    return undefined;
  }
}

/** Verify resolved path stays inside the allowed base directory (path traversal guard). */
function isInsideDir(filepath: string, baseDir: string): boolean {
  return resolve(filepath).startsWith(resolve(baseDir));
}

/* ── Filesystem helpers (fallback when Supabase is not configured) ── */

function listMeetingPrepFromFs(): readonly MeetingPrepSummary[] {
  const dir = paths.outputDir;
  if (!existsSync(dir)) return [];

  const files = readdirSync(dir)
    .filter((f) => MEETING_PREP_PATTERN.test(f))
    .map((f) => {
      const m = MEETING_PREP_PATTERN.exec(f)!;
      const filepath = join(dir, f);
      if (!isInsideDir(filepath, dir)) return null;
      const st = statSync(filepath);
      const tail = readTail(filepath, 500);
      const meta = parseMeetingPrepMeta(tail);
      return {
        date: `${m[1]}_${m[2]}`,
        filename: f,
        size_bytes: st.size,
        mtime: st.mtimeMs,
        meta,
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((a, b) => b.mtime - a.mtime);

  return files.map(({ date, filename, size_bytes, meta }) => ({
    date,
    filename,
    size_bytes,
    meta,
  }));
}

function getMeetingPrepFromFs(date: string): {
  date: string;
  filename: string;
  content: string;
  size_bytes: number;
  meta?: MeetingPrepMeta;
} | null {
  const dir = paths.outputDir;

  // Try exact match first
  const exactFilename = `meeting_prep_${date}.md`;
  const exactPath = resolve(join(dir, exactFilename));

  if (isInsideDir(exactPath, dir) && existsSync(exactPath)) {
    const content = readFileSync(exactPath, "utf-8");
    const size_bytes = statSync(exactPath).size;
    const meta = parseMeetingPrepMeta(content);
    return { date, filename: exactFilename, content, size_bytes, meta };
  }

  // Fuzzy match: find files starting with meeting_prep_YYYYMMDD
  const datePrefix = date.length === 8 ? date : date.split("_")[0];
  if (!existsSync(dir)) return null;

  const candidates = readdirSync(dir)
    .filter((f) => f.startsWith(`meeting_prep_${datePrefix}`) && f.endsWith(".md"))
    .sort()
    .reverse();

  if (candidates.length === 0) return null;

  const filename = candidates[0]!;
  const filepath = resolve(join(dir, filename));
  if (!isInsideDir(filepath, dir)) return null;

  const content = readFileSync(filepath, "utf-8");
  const size_bytes = statSync(filepath).size;
  const meta = parseMeetingPrepMeta(content);
  const matchedDate = MEETING_PREP_PATTERN.exec(filename);
  const resolvedDate = matchedDate ? `${matchedDate[1]}_${matchedDate[2]}` : date;

  return { date: resolvedDate, filename, content, size_bytes, meta };
}

/* ── Route definitions ── */

export const meetingPrepRoute = new Hono();

/** Enrich list items: inject source_report_date into meta from content, strip content from response. */
function enrichSourceReportDate(
  items: readonly (MeetingPrepSummary & { content: string })[],
): MeetingPrepSummary[] {
  return items.map(({ content, ...summary }) => {
    if (summary.meta?.source_report_date) return summary;
    const srcDate = parseSourceReportDate(content);
    if (!srcDate || !summary.meta) return summary;
    return { ...summary, meta: { ...summary.meta, source_report_date: srcDate } };
  });
}

meetingPrepRoute.get("/", async (c) => {
  if (meetingPrepStore) {
    try {
      const raw = await meetingPrepStore.listWithContent();
      const items = enrichSourceReportDate(raw);
      return c.json(ok({ items, total: items.length }));
    } catch {
      return c.json(fail("Store unavailable"), 503);
    }
  }
  const items = listMeetingPrepFromFs();
  return c.json(ok({ items, total: items.length }));
});

/** Parse "L1"→1, "L2"→2, etc. Returns 0 for unrecognised strings. */
function parseLevel(level: string): number {
  const m = /^L(\d+)$/i.exec(level);
  return m ? parseInt(m[1]!, 10) : 0;
}

/** Compute maturity trend summary from data points (first vs last). */
function computeTrendSummary(
  points: readonly MaturityDataPoint[],
): MaturityTrendSummary | null {
  if (points.length < 2) return null;

  const first = points[0]!.maturity;
  const last = points[points.length - 1]!.maturity;
  const dimensions = ["strategy", "process", "keywords", "metrics"] as const;

  const improved = dimensions.filter((d) => parseLevel(last[d]) > parseLevel(first[d]));
  const regressed = dimensions.filter((d) => parseLevel(last[d]) < parseLevel(first[d]));
  const stagnant = dimensions.filter((d) => parseLevel(last[d]) === parseLevel(first[d]));

  return { improved: [...improved], stagnant: [...stagnant], regressed: [...regressed] };
}

meetingPrepRoute.get("/maturity-trend", async (c) => {
  if (meetingPrepStore) {
    try {
      const data_points = await meetingPrepStore.listWithMeta();
      const summary = computeTrendSummary(data_points);
      const response: MaturityTrendResponse = { data_points, summary, total: data_points.length };
      return c.json(ok(response));
    } catch {
      return c.json(fail("Store unavailable"), 503);
    }
  }

  // Filesystem fallback
  const all = listMeetingPrepFromFs();
  const withMeta = all.filter(
    (item): item is MeetingPrepSummary & { meta: MeetingPrepMeta } =>
      item.meta !== undefined,
  );

  if (withMeta.length === 0) {
    const response: MaturityTrendResponse = { data_points: [], summary: null, total: 0 };
    return c.json(ok(response));
  }

  const sorted = [...withMeta].sort((a, b) => {
    const aDate = a.date.slice(0, 8);
    const bDate = b.date.slice(0, 8);
    return aDate.localeCompare(bDate);
  });

  const data_points: MaturityDataPoint[] = sorted.map((item) => {
    const dateStr = item.date.slice(0, 8);
    const formatted = `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
    return {
      date: formatted,
      maturity: item.meta.scores.maturity,
      eeat: item.meta.scores.eeat,
      alert_down_count: item.meta.alert_down_count,
    };
  });

  const summary = computeTrendSummary(data_points);
  const response: MaturityTrendResponse = { data_points, summary, total: data_points.length };
  return c.json(ok(response));
});

meetingPrepRoute.get("/:date", async (c) => {
  const date = c.req.param("date");
  if (!DATE_RE.test(date)) {
    return c.json(fail("Invalid date format, expected YYYYMMDD or YYYYMMDD_hash8"), 400);
  }

  if (meetingPrepStore) {
    try {
      const result = await meetingPrepStore.getByDate(date);
      if (!result) {
        return c.json(fail(`Meeting prep report for ${date} not found`), 404);
      }
      const meta = result.summary.meta;
      const enrichedMeta = meta && !meta.source_report_date
        ? { ...meta, source_report_date: parseSourceReportDate(result.content) }
        : meta;
      return c.json(ok({
        date: result.summary.date,
        filename: result.summary.filename,
        content: result.content,
        size_bytes: result.summary.size_bytes,
        meta: enrichedMeta,
      }));
    } catch {
      return c.json(fail("Store unavailable"), 503);
    }
  }

  // Filesystem fallback
  const result = getMeetingPrepFromFs(date);
  if (!result) {
    return c.json(fail(`Meeting prep report for ${date} not found`), 404);
  }
  return c.json(ok(result));
});
