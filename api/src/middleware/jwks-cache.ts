/**
 * Cloudflare Access team JWKS 快取（`https://<team_domain>/cdn-cgi/access/certs`）。
 *
 * 語意對齊 vocus-warehouse `auth/jwks.py`：
 * - 快取 1 小時；過期後下一次查 key 時重抓，重抓失敗沿用舊 key（Cloudflare 輪替有重疊期）
 * - 遇到未知 kid 重抓一次；強制重抓之間至少間隔 30 秒，避免偽造 kid 放大對外請求
 * - 只收 RSA key（驗證器只接受 RS256）
 * - 從未抓到任何 key 時拋 JwksUnavailableError（middleware 回 503，不是 401）
 */

import type { JWK } from "jose";

export const JWKS_TTL_MS = 60 * 60 * 1000;
export const MIN_REFRESH_INTERVAL_MS = 30 * 1000;
const FETCH_TIMEOUT_MS = 5_000;
const MAX_JWKS_BYTES = 1_000_000;
const USER_AGENT = "seo-knowledge-insight-rag-api";

export type JsonFetcher = (url: string) => Promise<unknown>;

export interface JwksCacheOptions {
  readonly fetchJson?: JsonFetcher;
  readonly now?: () => number;
  readonly ttlMs?: number;
  readonly minRefreshIntervalMs?: number;
}

export interface RsaJwk extends JWK {
  readonly kid: string;
  readonly kty: "RSA";
}

export class JwksUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "JwksUnavailableError";
  }
}

export function certsUrl(teamDomain: string): string {
  return `https://${teamDomain}/cdn-cgi/access/certs`;
}

async function defaultFetchJson(url: string): Promise<unknown> {
  const res = await fetch(url, {
    headers: { "User-Agent": USER_AGENT },
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  });
  if (!res.ok) throw new JwksUnavailableError(`JWKS HTTP ${res.status}`);
  const body = await res.text();
  if (body.length > MAX_JWKS_BYTES) throw new JwksUnavailableError("JWKS 回應超過大小上限");
  return JSON.parse(body) as unknown;
}

function isUsableRsaKey(raw: unknown): raw is RsaJwk {
  if (typeof raw !== "object" || raw === null) return false;
  const key = raw as Record<string, unknown>;
  return key.kty === "RSA" && typeof key.kid === "string" && key.kid.length > 0;
}

/** JWKS JSON → RSA key 清單；略過非 RSA 或缺 kid 的 key，一把都沒有時視為失敗。 */
export function parseJwks(data: unknown): readonly RsaJwk[] {
  const rawKeys = (data as { keys?: unknown } | null)?.keys;
  if (!Array.isArray(rawKeys)) throw new JwksUnavailableError("JWKS 缺少 keys 陣列");
  const keys = rawKeys.filter(isUsableRsaKey);
  if (keys.length === 0) throw new JwksUnavailableError("JWKS 沒有可用的 RSA key");
  return Object.freeze(keys.map((k) => Object.freeze({ ...k })));
}

export class JwksCache {
  private keys: ReadonlyMap<string, RsaJwk> = new Map();
  private fetchedAt: number | null = null;
  private lastAttempt: number | null = null;
  private inflight: Promise<void> | null = null;
  private readonly fetchJson: JsonFetcher;
  private readonly now: () => number;
  private readonly ttlMs: number;
  private readonly minIntervalMs: number;

  constructor(
    readonly url: string,
    options: JwksCacheOptions = {},
  ) {
    this.fetchJson = options.fetchJson ?? defaultFetchJson;
    this.now = options.now ?? Date.now;
    this.ttlMs = options.ttlMs ?? JWKS_TTL_MS;
    this.minIntervalMs = options.minRefreshIntervalMs ?? MIN_REFRESH_INTERVAL_MS;
  }

  /** 查 kid 對應的 key；快取過期或 kid 未知時（受最小間隔限制）重抓一次。 */
  async getKey(kid: string): Promise<RsaJwk | null> {
    if (this.isStale()) await this.tryRefresh();
    if (this.keys.size === 0) throw new JwksUnavailableError("JWKS 尚未取得");
    const cached = this.keys.get(kid);
    if (cached) return cached;
    await this.tryRefresh();
    return this.keys.get(kid) ?? null;
  }

  private isStale(): boolean {
    return this.fetchedAt === null || this.now() - this.fetchedAt >= this.ttlMs;
  }

  private refreshAllowed(): boolean {
    return this.lastAttempt === null || this.now() - this.lastAttempt >= this.minIntervalMs;
  }

  /**
   * 距上次嘗試超過最小間隔才重抓（過期與未知 kid 都受此限制，JWKS 端點掛掉時不會每個請求都打）。
   * 併發時共用同一個 in-flight 請求；失敗只記 log，保留舊 key。
   */
  private async tryRefresh(): Promise<void> {
    if (!this.inflight) {
      if (!this.refreshAllowed()) return;
      this.inflight = this.refresh().finally(() => {
        this.inflight = null;
      });
    }
    await this.inflight;
  }

  private async refresh(): Promise<void> {
    this.lastAttempt = this.now();
    try {
      const keys = parseJwks(await this.fetchJson(this.url));
      this.keys = new Map(keys.map((k) => [k.kid, k]));
      this.fetchedAt = this.lastAttempt;
    } catch (err) {
      const reason = err instanceof Error ? err.message : String(err);
      console.warn(`[cf-access] JWKS refresh failed: ${reason}`);
    }
  }
}
