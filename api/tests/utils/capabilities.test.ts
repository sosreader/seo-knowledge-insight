import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("../../src/config.js", () => ({
  config: {
    OPENAI_API_KEY: "",
    AGENT_ENABLED: false,
    SUPABASE_URL: "",
    SUPABASE_ANON_KEY: "",
  },
}));

import { config } from "../../src/config.js";
import {
  resolveServerCapabilities,
  resolveCapabilities,
  resolveHealthCapabilities,
  inferCaller,
  formatCapabilityTag,
} from "../../src/utils/capabilities.js";

describe("capabilities", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    (config as Record<string, unknown>).OPENAI_API_KEY = "";
    (config as Record<string, unknown>).AGENT_ENABLED = false;
    (config as Record<string, unknown>).SUPABASE_URL = "";
    (config as Record<string, unknown>).SUPABASE_ANON_KEY = "";
    delete process.env.AWS_LAMBDA_FUNCTION_NAME;
    delete process.env.AWS_EXECUTION_ENV;
  });

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  describe("resolveServerCapabilities", () => {
    it("returns local-server + none + file + disabled by default", () => {
      const caps = resolveServerCapabilities();
      expect(caps).toEqual({
        runtime: "local-server",
        llm: "none",
        store: "file",
        agent: "disabled",
      });
    });

    it("detects Lambda runtime via AWS_LAMBDA_FUNCTION_NAME", () => {
      process.env.AWS_LAMBDA_FUNCTION_NAME = "seo-insight-api";
      const caps = resolveServerCapabilities();
      expect(caps.runtime).toBe("lambda");
    });

    it("detects Lambda runtime via AWS_EXECUTION_ENV", () => {
      process.env.AWS_EXECUTION_ENV = "AWS_Lambda_nodejs22.x";
      const caps = resolveServerCapabilities();
      expect(caps.runtime).toBe("lambda");
    });

    it("detects OpenAI LLM provider", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      const caps = resolveServerCapabilities();
      expect(caps.llm).toBe("openai");
    });

    it("detects Supabase store backend", () => {
      (config as Record<string, unknown>).SUPABASE_URL = "https://test.supabase.co";
      (config as Record<string, unknown>).SUPABASE_ANON_KEY = "anon-key";
      const caps = resolveServerCapabilities();
      expect(caps.store).toBe("supabase");
    });

    it("requires both URL and ANON_KEY for supabase store", () => {
      (config as Record<string, unknown>).SUPABASE_URL = "https://test.supabase.co";
      // SUPABASE_ANON_KEY is "" (from beforeEach)
      const caps = resolveServerCapabilities();
      expect(caps.store).toBe("file");
    });

    it("detects agent enabled", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      (config as Record<string, unknown>).AGENT_ENABLED = true;
      const caps = resolveServerCapabilities();
      expect(caps.agent).toBe("enabled");
    });

    it("detects agent auto-enabled with OpenAI key", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      (config as Record<string, unknown>).AGENT_ENABLED = "auto";
      const caps = resolveServerCapabilities();
      expect(caps.agent).toBe("enabled");
    });

    it("agent auto-disabled without OpenAI key", () => {
      (config as Record<string, unknown>).AGENT_ENABLED = "auto";
      // OPENAI_API_KEY is "" (from beforeEach)
      const caps = resolveServerCapabilities();
      expect(caps.agent).toBe("disabled");
    });

    it("handles full Lambda + OpenAI + Supabase + Agent combo", () => {
      process.env.AWS_LAMBDA_FUNCTION_NAME = "seo-insight-api";
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      (config as Record<string, unknown>).SUPABASE_URL = "https://test.supabase.co";
      (config as Record<string, unknown>).SUPABASE_ANON_KEY = "anon-key";
      (config as Record<string, unknown>).AGENT_ENABLED = true;

      const caps = resolveServerCapabilities();
      expect(caps).toEqual({
        runtime: "lambda",
        llm: "openai",
        store: "supabase",
        agent: "enabled",
      });
    });
  });

  describe("inferCaller", () => {
    it("returns unknown for undefined User-Agent", () => {
      expect(inferCaller(undefined)).toBe("unknown");
    });

    it("returns unknown for empty User-Agent", () => {
      expect(inferCaller("")).toBe("unknown");
    });

    it("identifies claude-code caller", () => {
      expect(inferCaller("claude-code/1.0")).toBe("claude-code");
    });

    it("identifies claude-code caller (case insensitive)", () => {
      expect(inferCaller("Claude-Code/2.0")).toBe("claude-code");
    });

    it("identifies browser caller", () => {
      expect(inferCaller("Mozilla/5.0 (Macintosh; Intel Mac OS X)")).toBe("browser");
    });

    it("identifies CLI caller", () => {
      expect(inferCaller("seo-cli/3.5")).toBe("cli");
    });

    it("identifies Lambda caller", () => {
      expect(inferCaller("aws-sdk-nodejs/3.0")).toBe("lambda");
    });

    it("returns unknown for unrecognized User-Agent", () => {
      expect(inferCaller("curl/7.81.0")).toBe("unknown");
    });
  });

  describe("resolveCapabilities", () => {
    it("includes caller dimension from User-Agent", () => {
      const caps = resolveCapabilities("Mozilla/5.0");
      expect(caps.caller).toBe("browser");
      expect(caps.runtime).toBe("local-server");
    });

    it("defaults caller to unknown when no User-Agent", () => {
      const caps = resolveCapabilities();
      expect(caps.caller).toBe("unknown");
    });

    it("llm reflects server capability, not caller identity", () => {
      const caps = resolveCapabilities("claude-code/1.0");
      expect(caps.llm).toBe("none");
      expect(caps.caller).toBe("claude-code");
    });

    it("llm reflects server capability when OpenAI is available", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      const caps = resolveCapabilities("claude-code/1.0");
      expect(caps.llm).toBe("openai");
      expect(caps.caller).toBe("claude-code");
    });
  });

  describe("resolveHealthCapabilities", () => {
    it("returns claude-code llm when caller is Claude Code and server has no OpenAI", () => {
      const caps = resolveHealthCapabilities("claude-code/1.0");
      expect(caps.llm).toBe("claude-code");
      expect(caps.caller).toBe("claude-code");
    });

    it("returns openai llm when server has OpenAI, even from Claude Code caller", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      const caps = resolveHealthCapabilities("claude-code/1.0");
      expect(caps.llm).toBe("openai");
      expect(caps.caller).toBe("claude-code");
    });

    it("returns none llm for browser caller without OpenAI", () => {
      const caps = resolveHealthCapabilities("Mozilla/5.0 (Macintosh)");
      expect(caps.llm).toBe("none");
      expect(caps.caller).toBe("browser");
    });

    it("returns none llm when no User-Agent provided", () => {
      const caps = resolveHealthCapabilities();
      expect(caps.llm).toBe("none");
      expect(caps.caller).toBe("unknown");
    });
  });

  describe("formatCapabilityTag", () => {
    it("formats full 5-dimension capabilities", () => {
      const tag = formatCapabilityTag({
        runtime: "lambda",
        llm: "openai",
        store: "supabase",
        agent: "enabled",
        caller: "browser",
      });
      expect(tag).toBe("[runtime:lambda | llm:openai | store:supabase | agent:enabled | caller:browser]");
    });

    it("formats server capabilities without caller", () => {
      const tag = formatCapabilityTag({
        runtime: "local-server",
        llm: "none",
        store: "file",
        agent: "disabled",
      });
      expect(tag).toBe("[runtime:local-server | llm:none | store:file | agent:disabled]");
    });

    it("formats all dimension values correctly", () => {
      const tag = formatCapabilityTag({
        runtime: "local-server",
        llm: "openai",
        store: "supabase",
        agent: "enabled",
        caller: "claude-code",
      });
      expect(tag).toContain("caller:claude-code");
    });
  });
});
