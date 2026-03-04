import { describe, it, expect } from "vitest";
import { ok, fail } from "../../src/schemas/api-response.js";

describe("ApiResponse", () => {
  describe("ok()", () => {
    it("wraps data with null error", () => {
      const res = ok({ items: [1, 2, 3] });
      expect(res.data).toEqual({ items: [1, 2, 3] });
      expect(res.error).toBeNull();
      expect(res.meta.version).toBe("1.0");
      expect(res.meta.request_id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
      );
    });

    it("generates unique request_id per call", () => {
      const a = ok("a");
      const b = ok("b");
      expect(a.meta.request_id).not.toBe(b.meta.request_id);
    });
  });

  describe("fail()", () => {
    it("wraps error message with null data", () => {
      const res = fail("something went wrong");
      expect(res.data).toBeNull();
      expect(res.error).toBe("something went wrong");
      expect(res.meta.version).toBe("1.0");
      expect(res.meta.request_id).toBeDefined();
    });
  });
});
