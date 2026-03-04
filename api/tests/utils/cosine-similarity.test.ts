import { describe, it, expect } from "vitest";
import {
  dotProduct,
  normalizeL2,
  normalizeRows,
  matrixDotVector,
} from "../../src/utils/cosine-similarity.js";

describe("dotProduct", () => {
  it("computes dot product of two vectors", () => {
    const a = new Float32Array([1, 2, 3]);
    const b = new Float32Array([4, 5, 6]);
    expect(dotProduct(a, b)).toBeCloseTo(32); // 1*4 + 2*5 + 3*6
  });

  it("returns 0 for orthogonal vectors", () => {
    const a = new Float32Array([1, 0]);
    const b = new Float32Array([0, 1]);
    expect(dotProduct(a, b)).toBeCloseTo(0);
  });
});

describe("normalizeL2", () => {
  it("normalizes a vector to unit length", () => {
    const v = new Float32Array([3, 4]);
    const n = normalizeL2(v);
    expect(n[0]).toBeCloseTo(0.6);
    expect(n[1]).toBeCloseTo(0.8);
    expect(dotProduct(n, n)).toBeCloseTo(1.0);
  });

  it("handles zero vector", () => {
    const v = new Float32Array([0, 0, 0]);
    const n = normalizeL2(v);
    expect(n[0]).toBe(0);
  });
});

describe("normalizeRows", () => {
  it("normalizes each row independently", () => {
    // 2 rows x 2 cols
    const data = new Float32Array([3, 4, 0, 5]);
    const result = normalizeRows(data, 2, 2);

    // Row 0: [3,4] -> [0.6, 0.8]
    expect(result[0]).toBeCloseTo(0.6);
    expect(result[1]).toBeCloseTo(0.8);
    // Row 1: [0,5] -> [0, 1]
    expect(result[2]).toBeCloseTo(0);
    expect(result[3]).toBeCloseTo(1.0);
  });
});

describe("matrixDotVector", () => {
  it("computes dot product of each row with query", () => {
    // 2 rows x 3 cols
    const matrix = new Float32Array([1, 0, 0, 0, 1, 0]);
    const query = new Float32Array([0.5, 0.3, 0.1]);
    const scores = matrixDotVector(matrix, query, 2, 3);

    expect(scores[0]).toBeCloseTo(0.5); // [1,0,0] . [0.5,0.3,0.1]
    expect(scores[1]).toBeCloseTo(0.3); // [0,1,0] . [0.5,0.3,0.1]
  });
});
