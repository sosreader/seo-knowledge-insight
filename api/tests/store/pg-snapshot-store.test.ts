import { beforeEach, describe, expect, it } from "vitest";
import { PgSnapshotStore } from "../../src/store/pg-snapshot-store.js";
import type { MetricsSnapshot } from "../../src/schemas/pipeline.js";
import { pgAvailable, usePgFixture } from "../pg/pg-fixture.js";

const fx = usePgFixture("snap");
const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00$/;

function snapshot(id: string, createdAt: string, extra: Partial<MetricsSnapshot> = {}): MetricsSnapshot {
  return {
    id,
    created_at: createdAt,
    label: `label ${id}`,
    source: "sheets",
    tab: "weekly",
    weeks: 2,
    metrics: { CTR: { latest: 1.2 } },
    ...extra,
  } as MetricsSnapshot;
}

describe.skipIf(!pgAvailable)("PgSnapshotStore against app_metrics_snapshot (warehouse_rag)", () => {
  const store = new PgSnapshotStore();

  beforeEach(async () => {
    await fx.activate();
    await fx.admin().query("TRUNCATE app_metrics_snapshot");
  });

  it("saves and reads back a snapshot with PostgREST-style timestamps", async () => {
    await store.save(snapshot("20261020-120000", "2026-10-20T12:00:00.000Z", { maturity: { strategy: "L2" } }));
    const got = await store.getById("20261020-120000");
    expect(got).toMatchObject({
      id: "20261020-120000",
      label: "label 20261020-120000",
      weeks: 2,
      metrics: { CTR: { latest: 1.2 } },
      maturity: { strategy: "L2" },
    });
    expect(got!.created_at).toMatch(ISO_RE);
    expect(new Date(got!.created_at).toISOString()).toBe("2026-10-20T12:00:00.000Z");
  });

  it("omits maturity when not stored", async () => {
    await store.save(snapshot("20261020-120001", "2026-10-20T12:00:01.000Z"));
    expect(await store.getById("20261020-120001")).not.toHaveProperty("maturity");
  });

  it("lists newest first and hides soft-deleted rows (deleted_at IS NULL)", async () => {
    await store.save(snapshot("a", "2026-10-01T00:00:00Z"));
    await store.save(snapshot("b", "2026-10-02T00:00:00Z"));
    await store.save(snapshot("c", "2026-10-03T00:00:00Z"));
    await fx.admin().query("UPDATE app_metrics_snapshot SET deleted_at = now() WHERE id = 'b'");
    const list = await store.list();
    expect(list.map((s) => s.id)).toEqual(["c", "a"]);
    expect(list[0]).not.toHaveProperty("metrics");
    expect(await store.getById("b")).toBeNull();
  });

  it("soft-deletes once; second delete and unknown id return false", async () => {
    await store.save(snapshot("d", "2026-10-04T00:00:00Z"));
    expect(await store.delete("d")).toBe(true);
    expect(await store.delete("d")).toBe(false);
    expect(await store.delete("nope")).toBe(false);
    const { rows } = await fx.admin().query("SELECT deleted_at FROM app_metrics_snapshot WHERE id = 'd'");
    expect(rows[0].deleted_at).not.toBeNull();
  });

  it("re-saving a soft-deleted id revives it (upsert clears deleted_at)", async () => {
    await store.save(snapshot("e", "2026-10-05T00:00:00Z"));
    await store.delete("e");
    await store.save(snapshot("e", "2026-10-06T00:00:00Z", { label: "revived" }));
    expect((await store.getById("e"))?.label).toBe("revived");
  });
});
