/**
 * 每個整合測試檔一份獨立 DB（從 template 複製），pg-client 指向它並以 warehouse_rag 連線。
 *
 * 用法：
 *   const fx = usePgFixture("qa");          // 在 describe 外呼叫
 *   describe.skipIf(!pgAvailable)(...)      // 沒 Docker 時跳過
 *   await fx.admin().query("INSERT ...")    // superuser 連線，用來塞種子資料
 */

import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomBytes } from "node:crypto";
import pg from "pg";
import { afterAll, beforeAll, inject } from "vitest";
import { _configurePgClientForTest, closePool } from "../../src/store/pg-client.js";
import type { PgFixtureInfo } from "./pg-fixture-types.js";

export const pgInfo: PgFixtureInfo | null = inject("pgFixture");
export const pgAvailable = pgInfo !== null;

const CLONE_RETRIES = 5;

async function superClient(info: PgFixtureInfo, database: string): Promise<pg.Client> {
  const client = new pg.Client({
    host: info.host,
    port: info.port,
    user: info.superUser,
    password: info.superPassword,
    database,
  });
  await client.connect();
  return client;
}

async function cloneTemplate(info: PgFixtureInfo, dbName: string): Promise<void> {
  const maint = await superClient(info, info.maintenanceDb);
  try {
    for (let attempt = 1; ; attempt++) {
      try {
        await maint.query(`CREATE DATABASE ${dbName} TEMPLATE ${info.templateDb}`);
        return;
      } catch (err) {
        // 多個測試檔同時從同一個 template 複製時可能撞到 "being accessed by other users"
        if (attempt >= CLONE_RETRIES) throw err;
        await new Promise((r) => setTimeout(r, 200 * attempt));
      }
    }
  } finally {
    await maint.end();
  }
}

export interface PgFixture {
  admin(): pg.Client;
  readonly dbName: () => string;
  /** 重新把 pg-client 指回這份 DB（同檔其他測試改過 pg-client 設定時用）。 */
  activate(): Promise<void>;
}

export function usePgFixture(prefix: string): PgFixture {
  let adminClient: pg.Client | null = null;
  let dbName = "";
  let secretDir = "";
  let secretFile = "";

  beforeAll(async () => {
    if (!pgInfo) return;
    dbName = `t_${prefix}_${randomBytes(4).toString("hex")}`;
    await cloneTemplate(pgInfo, dbName);
    secretDir = mkdtempSync(join(tmpdir(), "rag-secret-"));
    secretFile = join(secretDir, "db-rag.json");
    writeFileSync(
      secretFile,
      JSON.stringify({
        username: pgInfo.ragUser,
        password: pgInfo.ragPassword,
        host: pgInfo.host,
        port: pgInfo.port,
        dbname: dbName,
      }),
    );
    await _configurePgClientForTest({ secretFile, ssl: false });
    adminClient = await superClient(pgInfo, dbName);
  }, 60_000);

  afterAll(async () => {
    await closePool();
    await adminClient?.end();
    if (secretDir) rmSync(secretDir, { recursive: true, force: true });
  });

  return {
    admin: () => {
      if (!adminClient) throw new Error("pg fixture 未初始化（Docker 不可用？）");
      return adminClient;
    },
    dbName: () => dbName,
    activate: () => _configurePgClientForTest({ secretFile, ssl: false }),
  };
}
