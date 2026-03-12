import { Hono } from "hono";
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import { paths } from "../config.js";
import { readTail } from "../utils/report-file.js";
import type { MeetingPrepMeta, MeetingPrepSummary } from "../schemas/meeting-prep.js";

/** Matches meeting_prep_YYYYMMDD_<hash8>.md */
const MEETING_PREP_PATTERN = /^meeting_prep_(\d{8})_([0-9a-f]{8})\.md$/;

const MEETING_PREP_META_RE = /<!-- meeting_prep_meta ({[\s\S]*?}) -->/;

const DATE_RE = /^\d{8}(?:_[0-9a-f]{8})?$/;

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
    };
  } catch {
    return undefined;
  }
}

/** Verify resolved path stays inside the allowed base directory (path traversal guard). */
function isInsideDir(filepath: string, baseDir: string): boolean {
  return resolve(filepath).startsWith(resolve(baseDir));
}

function listMeetingPrepFiles(): readonly MeetingPrepSummary[] {
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

export const meetingPrepRoute = new Hono();

meetingPrepRoute.get("/", (c) => {
  const items = listMeetingPrepFiles();
  return c.json(ok({ items, total: items.length }));
});

meetingPrepRoute.get("/:date", (c) => {
  const date = c.req.param("date");
  if (!DATE_RE.test(date)) {
    return c.json(fail("Invalid date format, expected YYYYMMDD or YYYYMMDD_hash8"), 400);
  }

  // Try exact match first
  const exactFilename = `meeting_prep_${date}.md`;
  const exactPath = resolve(join(paths.outputDir, exactFilename));

  if (!isInsideDir(exactPath, paths.outputDir)) {
    return c.json(fail("Invalid path"), 400);
  }

  if (existsSync(exactPath)) {
    const content = readFileSync(exactPath, "utf-8");
    const size_bytes = statSync(exactPath).size;
    const meta = parseMeetingPrepMeta(content);
    return c.json(ok({ date, filename: exactFilename, content, size_bytes, meta }));
  }

  // Fuzzy match: find files starting with meeting_prep_YYYYMMDD
  const datePrefix = date.length === 8 ? date : date.split("_")[0];
  const dir = paths.outputDir;
  if (!existsSync(dir)) {
    return c.json(fail("Meeting prep report not found"), 404);
  }

  const candidates = readdirSync(dir)
    .filter((f) => f.startsWith(`meeting_prep_${datePrefix}`) && f.endsWith(".md"))
    .sort()
    .reverse();

  if (candidates.length === 0) {
    return c.json(fail(`Meeting prep report for ${date} not found`), 404);
  }

  const filename = candidates[0]!;
  const filepath = resolve(join(dir, filename));

  if (!isInsideDir(filepath, dir)) {
    return c.json(fail("Invalid path"), 400);
  }

  const content = readFileSync(filepath, "utf-8");
  const size_bytes = statSync(filepath).size;
  const meta = parseMeetingPrepMeta(content);
  const matchedDate = MEETING_PREP_PATTERN.exec(filename);
  const resolvedDate = matchedDate ? `${matchedDate[1]}_${matchedDate[2]}` : date;

  return c.json(ok({ date: resolvedDate, filename, content, size_bytes, meta }));
});
