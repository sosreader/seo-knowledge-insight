import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  DEFAULT_RELOAD_INTERVAL_MS,
  MAX_RELOAD_INTERVAL_MS,
  resolveReloadIntervalMs,
  startStoreReloader,
  type ReloadResult,
  type StoreReloader,
} from "../../src/services/store-reloader.js";

const OK: ReloadResult = { ok: true, qa_items: 32439, synonyms: 7 };

describe("resolveReloadIntervalMs", () => {
  it.each([
    [undefined, DEFAULT_RELOAD_INTERVAL_MS],
    ["", DEFAULT_RELOAD_INTERVAL_MS],
    ["   ", DEFAULT_RELOAD_INTERVAL_MS],
    ["21600000", 21_600_000],
    [" 5000 ", 5000],
    ["0", 0],
    ["-1", 0],
    ["1.5", 0],
    ["abc", 0],
    ["1e3", 0],
    ["99999999999", MAX_RELOAD_INTERVAL_MS],
  ])("%j -> %j", (raw, expected) => {
    expect(resolveReloadIntervalMs(raw)).toBe(expected);
  });

  it("default is 6 hours", () => {
    expect(DEFAULT_RELOAD_INTERVAL_MS).toBe(21_600_000);
  });
});

describe("startStoreReloader", () => {
  let reloader: StoreReloader | null = null;
  const lines: string[] = [];
  const log = (line: string) => lines.push(line);

  beforeEach(() => {
    vi.useFakeTimers();
    lines.length = 0;
  });

  afterEach(() => {
    reloader?.stop();
    reloader = null;
    vi.useRealTimers();
  });

  it.each([0, -5, 1.5, Number.NaN])("returns null and creates no timer when intervalMs=%s", (intervalMs) => {
    const reload = vi.fn();
    reloader = startStoreReloader({ intervalMs, reload, log });
    expect(reloader).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
    vi.advanceTimersByTime(10_000_000);
    expect(reload).not.toHaveBeenCalled();
  });

  it("fires reload at each interval and logs one JSON line per round", async () => {
    const reload = vi.fn().mockResolvedValue(OK);
    reloader = startStoreReloader({ intervalMs: 1000, reload, log });
    expect(vi.getTimerCount()).toBe(1);

    await vi.advanceTimersByTimeAsync(999);
    expect(reload).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1);
    expect(reload).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(2000);
    expect(reload).toHaveBeenCalledTimes(3);
    expect(lines).toHaveLength(3);

    const entry = JSON.parse(lines[0]!);
    expect(entry).toMatchObject({ event: "store_reload", ok: true, qa_items: 32439, synonyms: 7 });
    expect(typeof entry.duration_ms).toBe("number");
  });

  it("measures duration_ms with the injected clock", async () => {
    const times = [100, 142.4];
    const now = vi.fn(() => times.shift() ?? 0);
    reloader = startStoreReloader({ intervalMs: 1000, reload: async () => OK, log, now });
    await reloader.runOnce();
    expect(JSON.parse(lines[0]!).duration_ms).toBe(42);
  });

  it("skips a round while the previous reload is still in flight", async () => {
    let release!: (value: ReloadResult) => void;
    const reload = vi.fn(() => new Promise<ReloadResult>((resolve) => (release = resolve)));
    reloader = startStoreReloader({ intervalMs: 1000, reload, log });

    await vi.advanceTimersByTimeAsync(1000);
    expect(reload).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(3000);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(lines.map((l) => JSON.parse(l).event)).toEqual([
      "store_reload_skipped",
      "store_reload_skipped",
      "store_reload_skipped",
    ]);
    expect(JSON.parse(lines[0]!).reason).toBe("in_flight");

    release(OK);
    await vi.advanceTimersByTimeAsync(0);
    expect(JSON.parse(lines.at(-1)!)).toMatchObject({ event: "store_reload", ok: true });

    await vi.advanceTimersByTimeAsync(1000);
    expect(reload).toHaveBeenCalledTimes(2);
  });

  it("runOnce returns false when a reload is already running", async () => {
    let release!: (value: ReloadResult) => void;
    const reload = vi.fn(() => new Promise<ReloadResult>((resolve) => (release = resolve)));
    reloader = startStoreReloader({ intervalMs: 1000, reload, log });

    const first = reloader.runOnce();
    expect(await reloader.runOnce()).toBe(false);
    release(OK);
    expect(await first).toBe(true);
  });

  it("logs ok:false with the fixed code and keeps the timer alive", async () => {
    const failure: ReloadResult = { ok: false, code: "db_timeout", failed: ["qa_items"] };
    const reload = vi.fn().mockResolvedValueOnce(failure).mockResolvedValueOnce(OK);
    reloader = startStoreReloader({ intervalMs: 1000, reload, log });

    await vi.advanceTimersByTimeAsync(1000);
    expect(JSON.parse(lines[0]!)).toMatchObject({
      event: "store_reload",
      ok: false,
      code: "db_timeout",
      failed: ["qa_items"],
    });

    await vi.advanceTimersByTimeAsync(1000);
    expect(JSON.parse(lines[1]!)).toMatchObject({ ok: true });
  });

  it("never throws when reload rejects, and does not leak the error message into the log", async () => {
    const reload = vi
      .fn()
      .mockRejectedValue(new Error("connect ECONNREFUSED postgres://user:secret@db.internal:5432/x"));
    reloader = startStoreReloader({ intervalMs: 1000, reload, log });

    await expect(reloader.runOnce()).resolves.toBe(true);
    await vi.advanceTimersByTimeAsync(1000);

    expect(JSON.parse(lines[0]!)).toMatchObject({ ok: false, code: "reload_failed" });
    expect(lines.join("\n")).not.toContain("secret");
    expect(lines.join("\n")).not.toContain("postgres://");
    // 失敗後下一輪仍會觸發
    expect(reload).toHaveBeenCalledTimes(2);
  });

  it("stop() clears the timer", async () => {
    const reload = vi.fn().mockResolvedValue(OK);
    reloader = startStoreReloader({ intervalMs: 1000, reload, log });
    reloader.stop();
    expect(vi.getTimerCount()).toBe(0);
    await vi.advanceTimersByTimeAsync(5000);
    expect(reload).not.toHaveBeenCalled();
  });

  it("unrefs the timer so it cannot keep the process alive", () => {
    const unref = vi.fn();
    const spy = vi.spyOn(globalThis, "setInterval").mockReturnValue({ unref } as unknown as NodeJS.Timeout);
    try {
      reloader = startStoreReloader({ intervalMs: 1000, reload: async () => OK, log });
      expect(unref).toHaveBeenCalledTimes(1);
    } finally {
      spy.mockRestore();
    }
  });

  it("uses console.log by default", async () => {
    const spy = vi.spyOn(console, "log").mockImplementation(() => undefined);
    try {
      reloader = startStoreReloader({ intervalMs: 1000, reload: async () => OK });
      await reloader.runOnce();
      expect(spy).toHaveBeenCalledTimes(1);
      expect(JSON.parse(spy.mock.calls[0]![0] as string).event).toBe("store_reload");
    } finally {
      spy.mockRestore();
    }
  });
});
