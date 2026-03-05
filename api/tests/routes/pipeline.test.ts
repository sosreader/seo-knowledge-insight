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
const mediumMdDir = join(rawDataDir, "medium_markdown");
const ithelpMdDir = join(rawDataDir, "ithelp_markdown");
const googleCasesMdDir = join(rawDataDir, "google_cases_markdown");
const qaPerMeetingDir = join(outputDir, "qa_per_meeting");
const qaPerArticleDir = join(outputDir, "qa_per_article");
const metricsSnapshotsDir = join(outputDir, "metrics_snapshots");

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
    rawMediumMdDir: mediumMdDir,
    rawIthelpMdDir: ithelpMdDir,
    rawGoogleCasesMdDir: googleCasesMdDir,
    fetchLogsDir,
    qaJsonPath: join(outputDir, "qa_final.json"),
    qaEnrichedJsonPath: join(outputDir, "qa_enriched.json"),
    qaEmbeddingsPath: join(outputDir, "qa_embeddings.npy"),
    qaPerArticleDir,
    sessionsDir: join(outputDir, "sessions"),
    scriptsDir: join(tmpDir, "scripts"),
    accessLogsDir: join(outputDir, "access_logs"),
    metricsSnapshotsDir,
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
  mkdirSync(mediumMdDir, { recursive: true });
  mkdirSync(ithelpMdDir, { recursive: true });
  mkdirSync(googleCasesMdDir, { recursive: true });
  mkdirSync(outputDir, { recursive: true });
  mkdirSync(fetchLogsDir, { recursive: true });
  mkdirSync(qaPerMeetingDir, { recursive: true });
  mkdirSync(qaPerArticleDir, { recursive: true });
  mkdirSync(join(outputDir, "sessions"), { recursive: true });
  mkdirSync(metricsSnapshotsDir, { recursive: true });

  // meetings_index.json
  writeFileSync(
    join(rawDataDir, "meetings_index.json"),
    JSON.stringify([MEETING_1, MEETING_2]),
    "utf-8"
  );

  // Markdown files — meetings
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

  // Markdown files — Medium (2 articles, 1 processed)
  writeFileSync(
    join(mediumMdDir, "ai_seo_strategy.md"),
    "# AI SEO Strategy\n\nMedium article.",
    "utf-8"
  );
  writeFileSync(
    join(mediumMdDir, "gsc_update.md"),
    "# GSC Update\n\nAnother Medium article.",
    "utf-8"
  );

  // Markdown files — iThome (1 article, unprocessed)
  writeFileSync(
    join(ithelpMdDir, "day01_intro.md"),
    "# Day 01 Intro\n\niThome article.",
    "utf-8"
  );

  // Markdown files — Google Cases (2 articles, unprocessed)
  writeFileSync(
    join(googleCasesMdDir, "saramin-case-study.md"),
    "# Saramin Case Study\n\nGoogle case study.",
    "utf-8"
  );
  writeFileSync(
    join(googleCasesMdDir, "vidio-case-study.md"),
    "# Vidio Case Study\n\nAnother Google case study.",
    "utf-8"
  );

  // QA per meeting (only one processed)
  writeFileSync(
    join(qaPerMeetingDir, "test_meeting_qa.json"),
    JSON.stringify({ qa_pairs: [{ q: "Q1", a: "A1" }] }),
    "utf-8"
  );

  // QA per article — all QA JSONs go to qa_per_meeting/ (same as meetings)
  writeFileSync(
    join(qaPerMeetingDir, "ai_seo_strategy_qa.json"),
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
  it("returns pipeline step statuses with all sources", async () => {
    const res = await app.request("/api/v1/pipeline/status");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.steps).toHaveLength(6);

    const [fetchNotion, fetchMedium, fetchIthelp, fetchGoogle, extract, dedupe] =
      body.data.steps;
    expect(fetchNotion.name).toBe("fetch-notion");
    expect(fetchNotion.count).toBe(2); // 2 meeting markdown files
    expect(fetchMedium.name).toBe("fetch-medium");
    expect(fetchMedium.count).toBe(2); // 2 medium markdown files
    expect(fetchIthelp.name).toBe("fetch-ithelp");
    expect(fetchIthelp.count).toBe(1); // 1 ithelp markdown file
    expect(fetchGoogle.name).toBe("fetch-google");
    expect(fetchGoogle.count).toBe(2); // 2 google case study files
    expect(extract.name).toBe("extract-qa");
    expect(extract.count).toBe(2); // 2 qa JSONs in qa_per_meeting/
    expect(extract.detail).toContain("2 / 7"); // 2 extracted out of 7 total
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

// --- GET /pipeline/source-docs ---

describe("GET /api/v1/pipeline/source-docs", () => {
  it("returns all source docs from all collections", async () => {
    const res = await app.request("/api/v1/pipeline/source-docs");
    expect(res.status).toBe(200);
    const body = await res.json();
    // 2 meetings + 2 medium + 1 ithelp + 2 google = 7
    expect(body.data.total).toBe(7);
    expect(body.data.items).toHaveLength(7);
    expect(body.data.offset).toBe(0);
    expect(body.data.limit).toBe(20);
  });

  it("filters by source_type", async () => {
    const res = await app.request("/api/v1/pipeline/source-docs?source_type=article");
    expect(res.status).toBe(200);
    const body = await res.json();
    // 2 medium + 1 ithelp + 2 google = 5
    expect(body.data.total).toBe(5);
    expect(body.data.items.every((i: { source_type: string }) => i.source_type === "article")).toBe(true);
  });

  it("filters by source_collection", async () => {
    const res = await app.request("/api/v1/pipeline/source-docs?source_collection=google-case-studies");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.total).toBe(2);
  });

  it("filters by keyword", async () => {
    const res = await app.request("/api/v1/pipeline/source-docs?keyword=saramin");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.total).toBe(1);
    expect(body.data.items[0].file).toBe("saramin-case-study.md");
  });

  it("filters by is_processed", async () => {
    const res = await app.request("/api/v1/pipeline/source-docs?is_processed=true");
    expect(res.status).toBe(200);
    const body = await res.json();
    // test_meeting.md + ai_seo_strategy.md = 2
    expect(body.data.total).toBe(2);
    expect(body.data.items.every((i: { is_processed: boolean }) => i.is_processed)).toBe(true);
  });

  it("supports pagination with limit and offset", async () => {
    const res = await app.request("/api/v1/pipeline/source-docs?limit=3&offset=2");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.total).toBe(7);
    expect(body.data.items).toHaveLength(3);
    expect(body.data.offset).toBe(2);
    expect(body.data.limit).toBe(3);
  });

  it("includes correct fields on each item", async () => {
    const res = await app.request("/api/v1/pipeline/source-docs?source_collection=seo-meetings");
    expect(res.status).toBe(200);
    const body = await res.json();
    const item = body.data.items[0];
    expect(item).toHaveProperty("file");
    expect(item).toHaveProperty("title");
    expect(item).toHaveProperty("source_type");
    expect(item).toHaveProperty("source_collection");
    expect(item).toHaveProperty("source_url");
    expect(item).toHaveProperty("created_time");
    expect(item).toHaveProperty("size_bytes");
    expect(item).toHaveProperty("is_processed");
    expect(item.source_type).toBe("meeting");
  });
});

// --- GET /pipeline/source-docs/:collection/:file/preview ---

describe("GET /api/v1/pipeline/source-docs/:collection/:file/preview", () => {
  it("returns markdown content for valid collection and file", async () => {
    const res = await app.request(
      "/api/v1/pipeline/source-docs/google-case-studies/saramin-case-study.md/preview"
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.file).toBe("saramin-case-study.md");
    expect(body.data.collection).toBe("google-case-studies");
    expect(body.data.content).toContain("# Saramin Case Study");
    expect(body.data.size_bytes).toBeGreaterThan(0);
  });

  it("returns 400 for unknown collection", async () => {
    const res = await app.request(
      "/api/v1/pipeline/source-docs/unknown-collection/test.md/preview"
    );
    expect(res.status).toBe(400);
  });

  it("returns 400 for path traversal attempt", async () => {
    const res = await app.request(
      "/api/v1/pipeline/source-docs/seo-meetings/..%2F..%2Fetc%2Fpasswd/preview"
    );
    expect(res.status).toBe(400);
  });

  it("returns 404 for non-existent file", async () => {
    const res = await app.request(
      "/api/v1/pipeline/source-docs/seo-meetings/nonexistent.md/preview"
    );
    expect(res.status).toBe(404);
  });

  it("returns meeting markdown via seo-meetings collection", async () => {
    const res = await app.request(
      "/api/v1/pipeline/source-docs/seo-meetings/test_meeting.md/preview"
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.content).toContain("# SEO Meeting");
  });
});

// --- GET /pipeline/unprocessed ---

describe("GET /api/v1/pipeline/unprocessed", () => {
  it("returns unprocessed markdown files from all sources", async () => {
    const res = await app.request("/api/v1/pipeline/unprocessed");
    expect(res.status).toBe(200);
    const body = await res.json();
    // Unprocessed: test_meeting_2.md (meeting), gsc_update.md (medium), day01_intro.md (ithelp),
    //   saramin-case-study.md (google), vidio-case-study.md (google)
    // Processed: test_meeting.md (meeting), ai_seo_strategy.md (medium)
    expect(body.data.total).toBe(5);

    const files = body.data.items.map(
      (i: { file: string }) => i.file
    );
    expect(files).toContain("test_meeting_2.md");
    expect(files).toContain("gsc_update.md");
    expect(files).toContain("day01_intro.md");
    expect(files).toContain("saramin-case-study.md");
    expect(files).toContain("vidio-case-study.md");
  });

  it("includes source_collection for each unprocessed item", async () => {
    const res = await app.request("/api/v1/pipeline/unprocessed");
    const body = await res.json();

    const meeting = body.data.items.find(
      (i: { file: string }) => i.file === "test_meeting_2.md"
    );
    expect(meeting.source_collection).toBe("seo-meetings");

    const medium = body.data.items.find(
      (i: { file: string }) => i.file === "gsc_update.md"
    );
    expect(medium.source_collection).toBe("genehong-medium");

    const ithelp = body.data.items.find(
      (i: { file: string }) => i.file === "day01_intro.md"
    );
    expect(ithelp.source_collection).toBe("ithelp-sc-kpi");

    const google = body.data.items.find(
      (i: { file: string }) => i.file === "saramin-case-study.md"
    );
    expect(google.source_collection).toBe("google-case-studies");
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

// --- POST /pipeline/fetch-articles ---

describe("POST /api/v1/pipeline/fetch-articles", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("triggers Medium, iThome, and Google Cases fetchers", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    const res = await app.request("/api/v1/pipeline/fetch-articles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.success).toBe(true);
    expect(body.data.results).toHaveLength(3);
    expect(body.data.results[0].source).toBe("medium");
    expect(body.data.results[1].source).toBe("ithelp");
    expect(body.data.results[2].source).toBe("google-cases");
    expect(execPython).toHaveBeenCalledWith("01b_fetch_medium.py", []);
    expect(execPython).toHaveBeenCalledWith("01c_fetch_ithelp.py", []);
    expect(execPython).toHaveBeenCalledWith("01d_fetch_google_cases.py", []);
  });

  it("reports partial failure when one script fails", async () => {
    const { execPython } = await import(
      "../../src/services/pipeline-runner.js"
    );
    vi.mocked(execPython)
      .mockResolvedValueOnce({
        success: true,
        output: "Medium OK",
        duration_ms: 1000,
      })
      .mockResolvedValueOnce({
        success: false,
        output: "iThome error",
        duration_ms: 500,
      })
      .mockResolvedValueOnce({
        success: true,
        output: "Google OK",
        duration_ms: 800,
      });
    const res = await app.request("/api/v1/pipeline/fetch-articles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.success).toBe(false);
    expect(body.data.results[0].success).toBe(true);
    expect(body.data.results[1].success).toBe(false);
    expect(body.data.results[2].success).toBe(true);
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

// --- POST /pipeline/metrics/save ---

describe("POST /api/v1/pipeline/metrics/save", () => {
  const validPayload = {
    metrics: { "曝光": { latest: 100, monthly: 0.05, latest_date: "3/1/2026" } },
    source: "https://docs.google.com/spreadsheets/d/abc123",
    tab: "vocus",
    label: "3/1/2026",
    weeks: 2,
  };

  it("saves a snapshot and returns id + created_at + label", async () => {
    const res = await app.request("/api/v1/pipeline/metrics/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(validPayload),
    });
    expect(res.status).toBe(201);
    const body = await res.json();
    expect(body.data.id).toMatch(/^[0-9]{8}-[0-9]{6}$/);
    expect(body.data.label).toBe("3/1/2026");
    expect(body.data.created_at).toBeTruthy();
  });

  it("rejects missing required fields", async () => {
    const res = await app.request("/api/v1/pipeline/metrics/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ metrics: {}, source: "too-short" }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects tab with invalid characters", async () => {
    const res = await app.request("/api/v1/pipeline/metrics/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...validPayload, tab: "bad tab!" }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects weeks out of range", async () => {
    const res = await app.request("/api/v1/pipeline/metrics/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...validPayload, weeks: 100 }),
    });
    expect(res.status).toBe(400);
  });
});

// --- GET /pipeline/metrics/snapshots ---

describe("GET /api/v1/pipeline/metrics/snapshots", () => {
  it("returns saved snapshots list", async () => {
    // Save one snapshot first
    await app.request("/api/v1/pipeline/metrics/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        metrics: { "點擊": { latest: 50 } },
        source: "https://docs.google.com/spreadsheets/d/xyz789",
        tab: "vocus",
        label: "Test Snapshot",
        weeks: 1,
      }),
    });

    const res = await app.request("/api/v1/pipeline/metrics/snapshots");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.data.items)).toBe(true);
    expect(body.data.total).toBeGreaterThan(0);
    const item = body.data.items[0];
    expect(item).toHaveProperty("id");
    expect(item).toHaveProperty("label");
    expect(item).toHaveProperty("created_at");
    expect(item).toHaveProperty("source");
    expect(item).toHaveProperty("tab");
    expect(item).toHaveProperty("weeks");
    // metrics body should NOT be in the list response
    expect(item).not.toHaveProperty("metrics");
  });

  it("returns list with items and total", async () => {
    const res = await app.request("/api/v1/pipeline/metrics/snapshots");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data).toHaveProperty("items");
    expect(body.data).toHaveProperty("total");
  });
});

// --- DELETE /pipeline/metrics/snapshots/:id ---

describe("DELETE /api/v1/pipeline/metrics/snapshots/:id", () => {
  it("deletes an existing snapshot", async () => {
    // Save first
    const saveRes = await app.request("/api/v1/pipeline/metrics/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        metrics: {},
        source: "https://docs.google.com/spreadsheets/d/del123",
        tab: "vocus",
        label: "To Delete",
        weeks: 1,
      }),
    });
    const saveBody = await saveRes.json();
    const id = saveBody.data.id as string;

    const delRes = await app.request(
      `/api/v1/pipeline/metrics/snapshots/${id}`,
      { method: "DELETE" }
    );
    expect(delRes.status).toBe(200);
    const delBody = await delRes.json();
    expect(delBody.data.deleted).toBe(true);
    expect(delBody.data.id).toBe(id);
  });

  it("returns 404 for non-existent snapshot", async () => {
    const res = await app.request(
      "/api/v1/pipeline/metrics/snapshots/20990101-000000",
      { method: "DELETE" }
    );
    expect(res.status).toBe(404);
  });

  it("returns 400 for invalid snapshot id format", async () => {
    const res = await app.request(
      "/api/v1/pipeline/metrics/snapshots/invalid-id",
      { method: "DELETE" }
    );
    expect(res.status).toBe(400);
  });
});
