import { describe, it, expect, vi, beforeAll, beforeEach, afterAll } from "vitest";
import { Hono } from "hono";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const tmpDir = mkdtempSync(join(tmpdir(), "meeting-prep-test-"));
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

const SAMPLE_META = `<!-- meeting_prep_meta {"date":"2026-03-12","scores":{"eeat":{"experience":3,"expertise":4,"authoritativeness":3,"trustworthiness":4},"maturity":{"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"}},"alert_down_count":5,"question_count":15,"generation_mode":"claude-code"} -->`;

const SAMPLE_CONTENT = `# 顧問會議準備深度研究報告\n\n## 零、執行摘要\n\nTest content\n\n${SAMPLE_META}`;

beforeAll(async () => {
  mkdirSync(join(tmpDir, "sessions"), { recursive: true });
  const { app: mainApp } = await import("../../src/index.js");
  app = mainApp;
});

beforeEach(() => {
  writeFileSync(
    join(tmpDir, "meeting_prep_20260312_a1b2c3d4.md"),
    SAMPLE_CONTENT,
    "utf-8",
  );
  writeFileSync(
    join(tmpDir, "meeting_prep_20260305_e5f6a7b8.md"),
    "# Older prep\n\n" + SAMPLE_META,
    "utf-8",
  );
});

describe("GET /api/v1/meeting-prep", () => {
  it("returns list of meeting prep reports", async () => {
    const res = await app.request("/api/v1/meeting-prep");
    expect(res.status).toBe(200);
    const json = (await res.json()) as { data: { items: unknown[]; total: number } };
    expect(json.data.total).toBeGreaterThanOrEqual(2);
    expect(json.data.items).toBeInstanceOf(Array);
  });

  it("each item has date, filename, size_bytes", async () => {
    const res = await app.request("/api/v1/meeting-prep");
    const json = (await res.json()) as { data: { items: Array<Record<string, unknown>> } };
    const item = json.data.items[0]!;
    expect(item).toHaveProperty("date");
    expect(item).toHaveProperty("filename");
    expect(item).toHaveProperty("size_bytes");
  });

  it("items contain parsed meta", async () => {
    const res = await app.request("/api/v1/meeting-prep");
    const json = (await res.json()) as { data: { items: Array<Record<string, unknown>> } };
    const withMeta = json.data.items.find((i) => i.meta != null);
    expect(withMeta).toBeDefined();
    const meta = withMeta!.meta as Record<string, unknown>;
    expect(meta).toHaveProperty("date");
    expect(meta).toHaveProperty("scores");
    expect(meta).toHaveProperty("generation_mode", "claude-code");
  });
});

describe("GET /api/v1/meeting-prep/:date", () => {
  it("returns report by date_hash key", async () => {
    const res = await app.request("/api/v1/meeting-prep/20260312_a1b2c3d4");
    expect(res.status).toBe(200);
    const json = (await res.json()) as { data: { content: string; meta: unknown } };
    expect(json.data.content).toContain("執行摘要");
    expect(json.data.meta).toBeDefined();
  });

  it("fuzzy matches by date-only prefix", async () => {
    const res = await app.request("/api/v1/meeting-prep/20260312");
    expect(res.status).toBe(200);
    const json = (await res.json()) as { data: { filename: string } };
    expect(json.data.filename).toContain("20260312");
  });

  it("returns 404 for non-existent date", async () => {
    const res = await app.request("/api/v1/meeting-prep/20250101");
    expect(res.status).toBe(404);
  });

  it("returns 400 for invalid date format", async () => {
    const res = await app.request("/api/v1/meeting-prep/invalid");
    expect(res.status).toBe(400);
  });

  it("gracefully handles malformed meta JSON", async () => {
    writeFileSync(
      join(tmpDir, "meeting_prep_20260301_deadbeef.md"),
      "# Bad meta\n\n<!-- meeting_prep_meta {broken json -->",
      "utf-8",
    );
    const res = await app.request("/api/v1/meeting-prep/20260301_deadbeef");
    expect(res.status).toBe(200);
    const json = (await res.json()) as { data: { meta: unknown } };
    expect(json.data.meta).toBeUndefined();
  });

  it("handles file without meta comment", async () => {
    writeFileSync(
      join(tmpDir, "meeting_prep_20260215_abcd1234.md"),
      "# No meta at all\n\nJust content.",
      "utf-8",
    );
    const res = await app.request("/api/v1/meeting-prep/20260215_abcd1234");
    expect(res.status).toBe(200);
    const json = (await res.json()) as { data: { meta: unknown; content: string } };
    expect(json.data.meta).toBeUndefined();
    expect(json.data.content).toContain("No meta at all");
  });
});

afterAll(() => {
  rmSync(tmpDir, { recursive: true, force: true });
});
