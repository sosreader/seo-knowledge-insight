import { Hono } from "hono";
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import {
  fetchRequestSchema,
  extractQARequestSchema,
  dedupeClassifyRequestSchema,
  type MeetingEntry,
  type MeetingsResponse,
  type MeetingPreviewResponse,
  type UnprocessedItem,
  type UnprocessedResponse,
  type FetchLogEntry,
  type FetchLogsResponse,
  type PipelineStepStatus,
  type PipelineStatusResponse,
} from "../schemas/pipeline.js";
import { execPython } from "../services/pipeline-runner.js";
import { paths } from "../config.js";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const FETCH_LOG_PATTERN = /^fetch_\d{4}-\d{2}-\d{2}\.jsonl$/;

// --- Helpers ---

function readMeetingsIndex(): readonly MeetingEntry[] {
  const indexPath = join(paths.rawDataDir, "meetings_index.json");
  if (!existsSync(indexPath)) return [];

  try {
    const raw = readFileSync(indexPath, "utf-8");
    const entries = JSON.parse(raw) as MeetingEntry[];
    return entries.map((e) => ({
      ...e,
      status: e.status ?? "fetched",
    }));
  } catch {
    return [];
  }
}

function countQAPerMeeting(): number {
  const dir = join(paths.outputDir, "qa_per_meeting");
  if (!existsSync(dir)) return 0;
  return readdirSync(dir).filter((f) => f.endsWith("_qa.json")).length;
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
  const mdCount = existsSync(mdDir)
    ? readdirSync(mdDir).filter((f) => f.endsWith(".md")).length
    : 0;

  const extractedCount = countQAPerMeeting();
  const finalCount = countQAFinal();

  const steps: PipelineStepStatus[] = [
    {
      name: "fetch-notion",
      label: "Notion 擷取",
      count: mdCount,
      detail: `${meetings.length} 筆會議，${mdCount} 份 Markdown`,
    },
    {
      name: "extract-qa",
      label: "Q&A 萃取",
      count: extractedCount,
      detail: `已萃取 ${extractedCount} / ${mdCount} 份`,
    },
    {
      name: "dedupe-classify",
      label: "去重 + 分類",
      count: finalCount,
      detail: `${finalCount} 筆 Q&A（去重後）`,
    },
  ];

  return { steps };
}

function findUnprocessed(): readonly UnprocessedItem[] {
  const mdDir = join(paths.rawDataDir, "markdown");
  const qaDir = join(paths.outputDir, "qa_per_meeting");

  if (!existsSync(mdDir)) return [];

  const mdFiles = readdirSync(mdDir).filter((f) => f.endsWith(".md"));
  const processedSet = new Set(
    existsSync(qaDir)
      ? readdirSync(qaDir)
          .filter((f) => f.endsWith("_qa.json"))
          .map((f) => f.replace(/_qa\.json$/, ".md"))
      : []
  );

  return mdFiles
    .filter((f) => !processedSet.has(f))
    .map((f) => ({
      file: f,
      title: f.replace(/\.md$/, "").replace(/_/g, " "),
    }));
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
    // Validate filename to prevent injection
    if (parsed.data.file.includes("..") || parsed.data.file.includes("/")) {
      return c.json(fail("Invalid file parameter"), 400);
    }
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
