/**
 * qa-ready middleware — 有界等待驗證。
 *
 * 對應 plans/active/lazy-qa-store-cold-start.md S2 的補充要求：
 * envoy route timeout 是 15s，qaStoreReady 不該無限期等 ensureQaStoreLoaded()，
 * 逾時要放行——但若這時 QA store 實際上仍未載入完成，不能靜默回 200 + 空結果
 * （那是「回沒有資料」的靜默錯誤資料），要回 503 帶使用者看得懂的訊息，
 * 且要分辨「還在載入中」與「重試後仍失敗」。也不能破壞
 * ensureQaStoreLoaded() 本身的 memo 語意，也不該留下沒清掉的 timer。
 *
 * 用 createQaStoreReadyMiddleware(小 timeout) 而非正式的 12s 常數來測，
 * 這樣可以用真實 timer 跑，不必跟 vi.useFakeTimers() 和完整 app 的其他
 * middleware（rate-limit、logger 等）打架，也不用真的等 12 秒。
 * timer 洩漏那個測試例外——用小型獨立 app + fake timer，不套完整 app。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Hono } from "hono";

const mocks = vi.hoisted(() => ({
  ensureQaStoreLoaded: vi.fn(),
  qaStoreLoadFailed: vi.fn(() => false),
  qaStore: { loaded: false },
}));

vi.mock("../../src/store/store-init.js", () => ({
  ensureQaStoreLoaded: mocks.ensureQaStoreLoaded,
  ensureSynonymsLoaded: vi.fn(async () => {}),
  qaStoreLoadFailed: mocks.qaStoreLoadFailed,
}));

vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: mocks.qaStore,
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
    mocks.qaStoreLoadFailed.mockReset().mockReturnValue(false);
    mocks.qaStore.loaded = false;
  });

  it("QA_STORE_WAIT_TIMEOUT_MS 是具名常數（12s），不是 hardcode 在 race 裡的 magic number", () => {
    expect(QA_STORE_WAIT_TIMEOUT_MS).toBe(12_000);
    // 正式匯出的 qaStoreReady 就是用這個常數建構的
    expect(qaStoreReady).toBeTypeOf("function");
  });

  it("載入在逾時前完成時，middleware 立即放行（200）", async () => {
    mocks.ensureQaStoreLoaded.mockImplementation(async () => {
      mocks.qaStore.loaded = true;
    });
    const app = appWith(createQaStoreReadyMiddleware(1000));

    const start = Date.now();
    const res = await app.request("/qa");
    const elapsed = Date.now() - start;

    expect(res.status).toBe(200);
    expect(elapsed).toBeLessThan(200);
  });

  it("逾時且 QA store 仍未載入完成時，回 503 帶『載入中』訊息，不會靜默回空", async () => {
    let resolveLoad!: () => void;
    const pending = new Promise<void>((resolve) => {
      resolveLoad = resolve;
    });
    mocks.ensureQaStoreLoaded.mockReturnValue(pending);
    // qaStoreLoadFailed 維持 false（beforeEach 預設）：這是「還在載入中」，不是「失敗」

    const timeoutMs = 30;
    const app = appWith(createQaStoreReadyMiddleware(timeoutMs));

    const start = Date.now();
    const res = await app.request("/qa");
    const elapsed = Date.now() - start;

    expect(res.status).toBe(503);
    expect(elapsed).toBeGreaterThanOrEqual(timeoutMs - 5);
    expect(elapsed).toBeLessThan(timeoutMs + 500); // 沒有真的卡住等 pending resolve

    const body = await res.json();
    expect(body.data).toBeNull();
    expect(body.error).toContain("載入中");

    resolveLoad(); // 收尾，避免 pending promise 洩漏到下一個測試
  });

  it("逾時且上一輪已經重試後仍失敗時，回 503 帶『載入失敗』訊息（跟『載入中』的文字要能分辨）", async () => {
    mocks.ensureQaStoreLoaded.mockReturnValue(new Promise(() => {})); // 這次請求還在等
    mocks.qaStoreLoadFailed.mockReturnValue(true); // 但上一輪已經判定失敗

    const app = appWith(createQaStoreReadyMiddleware(20));
    const res = await app.request("/qa");

    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toContain("載入失敗");
    expect(body.error).not.toContain("載入中");
  });

  it("在逾時前一瞬完成的話不回 503——判斷依據是 qaStore.loaded 的實際狀態，不是 race 有沒有逾時", async () => {
    mocks.ensureQaStoreLoaded.mockImplementation(
      () =>
        new Promise<void>((resolve) =>
          setTimeout(() => {
            mocks.qaStore.loaded = true;
            resolve();
          }, 5),
        ),
    );
    const app = appWith(createQaStoreReadyMiddleware(200)); // timeout 遠大於載入耗時

    const res = await app.request("/qa");
    expect(res.status).toBe(200);
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

describe("qa-ready middleware — 逾時 timer 不洩漏", () => {
  beforeEach(() => {
    mocks.ensureQaStoreLoaded.mockReset();
    mocks.qaStoreLoadFailed.mockReset().mockReturnValue(false);
    mocks.qaStore.loaded = false;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("載入 promise 先贏時，逾時用的 setTimeout 會被 clearTimeout，不留下 pending timer", async () => {
    mocks.ensureQaStoreLoaded.mockImplementation(async () => {
      mocks.qaStore.loaded = true;
    });
    const app = appWith(createQaStoreReadyMiddleware(10_000));

    const resPromise = app.request("/qa");
    await vi.advanceTimersByTimeAsync(0); // 讓已經 resolve 的 promise 有機會 flush
    await resPromise;

    expect(vi.getTimerCount()).toBe(0);
  });
});
