import { Hono } from "hono";
import { readFileSync, readdirSync, existsSync, statSync, mkdirSync, writeFileSync, unlinkSync } from "node:fs";
import { join, resolve } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import { z } from "zod";
import {
  fetchRequestSchema,
  extractQARequestSchema,
  dedupeClassifyRequestSchema,
  metricsRequestSchema,
  metricsSaveSchema,
  snapshotIdSchema,
  sourceDocsQuerySchema,
  type MeetingEntry,
  type MeetingsResponse,
  type MeetingPreviewResponse,
  type UnprocessedItem,
  type UnprocessedResponse,
  type FetchLogEntry,
  type FetchLogsResponse,
  type PipelineStepStatus,
  type PipelineStatusResponse,
  type SourceDocEntry,
  type SourceDocsResponse,
  type SourceDocPreviewResponse,
  type MetricsSnapshotMeta,
  type MetricsSnapshot,
} from "../schemas/pipeline.js";

const meetingEntrySchema = z.object({
  title: z.string(),
  id: z.string(),
  created_time: z.string(),
  last_edited_time: z.string(),
  url: z.string(),
  json_file: z.string(),
  md_file: z.string(),
  status: z.string().optional(),
});
import { execPython, execQaTools } from "../services/pipeline-runner.js";
import { paths } from "../config.js";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const FETCH_LOG_PATTERN = /^fetch_\d{4}-\d{2}-\d{2}\.jsonl$/;

// --- Helpers ---

function readMeetingsIndex(): readonly MeetingEntry[] {
  const indexPath = join(paths.rawDataDir, "meetings_index.json");
  if (!existsSync(indexPath)) return [];

  try {
    const raw = readFileSync(indexPath, "utf-8");
    const parsed = z.array(meetingEntrySchema).safeParse(JSON.parse(raw));
    if (!parsed.success) return [];
    return parsed.data.map((e) => ({
      ...e,
      status: e.status ?? "fetched",
    }));
  } catch {
    return [];
  }
}

function countMdFiles(dir: string): number {
  if (!existsSync(dir)) return 0;
  return readdirSync(dir).filter((f) => f.endsWith(".md")).length;
}

function countQAPerMeeting(): number {
  const dir = join(paths.outputDir, "qa_per_meeting");
  if (!existsSync(dir)) return 0;
  return readdirSync(dir).filter((f) => f.endsWith("_qa.json")).length;
}

function countQAPerArticle(): number {
  // Article QA files are also stored in qa_per_meeting/ (shared directory)
  // This function is kept for API compatibility but returns 0 since
  // countQAPerMeeting() already counts all QA files (meetings + articles)
  return 0;
}

function countQAFinal(): number {
  if (!existsSync(paths.qaJsonPath)) return 0;
  try {
    const raw = readFileSync(paths.qaJsonPath, "utf-8");
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    // qa_final.json is { total_count, qa_database: [...] }
    if (typeof parsed.total_count === "number") return parsed.total_count;
    if (Array.isArray(parsed.qa_database)) return parsed.qa_database.length;
    if (Array.isArray(parsed)) return parsed.length;
    return 0;
  } catch {
    return 0;
  }
}

function buildPipelineStatus(): PipelineStatusResponse {
  const meetings = readMeetingsIndex();
  const mdDir = join(paths.rawDataDir, "markdown");
  const mdCount = countMdFiles(mdDir);

  const mediumMdCount = countMdFiles(paths.rawMediumMdDir);
  const ithelpMdCount = countMdFiles(paths.rawIthelpMdDir);
  const googleMdCount = countMdFiles(paths.rawGoogleCasesMdDir);

  const extractedMeetings = countQAPerMeeting();
  const extractedArticles = countQAPerArticle();
  const totalMd = mdCount + mediumMdCount + ithelpMdCount + googleMdCount;
  const totalExtracted = extractedMeetings + extractedArticles;
  const finalCount = countQAFinal();

  const steps: PipelineStepStatus[] = [
    {
      name: "fetch-notion",
      label: "Notion 擷取",
      count: mdCount,
      detail: `${meetings.length} 筆會議，${mdCount} 份 Markdown`,
    },
    {
      name: "fetch-medium",
      label: "Medium 擷取",
      count: mediumMdCount,
      detail: `${mediumMdCount} 篇文章`,
    },
    {
      name: "fetch-ithelp",
      label: "iThome 擷取",
      count: ithelpMdCount,
      detail: `${ithelpMdCount} 篇文章`,
    },
    {
      name: "fetch-google",
      label: "Google 個案擷取",
      count: googleMdCount,
      detail: `${googleMdCount} 篇個案研究`,
    },
    {
      name: "extract-qa",
      label: "Q&A 萃取",
      count: totalExtracted,
      detail: `已萃取 ${totalExtracted} / ${totalMd} 份`,
    },
    {
      name: "dedupe-classify",
      label: "去重 + 分類",
      count: finalCount,
      detail: `${finalCount} 筆 Q&A（去重 + 分類後）`,
    },
  ];

  return { steps };
}

function findUnprocessed(): readonly UnprocessedItem[] {
  // All QA JSONs are written to qa_per_meeting/ (including articles)
  const qaDir = join(paths.outputDir, "qa_per_meeting");
  const sources: ReadonlyArray<{
    readonly mdDir: string;
    readonly qaDir: string;
    readonly sourceCollection: string;
  }> = [
    {
      mdDir: join(paths.rawDataDir, "markdown"),
      qaDir,
      sourceCollection: "seo-meetings",
    },
    {
      mdDir: paths.rawMediumMdDir,
      qaDir,
      sourceCollection: "genehong-medium",
    },
    {
      mdDir: paths.rawIthelpMdDir,
      qaDir,
      sourceCollection: "ithelp-sc-kpi",
    },
    {
      mdDir: paths.rawGoogleCasesMdDir,
      qaDir,
      sourceCollection: "google-case-studies",
    },
  ];

  const results: UnprocessedItem[] = [];

  for (const { mdDir, qaDir, sourceCollection } of sources) {
    if (!existsSync(mdDir)) continue;

    const mdFiles = readdirSync(mdDir).filter((f) => f.endsWith(".md"));
    const processedSet = new Set(
      existsSync(qaDir)
        ? readdirSync(qaDir)
            .filter((f) => f.endsWith("_qa.json"))
            .map((f) => f.replace(/_qa\.json$/, ".md"))
        : []
    );

    for (const f of mdFiles) {
      if (!processedSet.has(f)) {
        const fm = parseArticleFrontmatter(join(mdDir, f));
        results.push({
          file: f,
          title: fm.title ?? f.replace(/\.md$/, "").replace(/_/g, " "),
          source_collection: sourceCollection,
        });
      }
    }
  }

  return results;
}

function readFetchLogs(limit = 200): FetchLogsResponse {
  const logsDir = paths.fetchLogsDir;
  if (!existsSync(logsDir)) return { files: [], entries: [], total: 0 };

  const files = readdirSync(logsDir)
    .filter((f) => FETCH_LOG_PATTERN.test(f))
    .sort()
    .reverse();

  const entries: FetchLogEntry[] = [];

  for (const file of files) {
    if (entries.length >= limit) break;
    try {
      const content = readFileSync(join(logsDir, file), "utf-8");
      const lines = content.trim().split("\n").filter(Boolean);
      for (const line of lines) {
        if (entries.length >= limit) break;
        entries.push(JSON.parse(line) as FetchLogEntry);
      }
    } catch {
      // skip malformed log files
    }
  }

  return { files, entries, total: entries.length };
}

// --- Article frontmatter helpers ---

/** Parse key-value pairs from article Markdown frontmatter (lines like `- **Key**: Value`). */
function parseArticleFrontmatter(filePath: string): { title: string | null; publishedAt: string | null; sourceUrl: string | null } {
  let title: string | null = null;
  let publishedAt: string | null = null;
  let sourceUrl: string | null = null;
  try {
    const content = readFileSync(filePath, "utf-8");
    const lines = content.split("\n").slice(0, 10);
    for (const line of lines) {
      const h1Match = line.match(/^#\s+(.+)/);
      if (h1Match && !title) title = h1Match[1].trim();

      const dateMatch = line.match(/\*\*發佈日期\*\*:\s*(\d{4}-\d{2}-\d{2})/);
      if (dateMatch) publishedAt = `${dateMatch[1]}T00:00:00.000Z`;

      const urlMatch = line.match(/\*\*來源 URL\*\*:\s*(https?:\/\/\S+)/);
      if (urlMatch) sourceUrl = urlMatch[1];
    }
  } catch {
    // ignore read errors
  }
  return { title, publishedAt, sourceUrl };
}

// --- Collection → Directory mapping (whitelist, lazy to avoid module-scope path issues in tests) ---

function getCollectionDirMap(): Readonly<Record<string, { dir: string; sourceType: "meeting" | "article" }>> {
  return {
    "seo-meetings": { dir: join(paths.rawDataDir, "markdown"), sourceType: "meeting" },
    "genehong-medium": { dir: paths.rawMediumMdDir, sourceType: "article" },
    "ithelp-sc-kpi": { dir: paths.rawIthelpMdDir, sourceType: "article" },
    "google-case-studies": { dir: paths.rawGoogleCasesMdDir, sourceType: "article" },
  };
}

const SAFE_FILENAME_RE = /^[a-zA-Z0-9._\u4e00-\u9fff-]+\.md$/;

function buildSourceDocs(): readonly SourceDocEntry[] {
  const meetings = readMeetingsIndex();
  const meetingsByMd = new Map(meetings.map((m) => [m.md_file.replace(/^markdown\//, ""), m]));

  const qaPerMeetingDir = join(paths.outputDir, "qa_per_meeting");
  const processedMeetings = new Set(
    existsSync(qaPerMeetingDir)
      ? readdirSync(qaPerMeetingDir)
          .filter((f) => f.endsWith("_qa.json"))
          .map((f) => f.replace(/_qa\.json$/, ".md"))
      : []
  );
  // Article QA files are also stored in qa_per_meeting/ (shared directory)
  const processedArticles = new Set(
    existsSync(qaPerMeetingDir)
      ? readdirSync(qaPerMeetingDir)
          .filter((f) => f.endsWith("_qa.json"))
          .map((f) => f.replace(/_qa\.json$/, ".md"))
      : []
  );

  const results: SourceDocEntry[] = [];

  for (const [collection, { dir, sourceType }] of Object.entries(getCollectionDirMap())) {
    if (!existsSync(dir)) continue;

    const processedSet = sourceType === "meeting" ? processedMeetings : processedArticles;
    const mdFiles = readdirSync(dir).filter((f) => f.endsWith(".md"));

    for (const file of mdFiles) {
      const filePath = join(dir, file);
      let stat;
      try {
        stat = statSync(filePath);
      } catch {
        continue;
      }

      const meeting = sourceType === "meeting" ? meetingsByMd.get(file) : undefined;

      let title: string;
      let createdTime: string;
      let sourceUrl: string;
      if (meeting) {
        title = meeting.title;
        createdTime = meeting.created_time;
        sourceUrl = meeting.url;
      } else {
        const fm = parseArticleFrontmatter(filePath);
        title = fm.title ?? file.replace(/\.md$/, "").replace(/[-_]/g, " ");
        createdTime = fm.publishedAt ?? stat.mtime.toISOString();
        sourceUrl = fm.sourceUrl ?? "";
      }

      results.push({
        file,
        title,
        source_type: sourceType,
        source_collection: collection,
        source_url: sourceUrl,
        created_time: createdTime,
        size_bytes: stat.size,
        is_processed: processedSet.has(file),
      });
    }
  }

  return results;
}

// --- Snapshot helpers ---

const SNAPSHOT_ID_RE = /^[0-9]{8}-[0-9]{6}$/;

function generateSnapshotId(): string {
  const now = new Date();
  const pad2 = (n: number) => String(n).padStart(2, "0");
  const date =
    String(now.getFullYear()) +
    pad2(now.getMonth() + 1) +
    pad2(now.getDate());
  const time =
    pad2(now.getHours()) +
    pad2(now.getMinutes()) +
    pad2(now.getSeconds());
  return `${date}-${time}`;
}

function listSnapshots(): readonly MetricsSnapshotMeta[] {
  const dir = paths.metricsSnapshotsDir;
  if (!existsSync(dir)) return [];

  const files = readdirSync(dir)
    .filter((f) => /^[0-9]{8}-[0-9]{6}\.json$/.test(f))
    .sort()
    .reverse();

  const results: MetricsSnapshotMeta[] = [];
  for (const file of files) {
    try {
      const raw = readFileSync(join(dir, file), "utf-8");
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      results.push({
        id: String(parsed.id ?? ""),
        created_at: String(parsed.created_at ?? ""),
        label: String(parsed.label ?? ""),
        source: String(parsed.source ?? ""),
        tab: String(parsed.tab ?? ""),
        weeks: Number(parsed.weeks ?? 2),
      });
    } catch {
      // skip malformed snapshot files
    }
  }
  return results;
}

function readSnapshot(id: string): MetricsSnapshot | null {
  if (!SNAPSHOT_ID_RE.test(id)) return null;
  const dir = paths.metricsSnapshotsDir;
  const filePath = resolve(dir, `${id}.json`);
  // Path traversal guard
  if (!filePath.startsWith(dir)) return null;
  if (!existsSync(filePath)) return null;
  try {
    const raw = readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as MetricsSnapshot;
  } catch {
    return null;
  }
}

// --- Route ---

export const pipelineRoute = new Hono();

// GET /status
pipelineRoute.get("/status", (c) => {
  const status = buildPipelineStatus();
  return c.json(ok(status));
});

// GET /meetings
pipelineRoute.get("/meetings", (c) => {
  const items = readMeetingsIndex();
  const response: MeetingsResponse = { items, total: items.length };
  return c.json(ok(response));
});

// GET /meetings/:id/preview
pipelineRoute.get("/meetings/:id/preview", (c) => {
  const id = c.req.param("id");
  if (!UUID_RE.test(id)) {
    return c.json(fail("Invalid meeting ID format"), 400);
  }

  const meetings = readMeetingsIndex();
  const meeting = meetings.find((m) => m.id === id);
  if (!meeting) {
    return c.json(fail("Meeting not found"), 404);
  }

  const mdPath = resolve(paths.rawDataDir, meeting.md_file);

  // Path traversal guard
  if (!mdPath.startsWith(paths.rawDataDir)) {
    return c.json(fail("Invalid file path"), 400);
  }

  if (!existsSync(mdPath)) {
    return c.json(fail("Markdown file not found"), 404);
  }

  const content = readFileSync(mdPath, "utf-8");
  const size_bytes = statSync(mdPath).size;

  const response: MeetingPreviewResponse = {
    id: meeting.id,
    title: meeting.title,
    content,
    size_bytes,
  };
  return c.json(ok(response));
});

// GET /source-docs
pipelineRoute.get("/source-docs", (c) => {
  const parsed = sourceDocsQuerySchema.safeParse(Object.fromEntries(new URL(c.req.url).searchParams));
  if (!parsed.success) {
    return c.json(fail("Invalid query parameters"), 400);
  }

  const { source_type, source_collection, keyword, is_processed, limit, offset } = parsed.data;

  let docs = buildSourceDocs();

  if (source_type) {
    docs = docs.filter((d) => d.source_type === source_type);
  }
  if (source_collection) {
    docs = docs.filter((d) => d.source_collection === source_collection);
  }
  if (keyword) {
    const kw = keyword.toLowerCase();
    docs = docs.filter((d) => d.title.toLowerCase().includes(kw) || d.file.toLowerCase().includes(kw));
  }
  if (is_processed !== undefined) {
    docs = docs.filter((d) => d.is_processed === is_processed);
  }

  const total = docs.length;
  const items = docs.slice(offset, offset + limit);

  const response: SourceDocsResponse = { items, total, offset, limit };
  return c.json(ok(response));
});

// GET /source-docs/:collection/:file/preview
pipelineRoute.get("/source-docs/:collection/:file/preview", (c) => {
  const collection = c.req.param("collection");
  const file = c.req.param("file");

  // Whitelist check
  const entry = getCollectionDirMap()[collection];
  if (!entry) {
    return c.json(fail("Unknown collection"), 400);
  }

  // Filename safety check
  if (!SAFE_FILENAME_RE.test(file)) {
    return c.json(fail("Invalid filename"), 400);
  }

  const filePath = resolve(entry.dir, file);

  // Path traversal guard
  if (!filePath.startsWith(entry.dir)) {
    return c.json(fail("Invalid file path"), 400);
  }

  if (!existsSync(filePath)) {
    return c.json(fail("File not found"), 404);
  }

  const content = readFileSync(filePath, "utf-8");
  const size_bytes = statSync(filePath).size;

  // Extract H1 title from content, fallback to filename slug
  const h1Match = content.match(/^#\s+(.+)/m);
  const title = h1Match ? h1Match[1].trim() : file.replace(/\.md$/, "").replace(/[-_]/g, " ");

  const response: SourceDocPreviewResponse = {
    file,
    title,
    collection,
    content,
    size_bytes,
  };
  return c.json(ok(response));
});

// GET /unprocessed
pipelineRoute.get("/unprocessed", (c) => {
  const items = findUnprocessed();
  const response: UnprocessedResponse = { items, total: items.length };
  return c.json(ok(response));
});

// GET /logs
pipelineRoute.get("/logs", (c) => {
  const limitParam = c.req.query("limit");
  const limit = limitParam ? Math.min(Number(limitParam), 1000) : 200;
  const logs = readFetchLogs(limit);
  return c.json(ok(logs));
});

// POST /fetch
pipelineRoute.post("/fetch", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = fetchRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const args: string[] = [];
  if (parsed.data.since) {
    args.push("--since", parsed.data.since);
  }
  // No --force flag exposed via API (security constraint)

  const result = await execPython("01_fetch_notion.py", args);

  if (!result.success) {
    const msg = result.output.includes("timed out")
      ? "Fetch timed out"
      : "Fetch failed";
    console.error("Pipeline fetch failed:", result.output);
    return c.json(fail(msg), 500);
  }

  return c.json(ok(result));
});

// POST /extract-qa
pipelineRoute.post("/extract-qa", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = extractQARequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const args: string[] = [];
  if (parsed.data.limit) {
    args.push("--limit", String(parsed.data.limit));
  }
  if (parsed.data.file) {
    // Schema-level SAFE_MD_FILENAME regex already prevents path traversal / injection
    args.push("--file", parsed.data.file);
  }

  const result = await execPython("02_extract_qa.py", args);

  if (!result.success) {
    console.error("Pipeline extract-qa failed:", result.output);
    return c.json(fail("Extract QA failed"), 500);
  }

  return c.json(ok(result));
});

// POST /dedupe-classify
pipelineRoute.post("/dedupe-classify", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = dedupeClassifyRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const args: string[] = [];
  if (parsed.data.skip_dedup) {
    args.push("--skip-dedup");
  }
  if (parsed.data.skip_classify) {
    args.push("--skip-classify");
  }
  if (parsed.data.limit) {
    args.push("--limit", String(parsed.data.limit));
  }

  const result = await execPython("03_dedupe_classify.py", args);

  if (!result.success) {
    console.error("Pipeline dedupe-classify failed:", result.output);
    return c.json(fail("Dedupe/classify failed"), 500);
  }

  return c.json(ok(result));
});

// POST /fetch-articles — fetch Medium + iThome + Google Cases articles (parallel)
pipelineRoute.post("/fetch-articles", async (c) => {
  const [mediumResult, ithelpResult, googleResult] = await Promise.all([
    execPython("01b_fetch_medium.py", []),
    execPython("01c_fetch_ithelp.py", []),
    execPython("01d_fetch_google_cases.py", []),
  ]);

  const allSuccess =
    mediumResult.success && ithelpResult.success && googleResult.success;

  if (!allSuccess) {
    const failures = [mediumResult, ithelpResult, googleResult].filter(
      (r) => !r.success
    );
    console.error(
      "Pipeline fetch-articles partial failure:",
      failures.map((f) => f.output).join("\n")
    );
  }

  return c.json(
    ok({
      success: allSuccess,
      results: [
        {
          source: "medium",
          success: mediumResult.success,
          output: mediumResult.output,
          duration_ms: mediumResult.duration_ms,
        },
        {
          source: "ithelp",
          success: ithelpResult.success,
          output: ithelpResult.output,
          duration_ms: ithelpResult.duration_ms,
        },
        {
          source: "google-cases",
          success: googleResult.success,
          output: googleResult.output,
          duration_ms: googleResult.duration_ms,
        },
      ],
    })
  );
});

// POST /metrics/save — save a metrics snapshot
pipelineRoute.post("/metrics/save", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = metricsSaveSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { metrics, source, tab, label, weeks } = parsed.data;
  const id = generateSnapshotId();
  const created_at = new Date().toISOString();

  const snapshot: MetricsSnapshot = {
    id,
    created_at,
    label,
    source,
    tab,
    weeks,
    metrics,
  };

  const dir = paths.metricsSnapshotsDir;
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  const filePath = resolve(dir, `${id}.json`);
  // Path traversal guard
  if (!filePath.startsWith(dir)) {
    return c.json(fail("Invalid snapshot path"), 400);
  }

  try {
    writeFileSync(filePath, JSON.stringify(snapshot, null, 2), "utf-8");
  } catch {
    return c.json(fail("Failed to save snapshot"), 500);
  }

  return c.json(ok({ id, created_at, label }), 201);
});

// GET /metrics/snapshots — list saved snapshots (metadata only)
pipelineRoute.get("/metrics/snapshots", (c) => {
  const snapshots = listSnapshots();
  return c.json(ok({ items: snapshots, total: snapshots.length }));
});

// DELETE /metrics/snapshots/:id — delete a snapshot
pipelineRoute.delete("/metrics/snapshots/:id", (c) => {
  const id = c.req.param("id");
  const parsed = snapshotIdSchema.safeParse(id);
  if (!parsed.success) {
    return c.json(fail("Invalid snapshot ID format"), 400);
  }

  const dir = paths.metricsSnapshotsDir;
  const filePath = resolve(dir, `${id}.json`);
  // Path traversal guard
  if (!filePath.startsWith(dir)) {
    return c.json(fail("Invalid snapshot path"), 400);
  }

  if (!existsSync(filePath)) {
    return c.json(fail("Snapshot not found"), 404);
  }

  try {
    unlinkSync(filePath);
  } catch {
    return c.json(fail("Failed to delete snapshot"), 500);
  }

  return c.json(ok({ deleted: true, id }));
});

// POST /metrics — parse SEO metrics from source
pipelineRoute.post("/metrics", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = metricsRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { source, tab } = parsed.data;
  const args: string[] = ["--source", source, "--tab", tab, "--json"];

  const result = await execQaTools("load-metrics", args);

  if (!result.success) {
    console.error("Pipeline load-metrics failed:", result.output);
    return c.json(fail("Metrics loading failed"), 500);
  }

  // Python output may contain log lines before/after the JSON block — extract between first `{` and last `}`
  const jsonStart = result.output.indexOf("{");
  const jsonEnd = result.output.lastIndexOf("}");
  const jsonStr = jsonStart >= 0 && jsonEnd > jsonStart
    ? result.output.slice(jsonStart, jsonEnd + 1)
    : result.output;
  try {
    return c.json(ok(JSON.parse(jsonStr)));
  } catch {
    return c.json(ok({ raw: result.output }));
  }
});
