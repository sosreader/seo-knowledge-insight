/**
 * Tests for audit-logger — JSONL access log.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { existsSync, appendFileSync, mkdirSync } from "node:fs";

// Mock node:fs
vi.mock("node:fs", () => ({
  existsSync: vi.fn(),
  appendFileSync: vi.fn(),
  mkdirSync: vi.fn(),
}));

// Mock config
vi.mock("../../src/config.js", () => ({
  config: {
    SUPABASE_URL: "",
    SUPABASE_ANON_KEY: "",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
  },
  paths: { accessLogsDir: "/tmp/test-logs" },
}));

import { logListQa, logSearch, logChat } from "../../src/utils/audit-logger.js";

describe("audit-logger", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("logListQa writes event to JSONL", () => {
    vi.mocked(existsSync).mockReturnValue(true);
    logListQa({
      filters: { category: "SEO" },
      returnedIds: ["id1", "id2"],
      total: 2,
      clientIp: "127.0.0.1",
    });

    expect(appendFileSync).toHaveBeenCalledOnce();
    const [, content] = vi.mocked(appendFileSync).mock.calls[0]!;
    const parsed = JSON.parse((content as string).trim());
    expect(parsed.event).toBe("list_qa");
    expect(parsed.total).toBe(2);
    expect(parsed.clientIp).toBe("127.0.0.1");
    expect(parsed.timestamp).toBeDefined();
  });

  it("logSearch writes event with query info", () => {
    vi.mocked(existsSync).mockReturnValue(true);
    logSearch({
      query: "LCP optimization",
      topK: 5,
      category: null,
      returnedIds: ["id1"],
      sourceTitles: ["Meeting 1"],
      clientIp: null,
    });

    expect(appendFileSync).toHaveBeenCalledOnce();
    const [, content] = vi.mocked(appendFileSync).mock.calls[0]!;
    const parsed = JSON.parse((content as string).trim());
    expect(parsed.event).toBe("search");
    expect(parsed.query).toBe("LCP optimization");
  });

  it("logChat writes event with message", () => {
    vi.mocked(existsSync).mockReturnValue(true);
    logChat({
      message: "What is SEO?",
      returnedIds: ["id1"],
      sourceTitles: ["Source 1"],
      clientIp: "10.0.0.1",
    });

    expect(appendFileSync).toHaveBeenCalledOnce();
    const [, content] = vi.mocked(appendFileSync).mock.calls[0]!;
    const parsed = JSON.parse((content as string).trim());
    expect(parsed.event).toBe("chat");
    expect(parsed.message).toBe("What is SEO?");
  });

  it("creates log directory when it does not exist", () => {
    vi.mocked(existsSync).mockReturnValue(false);
    logListQa({
      filters: {},
      returnedIds: [],
      total: 0,
      clientIp: null,
    });

    expect(mkdirSync).toHaveBeenCalledWith("/tmp/test-logs", { recursive: true });
  });

  it("does not throw when appendFileSync fails", () => {
    vi.mocked(existsSync).mockReturnValue(true);
    vi.mocked(appendFileSync).mockImplementation(() => {
      throw new Error("disk full");
    });

    expect(() =>
      logListQa({ filters: {}, returnedIds: [], total: 0, clientIp: null })
    ).not.toThrow();
  });
});
