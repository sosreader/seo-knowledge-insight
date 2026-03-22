import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../src/config.js", () => ({
  config: {
    OPENAI_API_KEY: "",
    ANTHROPIC_API_KEY: "",
    CHAT_LLM_PROVIDER: "openai",
    AGENT_ENABLED: false,
  },
}));

import { config } from "../../src/config.js";
import {
  resolveMode,
  isAgentEnabled,
  hasOpenAI,
  hasChatLLM,
  getChatProvider,
} from "../../src/utils/mode-detect.js";

describe("mode-detect", () => {
  beforeEach(() => {
    (config as Record<string, unknown>).OPENAI_API_KEY = "";
    (config as Record<string, unknown>).ANTHROPIC_API_KEY = "";
    (config as Record<string, unknown>).CHAT_LLM_PROVIDER = "openai";
    (config as Record<string, unknown>).AGENT_ENABLED = false;
  });

  describe("resolveMode", () => {
    it("returns request mode when provided (agent)", () => {
      expect(resolveMode("agent")).toBe("agent");
    });

    it("returns request mode when provided (rag)", () => {
      expect(resolveMode("rag")).toBe("rag");
    });

    it("falls back to agent when AGENT_ENABLED=true and no request mode", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      (config as Record<string, unknown>).AGENT_ENABLED = true;
      expect(resolveMode(undefined)).toBe("agent");
    });

    it("falls back to rag when AGENT_ENABLED=false and no request mode", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      (config as Record<string, unknown>).AGENT_ENABLED = false;
      expect(resolveMode(undefined)).toBe("rag");
    });

    it("falls back to agent in auto mode with OpenAI key", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      (config as Record<string, unknown>).AGENT_ENABLED = "auto";
      expect(resolveMode(undefined)).toBe("agent");
    });

    it("request mode overrides server-level setting", () => {
      (config as Record<string, unknown>).AGENT_ENABLED = true;
      expect(resolveMode("rag")).toBe("rag");
    });
  });

  describe("hasOpenAI", () => {
    it("returns false when no key", () => {
      expect(hasOpenAI()).toBe(false);
    });

    it("returns true when key is set", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      expect(hasOpenAI()).toBe(true);
    });
  });

  describe("getChatProvider", () => {
    it("returns none when provider=openai but no OpenAI key", () => {
      expect(getChatProvider()).toBe("none");
    });

    it("returns openai when provider=openai and OpenAI key set", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      expect(getChatProvider()).toBe("openai");
    });

    it("returns anthropic when provider=anthropic and Anthropic key set", () => {
      (config as Record<string, unknown>).CHAT_LLM_PROVIDER = "anthropic";
      (config as Record<string, unknown>).ANTHROPIC_API_KEY = "sk-ant-test";
      expect(getChatProvider()).toBe("anthropic");
    });

    it("returns none when provider=anthropic but no Anthropic key", () => {
      (config as Record<string, unknown>).CHAT_LLM_PROVIDER = "anthropic";
      expect(getChatProvider()).toBe("none");
    });

    it("returns openai when both keys set but provider=openai", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      (config as Record<string, unknown>).ANTHROPIC_API_KEY = "sk-ant-test";
      expect(getChatProvider()).toBe("openai");
    });
  });

  describe("hasChatLLM", () => {
    it("returns false when no keys", () => {
      expect(hasChatLLM()).toBe(false);
    });

    it("returns true when OpenAI key set (default provider)", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      expect(hasChatLLM()).toBe(true);
    });

    it("returns true when Anthropic key set and provider=anthropic", () => {
      (config as Record<string, unknown>).CHAT_LLM_PROVIDER = "anthropic";
      (config as Record<string, unknown>).ANTHROPIC_API_KEY = "sk-ant-test";
      expect(hasChatLLM()).toBe(true);
    });
  });

  describe("isAgentEnabled", () => {
    it("returns false when AGENT_ENABLED=false", () => {
      expect(isAgentEnabled()).toBe(false);
    });

    it("returns true when AGENT_ENABLED=true", () => {
      (config as Record<string, unknown>).AGENT_ENABLED = true;
      expect(isAgentEnabled()).toBe(true);
    });

    it("returns true in auto mode with OpenAI key", () => {
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test";
      (config as Record<string, unknown>).AGENT_ENABLED = "auto";
      expect(isAgentEnabled()).toBe(true);
    });

    it("returns true in auto mode with Anthropic provider", () => {
      (config as Record<string, unknown>).CHAT_LLM_PROVIDER = "anthropic";
      (config as Record<string, unknown>).ANTHROPIC_API_KEY = "sk-ant-test";
      (config as Record<string, unknown>).AGENT_ENABLED = "auto";
      expect(isAgentEnabled()).toBe(true);
    });
  });
});
