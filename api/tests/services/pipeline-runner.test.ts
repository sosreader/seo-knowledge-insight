/**
 * Tests for pipeline-runner — Python script execution wrapper.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

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
  paths: {
    scriptsDir: "/fake/scripts",
    rootDir: "/fake/root",
    outputDir: "/tmp",
  },
}));

const { mockExecFileAsync } = vi.hoisted(() => ({
  mockExecFileAsync: vi.fn(),
}));

vi.mock("node:child_process", () => ({
  execFile: () => {},
}));

vi.mock("node:util", () => ({
  promisify: () => mockExecFileAsync,
}));

import { execPython, execQaTools } from "../../src/services/pipeline-runner.js";

describe("pipeline-runner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("execPython", () => {
    it("returns success with stdout", async () => {
      mockExecFileAsync.mockResolvedValueOnce({
        stdout: '{"result": "ok"}\n',
        stderr: "",
      });

      const result = await execPython("test_script.py", ["--arg1"]);
      expect(result.success).toBe(true);
      expect(result.output).toBe('{"result": "ok"}');
      expect(result.duration_ms).toBeGreaterThanOrEqual(0);
    });

    it("logs stderr but still succeeds", async () => {
      mockExecFileAsync.mockResolvedValueOnce({
        stdout: "output",
        stderr: "some warning",
      });

      const result = await execPython("script.py");
      expect(result.success).toBe(true);
      expect(result.output).toBe("output");
    });

    it("returns failure on error", async () => {
      mockExecFileAsync.mockRejectedValueOnce(
        Object.assign(new Error("exit code 1"), {
          stdout: "",
          stderr: "traceback info",
        }),
      );

      const result = await execPython("bad_script.py");
      expect(result.success).toBe(false);
      expect(result.output).toContain("traceback info");
    });

    it("detects timeout errors", async () => {
      mockExecFileAsync.mockRejectedValueOnce(
        new Error("TIMEOUT: script timed out"),
      );

      const result = await execPython("slow.py", [], 1000);
      expect(result.success).toBe(false);
      expect(result.output).toBe("Script timed out");
    });
  });

  describe("execQaTools", () => {
    it("delegates to execPython with qa_tools.py", async () => {
      mockExecFileAsync.mockResolvedValueOnce({
        stdout: "search results",
        stderr: "",
      });

      const result = await execQaTools("search", ["--query", "SEO"]);
      expect(result.success).toBe(true);
    });
  });
});
