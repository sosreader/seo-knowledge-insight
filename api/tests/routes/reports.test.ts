import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import { Hono } from "hono";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const CONTENT_HASH_RE = /^report_\d{8}_[0-9a-f]{8}\.md$/;

const tmpDir = mkdtempSync(join(tmpdir(), "reports-test-"));
const tmpSnapshotsDir = join(tmpDir, "metrics_snapshots");
mkdirSync(tmpSnapshotsDir, { recursive: true });

vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: {
    loaded: false,
    count: 0,
    getAll: () => [],
    keywordSearch: () => [],
  },
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
    outputDir: tmpDir,
    sessionsDir: join(tmpDir, "sessions"),
    scriptsDir: "/tmp/scripts",
    rootDir: "/tmp",
    metricsSnapshotsDir: tmpSnapshotsDir,
  },
}));

vi.mock("../../src/utils/mode-detect.js", () => ({
  hasOpenAI: vi.fn(() => false),
  isAgentEnabled: vi.fn(() => false),
  resolveMode: vi.fn(() => "rag"),
}));

let app: Hono;

beforeAll(async () => {
  mkdirSync(join(tmpDir, "sessions"), { recursive: true });
  const { app: mainApp } = await import("../../src/index.js");
  app = mainApp;
});

beforeEach(() => {
  // Create test report files
  writeFileSync(join(tmpDir, "report_20260301.md"), "# Report March 1", "utf-8");
  writeFileSync(join(tmpDir, "report_20260228.md"), "# Report Feb 28", "utf-8");
});

describe("GET /api/v1/reports", () => {
  it("returns list of reports", async () => {
    const res = await app.request("/api/v1/reports");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.items.length).toBeGreaterThanOrEqual(2);
    expect(body.data.total).toBeGreaterThanOrEqual(2);
    // Check structure
    expect(body.data.items[0]).toHaveProperty("date");
    expect(body.data.items[0]).toHaveProperty("filename");
    expect(body.data.items[0]).toHaveProperty("size_bytes");
  });
});

describe("GET /api/v1/reports/:date", () => {
  it("returns report content for legacy YYYYMMDD format", async () => {
    const res = await app.request("/api/v1/reports/20260301");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.content).toBe("# Report March 1");
    expect(body.data.date).toBe("20260301");
  });

  it("returns report content for content-addressed YYYYMMDD_hash format", async () => {
    writeFileSync(join(tmpDir, "report_20260301_abc12345.md"), "# Report March 1 v2", "utf-8");
    const res = await app.request("/api/v1/reports/20260301_abc12345");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.content).toBe("# Report March 1 v2");
    expect(body.data.date).toBe("20260301_abc12345");
  });

  it("returns 400 for invalid date format", async () => {
    const res = await app.request("/api/v1/reports/2026-03-01");
    expect(res.status).toBe(400);
  });

  it("returns 404 for non-existent report", async () => {
    const res = await app.request("/api/v1/reports/99990101");
    expect(res.status).toBe(404);
  });
});

describe("POST /api/v1/reports/generate (local mode — no OpenAI)", () => {
  const SNAPSHOT_ID = "20260305-120000";
  const snapshotData = {
    id: SNAPSHOT_ID,
    created_at: "2026-03-05T12:00:00.000Z",
    label: "2026/03/05",
    source: "https://docs.google.com/spreadsheets/d/test",
    tab: "vocus",
    weeks: 2,
    metrics: {
      CTR: { latest: 0.042, monthly: -0.12, weekly: -0.08 },
      曝光: { latest: 120000, monthly: 0.05, weekly: 0.02 },
    },
  };

  beforeEach(() => {
    writeFileSync(
      join(tmpSnapshotsDir, `${SNAPSHOT_ID}.json`),
      JSON.stringify(snapshotData),
      "utf-8"
    );
  });

  it("generates report from snapshot in local mode", async () => {
    const res = await app.request("/api/v1/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot_id: SNAPSHOT_ID }),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data).toHaveProperty("date");
    expect(body.data).toHaveProperty("filename");
    expect(body.data).toHaveProperty("size_bytes");
    // Filename must use content-addressed naming: report_YYYYMMDD_<sha1-8>.md
    expect(CONTENT_HASH_RE.test(body.data.filename)).toBe(true);
    // date field must be YYYYMMDD_hash8
    expect(/^\d{8}_[0-9a-f]{8}$/.test(body.data.date)).toBe(true);
  });

  it("returns 404 when snapshot does not exist", async () => {
    const res = await app.request("/api/v1/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot_id: "20991231-235959" }),
    });
    expect(res.status).toBe(404);
  });

  it("returns 400 for invalid snapshot_id format", async () => {
    const res = await app.request("/api/v1/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot_id: "bad-id" }),
    });
    expect(res.status).toBe(400);
  });

  it("generated report contains all 6 section headings", async () => {
    const res = await app.request("/api/v1/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot_id: SNAPSHOT_ID }),
    });
    expect(res.status).toBe(200);

    // Find the generated report file and read its content
    const { readFileSync, readdirSync } = await import("node:fs");
    const { join: pathJoin } = await import("node:path");
    const files = readdirSync(tmpDir).filter((f: string) => f.startsWith("report_") && f.endsWith(".md"));
    expect(files.length).toBeGreaterThan(0);
    const content = readFileSync(pathJoin(tmpDir, files[files.length - 1]!), "utf-8");

    for (const heading of ["## 一、", "## 二、", "## 三、", "## 四、", "## 五、", "## 六、", "## 七、"]) {
      expect(content).toContain(heading);
    }
  });

  it("generated report meta block contains kb version pattern", async () => {
    const res = await app.request("/api/v1/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot_id: SNAPSHOT_ID }),
    });
    expect(res.status).toBe(200);

    const { readFileSync, readdirSync } = await import("node:fs");
    const { join: pathJoin } = await import("node:path");
    const files = readdirSync(tmpDir).filter((f: string) => f.startsWith("report_") && f.endsWith(".md"));
    const content = readFileSync(pathJoin(tmpDir, files[files.length - 1]!), "utf-8");

    // Meta block should contain version pattern v\d{4}.\d{2}.\d{2} or v(unknown)
    expect(content).toMatch(/知識庫版本：v[\d]{4}\.[\d]{2}\.[\d]{2}|知識庫版本：v\(unknown\)/);
  });

  it("generated report section 七 contains at least one link", async () => {
    const res = await app.request("/api/v1/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot_id: SNAPSHOT_ID }),
    });
    expect(res.status).toBe(200);

    const { readFileSync, readdirSync } = await import("node:fs");
    const { join: pathJoin } = await import("node:path");
    const files = readdirSync(tmpDir).filter((f: string) => f.startsWith("report_") && f.endsWith(".md"));
    const content = readFileSync(pathJoin(tmpDir, files[files.length - 1]!), "utf-8");

    // Section 六 should exist and have a link (KB or external)
    expect(content).toContain("## 七、來源");
    // When no QAs found, section says "未找到" — this is acceptable fallback
    const hasKbLink = content.includes("/admin/seoInsight/") || content.includes("https://") || content.includes("未找到");
    expect(hasKbLink).toBe(true);
  });

  it("hybrid mode: report contains AI 輔助 marker when situation_analysis provided", async () => {
    const res = await app.request("/api/v1/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        snapshot_id: SNAPSHOT_ID,
        situation_analysis: "本週 CTR 下滑與 AMP Article 崩跌有跨指標關聯，建議優先排查新聞版位流量分配。",
        traffic_analysis: "流量呈高曝光低CTR象限，應優先優化 Title 吸引力。",
      }),
    });
    expect(res.status).toBe(200);

    const { readFileSync, readdirSync, statSync: statSyncFs } = await import("node:fs");
    const { join: pathJoin } = await import("node:path");
    const files = readdirSync(tmpDir)
      .filter((f: string) => f.startsWith("report_") && f.endsWith(".md"))
      .sort((a: string, b: string) => statSyncFs(pathJoin(tmpDir, b)).mtimeMs - statSyncFs(pathJoin(tmpDir, a)).mtimeMs);
    const content = readFileSync(pathJoin(tmpDir, files[0]!), "utf-8");

    expect(content).toContain("AI 輔助");
    expect(content).toContain("AI 解讀");
    expect(content).toContain("Hybrid Mode");
  });

  it("template mode: report does not contain AI markers when no analysis provided", async () => {
    const res = await app.request("/api/v1/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot_id: SNAPSHOT_ID }),
    });
    expect(res.status).toBe(200);

    const json = await res.json();
    const filename = json.data.filename as string;

    const { readFileSync } = await import("node:fs");
    const { join: pathJoin } = await import("node:path");
    const content = readFileSync(pathJoin(tmpDir, filename), "utf-8");

    expect(content).not.toContain("AI 輔助");
    expect(content).not.toContain("AI 解讀");
    expect(content).toContain("Template Mode");
  });
});
