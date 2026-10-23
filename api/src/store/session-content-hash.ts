/**
 * app_session.content_hash（NOT NULL）的計算方式，與 SKI scripts/sync_db_sources.py 的
 * session_content_hash() 相同：`sha256:` + sha256(canonical JSON of {title, messages})，
 * canonical = 物件 key 遞迴排序、無空白、非 ASCII 原樣（Python json.dumps(sort_keys=True,
 * separators=(",", ":"), ensure_ascii=False)）。metadata 不進 hash（同 Python 版）。
 *
 * 已知差異：整數值的浮點數（例如 1.0）Python 會輸出 "1.0"、JS 輸出 "1"；session 訊息由 JS 寫入，
 * 本來就不會出現 1.0 這種表示，且 chat 上線後 VW 為權威（S4.6，sync 停送 sessions），不影響去重。
 */

import { createHash } from "node:crypto";

export const HASH_PREFIX = "sha256:";

export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => v !== undefined)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
    return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${canonicalJson(v)}`).join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

export function sessionContentHash(title: string, messages: readonly unknown[]): string {
  const canonical = canonicalJson({ title, messages });
  return HASH_PREFIX + createHash("sha256").update(canonical, "utf-8").digest("hex");
}
