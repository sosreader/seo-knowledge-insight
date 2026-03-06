import { Hono } from "hono";
import { readFileSync, existsSync, statSync, mkdirSync, writeFileSync, unlinkSync } from "node:fs";
import { resolve } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import {
  fetchRequestSchema,
  extractQARequestSchema,
  dedupeClassifyRequestSchema,
  metricsRequestSchema,
  metricsSaveSchema,
  snapshotIdSchema,
  sourceDocsQuerySchema,
  type MeetingsResponse,
  type MeetingPreviewResponse,
  type UnprocessedResponse,
  type SourceDocsResponse,
  type SourceDocPreviewResponse,
  type MetricsSnapshot,
} from "../schemas/pipeline.js";
import { execPython, execQaTools } from "../services/pipeline-runner.js";
import { paths } from "../config.js";
import { hasSupabase } from "../store/supabase-client.js";
import { SupabaseSnapshotStore } from "../store/supabase-snapshot-store.js";
import {
  UUID_RE,
  SAFE_FILENAME_RE,
  SNAPSHOT_ID_RE,
  readMeetingsIndex,
  buildPipelineStatus,
  findUnprocessed,
  readFetchLogs,
  getCollectionDirMap,
  buildSourceDocs,
  generateSnapshotId,
  listSnapshots,
} from "./pipeline-fs.js";

const supabaseSnapshotStore = hasSupabase() ? new SupabaseSnapshotStore() : null;

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

  const entry = getCollectionDirMap()[collection];
  if (!entry) {
    return c.json(fail("Unknown collection"), 400);
  }

  if (!SAFE_FILENAME_RE.test(file)) {
    return c.json(fail("Invalid filename"), 400);
  }

  const filePath = resolve(entry.dir, file);

  if (!filePath.startsWith(entry.dir)) {
    return c.json(fail("Invalid file path"), 400);
  }

  if (!existsSync(filePath)) {
    return c.json(fail("File not found"), 404);
  }

  const content = readFileSync(filePath, "utf-8");
  const size_bytes = statSync(filePath).size;

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

// POST /fetch-articles
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

// POST /metrics/save
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

  if (supabaseSnapshotStore) {
    try {
      await supabaseSnapshotStore.save(snapshot);
    } catch {
      return c.json(fail("Failed to save snapshot"), 500);
    }
    return c.json(ok({ id, created_at, label }), 201);
  }

  const dir = paths.metricsSnapshotsDir;
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  const filePath = resolve(dir, `${id}.json`);
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

// GET /metrics/snapshots
pipelineRoute.get("/metrics/snapshots", async (c) => {
  if (supabaseSnapshotStore) {
    const snapshots = await supabaseSnapshotStore.list();
    return c.json(ok({ items: snapshots, total: snapshots.length }));
  }
  const snapshots = listSnapshots();
  return c.json(ok({ items: snapshots, total: snapshots.length }));
});

// DELETE /metrics/snapshots/:id
pipelineRoute.delete("/metrics/snapshots/:id", async (c) => {
  const id = c.req.param("id");
  const parsed = snapshotIdSchema.safeParse(id);
  if (!parsed.success) {
    return c.json(fail("Invalid snapshot ID format"), 400);
  }

  if (supabaseSnapshotStore) {
    const deleted = await supabaseSnapshotStore.delete(id);
    if (!deleted) {
      return c.json(fail("Snapshot not found"), 404);
    }
    return c.json(ok({ deleted: true, id }));
  }

  const dir = paths.metricsSnapshotsDir;
  const filePath = resolve(dir, `${id}.json`);
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

// POST /metrics
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
