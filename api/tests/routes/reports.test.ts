import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import { Hono } from "hono";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

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
  it("returns report content", async () => {
    const res = await app.request("/api/v1/reports/20260301");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.content).toBe("# Report March 1");
    expect(body.data.date).toBe("20260301");
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
});
