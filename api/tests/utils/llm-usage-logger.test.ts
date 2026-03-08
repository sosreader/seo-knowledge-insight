import { describe, it, expect, vi, beforeEach } from "vitest";
import { logLLMUsage, type LLMUsageEntry } from "../../src/utils/llm-usage-logger.js";

vi.mock("../../src/store/supabase-client.js", () => ({
  hasSupabase: vi.fn(() => true),
  supabaseInsert: vi.fn(),
}));

import { hasSupabase, supabaseInsert } from "../../src/store/supabase-client.js";

const mockHasSupabase = vi.mocked(hasSupabase);
const mockInsert = vi.mocked(supabaseInsert);

const sampleEntry: LLMUsageEntry = {
  endpoint: "/api/v1/chat",
  model: "gpt-5.2",
  input_tokens: 500,
  output_tokens: 200,
  latency_ms: 1500,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockHasSupabase.mockReturnValue(true);
  mockInsert.mockResolvedValue([]);
});

describe("logLLMUsage", () => {
  it("skips when Supabase is not configured", () => {
    mockHasSupabase.mockReturnValue(false);
    logLLMUsage(sampleEntry);
    expect(mockInsert).not.toHaveBeenCalled();
  });

  it("inserts correct row to llm_usage table", () => {
    logLLMUsage(sampleEntry);
    expect(mockInsert).toHaveBeenCalledWith("llm_usage", [
      {
        endpoint: "/api/v1/chat",
        model: "gpt-5.2",
        input_tokens: 500,
        output_tokens: 200,
        latency_ms: 1500,
      },
    ]);
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
