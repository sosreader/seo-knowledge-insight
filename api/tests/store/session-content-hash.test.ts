import { describe, expect, it } from "vitest";
import { canonicalJson, sessionContentHash } from "../../src/store/session-content-hash.js";

// 期望值由 SKI scripts/sync_db_sources.py 的 session_content_hash() 以 Python 算出（同一份輸入），
// 確保 rag-api 寫入的 content_hash 與 sync-db 寫入端一致。
const MESSAGES = [
  {
    role: "user",
    content: '什麼是 LCP？\n"quote"',
    sources: [],
    created_at: "2026-10-23T01:02:03.456Z",
  },
  {
    role: "assistant",
    content: "答",
    sources: [{ id: "a1b2c3d4e5f67890", score: 0.8123, nested: { z: 1, a: [true, null] } }],
    created_at: "2026-10-23T01:02:04.000Z",
    metadata: { provider: "openai", duration_ms: 1234 },
  },
];

describe("sessionContentHash (parity with Python session_content_hash)", () => {
  it("matches Python for an empty session", () => {
    expect(sessionContentHash("New Chat", [])).toBe(
      "sha256:91fd14af649fea6271a1f9353c9b0ee189448bd0a34efdce407b0690241677c1",
    );
  });

  it("matches Python for CJK, escapes, nested objects with unsorted keys", () => {
    expect(sessionContentHash("什麼是 LCP？", MESSAGES)).toBe(
      "sha256:e0151dc4e096ee03800aa8bb8931bfbefe6f75f8c6dce4c6599310fe5ad2c74c",
    );
  });

  it("satisfies the VW content_hash pattern", () => {
    expect(sessionContentHash("t", [])).toMatch(/^[A-Za-z0-9:_-]{8,128}$/);
  });
});

describe("canonicalJson", () => {
  it("sorts keys recursively, drops undefined, keeps array order", () => {
    expect(canonicalJson({ b: 1, a: { d: [3, 1], c: undefined } })).toBe('{"a":{"d":[3,1]},"b":1}');
  });

  it("serialises primitives like JSON.stringify", () => {
    expect(canonicalJson(null)).toBe("null");
    expect(canonicalJson("é")).toBe('"é"');
    expect(canonicalJson(undefined)).toBe("null");
  });
});
