/**
 * LLM 開關與 OpenAI 相容 client（S3.1）：
 *   - 沒有 OPENAI_API_KEY 且沒有 LLM_BASE_URL → LLM disabled
 *   - LLM_BASE_URL（本機 Ollama /v1）單獨即可啟用，apiKey 用佔位字串
 *   - LLM_CHAT_MODEL／LLM_EMBEDDING_MODEL 覆寫舊的 CHAT_MODEL／OPENAI_EMBEDDING_MODEL
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockConfig: Record<string, unknown> = {};

vi.mock("../../src/config.js", () => ({ config: mockConfig }));

const openaiCtor = vi.fn();
vi.mock("openai", () => ({
  default: class FakeOpenAI {
    constructor(opts: unknown) {
      openaiCtor(opts);
    }
  },
}));

const {
  isLlmEnabled,
  assertLlmEnabled,
  llmChatModel,
  llmEmbeddingModel,
  llmClientOptions,
  createLlmClient,
  LOCAL_LLM_PLACEHOLDER_KEY,
} = await import("../../src/services/llm-client.js");
const { FeatureUnavailableError } = await import("../../src/utils/feature-errors.js");

function setConfig(values: Record<string, unknown>): void {
  for (const k of Object.keys(mockConfig)) delete mockConfig[k];
  Object.assign(mockConfig, {
    CHAT_MODEL: "gpt-chat-default",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    ...values,
  });
}

describe("llm-client", () => {
  beforeEach(() => {
    openaiCtor.mockClear();
    setConfig({});
  });

  it.each([
    [{}, false],
    [{ OPENAI_API_KEY: "" , LLM_BASE_URL: "" }, false],
    [{ LLM_BASE_URL: "   " }, false],
    [{ OPENAI_API_KEY: "sk-x" }, true],
    [{ LLM_BASE_URL: "http://localhost:11434/v1" }, true],
  ])("isLlmEnabled(%j) → %s", (values, expected) => {
    setConfig(values);
    expect(isLlmEnabled()).toBe(expected);
  });

  it("assertLlmEnabled throws a 501 llm_disabled error when disabled", () => {
    let caught: unknown;
    try {
      assertLlmEnabled();
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(FeatureUnavailableError);
    expect((caught as InstanceType<typeof FeatureUnavailableError>).status).toBe(501);
    expect((caught as InstanceType<typeof FeatureUnavailableError>).code).toBe("llm_disabled");
  });

  it("assertLlmEnabled passes when a key is configured", () => {
    setConfig({ OPENAI_API_KEY: "sk-x" });
    expect(() => assertLlmEnabled()).not.toThrow();
  });

  it("model names fall back to the legacy settings and honour LLM_* overrides", () => {
    expect(llmChatModel()).toBe("gpt-chat-default");
    expect(llmEmbeddingModel()).toBe("text-embedding-3-small");
    setConfig({ LLM_CHAT_MODEL: "qwen3:8b", LLM_EMBEDDING_MODEL: "nomic-embed-text" });
    expect(llmChatModel()).toBe("qwen3:8b");
    expect(llmEmbeddingModel()).toBe("nomic-embed-text");
  });

  it("client options: OpenAI default when only a key is set", () => {
    setConfig({ OPENAI_API_KEY: "sk-x" });
    expect(llmClientOptions()).toEqual({ apiKey: "sk-x" });
  });

  it("client options: base URL with placeholder key for a local Ollama", () => {
    setConfig({ LLM_BASE_URL: "http://localhost:11434/v1" });
    expect(llmClientOptions()).toEqual({
      apiKey: LOCAL_LLM_PLACEHOLDER_KEY,
      baseURL: "http://localhost:11434/v1",
    });
  });

  it("createLlmClient builds an OpenAI client with the resolved options", () => {
    setConfig({ OPENAI_API_KEY: "sk-x", LLM_BASE_URL: "http://gw.local/v1" });
    createLlmClient();
    expect(openaiCtor).toHaveBeenCalledWith({ apiKey: "sk-x", baseURL: "http://gw.local/v1" });
  });

  it("createLlmClient refuses to build a client when LLM is disabled", () => {
    expect(() => createLlmClient()).toThrow(FeatureUnavailableError);
    expect(openaiCtor).not.toHaveBeenCalled();
  });
});
