import { describe, it, expect } from "vitest";
import { parseNpy } from "../../src/utils/npy-reader.js";
import { createNpyBuffer } from "../setup.js";

describe("parseNpy", () => {
  it("parses a float32 2D array", () => {
    const data = new Float32Array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]);
    const buf = createNpyBuffer(data, 2, 3);

    const result = parseNpy(buf);

    expect(result.shape).toEqual([2, 3]);
    expect(result.data.length).toBe(6);
    expect(result.data[0]).toBeCloseTo(1.0);
    expect(result.data[5]).toBeCloseTo(6.0);
  });

  it("throws on invalid magic", () => {
    const buf = Buffer.from("NOT_NPY_FILE");
    expect(() => parseNpy(buf)).toThrow("Not a valid .npy file");
  });

  it("handles larger arrays", () => {
    const rows = 100;
    const cols = 16;
    const data = new Float32Array(rows * cols);
    for (let i = 0; i < data.length; i++) {
      data[i] = Math.random();
    }
    const buf = createNpyBuffer(data, rows, cols);
    const result = parseNpy(buf);

    expect(result.shape).toEqual([rows, cols]);
    expect(result.data.length).toBe(rows * cols);
  });
});
