import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import type pg from "pg";
import { closePool, pgQuery } from "../../src/store/pg-client.js";
import { updateFreshness } from "../../src/jobs/update-freshness.js";
import { pgAvailable, usePgFixture } from "../pg/pg-fixture.js";
import { REFERENCE, golden } from "./golden.js";

const fx = usePgFixture("freshness");

interface ScoreRow {
  id: string;
  freshness_score: number | null;
  search_hit_count: number;
}

async function insertGolden(admin: pg.Client): Promise<void> {
  await admin.query("DELETE FROM app_qa_item");
  for (const it of golden.items) {
    await admin.query(
      `INSERT INTO app_qa_item (id, seq, question, answer, source_date, evergreen, freshness_score, search_hit_count)
       VALUES ($1, $2, 'q', 'a', $3, $4, $5, 7)`,
      [it.id, it.seq, it.source_date, it.evergreen, it.freshness_score],
    );
  }
}

async function scores(admin: pg.Client): Promise<Record<string, number | null>> {
  const { rows } = await admin.query<ScoreRow>("SELECT id, freshness_score FROM app_qa_item ORDER BY seq");
  return Object.fromEntries(rows.map((r) => [r.id, r.freshness_score]));
}

describe.skipIf(!pgAvailable)("update-freshness against app_qa_item (warehouse_rag)", () => {
  beforeAll(() => fx.activate());
  beforeEach(async () => {
    await fx.activate();
    await insertGolden(fx.admin());
  });

  it("writes exactly what the Python version would (golden parity)", async () => {
    const result = await updateFreshness({ dryRun: false, now: REFERENCE });

    expect(await scores(fx.admin())).toEqual(golden.expected_final);
    expect(result.processed).toBe(golden.items.length);
    expect(result.need_update).toBe(Object.keys(golden.expected_updates).length);
    expect(result.updated).toBe(result.need_update);
    expect(result.skipped).toBe(golden.expected_skipped);
    expect(result.evergreen).toBe(golden.expected_evergreen);
    expect(result.failed).toBe(0);
  });

  it("only changes freshness_score (other columns, including search_hit_count, are untouched)", async () => {
    await updateFreshness({ dryRun: false, now: REFERENCE });
    const { rows } = await fx.admin().query<ScoreRow>("SELECT search_hit_count FROM app_qa_item");
    expect(new Set(rows.map((r) => r.search_hit_count))).toEqual(new Set([7]));
  });

  it("dry-run performs zero writes but reports the plan", async () => {
    const before = await scores(fx.admin());
    const result = await updateFreshness({ dryRun: true, now: REFERENCE });

    expect(await scores(fx.admin())).toEqual(before);
    expect(result.dry_run).toBe(true);
    expect(result.updated).toBe(0);
    expect(result.need_update).toBe(Object.keys(golden.expected_updates).length);
    expect(result.sample).toHaveLength(5);
    expect(result.readback).toBeNull();
  });

  it("is idempotent: a second run has nothing to update", async () => {
    await updateFreshness({ dryRun: false, now: REFERENCE });
    const second = await updateFreshness({ dryRun: false, now: REFERENCE });
    expect(second.need_update).toBe(0);
    expect(second.updated).toBe(0);
    expect(await scores(fx.admin())).toEqual(golden.expected_final);
  });

  it("spans several batches when batchSize is small", async () => {
    const result = await updateFreshness({ dryRun: false, now: REFERENCE, batchSize: 3 });
    expect(await scores(fx.admin())).toEqual(golden.expected_final);
    expect(result.failed).toBe(0);
  });

  it("honours --limit (first N rows by seq) and --since", async () => {
    const limited = await updateFreshness({ dryRun: true, now: REFERENCE, limit: 5 });
    expect(limited.processed).toBe(5);

    const since = await updateFreshness({ dryRun: true, now: REFERENCE, since: "2026-01-01" });
    const expected = golden.items.filter((i) => (i.source_date ?? "") >= "2026-01-01").length;
    expect(since.processed).toBe(expected);
    expect(since.since).toBe("2026-01-01");
  });

  it("reports before / planned_after distribution and a DB readback", async () => {
    const result = await updateFreshness({ dryRun: false, now: REFERENCE });
    expect(result.distribution.before.count).toBe(golden.items.length);
    expect(result.distribution.planned_after.min).toBe(0.01);
    expect(result.distribution.planned_after.max).toBe(1);
    expect(result.readback?.table_rows).toBe(golden.items.length);
    expect(result.readback?.min).toBe(0.01);
    expect(result.readback?.max).toBe(1);
    expect(result.duration_ms).toBeGreaterThanOrEqual(0);
  });

  it("flags legacy rows that are still at full score in the readback", async () => {
    await fx.admin().query("UPDATE app_qa_item SET freshness_score = 1 WHERE source_date = '2024-02-29'");
    // since 把這列排除在更新範圍外，所以讀回時它仍是 1.0
    const result = await updateFreshness({ dryRun: false, now: REFERENCE, since: "2026-01-01" });
    expect(result.readback?.legacy_at_full_score).toBeGreaterThan(0);
  });

  it("keeps going when one batch fails and reports the failed row count", async () => {
    const admin = fx.admin();
    await admin.query(`
      CREATE OR REPLACE FUNCTION reject_one() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF NEW.id = '0000000000000004' THEN RAISE EXCEPTION 'boom'; END IF;
        RETURN NEW;
      END $$;
      CREATE TRIGGER reject_one BEFORE UPDATE ON app_qa_item FOR EACH ROW EXECUTE FUNCTION reject_one();
    `);
    try {
      const result = await updateFreshness({ dryRun: false, now: REFERENCE, batchSize: 3 });
      // id 4 在第二批（seq 4–6），該批 3 列整批回滾；其餘批次照常寫入
      expect(result.failed).toBe(3);
      expect(result.updated).toBe(result.need_update - 3);
      const final = await scores(admin);
      expect(final["0000000000000004"]).toBe(1);
      expect(final["0000000000000010"]).toBe(golden.expected_final["0000000000000010"]);
    } finally {
      await admin.query("DROP TRIGGER reject_one ON app_qa_item; DROP FUNCTION reject_one();");
    }
  });

  it("uses a single connection role that cannot write other columns", async () => {
    await expect(pgQuery("UPDATE app_qa_item SET answer = 'x'")).rejects.toThrow(/permission denied/);
    await closePool();
  });
});
