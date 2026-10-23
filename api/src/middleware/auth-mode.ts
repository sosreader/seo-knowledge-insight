import type { MiddlewareHandler } from "hono";

/**
 * 驗證模式：
 * - `cf-access`：容器模式（vocus-stg EKS 的 rag-api）。驗 Cloudflare Access JWT（cf-access.ts）
 * - `api-key`：Lambda 模式（即將退役）與本機 docker-compose／evals。沿用 X-API-Key（auth.ts）
 *
 * env `AUTH_MODE` 未設時：Lambda → api-key，其餘 → cf-access。
 * 設了無法辨識的值一律退回 cf-access（fail closed：寧可 503／401，也不要意外變成無驗證）。
 */
export type AuthMode = "cf-access" | "api-key";

export function resolveAuthMode(raw: string | undefined, isLambda: boolean): AuthMode {
  const value = (raw ?? "").trim();
  if (value === "cf-access" || value === "api-key") return value;
  if (value === "" && isLambda) return "api-key";
  return "cf-access";
}

export interface AuthMiddlewares {
  readonly apiKey: MiddlewareHandler;
  readonly cfAccess: MiddlewareHandler;
}

export function selectAuthMiddleware(mode: AuthMode, middlewares: AuthMiddlewares): MiddlewareHandler {
  return mode === "api-key" ? middlewares.apiKey : middlewares.cfAccess;
}
