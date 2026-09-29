/** 保留原 5.4 / nano 的 none 行為，並滿足 Luna 的 Chat Completions 工具呼叫限制。 */
export function reasoningOptions(model: string): { reasoning_effort?: "none" } {
  return model === "gpt-6-luna" || model === "gpt-6-sol"
    ? { reasoning_effort: "none" }
    : {};
}
