import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";
import {
  APPLICATION_NAME,
  DEFAULT_STATEMENT_TIMEOUT_MS,
  _configurePgClientForTest,
  buildPoolConfig,
  classifyPgError,
  closePool,
  getPool,
  hasPg,
  isoColumn,
  pgQuery,
  readDbSecret,
  withPgTransaction,
} from "../../src/store/pg-client.js";
import {
  DbTimeoutError,
  DbUnavailableError,
  NotAvailableInRagApiError,
  storeErrorResponse,
} from "../../src/store/store-errors.js";
import { pgAvailable, pgInfo, usePgFixture } from "../pg/pg-fixture.js";

const SECRET = {
  username: "warehouse_rag",
  password: "s3cr3t-value",
  host: "db.example.internal",
  port: 5432,
  dbname: "vocus_warehouse",
};

let dir = "";
beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "pg-client-test-"));
});
afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

function writeJson(name: string, payload: unknown): string {
  const p = join(dir, name);
  writeFileSync(p, typeof payload === "string" ? payload : JSON.stringify(payload));
  return p;
}

describe("readDbSecret", () => {
  it("reads a Secrets Manager JSON payload", () => {
    const p = writeJson("ok.json", { ...SECRET, port: "5432", engine: "postgres" });
    expect(readDbSecret(p)).toEqual(SECRET);
  });

  it("reads a K8s Secret volume directory (one file per key)", () => {
    const d = join(dir, "mounted");
    mkdirSync(d);
    for (const [k, v] of Object.entries(SECRET)) writeFileSync(join(d, k), `${v}\n`);
    expect(readDbSecret(d)).toEqual(SECRET);
  });

  it("treats an empty mounted directory as unavailable and names the missing keys only", () => {
    const d = join(dir, "empty");
    mkdirSync(d);
    expect(() => readDbSecret(d)).toThrow(DbUnavailableError);
    expect(() => readDbSecret(d)).toThrow(/username, password, host, port, dbname/);
  });

  it("never echoes secret values in errors", () => {
    const p = writeJson("partial.json", { password: "s3cr3t-value", host: "h" });
    try {
      readDbSecret(p);
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(DbUnavailableError);
      expect((err as Error).message).not.toContain("s3cr3t-value");
      expect((err as Error).message).toContain("username");
    }
  });

  it("rejects missing file, invalid JSON, non-object JSON, bad port", () => {
    expect(() => readDbSecret(join(dir, "nope.json"))).toThrow(/不存在/);
    expect(() => readDbSecret(writeJson("bad.json", "{not json"))).toThrow(/JSON/);
    expect(() => readDbSecret(writeJson("arr.json", [1, 2]))).toThrow(/物件/);
    expect(() => readDbSecret(writeJson("port.json", { ...SECRET, port: "abc" }))).toThrow(/port/);
    expect(() => readDbSecret(writeJson("port0.json", { ...SECRET, port: 0 }))).toThrow(/port/);
  });
});

describe("buildPoolConfig", () => {
  it("sets application_name, statement_timeout 10s, UTC timezone and passes TLS through", () => {
    const ssl = { ca: "PEM", rejectUnauthorized: true as const };
    const cfg = buildPoolConfig(SECRET, ssl);
    expect(cfg).toMatchObject({
      host: SECRET.host,
      port: 5432,
      user: SECRET.username,
      database: SECRET.dbname,
      application_name: APPLICATION_NAME,
      statement_timeout: DEFAULT_STATEMENT_TIMEOUT_MS,
      options: "-c timezone=UTC",
      ssl,
    });
    expect(APPLICATION_NAME).toBe("rag-api");
    expect(DEFAULT_STATEMENT_TIMEOUT_MS).toBe(10_000);
  });
});

describe("classifyPgError", () => {
  it("maps statement timeout to DbTimeoutError", () => {
    expect(classifyPgError({ code: "57014", message: "canceling statement" })).toBeInstanceOf(DbTimeoutError);
  });

  it.each([
    [{ code: "ECONNREFUSED" }],
    [{ code: "28P01", message: "password authentication failed" }],
    [{ code: "3D000" }],
    [{ code: "08006" }],
    [{ code: "57P01" }],
    [{ message: "timeout exceeded when trying to connect" }],
    [{ message: "Connection terminated unexpectedly" }],
    [{ message: "The server does not support SSL connections" }],
    [{ code: "ERR_TLS_CERT_ALTNAME_INVALID" }],
    [{ code: "SELF_SIGNED_CERT_IN_CHAIN" }],
  ])("maps connection-level failure %o to DbUnavailableError", (err) => {
    expect(classifyPgError(err)).toBeInstanceOf(DbUnavailableError);
  });

  it("passes query errors (syntax, permission) through unchanged", () => {
    const syntax = { code: "42601", message: "syntax error" };
    const denied = { code: "42501", message: "permission denied" };
    expect(classifyPgError(syntax)).toBe(syntax);
    expect(classifyPgError(denied)).toBe(denied);
    expect(classifyPgError("weird")).toBe("weird");
  });

  it("keeps store errors as-is", () => {
    const e = new DbUnavailableError("x");
    expect(classifyPgError(e)).toBe(e);
  });
});

describe("storeErrorResponse", () => {
  it("maps store errors to HTTP status + code, others to null", () => {
    expect(storeErrorResponse(new DbUnavailableError("x"))).toEqual({ status: 503, code: "db_unavailable" });
    expect(storeErrorResponse(new DbTimeoutError())).toEqual({ status: 504, code: "db_timeout" });
    expect(storeErrorResponse(new NotAvailableInRagApiError("reports"))).toEqual({
      status: 410,
      code: "not_available_in_rag_api",
    });
    expect(storeErrorResponse(new Error("x"))).toBeNull();
  });
});

describe("getPool without a usable secret", () => {
  afterEach(async () => {
    await _configurePgClientForTest({});
  });

  it("is not PG mode when VW_DB_SECRET_FILE_RAG is unset", () => {
    expect(hasPg()).toBe(false);
  });

  it("throws DbUnavailableError (not a crash) when the env is unset", async () => {
    await _configurePgClientForTest({ secretFile: "" });
    expect(() => getPool()).toThrow(DbUnavailableError);
    await expect(pgQuery("SELECT 1")).rejects.toBeInstanceOf(DbUnavailableError);
    await expect(withPgTransaction(async () => 1)).rejects.toBeInstanceOf(DbUnavailableError);
  });

  it("throws DbUnavailableError when the secret file is missing", async () => {
    await _configurePgClientForTest({ secretFile: join(dir, "missing.json") });
    expect(() => getPool()).toThrow(/不存在/);
  });

  it("refuses to downgrade TLS when the CA bundle is missing", async () => {
    const p = writeJson("tls.json", SECRET);
    await _configurePgClientForTest({ secretFile: p, sslRootCert: join(dir, "no-ca.pem") });
    expect(() => getPool()).toThrow(/CA bundle/);
  });

  it("builds a verify-full pool when the CA bundle exists (no connection attempted)", async () => {
    const p = writeJson("tls-ok.json", SECRET);
    const ca = join(dir, "ca.pem");
    writeFileSync(ca, "-----BEGIN CERTIFICATE-----\n-----END CERTIFICATE-----\n");
    await _configurePgClientForTest({ secretFile: p, sslRootCert: ca });
    const pool = getPool();
    expect(getPool()).toBe(pool);
    const opts = (pool as unknown as { options: { ssl: { rejectUnauthorized: boolean } } }).options;
    expect(opts.ssl.rejectUnauthorized).toBe(true);
    await closePool();
  });
});

describe("isoColumn", () => {
  it("renders timestamptz as PostgREST-style ISO string", () => {
    expect(isoColumn("created_at")).toBe("to_json(created_at) #>> '{}' AS created_at");
    expect(isoColumn("s.updated_at")).toBe("to_json(s.updated_at) #>> '{}' AS updated_at");
  });
});

const fx = usePgFixture("client");

describe.skipIf(!pgAvailable)("pg-client against PostgreSQL (warehouse_rag)", () => {
  beforeEach(() => fx.activate());

  it("connects as warehouse_rag with application_name and 10s statement_timeout", async () => {
    const [row] = await pgQuery<{ u: string; app: string; st: string; tz: string }>(
      "SELECT current_user AS u, current_setting('application_name') AS app, " +
        "current_setting('statement_timeout') AS st, current_setting('TimeZone') AS tz",
    );
    expect(row).toEqual({ u: "warehouse_rag", app: "rag-api", st: "10s", tz: "UTC" });
  });

  it("overrides statement_timeout for one query only", async () => {
    const [over] = await pgQuery<{ st: string }>("SELECT current_setting('statement_timeout') AS st", [], {
      timeoutMs: 25_000,
    });
    expect(over!.st).toBe("25s");
    const [after] = await pgQuery<{ st: string }>("SELECT current_setting('statement_timeout') AS st");
    expect(after!.st).toBe("10s");
  });

  it("maps a statement timeout to DbTimeoutError", async () => {
    await expect(pgQuery("SELECT pg_sleep(1)", [], { timeoutMs: 50 })).rejects.toBeInstanceOf(DbTimeoutError);
  });

  it("rolls back a failed transaction", async () => {
    const term = "rollback-term";
    await expect(
      withPgTransaction(async (c) => {
        await c.query("INSERT INTO app_synonym_custom (term, synonyms) VALUES ($1, '{}')", [term]);
        throw new Error("boom");
      }),
    ).rejects.toThrow("boom");
    const rows = await fx.admin().query("SELECT 1 FROM app_synonym_custom WHERE term = $1", [term]);
    expect(rows.rowCount).toBe(0);
  });

  it("surfaces permission errors as plain errors (500), not 503", async () => {
    // warehouse_rag 沒有 app_report 權限（roles-matrix）
    await expect(pgQuery("SELECT 1 FROM app_report")).rejects.toMatchObject({ code: "42501" });
  });

  it("reports an unreachable database as DbUnavailableError", async () => {
    const p = writeJson("unreachable.json", { ...SECRET, host: pgInfo!.host, port: 1, dbname: fx.dbName() });
    await _configurePgClientForTest({ secretFile: p, ssl: false });
    await expect(pgQuery("SELECT 1")).rejects.toBeInstanceOf(DbUnavailableError);
  });
});
