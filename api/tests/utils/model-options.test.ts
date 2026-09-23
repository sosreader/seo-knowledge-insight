import { describe, expect, it } from "vitest";
import { reasoningOptions } from "../../src/utils/model-options.js";

describe("模型升級推理參數", () => {
  it.each(["gpt-6-luna", "gpt-6-sol"])("%s 保留原 none 行為", (model) => {
    expect(reasoningOptions(model)).toEqual({ reasoning_effort: "none" });
  });
  it.each(["gpt-5.4-nano", "gpt-5.4", "custom-model", "gpt-6-astra"])("%s 保留原請求", (model) => {
    expect(reasoningOptions(model)).toEqual({});
  });
});
