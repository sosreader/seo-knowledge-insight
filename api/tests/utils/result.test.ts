import { describe, it, expect } from "vitest";
import { Ok, Err, mapResult, flatMapResult, unwrapOr, type Result } from "../../src/utils/result.js";

describe("Result type", () => {
  describe("Ok", () => {
    it("creates a success result", () => {
      const r = Ok(42);
      expect(r.ok).toBe(true);
      expect(r.value).toBe(42);
    });

    it("works with string values", () => {
      const r = Ok("hello");
      expect(r).toEqual({ ok: true, value: "hello" });
    });

    it("works with object values", () => {
      const r = Ok({ a: 1 });
      expect(r).toEqual({ ok: true, value: { a: 1 } });
    });
  });

  describe("Err", () => {
    it("creates a failure result", () => {
      const r = Err("something went wrong");
      expect(r.ok).toBe(false);
      expect(r.error).toBe("something went wrong");
    });

    it("works with typed errors", () => {
      const r: Result<number, { code: number; msg: string }> = Err({ code: 404, msg: "not found" });
      expect(r.ok).toBe(false);
      if (!r.ok) {
        expect(r.error.code).toBe(404);
      }
    });
  });

  describe("mapResult", () => {
    it("maps Ok value", () => {
      const r = Ok(5);
      const mapped = mapResult(r, (v) => v * 2);
      expect(mapped).toEqual({ ok: true, value: 10 });
    });

    it("passes through Err unchanged", () => {
      const r: Result<number> = Err("fail");
      const mapped = mapResult(r, (v) => v * 2);
      expect(mapped).toEqual({ ok: false, error: "fail" });
    });

    it("transforms value type", () => {
      const r = Ok(42);
      const mapped = mapResult(r, (v) => String(v));
      expect(mapped).toEqual({ ok: true, value: "42" });
    });
  });

  describe("flatMapResult", () => {
    it("chains Ok results", () => {
      const r = Ok(10);
      const chained = flatMapResult(r, (v) => (v > 5 ? Ok(v * 2) : Err("too small")));
      expect(chained).toEqual({ ok: true, value: 20 });
    });

    it("chains to Err when predicate fails", () => {
      const r = Ok(3);
      const chained = flatMapResult(r, (v) => (v > 5 ? Ok(v * 2) : Err("too small")));
      expect(chained).toEqual({ ok: false, error: "too small" });
    });

    it("passes through Err unchanged", () => {
      const r: Result<number> = Err("initial error");
      const chained = flatMapResult(r, (v) => Ok(v * 2));
      expect(chained).toEqual({ ok: false, error: "initial error" });
    });
  });

  describe("unwrapOr", () => {
    it("returns value for Ok", () => {
      expect(unwrapOr(Ok(42), 0)).toBe(42);
    });

    it("returns fallback for Err", () => {
      expect(unwrapOr(Err("fail"), 0)).toBe(0);
    });
  });
});
