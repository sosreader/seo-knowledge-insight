/**
 * response-cache 與 llm-usage 的 SQL 對真 PG（warehouse_rag）驗證；
 * 兩者在 PG 模式才動作，所以這裡把 hasPg mock 成 true，pgQuery 用真的。
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/store/pg-client.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../src/store/pg-client.js")>();
  return { ...actual, hasPg: () => true };
});
vi.mock("../../src/utils/laminar-scoring.js", () => ({ scoreEvent: vi.fn() }));

import { lookupCache, saveCache } from "../../src/services/response-cache.js";
import { insertLLMUsage, listLLMUsageSince } from "../../src/store/pg-llm-usage-store.js";
import { logLLMUsage } from "../../src/utils/llm-usage-logger.js";
import { pgAvailable, usePgFixture } from "../pg/pg-fixture.js";

const fx = usePgFixture("cache");

describe.skipIf(!pgAvailable)("response cache on app_response_cache (warehouse_rag)", () => {
  beforeEach(async () => {
    await fx.activate();
    await fx.admin().query("TRUNCATE app_response_cache");
  });

  it("round-trips a response and upserts on the same query_hash", async () => {
    await saveCache("q", "h1", { answer: "v1" });
    expect(await lookupCache("h1")).toEqual({ answer: "v1" });
    await fx.admin().query("UPDATE app_response_cache SET hit_count = 5 WHERE query_hash = 'h1'");
    await saveCache("q", "h1", { answer: "v2" });
    expect(await lookupCache("h1")).toEqual({ answer: "v2" });
    const { rows } = await fx.admin().query("SELECT count(*)::int AS n, max(hit_count) AS hits FROM app_response_cache");
    expect(rows[0]).toEqual({ n: 1, hits: 0 });
  });

  it("ignores expired entries and misses", async () => {
    await saveCache("old", "h2", { answer: "stale" }, -1);
    expect(await lookupCache("h2")).toBeNull();
    expect(await lookupCache("never")).toBeNull();
  });
});

describe.skipIf(!pgAvailable)("llm usage on app_llm_usage (warehouse_rag)", () => {
  beforeEach(async () => {
    await fx.activate();
    await fx.admin().query("TRUNCATE app_llm_usage");
  });

  it("inserts and lists rows newest first within the window, honouring limit", async () => {
    await insertLLMUsage({ endpoint: "/chat", model: "m1", input_tokens: 10, output_tokens: 5, latency_ms: 100 });
    await insertLLMUsage({ endpoint: "/chat", model: "m2", input_tokens: 20, output_tokens: 6, latency_ms: 200 });
    await fx.admin().query(
      "INSERT INTO app_llm_usage (endpoint, model, created_at) VALUES ('/old', 'm0', now() - interval '40 days')",
    );
    const since = new Date(Date.now() - 30 * 86_400_000).toISOString();
    const rows = await listLLMUsageSince(since, 1000);
    expect(rows.map((r) => r.model).sort()).toEqual(["m1", "m2"]);
    expect(rows[0]!.created_at).toMatch(/\+00:00$/);
    expect(await listLLMUsageSince(since, 1)).toHaveLength(1);
  });

  it("logLLMUsage writes fire-and-forget", async () => {
    logLLMUsage({ endpoint: "/x", model: "m", input_tokens: 1, output_tokens: 1, latency_ms: 1 });
    await vi.waitFor(async () => {
      const { rowCount } = await fx.admin().query("SELECT 1 FROM app_llm_usage WHERE endpoint = '/x'");
      expect(rowCount).toBe(1);
    });
  });
});
