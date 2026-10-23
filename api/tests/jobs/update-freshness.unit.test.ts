import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/store/pg-client.js", () => ({
  pgQuery: vi.fn(),
  pgQueryResult: vi.fn(),
  closePool: vi.fn(),
}));

import { pgQuery, pgQueryResult } from "../../src/store/pg-client.js";
import { DbUnavailableError } from "../../src/store/store-errors.js";
import { BATCH_SIZE, updateFreshness } from "../../src/jobs/update-freshness.js";

const NOW = new Date("2026-10-26T02:00:00Z");
const query = vi.mocked(pgQuery);
const queryResult = vi.mocked(pgQueryResult);

function rows(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: String(i).padStart(16, "0"),
    source_date: "2020-01-01",
    evergreen: false,
    freshness_score: 1,
  }));
}

const READBACK = { table_rows: 0, min: null, avg: null, max: null, legacy_at_full_score: 0 };

beforeEach(() => {
  query.mockReset();
  queryResult.mockReset();
});

describe("updateFreshness (mocked DB)", () => {
  it("splits writes into BATCH_SIZE chunks", async () => {
    query.mockResolvedValueOnce(rows(250) as never).mockResolvedValueOnce([READBACK] as never);
    queryResult.mockImplementation(async (_sql, values) => ({ rowCount: (values![0] as string[]).length }) as never);

    const result = await updateFreshness({ dryRun: false, now: NOW });

    expect(BATCH_SIZE).toBe(100);
    expect(queryResult).toHaveBeenCalledTimes(3);
    expect(result.updated).toBe(250);
    expect(result.failed).toBe(0);
  });

  it("gives up on the remaining batches when the database becomes unavailable", async () => {
    query.mockResolvedValueOnce(rows(250) as never).mockResolvedValueOnce([READBACK] as never);
    queryResult
      .mockResolvedValueOnce({ rowCount: 100 } as never)
      .mockRejectedValueOnce(new DbUnavailableError("ECONNRESET"));

    const result = await updateFreshness({ dryRun: false, now: NOW });

    expect(queryResult).toHaveBeenCalledTimes(2);
    expect(result.updated).toBe(100);
    expect(result.failed).toBe(150);
  });

  it("counts only the failing batch for non-connection errors and continues", async () => {
    query.mockResolvedValueOnce(rows(250) as never).mockResolvedValueOnce([READBACK] as never);
    queryResult
      .mockRejectedValueOnce(new Error("constraint"))
      .mockResolvedValueOnce({ rowCount: 100 } as never)
      .mockResolvedValueOnce({ rowCount: 50 } as never);

    const result = await updateFreshness({ dryRun: false, now: NOW });

    expect(result.failed).toBe(100);
    expect(result.updated).toBe(150);
  });

  it("does not call the write path in dry-run", async () => {
    query.mockResolvedValueOnce(rows(10) as never);
    const result = await updateFreshness({ dryRun: true, now: NOW });
    expect(queryResult).not.toHaveBeenCalled();
    expect(result.need_update).toBe(10);
  });

  it("handles an empty table", async () => {
    query.mockResolvedValueOnce([] as never).mockResolvedValueOnce([] as never);
    const result = await updateFreshness({ dryRun: false, now: NOW });
    expect(result.processed).toBe(0);
    expect(result.distribution.before.min).toBeNull();
    expect(result.readback?.table_rows).toBe(0);
  });

  it("passes NULL for --since / --limit when not provided", async () => {
    query.mockResolvedValueOnce([] as never);
    await updateFreshness({ dryRun: true, now: NOW });
    expect(query.mock.calls[0]![1]).toEqual([null, null]);
  });
});
