import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import { Hono } from "hono";
import {
  mkdtempSync,
  writeFileSync,
  mkdirSync,
  existsSync,
} from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const tmpDir = mkdtempSync(join(tmpdir(), "pipeline-test-"));
const rawDataDir = join(tmpDir, "raw_data");
const outputDir = join(tmpDir, "output");
const fetchLogsDir = join(outputDir, "fetch_logs");
const markdownDir = join(rawDataDir, "markdown");
const qaPerMeetingDir = join(outputDir, "qa_per_meeting");

vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: { loaded: false, count: 0 },
}));

vi.mock("../../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
  },
  paths: {
    rootDir: tmpDir,
    outputDir,
    rawDataDir,
    fetchLogsDir,
    qaJsonPath: join(outputDir, "qa_final.json"),
    qaEnrichedJsonPath: join(outputDir, "qa_enriched.json"),
    qaEmbeddingsPath: join(outputDir, "qa_embeddings.npy"),
    sessionsDir: join(outputDir, "sessions"),
    scriptsDir: join(tmpDir, "scripts"),
    accessLogsDir: join(outputDir, "access_logs"),
  },
}));

vi.mock("../../src/services/pipeline-runner.js", () => ({
  execPython: vi.fn().mockResolvedValue({
    success: true,
    output: "Pipeline step completed",
    duration_ms: 1234,
  }),
  execQaTools: vi.fn().mockResolvedValue({
    success: true,
    output: "OK",
    duration_ms: 100,
  }),
}));

let app: Hono;

const MEETING_1 = {
  title: "SEO 會議_2024/05/02",
  id: "052d1af9-3b5b-4de6-88e0-ac006848ed45",
  created_time: "2024-05-15T01:55:00.000Z",
  last_edited_time: "2024-09-18T01:01:00.000Z",
  url: "https://www.notion.so/test-page",
  json_file: "notion_json/test_meeting.json",
  md_file: "markdown/test_meeting.md",
};

const MEETING_2 = {
  title: "SEO 會議_2024/06/01",
  id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  created_time: "2024-06-01T00:00:00.000Z",
  last_edited_time: "2024-06-15T00:00:00.000Z",
  url: "https://www.notion.so/test-page-2",
  json_file: "notion_json/test_meeting_2.json",
  md_file: "markdown/test_meeting_2.md",
};

function setupTestData() {
  // Create directories
  mkdirSync(rawDataDir, { recursive: true });
  mkdirSync(markdownDir, { recursive: true });
  mkdirSync(outputDir, { recursive: true });
  mkdirSync(fetchLogsDir, { recursive: true });
  mkdirSync(qaPerMeetingDir, { recursive: true });
  mkdirSync(join(outputDir, "sessions"), { recursive: true });

  // meetings_index.json
  writeFileSync(
    join(rawDataDir, "meetings_index.json"),
    JSON.stringify([MEETING_1, MEETING_2]),
    "utf-8"
  );

  // Markdown files
  writeFileSync(
    join(markdownDir, "test_meeting.md"),
    "# SEO Meeting\n\nContent here.",
    "utf-8"
  );
  writeFileSync(
    join(markdownDir, "test_meeting_2.md"),
    "# SEO Meeting 2\n\nMore content.",
    "utf-8"
  );

  // QA per meeting (only one processed)
  writeFileSync(
    join(qaPerMeetingDir, "test_meeting_qa.json"),
    JSON.stringify({ qa_pairs: [{ q: "Q1", a: "A1" }] }),
    "utf-8"
  );

  // qa_final.json (dict format with qa_database array)
  writeFileSync(
    join(outputDir, "qa_final.json"),
    JSON.stringify({
      version: "2.0",
      total_count: 2,
      original_count: 3,
      meetings_processed: 2,
      qa_database: [
        { id: "abc123", question: "Q1", answer: "A1" },
        { id: "def456", question: "Q2", answer: "A2" },
      ],
    }),
    "utf-8"
  );

  // Fetch logs
  const logEntries = [
    JSON.stringify({
      event: "fetch_complete",
      session_id: "abc123",
      ts: "2026-03-04T03:51:15.660Z",
      page_id: MEETING_1.id,
      page_title: MEETING_1.title,
    }),
    JSON.stringify({
      event: "fetch_skip",
      session_id: "abc123",
      ts: "2026-03-04T03:51:16.000Z",
      page_id: MEETING_2.id,
      page_title: MEETING_2.title,
      skipped_reason: "since_time_filter",
    }),
  ];
  writeFileSync(
    join(fetchLogsDir, "fetch_2026-03-04.jsonl"),
    logEntries.join("\n"),
    "utf-8"
  );
}

beforeAll(async () => {
  setupTestData();
  const { app: mainApp } = await import("../../src/index.js");
  app = mainApp;
});

// --- GET /pipeline/status ---

describe("GET /api/v1/pipeline/status", () => {
  it("returns pipeline step statuses", async () => {
    const res = await app.request("/api/v1/pipeline/status");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.steps).toHaveLength(3);

    const [fetch, extract, dedupe] = body.data.steps;
    expect(fetch.name).toBe("fetch-notion");
    expect(fetch.count).toBe(2); // 2 markdown files
    expect(extract.name).toBe("extract-qa");
    expect(extract.count).toBe(1); // 1 qa_per_meeting file
    expect(dedupe.name).toBe("dedupe-classify");
    expect(dedupe.count).toBe(2); // 2 qa_final items
  });
});

// --- GET /pipeline/meetings ---

describe("GET /api/v1/pipeline/meetings", () => {
  it("returns meeting list", async () => {
    const res = await app.request("/api/v1/pipeline/meetings");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.items).toHaveLength(2);
    expect(body.data.total).toBe(2);
    expect(body.data.items[0].title).toBe("SEO 會議_2024/05/02");
    expect(body.data.items[0].id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
    );
  });

  it("includes status field with default 'fetched'", async () => {
    const res = await app.request("/api/v1/pipeline/meetings");
    const body = await res.json();
    expect(body.data.items[0].status).toBe("fetched");
  });
});

// --- GET /pipeline/meetings/:id/preview ---

describe("GET /api/v1/pipeline/meetings/:id/preview", () => {
  it("returns markdown content for valid meeting", async () => {
    const res = await app.request(
      `/api/v1/pipeline/meetings/${MEETING_1.id}/preview`
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.id).toBe(MEETING_1.id);
    expect(body.data.title).toBe(MEETING_1.title);
    expect(body.data.content).toContain("# SEO Meeting");
    expect(body.data.size_bytes).toBeGreaterThan(0);
  });

  it("returns 400 for invalid UUID format", async () => {
    const res = await app.request(
      "/api/v1/pipeline/meetings/not-a-uuid/preview"
    );
    expect(res.status).toBe(400);
  });

  it("returns 404 for non-existent meeting", async () => {
    const res = await app.request(
      "/api/v1/pipeline/meetings/11111111-2222-3333-4444-555555555555/preview"
    );
    expect(res.status).toBe(404);
  });
});

// --- GET /pipeline/unprocessed ---

describe("GET /api/v1/pipeline/unprocessed", () => {
  it("returns unprocessed markdown files", async () => {
    const res = await app.request("/api/v1/pipeline/unprocessed");
    expect(res.status).toBe(200);
    const body = await res.json();
    // test_meeting.md has a qa file, test_meeting_2.md does not
    expect(body.data.items).toHaveLength(1);
    expect(body.data.items[0].file).toBe("test_meeting_2.md");
    expect(body.data.total).toBe(1);
  });
});

// --- GET /pipeline/logs ---

describe("GET /api/v1/pipeline/logs", () => {
  it("returns fetch log entries", async () => {
    const res = await app.request("/api/v1/pipeline/logs");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.files).toContain("fetch_2026-03-04.jsonl");
    expect(body.data.entries).toHaveLength(2);
    expect(body.data.entries[0].event).toBe("fetch_complete");
    expect(body.data.total).toBe(2);
  });

  it("respects limit parameter", async () => {
    const res = await app.request("/api/v1/pipeline/logs?limit=1");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.entries).toHaveLength(1);
  });
});

// --- POST /pipeline/fetch ---

describe("POST /api/v1/pipeline/fetch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("triggers fetch with no params", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.success).toBe(true);
    expect(execPython).toHaveBeenCalledWith("01_fetch_notion.py", []);
  });

  it("passes since parameter", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ since: "2026-02-27" }),
    });
    expect(res.status).toBe(200);
    expect(execPython).toHaveBeenCalledWith("01_fetch_notion.py", [
      "--since",
      "2026-02-27",
    ]);
  });

  it("accepts relative day format for since", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ since: "7d" }),
    });
    expect(res.status).toBe(200);
    expect(execPython).toHaveBeenCalledWith("01_fetch_notion.py", [
      "--since",
      "7d",
    ]);
  });

  it("rejects invalid since format", async () => {
    const res = await app.request("/api/v1/pipeline/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ since: "invalid" }),
    });
    expect(res.status).toBe(400);
  });

  it("returns 500 on script failure", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    vi.mocked(execPython).mockResolvedValueOnce({
      success: false,
      output: "NOTION_TOKEN not set",
      duration_ms: 500,
    });
    const res = await app.request("/api/v1/pipeline/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(500);
  });
});

// --- POST /pipeline/extract-qa ---

describe("POST /api/v1/pipeline/extract-qa", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("triggers extract with no params", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/extract-qa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(200);
    expect(execPython).toHaveBeenCalledWith("02_extract_qa.py", []);
  });

  it("passes limit parameter", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/extract-qa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: 5 }),
    });
    expect(res.status).toBe(200);
    expect(execPython).toHaveBeenCalledWith("02_extract_qa.py", [
      "--limit",
      "5",
    ]);
  });

  it("passes file parameter", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/extract-qa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file: "test_meeting.md" }),
    });
    expect(res.status).toBe(200);
    expect(execPython).toHaveBeenCalledWith("02_extract_qa.py", [
      "--file",
      "test_meeting.md",
    ]);
  });

  it("rejects path traversal in file param", async () => {
    const res = await app.request("/api/v1/pipeline/extract-qa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file: "../../../etc/passwd" }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects file param with slashes", async () => {
    const res = await app.request("/api/v1/pipeline/extract-qa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file: "subdir/file.md" }),
    });
    expect(res.status).toBe(400);
  });
});

// --- POST /pipeline/dedupe-classify ---

describe("POST /api/v1/pipeline/dedupe-classify", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("triggers dedupe with no params", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/dedupe-classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(200);
    expect(execPython).toHaveBeenCalledWith("03_dedupe_classify.py", []);
  });

  it("passes skip flags", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/dedupe-classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skip_dedup: true, skip_classify: true }),
    });
    expect(res.status).toBe(200);
    expect(execPython).toHaveBeenCalledWith("03_dedupe_classify.py", [
      "--skip-dedup",
      "--skip-classify",
    ]);
  });

  it("passes limit parameter", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/dedupe-classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: 10 }),
    });
    expect(res.status).toBe(200);
    expect(execPython).toHaveBeenCalledWith("03_dedupe_classify.py", [
      "--limit",
      "10",
    ]);
  });

  it("returns 500 on script failure", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    vi.mocked(execPython).mockResolvedValueOnce({
      success: false,
      output: "Error in dedupe",
      duration_ms: 1000,
    });
    const res = await app.request("/api/v1/pipeline/dedupe-classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(500);
  });
});
