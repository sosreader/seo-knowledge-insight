import { beforeEach, describe, expect, it, vi } from "vitest";
import { config } from "../../src/config.js";
import { generateReportLlm } from "../../src/services/report-llm.js";

const { create } = vi.hoisted(() => ({ create: vi.fn() }));
vi.mock("openai", () => ({
  default: class { chat = { completions: { create } }; },
}));
vi.mock("../../src/config.js", () => ({
  config: { get REPORT_MODEL() { return "gpt-6-sol"; }, OPENAI_API_KEY: "test" },
}));
vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: { loaded: true, count: 0, allItems: [], keywordSearch: () => [] },
}));
vi.mock("../../src/store/store-init.js", () => ({ ensureQaStoreLoaded: vi.fn() }));

describe("週報模型請求相容性", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    create.mockResolvedValue({ choices: [{ message: { content: "週報內容" } }] });
  });

  it.each(["gpt-6-sol", "gpt-5.4"])("使用 %s 並保留報告來源標記", async (model) => {
    vi.spyOn(config, "REPORT_MODEL", "get").mockReturnValue(model);
    const result = await generateReportLlm({}, 1);
    const request = create.mock.calls[0][0];
    expect(request.model).toBe(model);
    expect(request.max_completion_tokens).toBe(16384);
    if (model === "gpt-6-sol") expect(request.reasoning_effort).toBe("none");
    else expect(request).not.toHaveProperty("reasoning_effort");
    expect(result.model).toBe(model);
    expect(result.content).toContain(`"model":"${model}"`);
  });
});
