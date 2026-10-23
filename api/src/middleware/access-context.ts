/**
 * CF Access 驗證通過後寫進 Hono context 的身分，供限流（rate-limit.ts）與 llm_usage 記錄使用。
 * - accessIdentity：JWT `sub`；service token 的 `sub` 為空，改用 `common_name`
 * - accessClaims：驗證過的 claims（唯讀）
 */

import type { Context } from "hono";
import type { JWTPayload } from "jose";

declare module "hono" {
  interface ContextVariableMap {
    accessIdentity: string;
    accessClaims: Readonly<JWTPayload>;
  }
}

export function getAccessIdentity(c: Context): string | null {
  return c.get("accessIdentity") ?? null;
}
