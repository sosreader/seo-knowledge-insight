import { describe, it, expect, vi, beforeEach } from "vitest";
import { logLLMUsage, type LLMUsageEntry } from "../../src/utils/llm-usage-logger.js";

vi.mock("../../src/store/pg-client.js", () => ({
  hasPg: vi.fn(() => true),
}));

vi.mock("../../src/store/pg-llm-usage-store.js", () => ({
  insertLLMUsage: vi.fn(),
}));

import { hasPg } from "../../src/store/pg-client.js";
import { insertLLMUsage } from "../../src/store/pg-llm-usage-store.js";

const mockHasPg = vi.mocked(hasPg);
const mockInsert = vi.mocked(insertLLMUsage);

const sampleEntry: LLMUsageEntry = {
  endpoint: "/api/v1/chat",
  model: "gpt-5.2",
  input_tokens: 500,
  output_tokens: 200,
  latency_ms: 1500,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockHasPg.mockReturnValue(true);
  mockInsert.mockResolvedValue(undefined);
});

describe("logLLMUsage", () => {
  it("skips when not in PG mode", () => {
    mockHasPg.mockReturnValue(false);
    logLLMUsage(sampleEntry);
    expect(mockInsert).not.toHaveBeenCalled();
  });

  it("inserts the usage row via the app_llm_usage store", () => {
    logLLMUsage(sampleEntry);
    expect(mockInsert).toHaveBeenCalledWith({
      endpoint: "/api/v1/chat",
      model: "gpt-5.2",
      input_tokens: 500,
      output_tokens: 200,
      latency_ms: 1500,
    });
  });

  it("does not throw on insert failure (fire-and-forget)", () => {
    mockInsert.mockRejectedValue(new Error("db error"));
    expect(() => logLLMUsage(sampleEntry)).not.toThrow();
  });

  it("does not block execution", () => {
    // logLLMUsage returns void (not Promise), confirming fire-and-forget
    const result = logLLMUsage(sampleEntry);
    expect(result).toBeUndefined();
  });
});
