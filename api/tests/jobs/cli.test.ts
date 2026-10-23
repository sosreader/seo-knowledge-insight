import { describe, expect, it, vi } from "vitest";
import { DbUnavailableError } from "../../src/store/store-errors.js";
import { EXIT_FAILED, EXIT_OK, EXIT_USAGE, parseUpdateFreshnessArgs, runCli, type CliDeps } from "../../src/jobs/cli.js";
import type { UpdateFreshnessResult } from "../../src/jobs/update-freshness.js";

function result(overrides: Partial<UpdateFreshnessResult> = {}): UpdateFreshnessResult {
  return {
    dry_run: false,
    reference_time: "2026-10-26T02:00:00.000Z",
    since: null,
    limit: 0,
    processed: 3,
    evergreen: 1,
    need_update: 2,
    skipped: 1,
    updated: 2,
    failed: 0,
    distribution: {
      before: { count: 3, min: 1, avg: 1, max: 1 },
      planned_after: { count: 3, min: 0.5, avg: 0.8333, max: 1 },
    },
    sample: [],
    readback: null,
    duration_ms: 5,
    ...overrides,
  };
}

function deps(run: CliDeps["run"]): { deps: CliDeps; records: Record<string, unknown>[]; close: ReturnType<typeof vi.fn> } {
  const records: Record<string, unknown>[] = [];
  const close = vi.fn(async () => undefined);
  return {
    records,
    close,
    deps: { emit: (r) => records.push(r), run, close, now: () => new Date("2026-10-26T02:00:00Z") },
  };
}

describe("parseUpdateFreshnessArgs", () => {
  it("defaults to a real run (not dry-run)", () => {
    expect(parseUpdateFreshnessArgs([])).toEqual({ ok: true, options: { dryRun: false, since: undefined, limit: 0 } });
  });

  it("parses --dry-run, --since and --limit", () => {
    expect(parseUpdateFreshnessArgs(["--dry-run", "--since", "2024-01-01", "--limit", "10"])).toEqual({
      ok: true,
      options: { dryRun: true, since: "2024-01-01", limit: 10 },
    });
  });

  it.each([
    [["--since"]],
    [["--since", "yesterday"]],
    [["--limit"]],
    [["--limit", "-1"]],
    [["--limit", "1.5"]],
    [["--execute"]],
  ])("rejects %j", (args) => {
    expect(parseUpdateFreshnessArgs(args).ok).toBe(false);
  });
});

describe("runCli", () => {
  it("returns 2 for an unknown or missing command", async () => {
    const a = deps(vi.fn());
    expect(await runCli(["nope"], a.deps)).toBe(EXIT_USAGE);
    expect(await runCli([], a.deps)).toBe(EXIT_USAGE);
    expect(a.records[0]).toMatchObject({ event: "usage_error" });
  });

  it("returns 2 for bad arguments without touching the database", async () => {
    const run = vi.fn();
    const a = deps(run);
    expect(await runCli(["update-freshness", "--limit", "x"], a.deps)).toBe(EXIT_USAGE);
    expect(run).not.toHaveBeenCalled();
  });

  it("emits start and done records and returns 0 on success, always closing the pool", async () => {
    const run = vi.fn(async () => result());
    const a = deps(run);
    expect(await runCli(["update-freshness", "--dry-run"], a.deps)).toBe(EXIT_OK);
    expect(run).toHaveBeenCalledWith({ dryRun: true, since: undefined, limit: 0 });
    expect(a.records.map((r) => r.event)).toEqual(["update_freshness_start", "update_freshness_done"]);
    expect(a.records[1]).toMatchObject({ processed: 3, updated: 2, duration_ms: 5 });
    expect(a.close).toHaveBeenCalledOnce();
  });

  it("returns 1 when any batch failed", async () => {
    const a = deps(vi.fn(async () => result({ failed: 3 })));
    expect(await runCli(["update-freshness"], a.deps)).toBe(EXIT_FAILED);
  });

  it("returns 1 and logs only a fixed error code when the database is unavailable", async () => {
    const a = deps(vi.fn(async () => { throw new DbUnavailableError("db-rag secret 檔不存在"); }));
    expect(await runCli(["update-freshness"], a.deps)).toBe(EXIT_FAILED);
    expect(a.records.at(-1)).toEqual({ event: "update_freshness_failed", error: "db_unavailable: db-rag secret 檔不存在" });
    expect(a.close).toHaveBeenCalledOnce();
  });

  it("names unexpected errors by class only", async () => {
    const a = deps(vi.fn(async () => { throw new TypeError("password=hunter2"); }));
    expect(await runCli(["update-freshness"], a.deps)).toBe(EXIT_FAILED);
    expect(JSON.stringify(a.records)).not.toContain("hunter2");
    expect(a.records.at(-1)).toMatchObject({ error: "TypeError" });
  });
});
