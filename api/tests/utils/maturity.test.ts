import { describe, it, expect } from "vitest";
import {
  parseMaturityLevel,
  buildMaturityContext,
  applyMaturityBoost,
  buildReportMaturityBlock,
  MATURITY_LEVEL_DESCRIPTIONS,
} from "../../src/utils/maturity.js";
import { FAKE_ITEMS } from "../setup.js";

describe("maturity utils", () => {
  describe("parseMaturityLevel", () => {
    it("parses valid levels", () => {
      expect(parseMaturityLevel("L1")).toBe("L1");
      expect(parseMaturityLevel("L2")).toBe("L2");
      expect(parseMaturityLevel("L3")).toBe("L3");
      expect(parseMaturityLevel("L4")).toBe("L4");
    });

    it("is case-insensitive", () => {
      expect(parseMaturityLevel("l1")).toBe("L1");
      expect(parseMaturityLevel("l4")).toBe("L4");
    });

    it("trims whitespace", () => {
      expect(parseMaturityLevel("  L2  ")).toBe("L2");
    });

    it("returns null for invalid input", () => {
      expect(parseMaturityLevel("L5")).toBeNull();
      expect(parseMaturityLevel("")).toBeNull();
      expect(parseMaturityLevel(null)).toBeNull();
      expect(parseMaturityLevel(undefined)).toBeNull();
      expect(parseMaturityLevel("invalid")).toBeNull();
    });
  });

  describe("MATURITY_LEVEL_DESCRIPTIONS", () => {
    it("has all 4 levels", () => {
      expect(Object.keys(MATURITY_LEVEL_DESCRIPTIONS)).toEqual(["L1", "L2", "L3", "L4"]);
    });

    it("descriptions are non-empty strings", () => {
      for (const desc of Object.values(MATURITY_LEVEL_DESCRIPTIONS)) {
        expect(typeof desc).toBe("string");
        expect(desc.length).toBeGreaterThan(10);
      }
    });
  });

  describe("buildMaturityContext", () => {
    it("returns L1 context with beginner guidance", () => {
      const ctx = buildMaturityContext("L1");
      expect(ctx).toContain("起步期");
      expect(ctx).toContain("L1");
    });

    it("returns L3 context with optimization guidance", () => {
      const ctx = buildMaturityContext("L3");
      expect(ctx).toContain("優化期");
      expect(ctx).toContain("數據");
    });

    it("returns L4 context with advanced guidance", () => {
      const ctx = buildMaturityContext("L4");
      expect(ctx).toContain("領先期");
      expect(ctx).toContain("預測");
    });

    it("each level returns different content", () => {
      const contexts = ["L1", "L2", "L3", "L4"].map(
        (l) => buildMaturityContext(l as "L1" | "L2" | "L3" | "L4"),
      );
      const unique = new Set(contexts);
      expect(unique.size).toBe(4);
    });
  });

  describe("applyMaturityBoost", () => {
    const hits = FAKE_ITEMS.map((item, i) => ({
      item,
      score: 0.9 - i * 0.1,
    }));

    it("returns unchanged results when maturityLevel is null", () => {
      const result = applyMaturityBoost(hits, null);
      expect(result).toBe(hits); // Same reference — no copy
    });

    it("boosts matching items by 1.15x", () => {
      // FAKE_ITEMS[0] has maturity_relevance: "L1"
      const result = applyMaturityBoost(hits, "L1");
      const boostedItem = result.find((h) => h.item.id === FAKE_ITEMS[0]!.id);
      expect(boostedItem!.score).toBeCloseTo(0.9 * 1.15, 4);
    });

    it("does not boost non-matching items", () => {
      const result = applyMaturityBoost(hits, "L1");
      // FAKE_ITEMS[1] has L2 — should NOT be boosted
      const unboostedItem = result.find((h) => h.item.id === FAKE_ITEMS[1]!.id);
      expect(unboostedItem!.score).toBeCloseTo(0.8, 4);
    });

    it("re-sorts results after boosting", () => {
      // Create hits where a lower-ranked L2 item should be promoted
      const customHits = [
        { item: FAKE_ITEMS[0]!, score: 0.80 }, // L1
        { item: FAKE_ITEMS[1]!, score: 0.75 }, // L2
        { item: FAKE_ITEMS[2]!, score: 0.70 }, // L3
      ];
      const result = applyMaturityBoost(customHits, "L2");
      // L2 item boosted: 0.75 * 1.15 = 0.8625, should now be first
      expect(result[0]!.item.maturity_relevance).toBe("L2");
    });

    it("returns a new array (immutable)", () => {
      const result = applyMaturityBoost(hits, "L1");
      expect(result).not.toBe(hits);
    });

    it("handles items without maturity_relevance", () => {
      // FAKE_ITEMS[3] has maturity_relevance: undefined
      const result = applyMaturityBoost(hits, "L1");
      const noMaturity = result.find((h) => h.item.id === FAKE_ITEMS[3]!.id);
      expect(noMaturity).toBeDefined();
      // Original score unchanged (index 3 → 0.9 - 3*0.1 = 0.6)
      expect(noMaturity!.score).toBeCloseTo(0.6, 4);
    });
  });

  describe("buildReportMaturityBlock", () => {
    it("generates maturity reference with all dimensions", () => {
      const block = buildReportMaturityBlock({
        strategy: "L2",
        process: "L1",
        keywords: "L3",
        metrics: "L2",
      });
      expect(block).toContain("成熟度參考");
      expect(block).toContain("策略 L2");
      expect(block).toContain("流程 L1");
      expect(block).toContain("關鍵字 L3");
      expect(block).toContain("指標 L2");
    });

    it("generates upgrade labels for non-L4 dimensions", () => {
      const block = buildReportMaturityBlock({
        strategy: "L2",
        process: "L3",
        keywords: "L4",
        metrics: "L1",
      });
      expect(block).toContain("[策略 L2→L3]");
      expect(block).toContain("[流程 L3→L4]");
      expect(block).not.toContain("[關鍵字"); // L4 — no upgrade
      expect(block).toContain("[指標 L1→L2]");
    });

    it("handles partial maturity data", () => {
      const block = buildReportMaturityBlock({ strategy: "L1" });
      expect(block).toContain("策略 L1");
      expect(block).toContain("[策略 L1→L2]");
    });

    it("handles empty maturity data", () => {
      const block = buildReportMaturityBlock({});
      expect(block).toContain("成熟度參考");
    });
  });
});
