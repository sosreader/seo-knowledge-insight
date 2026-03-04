import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import { Hono } from "hono";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const tmpDir = mkdtempSync(join(tmpdir(), "reports-test-"));

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
    outputDir: tmpDir,
    sessionsDir: join(tmpDir, "sessions"),
    scriptsDir: "/tmp/scripts",
    rootDir: "/tmp",
  },
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
