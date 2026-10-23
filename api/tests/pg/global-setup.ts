/**
 * Vitest globalSetup：啟一個 pgvector PostgreSQL 容器，套 VW migration 做成 template DB。
 *
 * - 設 SKIP_PG_TESTS=1 可略過（沒有 Docker 的環境）；整合測試會以 describe.skipIf 跳過。
 * - 測試以 warehouse_rag 登入，權限與正式環境相同（逐表 GRANT 來自 0011）。
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";
import { PostgreSqlContainer, type StartedPostgreSqlContainer } from "@testcontainers/postgresql";
import type { TestProject } from "vitest/node";
import type { PgFixtureInfo } from "./pg-fixture-types.js";

// pgvector 0.8.7 / PostgreSQL 17.11（2026-10-01 build），以 multi-arch index digest 釘住。
const PGVECTOR_IMAGE =
  "pgvector/pgvector:pg17@sha256:ac08538c6f8b9904c33c8224c5e5706dbe760aca29db1d096972b4052c22a75d";
export const TEMPLATE_DB = "rag_template";
const RAG_PASSWORD = "rag-test-only";

const schemaDir = join(dirname(fileURLToPath(import.meta.url)), "../fixtures/schema");
const sql = (name: string): string => readFileSync(join(schemaDir, name), "utf-8");

const ROLES_SQL = `
  CREATE ROLE warehouse_admin NOLOGIN;
  CREATE ROLE warehouse_app NOLOGIN;
  CREATE ROLE warehouse_reader NOLOGIN;
  CREATE ROLE warehouse_rag LOGIN PASSWORD '${RAG_PASSWORD}';
`;

async function withClient<T>(
  container: StartedPostgreSqlContainer,
  database: string,
  fn: (client: pg.Client) => Promise<T>,
): Promise<T> {
  const client = new pg.Client({
    host: container.getHost(),
    port: container.getPort(),
    user: container.getUsername(),
    password: container.getPassword(),
    database,
  });
  await client.connect();
  try {
    return await fn(client);
  } finally {
    await client.end();
  }
}

async function buildTemplate(container: StartedPostgreSqlContainer): Promise<void> {
  await withClient(container, container.getDatabase(), async (c) => {
    await c.query(ROLES_SQL);
    await c.query(`CREATE DATABASE ${TEMPLATE_DB}`);
  });
  await withClient(container, TEMPLATE_DB, async (c) => {
    await c.query("GRANT CREATE, USAGE ON SCHEMA public TO warehouse_admin");
    await c.query(sql("0010_extension_vector.sql"));
    await c.query("SET ROLE warehouse_admin");
    await c.query(sql("0009_app_tables.sql"));
    await c.query(sql("0011_rag_tables.sql"));
    await c.query("RESET ROLE");
  });
}

export default async function setup(project: TestProject): Promise<() => Promise<void>> {
  if (process.env.SKIP_PG_TESTS === "1") {
    project.provide("pgFixture", null);
    return async () => undefined;
  }
  const container = await new PostgreSqlContainer(PGVECTOR_IMAGE).start();
  await buildTemplate(container);
  const info: PgFixtureInfo = {
    host: container.getHost(),
    port: container.getPort(),
    superUser: container.getUsername(),
    superPassword: container.getPassword(),
    maintenanceDb: container.getDatabase(),
    templateDb: TEMPLATE_DB,
    ragUser: "warehouse_rag",
    ragPassword: RAG_PASSWORD,
  };
  project.provide("pgFixture", info);
  return async () => {
    await container.stop();
  };
}
