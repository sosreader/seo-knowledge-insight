/**
 * qa-ready middleware — 有界等待驗證。
 *
 * 對應 plans/active/lazy-qa-store-cold-start.md S2 的補充要求：
 * envoy route timeout 是 15s，qaStoreReady 不該無限期等 ensureQaStoreLoaded()，
 * 逾時要放行、但不能弄壞 ensureQaStoreLoaded() 本身的 memo 語意。
 *
 * 用 createQaStoreReadyMiddleware(小 timeout) 而非正式的 12s 常數來測，
 * 這樣可以用真實 timer 跑，不必跟 vi.useFakeTimers() 和完整 app 的其他
 * middleware（rate-limit、logger 等）打架，也不用真的等 12 秒。
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { Hono } from "hono";

const mocks = vi.hoisted(() => ({
  ensureQaStoreLoaded: vi.fn(),
}));

vi.mock("../../src/store/store-init.js", () => ({
  ensureQaStoreLoaded: mocks.ensureQaStoreLoaded,
  ensureSynonymsLoaded: vi.fn(async () => {}),
}));

import {
  createQaStoreReadyMiddleware,
  qaStoreReady,
  QA_STORE_WAIT_TIMEOUT_MS,
} from "../../src/middleware/qa-ready.js";

function appWith(middleware: ReturnType<typeof createQaStoreReadyMiddleware>) {
  const app = new Hono();
  app.use("/qa", middleware);
  app.get("/qa", (c) => c.json({ ok: true }));
  return app;
}

describe("qa-ready middleware — 有界等待", () => {
  beforeEach(() => {
    mocks.ensureQaStoreLoaded.mockReset();
  });

  it("QA_STORE_WAIT_TIMEOUT_MS 是具名常數（12s），不是 hardcode 在 race 裡的 magic number", () => {
    expect(QA_STORE_WAIT_TIMEOUT_MS).toBe(12_000);
    // 正式匯出的 qaStoreReady 就是用這個常數建構的
    expect(qaStoreReady).toBeTypeOf("function");
  });

  it("ensureQaStoreLoaded 在逾時前完成時，middleware 立即放行", async () => {
    mocks.ensureQaStoreLoaded.mockResolvedValue(undefined);
    const app = appWith(createQaStoreReadyMiddleware(1000));

    const start = Date.now();
    const res = await app.request("/qa");
    const elapsed = Date.now() - start;

    expect(res.status).toBe(200);
    expect(elapsed).toBeLessThan(200);
  });

  it("ensureQaStoreLoaded 逾時未完成時，middleware 仍會在時限內放行，不會一直卡住", async () => {
    let resolveLoad!: () => void;
    const pending = new Promise<void>((resolve) => {
      resolveLoad = resolve;
    });
    mocks.ensureQaStoreLoaded.mockReturnValue(pending);

    const timeoutMs = 30;
    const app = appWith(createQaStoreReadyMiddleware(timeoutMs));

    const start = Date.now();
    const res = await app.request("/qa");
    const elapsed = Date.now() - start;

    expect(res.status).toBe(200);
    expect(elapsed).toBeGreaterThanOrEqual(timeoutMs - 5);
    expect(elapsed).toBeLessThan(timeoutMs + 500); // 沒有真的卡住等 pending resolve

    resolveLoad(); // 收尾，避免 pending promise 洩漏到下一個測試
  });

  it("逾時後仍會呼叫 ensureQaStoreLoaded()；memo 語意本身在 store-init.ts 保證，middleware 不會自己重置它", async () => {
    // 永不 resolve，模擬「這次請求等到逾時，載入還在背景跑」。
    mocks.ensureQaStoreLoaded.mockReturnValue(new Promise(() => {}));
    const app = appWith(createQaStoreReadyMiddleware(20));

    await app.request("/qa");
    await app.request("/qa");

    // middleware 本身沒有自己的 memo——它每次都會呼叫一次 ensureQaStoreLoaded()，
    // 「不重觸發第二輪真正的載入」這件事是 ensureQaStoreLoaded() 內部
    // _qaPromise 的責任（見 tests/lazy-store-init.test.ts 的
    // 「連續請求只載入一次（memoize）」），Promise.race 本身不會取消或
    // 重置任何 promise，所以逾時不會破壞這個保證。
    expect(mocks.ensureQaStoreLoaded).toHaveBeenCalledTimes(2);
  });
});
