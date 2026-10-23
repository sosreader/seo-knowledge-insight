/**
 * rag-api（PG 模式）不執行的 pipeline 路由（S3.7）→ 501 run_locally。
 *
 * - 觸發類：fetch、extract-qa、dedupe-classify、fetch-articles（spawn Python、寫 output/）
 * - 本機檔案依賴：meetings（含 preview）、unprocessed、logs、source-docs 單檔 preview（讀 raw_data/、output/）
 *
 * 本機檔案模式照舊執行；/status、/source-docs 列表、metrics 類、crawled-not-indexed、llm-usage 不受影響。
 * 必須在 pipeline.ts 註冊 handler 之前呼叫（Hono 依註冊順序執行）。
 */

import type { Hono } from "hono";
import { runLocallyInRagApi } from "../middleware/feature-gates.js";

export const RUN_LOCALLY_ROUTES: ReadonlyArray<{ readonly method: "GET" | "POST"; readonly path: string }> = [
  { method: "POST", path: "/fetch" },
  { method: "POST", path: "/extract-qa" },
  { method: "POST", path: "/dedupe-classify" },
  { method: "POST", path: "/fetch-articles" },
  { method: "GET", path: "/meetings" },
  { method: "GET", path: "/meetings/:id/preview" },
  { method: "GET", path: "/unprocessed" },
  { method: "GET", path: "/logs" },
  { method: "GET", path: "/source-docs/:collection/:file/preview" },
];

export function applyRunLocallyGates(route: Hono): void {
  for (const { method, path } of RUN_LOCALLY_ROUTES) {
    route.on(method, path, runLocallyInRagApi);
  }
}
