/**
 * 定期重載計時器（rag-api 長駐 process 用）。
 *
 * 動機：QA 與 synonyms 在啟動時整表載進記憶體，VW CronJob 週更 freshness_score 後，
 * 不重啟就看不到新值。這裡只負責「何時重載」：到點呼叫注入的 reload()，
 * 重載本身（換快取、失敗保舊）由 store 層負責。
 *
 * 設計：
 *   - setInterval(...).unref()：不擋 process 關閉
 *   - 不重疊：上一輪還在跑就跳過本輪
 *   - 永不丟例外：reload() 拋錯也只記成 ok:false，計時器不會因此停掉
 *   - 每輪一行 JSON log，只含固定錯誤代碼，不帶連線字串
 */

/** 預設 6 小時。 */
export const DEFAULT_RELOAD_INTERVAL_MS = 6 * 60 * 60 * 1000;
/** Node 計時器上限（2^31-1 ms，約 24.8 天）；超過會被當成 1ms 狂觸發，所以夾住。 */
export const MAX_RELOAD_INTERVAL_MS = 2_147_483_647;

export type ReloadResult =
  | { readonly ok: true; readonly qa_items: number; readonly synonyms: number }
  | { readonly ok: false; readonly code: string; readonly failed: readonly string[] };

export interface StoreReloaderOptions {
  /** 重載間隔（毫秒）；非正整數視為停用。 */
  readonly intervalMs: number;
  /** 實際執行重載；預期不拋，但拋了也會被接住。 */
  readonly reload: () => Promise<ReloadResult>;
  /** 每輪輸出一行（預設 console.log）。 */
  readonly log?: (line: string) => void;
  /** 量測耗時用的單調時鐘（預設 performance.now）。 */
  readonly now?: () => number;
}

export interface StoreReloader {
  /** 立即跑一輪（測試與手動觸發用）；有 in-flight 就回 false 並跳過。 */
  runOnce(): Promise<boolean>;
  stop(): void;
}

/**
 * 解析 RAG_RELOAD_INTERVAL_MS：
 *   - 未設或空字串 → 預設 6 小時
 *   - "0"、負數、小數、非數字 → 0（停用）
 *   - 超過 Node 計時器上限 → 夾到上限
 */
export function resolveReloadIntervalMs(raw: string | undefined): number {
  const text = (raw ?? "").trim();
  if (text === "") return DEFAULT_RELOAD_INTERVAL_MS;
  if (!/^\d+$/.test(text)) return 0;
  const value = Number(text);
  if (!Number.isSafeInteger(value) || value <= 0) return 0;
  return Math.min(value, MAX_RELOAD_INTERVAL_MS);
}

function isEnabled(intervalMs: number): boolean {
  return Number.isInteger(intervalMs) && intervalMs > 0;
}

/** 停用（intervalMs 非正整數）時回傳 null，且不建立任何 timer。 */
export function startStoreReloader(options: StoreReloaderOptions): StoreReloader | null {
  const { intervalMs, reload } = options;
  if (!isEnabled(intervalMs)) return null;

  const log = options.log ?? ((line: string) => console.log(line));
  const now = options.now ?? (() => performance.now());
  let inFlight = false;

  const runOnce = async (): Promise<boolean> => {
    if (inFlight) {
      log(JSON.stringify({ event: "store_reload_skipped", reason: "in_flight" }));
      return false;
    }
    inFlight = true;
    const startedAt = now();
    try {
      const result = await safeReload(reload);
      const duration_ms = Math.round(now() - startedAt);
      log(JSON.stringify({ event: "store_reload", ...result, duration_ms }));
    } finally {
      inFlight = false;
    }
    return true;
  };

  const timer = setInterval(() => {
    void runOnce();
  }, intervalMs);
  timer.unref();

  return { runOnce, stop: () => clearInterval(timer) };
}

async function safeReload(reload: () => Promise<ReloadResult>): Promise<ReloadResult> {
  try {
    return await reload();
  } catch {
    return { ok: false, code: "reload_failed", failed: [] };
  }
}
