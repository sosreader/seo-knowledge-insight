/**
 * PostgreSQL 連線池（vocus-warehouse，角色 warehouse_rag）。
 *
 * 憑證：K8s Secret `vocus-warehouse-db-rag` 掛成檔案，env `VW_DB_SECRET_FILE_RAG` 指向它。
 *   - JSON 檔（Secrets Manager payload 原樣：username、password、host、port、dbname），或
 *   - volume 掛載的目錄（每個 key 一個檔）。
 *   比照 vocus-warehouse 的 `VW_DB_SECRET_FILE_APP`。不讀 PG* env 當憑證來源。
 *
 * TLS 一律 verify-full：CA bundle 預設 image 內的 /etc/ssl/rds/global-bundle.pem（Dockerfile 下載並驗
 *   sha256），可由 PGSSLROOTCERT 覆寫路徑；找不到 CA 檔就視為不可用，不降級成不驗證。
 *   只有測試以 _configurePgClientForTest({ ssl: false }) 才能關 TLS。
 *
 * 缺 secret 檔、欄位不齊、CA 檔不在：getPool() 拋 DbUnavailableError，路由回 503，app 照常啟動。
 * 失敗不快取，下一個請求會重讀（Secret 稍後才掛上也能自行恢復）；成功建立的 pool 才快取。
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import pg from "pg";
import { config } from "../config.js";
import { DbTimeoutError, DbUnavailableError } from "./store-errors.js";

export const RAG_SECRET_FILE_ENV = "VW_DB_SECRET_FILE_RAG";
export const DEFAULT_STATEMENT_TIMEOUT_MS = 10_000;
export const APPLICATION_NAME = "rag-api";
export const DEFAULT_SSLROOTCERT = "/etc/ssl/rds/global-bundle.pem";
const CONNECT_TIMEOUT_MS = 5_000;
const IDLE_TIMEOUT_MS = 30_000;
const POOL_MAX = 5;
const SECRET_FIELDS = ["username", "password", "host", "port", "dbname"] as const;

export interface DbSecret {
  readonly username: string;
  readonly password: string;
  readonly host: string;
  readonly port: number;
  readonly dbname: string;
}

type SslOption = false | { readonly ca: string; readonly rejectUnauthorized: true };

interface PgClientOptions {
  readonly secretFile: string;
  readonly sslRootCert: string;
  /** 測試容器沒有 TLS；正式路徑永遠是 undefined（= verify-full）。 */
  readonly ssl?: false;
}

function configuredSecretFile(): string {
  return (config.VW_DB_SECRET_FILE_RAG ?? "").trim();
}

/** 有設 VW_DB_SECRET_FILE_RAG 就是 PG 模式（rag-api）；檔案能不能讀是另一回事，見 getPool()。 */
export function hasPg(): boolean {
  return configuredSecretFile() !== "";
}

function readSecretDir(dir: string): Record<string, string> {
  const present = new Set(readdirSync(dir));
  return Object.fromEntries(
    SECRET_FIELDS.filter((f) => present.has(f)).map((f) => [
      f,
      readFileSync(join(dir, f), "utf-8").trim(),
    ]),
  );
}

function readSecretJson(path: string): Record<string, unknown> {
  let payload: unknown;
  try {
    payload = JSON.parse(readFileSync(path, "utf-8"));
  } catch {
    throw new DbUnavailableError("db-rag secret 不是合法 JSON");
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new DbUnavailableError("db-rag secret 的 JSON 必須是物件");
  }
  return payload as Record<string, unknown>;
}

function readRawSecret(path: string): Record<string, unknown> {
  let isDir: boolean;
  try {
    isDir = statSync(path).isDirectory();
  } catch {
    throw new DbUnavailableError("db-rag secret 檔不存在");
  }
  return isDir ? readSecretDir(path) : readSecretJson(path);
}

/** 讀 db-rag secret；錯誤訊息只列缺的欄位名，不含任何值。 */
export function readDbSecret(path: string): DbSecret {
  const raw = readRawSecret(path);
  const missing = SECRET_FIELDS.filter((f) => raw[f] === undefined || raw[f] === null || raw[f] === "");
  if (missing.length > 0) {
    throw new DbUnavailableError(`db-rag secret 缺欄位：${missing.join(", ")}`);
  }
  const port = Number(raw.port);
  if (!Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new DbUnavailableError("db-rag secret 的 port 不合法");
  }
  return {
    username: String(raw.username),
    password: String(raw.password),
    host: String(raw.host),
    port,
    dbname: String(raw.dbname),
  };
}

function resolveSsl(options: PgClientOptions): SslOption {
  if (options.ssl === false) return false;
  try {
    return { ca: readFileSync(options.sslRootCert, "utf-8"), rejectUnauthorized: true };
  } catch {
    throw new DbUnavailableError("RDS CA bundle 不存在（sslmode=verify-full 不降級）");
  }
}

/** 純函式：secret＋TLS 設定 → pg.PoolConfig（timezone 固定 UTC，時間欄的 ISO 字串才穩定）。 */
export function buildPoolConfig(secret: DbSecret, ssl: SslOption): pg.PoolConfig {
  return {
    host: secret.host,
    port: secret.port,
    user: secret.username,
    password: secret.password,
    database: secret.dbname,
    ssl,
    application_name: APPLICATION_NAME,
    statement_timeout: DEFAULT_STATEMENT_TIMEOUT_MS,
    options: "-c timezone=UTC",
    connectionTimeoutMillis: CONNECT_TIMEOUT_MS,
    idleTimeoutMillis: IDLE_TIMEOUT_MS,
    max: POOL_MAX,
    keepAlive: true,
  };
}

let pool: pg.Pool | null = null;
let testOverrides: Partial<PgClientOptions> = {};

function currentOptions(): PgClientOptions {
  return {
    secretFile: configuredSecretFile(),
    sslRootCert: config.PGSSLROOTCERT ?? DEFAULT_SSLROOTCERT,
    ...testOverrides,
  };
}

/** 取得連線池；secret 不可用時拋 DbUnavailableError（不快取失敗）。 */
export function getPool(): pg.Pool {
  if (pool) return pool;
  const options = currentOptions();
  if (!options.secretFile) {
    throw new DbUnavailableError(`${RAG_SECRET_FILE_ENV} 未設定（db-rag secret 未掛載）`);
  }
  const secret = readDbSecret(options.secretFile);
  const created = new pg.Pool(buildPoolConfig(secret, resolveSsl(options)));
  // idle client 斷線時 pg 會 emit error；沒有 listener 會讓整個 process crash。
  created.on("error", (err) => console.warn(`pg pool idle client error: ${err.message}`));
  pool = created;
  return created;
}

const UNAVAILABLE_SQLSTATE_PREFIXES = ["08", "28", "3D", "53", "57P"];
const UNAVAILABLE_NODE_CODES = new Set([
  "ECONNREFUSED", "ECONNRESET", "ENOTFOUND", "ETIMEDOUT", "EAI_AGAIN", "EHOSTUNREACH",
  // TLS（verify-full 驗不過）：設定問題，對呼叫端一樣是 DB 不可用
  "DEPTH_ZERO_SELF_SIGNED_CERT", "SELF_SIGNED_CERT_IN_CHAIN", "UNABLE_TO_VERIFY_LEAF_SIGNATURE",
  "UNABLE_TO_GET_ISSUER_CERT_LOCALLY", "CERT_HAS_EXPIRED", "ERR_TLS_CERT_ALTNAME_INVALID",
]);
const UNAVAILABLE_MESSAGES = [
  "timeout exceeded when trying to connect",
  "Connection terminated",
  "The server does not support SSL connections",
];

/** pg／node 錯誤 → store 錯誤；查詢本身的錯（語法、權限、約束）原樣回傳讓它變 500。 */
export function classifyPgError(err: unknown): unknown {
  if (err instanceof DbUnavailableError || err instanceof DbTimeoutError) return err;
  const e = err as { code?: string; message?: string };
  const code = typeof e?.code === "string" ? e.code : "";
  const message = typeof e?.message === "string" ? e.message : "";
  if (code === "57014") return new DbTimeoutError({ cause: err });
  if (
    UNAVAILABLE_NODE_CODES.has(code) ||
    UNAVAILABLE_SQLSTATE_PREFIXES.some((p) => code.startsWith(p)) ||
    UNAVAILABLE_MESSAGES.some((m) => message.includes(m))
  ) {
    return new DbUnavailableError(code || "connection_failed", { cause: err });
  }
  return err;
}

export interface QueryOptions {
  /** 覆寫這一句的 statement_timeout（例如啟動時全量載入 QA）；預設 10s。 */
  readonly timeoutMs?: number;
}

export type Queryable = Pick<pg.PoolClient, "query">;

async function runWithTimeout<T extends pg.QueryResultRow>(
  client: pg.PoolClient,
  text: string,
  values: readonly unknown[],
  timeoutMs: number,
): Promise<pg.QueryResult<T>> {
  await client.query("BEGIN");
  try {
    await client.query(`SET LOCAL statement_timeout = ${Math.trunc(timeoutMs)}`);
    const result = await client.query<T>(text, values as unknown[]);
    await client.query("COMMIT");
    return result;
  } catch (err) {
    await client.query("ROLLBACK").catch(() => undefined);
    throw err;
  }
}

/** 執行單一查詢並回傳完整結果；錯誤經 classifyPgError 轉換。 */
export async function pgQueryResult<T extends pg.QueryResultRow>(
  text: string,
  values: readonly unknown[] = [],
  options: QueryOptions = {},
): Promise<pg.QueryResult<T>> {
  try {
    const p = getPool();
    if (!options.timeoutMs) return await p.query<T>(text, values as unknown[]);
    const client = await p.connect();
    try {
      return await runWithTimeout<T>(client, text, values, options.timeoutMs);
    } finally {
      client.release();
    }
  } catch (err) {
    throw classifyPgError(err);
  }
}

/** 執行單一查詢，回傳 rows。 */
export async function pgQuery<T extends pg.QueryResultRow>(
  text: string,
  values: readonly unknown[] = [],
  options: QueryOptions = {},
): Promise<T[]> {
  return (await pgQueryResult<T>(text, values, options)).rows;
}

/** 在單一交易內執行 fn（例如 SELECT ... FOR UPDATE 後 UPDATE）。 */
export async function withPgTransaction<T>(fn: (client: Queryable) => Promise<T>): Promise<T> {
  try {
    const client = await getPool().connect();
    try {
      await client.query("BEGIN");
      const result = await fn(client);
      await client.query("COMMIT");
      return result;
    } catch (err) {
      await client.query("ROLLBACK").catch(() => undefined);
      throw err;
    } finally {
      client.release();
    }
  } catch (err) {
    throw classifyPgError(err);
  }
}

/** timestamptz 欄位以 PostgREST 相同的 ISO 8601 字串輸出（例：2026-10-23T01:02:03.456+00:00）。 */
export function isoColumn(column: string, alias: string = column.split(".").pop()!): string {
  return `to_json(${column}) #>> '{}' AS ${alias}`;
}

/** 關閉連線池（graceful shutdown 與測試用）。 */
export async function closePool(): Promise<void> {
  const current = pool;
  pool = null;
  if (current) await current.end();
}

/** 測試用：覆寫 secret 路徑／關 TLS，並丟掉既有 pool。 */
export async function _configurePgClientForTest(overrides: Partial<PgClientOptions>): Promise<void> {
  await closePool();
  testOverrides = { ...overrides };
}
