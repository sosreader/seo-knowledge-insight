/**
 * Tests for retrieval-gate — CRAG-inspired quality gate + citation validator.
 */

import { describe, it, expect } from "vitest";
import {
  evaluateRetrievalQuality,
  validateCitations,
} from "../../src/services/retrieval-gate.js";

describe("evaluateRetrievalQuality", () => {
  it("returns 'incorrect' for empty hits", () => {
    expect(evaluateRetrievalQuality([])).toBe("incorrect");
  });

  it("returns 'correct' when top score >= 0.6", () => {
    expect(evaluateRetrievalQuality([{ score: 0.6 }])).toBe("correct");
    expect(evaluateRetrievalQuality([{ score: 0.95 }])).toBe("correct");
  });

  it("returns 'ambiguous' when 0.4 <= top score < 0.6", () => {
    expect(evaluateRetrievalQuality([{ score: 0.4 }])).toBe("ambiguous");
    expect(evaluateRetrievalQuality([{ score: 0.59 }])).toBe("ambiguous");
  });

  it("returns 'incorrect' when top score < 0.4", () => {
    expect(evaluateRetrievalQuality([{ score: 0.39 }])).toBe("incorrect");
    expect(evaluateRetrievalQuality([{ score: 0.0 }])).toBe("incorrect");
  });

  it("only checks the first hit (top-1 score)", () => {
    // Even if later scores are high, top-1 determines quality
    expect(evaluateRetrievalQuality([{ score: 0.3 }, { score: 0.9 }])).toBe(
      "incorrect",
    );
  });

  it("handles boundary values precisely", () => {
    expect(evaluateRetrievalQuality([{ score: 0.4 }])).toBe("ambiguous");
    expect(evaluateRetrievalQuality([{ score: 0.6 }])).toBe("correct");
    expect(evaluateRetrievalQuality([{ score: 0.3999 }])).toBe("incorrect");
    expect(evaluateRetrievalQuality([{ score: 0.5999 }])).toBe("ambiguous");
  });
});

describe("validateCitations", () => {
  it("returns zero citations for answer without refs", () => {
    const result = validateCitations("No citations here.", 5);
    expect(result.citationCount).toBe(0);
    expect(result.invalidRefs).toEqual([]);
  });

  it("counts valid citations", () => {
    const result = validateCitations("LCP [1] and CLS [2] are metrics.", 5);
    expect(result.citationCount).toBe(2);
    expect(result.invalidRefs).toEqual([]);
  });

  it("deduplicates repeated citations", () => {
    const result = validateCitations("LCP [1] is important [1].", 5);
    expect(result.citationCount).toBe(1);
    expect(result.invalidRefs).toEqual([]);
  });

  it("detects out-of-range refs", () => {
    const result = validateCitations("See [0] and [6] for details.", 5);
    expect(result.citationCount).toBe(0);
    expect(result.invalidRefs).toEqual([0, 6]);
  });

  it("separates valid and invalid refs", () => {
    const result = validateCitations("Sources [1][3][7] are relevant.", 5);
    expect(result.citationCount).toBe(2); // [1] and [3]
    expect(result.invalidRefs).toEqual([7]);
  });

  it("handles sourceCount of 0", () => {
    const result = validateCitations("See [1].", 0);
    expect(result.citationCount).toBe(0);
    expect(result.invalidRefs).toEqual([1]);
  });
});
