/**
 * Cloudflare Access JWT 驗證（容器模式的 rag-api；取代 X-API-Key）。
 *
 * 語意對齊 vocus-warehouse `auth/access_jwt.py`，差異只在 rag-api 只有一組 AUD 允許清單：
 * - header `Cf-Access-Jwt-Assertion`；只收 RS256（none、HS*、RS384 等一律拒絕），kid 必填
 * - `iss` 必須是 `https://<team_domain>`；`aud` 至少一個在 `RAG_AUDS`；`exp`／`iss`／`aud` 必填
 * - `exp`／`nbf` 容忍 60 秒時鐘誤差
 * - 簽章 key 取自 team JWKS（jwks-cache.ts：快取 1 h、未知 kid 重抓一次）
 * - `RAG_AUDS` 或 `CF_ACCESS_TEAM_DOMAIN` 缺值 → 503 `unavailable`（fail closed；/health 不經過這裡）
 * - JWKS 從未取得 → 503 `unavailable`；其餘驗證失敗一律 401 `unauthorized`，原因只寫 log 不回給 client
 */

import { createMiddleware } from "hono/factory";
import type { MiddlewareHandler } from "hono";
import { decodeProtectedHeader, importJWK, jwtVerify, type JWTPayload } from "jose";
import { fail } from "../schemas/api-response.js";
import { JwksCache, JwksUnavailableError, certsUrl } from "./jwks-cache.js";
import "./access-context.js";

export { getAccessIdentity } from "./access-context.js";

export const ACCESS_JWT_HEADER = "Cf-Access-Jwt-Assertion";
export const CLOCK_TOLERANCE_SECONDS = 60;
const ALGORITHM = "RS256";
const REQUIRED_CLAIMS = ["exp", "iss", "aud"];
const HOSTNAME_RE = /^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9-]{1,63})+$/;

export interface AccessSettings {
  readonly teamDomain: string;
  readonly auds: readonly string[];
}

class AccessRejected extends Error {
  constructor(readonly reason: string) {
    super(reason);
  }
}

/** team domain（可帶或不帶 scheme）與逗號分隔的 AUD 清單；任一缺值或格式不對回 null（fail closed）。 */
export function parseAccessSettings(
  teamDomain: string | undefined,
  rawAuds: string | undefined,
): AccessSettings | null {
  const domain = (teamDomain ?? "")
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/\/+$/, "");
  const auds = (rawAuds ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (!HOSTNAME_RE.test(domain) || auds.length === 0) return null;
  return Object.freeze({ teamDomain: domain, auds: Object.freeze(auds) });
}

function nonEmptyString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

/** JWT `sub`；service token 的 `sub` 為空，改用 `common_name`。兩者皆無 → 拒絕。 */
export function identityFromClaims(claims: JWTPayload): string | null {
  return nonEmptyString(claims.sub) ?? nonEmptyString(claims.common_name);
}

function readKid(token: string): string {
  let header: ReturnType<typeof decodeProtectedHeader>;
  try {
    header = decodeProtectedHeader(token);
  } catch {
    throw new AccessRejected("malformed_token");
  }
  if (header.alg !== ALGORITHM) throw new AccessRejected("unsupported_alg");
  const kid = nonEmptyString(header.kid);
  if (!kid) throw new AccessRejected("missing_kid");
  return kid;
}

async function verifyToken(
  token: string,
  settings: AccessSettings,
  jwks: JwksCache,
): Promise<JWTPayload> {
  const jwk = await jwks.getKey(readKid(token));
  if (!jwk) throw new AccessRejected("unknown_kid");
  try {
    const key = await importJWK(jwk, ALGORITHM);
    const { payload } = await jwtVerify(token, key, {
      algorithms: [ALGORITHM],
      issuer: `https://${settings.teamDomain}`,
      audience: [...settings.auds],
      clockTolerance: CLOCK_TOLERANCE_SECONDS,
      requiredClaims: REQUIRED_CLAIMS,
    });
    return payload;
  } catch (err) {
    const code = (err as { code?: string }).code ?? "invalid_token";
    throw new AccessRejected(code);
  }
}

export function createCfAccessMiddleware(
  settings: AccessSettings | null,
  jwks: JwksCache | null = settings ? new JwksCache(certsUrl(settings.teamDomain)) : null,
): MiddlewareHandler {
  return createMiddleware(async (c, next) => {
    if (!settings || !jwks) return c.json(fail("unavailable"), 503);

    const token = c.req.header(ACCESS_JWT_HEADER) ?? "";
    try {
      if (!token) throw new AccessRejected("missing_token");
      const claims = await verifyToken(token, settings, jwks);
      const identity = identityFromClaims(claims);
      if (!identity) throw new AccessRejected("missing_identity");
      c.set("accessIdentity", identity);
      c.set("accessClaims", Object.freeze({ ...claims }));
    } catch (err) {
      if (err instanceof JwksUnavailableError) {
        console.error(`[cf-access] JWKS unavailable: ${err.message}`);
        return c.json(fail("unavailable"), 503);
      }
      const reason = err instanceof AccessRejected ? err.reason : "internal";
      console.warn(`[cf-access] rejected ${c.req.method} ${c.req.path}: ${reason}`);
      return c.json(fail("unauthorized"), 401);
    }
    await next();
  });
}
