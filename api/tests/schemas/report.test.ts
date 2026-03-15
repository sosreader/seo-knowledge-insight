import { describe, it, expect } from "vitest";
import { generateRequestSchema } from "../../src/schemas/report.js";

describe("generateRequestSchema", () => {
  it("accepts maturity_context as optional record", () => {
    const result = generateRequestSchema.safeParse({
      snapshot_id: "20260316-120000",
      maturity_context: {
        strategy: "L2",
        process: "L2",
        keywords: "L3",
        metrics: "L2",
      },
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.maturity_context).toEqual({
        strategy: "L2",
        process: "L2",
        keywords: "L3",
        metrics: "L2",
      });
    }
  });

  it("accepts request without maturity_context", () => {
    const result = generateRequestSchema.safeParse({
      snapshot_id: "20260316-120000",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.maturity_context).toBeUndefined();
    }
  });

  it("rejects maturity_context with non-string values", () => {
    const result = generateRequestSchema.safeParse({
      snapshot_id: "20260316-120000",
      maturity_context: { strategy: 123 },
    });
    expect(result.success).toBe(false);
  });
});
