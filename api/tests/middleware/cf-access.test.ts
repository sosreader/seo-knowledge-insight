import { describe, it, expect, beforeAll } from "vitest";
import { Hono } from "hono";
import { generateKeyPair, exportJWK, SignJWT, type CryptoKey, type JWK } from "jose";
import {
  createCfAccessMiddleware,
  parseAccessSettings,
  ACCESS_JWT_HEADER,
  getAccessIdentity,
} from "../../src/middleware/cf-access.js";
import { JwksCache } from "../../src/middleware/jwks-cache.js";

const TEAM = "vocus-test.cloudflareaccess.com";
const ISS = `https://${TEAM}`;
const AUD = "rag-aud-1";

interface KeyMaterial {
  readonly kid: string;
  readonly privateKey: CryptoKey;
  readonly jwk: JWK;
}

async function makeKey(kid: string): Promise<KeyMaterial> {
  const { publicKey, privateKey } = await generateKeyPair("RS256", { extractable: true });
  return { kid, privateKey, jwk: { ...(await exportJWK(publicKey)), kid, alg: "RS256" } };
}

interface TokenOptions {
  readonly key: KeyMaterial;
  readonly aud?: string | string[];
  readonly iss?: string;
  readonly sub?: string;
  readonly claims?: Record<string, unknown>;
  readonly exp?: number;
  readonly nbf?: number;
  readonly kid?: string | null;
}

function nowSec(): number {
  return Math.floor(Date.now() / 1000);
}

async function sign(opts: TokenOptions): Promise<string> {
  const header: { alg: string; kid?: string } = { alg: "RS256" };
  if (opts.kid !== null) header.kid = opts.kid ?? opts.key.kid;
  const jwt = new SignJWT({ ...(opts.claims ?? {}) })
    .setProtectedHeader(header)
    .setIssuer(opts.iss ?? ISS)
    .setAudience(opts.aud ?? AUD)
    .setIssuedAt()
    .setExpirationTime(opts.exp ?? nowSec() + 300);
  if (opts.sub !== undefined) jwt.setSubject(opts.sub);
  if (opts.nbf !== undefined) jwt.setNotBefore(opts.nbf);
  return jwt.sign(opts.key.privateKey);
}

function buildApp(
  jwksKeys: () => JWK[],
  settings = { teamDomain: TEAM, auds: [AUD] },
  fetchCount = { n: 0 },
) {
  const jwks = new JwksCache(`https://${TEAM}/cdn-cgi/access/certs`, {
    fetchJson: async () => {
      fetchCount.n += 1;
      return { keys: jwksKeys() };
    },
    minRefreshIntervalMs: 0,
  });
  const app = new Hono();
  app.get("/health", (c) => c.json({ status: "healthy" }));
  const api = new Hono();
  api.use("*", createCfAccessMiddleware(parseAccessSettings(settings.teamDomain, settings.auds.join(",")), jwks));
  api.get("/whoami", (c) => c.json({ identity: getAccessIdentity(c) }));
  app.route("/internal/rag", api);
  return app;
}

async function call(app: Hono, token?: string) {
  const headers: Record<string, string> = {};
  if (token !== undefined) headers[ACCESS_JWT_HEADER] = token;
  const res = await app.request("/internal/rag/whoami", { headers });
  return { status: res.status, body: (await res.json()) as Record<string, unknown> };
}

let k1: KeyMaterial;
let k2: KeyMaterial;

beforeAll(async () => {
  k1 = await makeKey("kid-1");
  k2 = await makeKey("kid-2");
});

describe("parseAccessSettings", () => {
  it("normalises team domain and splits the AUD allow list", () => {
    expect(parseAccessSettings("https://Team.CloudflareAccess.com/", " a , ,b ")).toEqual({
      teamDomain: "team.cloudflareaccess.com",
      auds: ["a", "b"],
    });
  });

  it("returns null when either setting is missing or malformed", () => {
    expect(parseAccessSettings("", "a")).toBeNull();
    expect(parseAccessSettings(TEAM, "")).toBeNull();
    expect(parseAccessSettings(TEAM, " , ")).toBeNull();
    expect(parseAccessSettings("not a host", "a")).toBeNull();
    expect(parseAccessSettings(undefined, undefined)).toBeNull();
  });
});

describe("cf-access middleware", () => {
  it("accepts a valid token and exposes sub as the identity", async () => {
    const app = buildApp(() => [k1.jwk]);
    const { status, body } = await call(app, await sign({ key: k1, sub: "user-123" }));
    expect(status).toBe(200);
    expect(body.identity).toBe("user-123");
  });

  it("uses common_name for service tokens (empty sub)", async () => {
    const app = buildApp(() => [k1.jwk]);
    const token = await sign({ key: k1, sub: "", claims: { common_name: "svc.access" } });
    const { status, body } = await call(app, token);
    expect(status).toBe(200);
    expect(body.identity).toBe("svc.access");
  });

  it("accepts an aud array that contains an allowed AUD", async () => {
    const app = buildApp(() => [k1.jwk]);
    const { status } = await call(app, await sign({ key: k1, sub: "u", aud: ["other", AUD] }));
    expect(status).toBe(200);
  });

  it("rejects a token without sub or common_name", async () => {
    const app = buildApp(() => [k1.jwk]);
    const { status } = await call(app, await sign({ key: k1 }));
    expect(status).toBe(401);
  });

  it("rejects a wrong aud with 401", async () => {
    const app = buildApp(() => [k1.jwk]);
    const { status, body } = await call(app, await sign({ key: k1, sub: "u", aud: "api-aud" }));
    expect(status).toBe(401);
    expect(body.error).toBe("unauthorized");
  });

  it("rejects a wrong iss with 401", async () => {
    const app = buildApp(() => [k1.jwk]);
    const token = await sign({ key: k1, sub: "u", iss: "https://evil.cloudflareaccess.com" });
    expect((await call(app, token)).status).toBe(401);
  });

  it("rejects a token expired beyond the 60s leeway", async () => {
    const app = buildApp(() => [k1.jwk]);
    const token = await sign({ key: k1, sub: "u", exp: nowSec() - 120 });
    expect((await call(app, token)).status).toBe(401);
  });

  it("tolerates up to 60s of clock skew on exp and nbf", async () => {
    const app = buildApp(() => [k1.jwk]);
    const expired = await sign({ key: k1, sub: "u", exp: nowSec() - 30 });
    expect((await call(app, expired)).status).toBe(200);
    const early = await sign({ key: k1, sub: "u", nbf: nowSec() + 30 });
    expect((await call(app, early)).status).toBe(200);
  });

  it("rejects nbf beyond the leeway", async () => {
    const app = buildApp(() => [k1.jwk]);
    const token = await sign({ key: k1, sub: "u", nbf: nowSec() + 600 });
    expect((await call(app, token)).status).toBe(401);
  });

  it("rejects a missing header with 401", async () => {
    const app = buildApp(() => [k1.jwk]);
    const { status, body } = await call(app);
    expect(status).toBe(401);
    expect(body.error).toBe("unauthorized");
    expect(body.data).toBeNull();
  });

  it("rejects malformed, unsigned and tampered tokens", async () => {
    const app = buildApp(() => [k1.jwk]);
    expect((await call(app, "not-a-jwt")).status).toBe(401);

    const none = `${Buffer.from(JSON.stringify({ alg: "none", kid: k1.kid })).toString("base64url")}.${Buffer.from(
      JSON.stringify({ iss: ISS, aud: AUD, sub: "u", exp: nowSec() + 300 }),
    ).toString("base64url")}.`;
    expect((await call(app, none)).status).toBe(401);

    const valid = await sign({ key: k1, sub: "u" });
    const [h, , s] = valid.split(".");
    const forgedPayload = Buffer.from(
      JSON.stringify({ iss: ISS, aud: AUD, sub: "admin", exp: nowSec() + 300 }),
    ).toString("base64url");
    expect((await call(app, `${h}.${forgedPayload}.${s}`)).status).toBe(401);
  });

  it("rejects HS256 tokens even when the kid exists", async () => {
    const app = buildApp(() => [k1.jwk]);
    const secret = new TextEncoder().encode("x".repeat(32));
    const token = await new SignJWT({ sub: "u" })
      .setProtectedHeader({ alg: "HS256", kid: k1.kid })
      .setIssuer(ISS)
      .setAudience(AUD)
      .setExpirationTime(nowSec() + 300)
      .sign(secret);
    expect((await call(app, token)).status).toBe(401);
  });

  it("rejects a token without kid", async () => {
    const app = buildApp(() => [k1.jwk]);
    expect((await call(app, await sign({ key: k1, sub: "u", kid: null }))).status).toBe(401);
  });

  it("rejects a token signed by a key that is not in the JWKS", async () => {
    const app = buildApp(() => [k1.jwk]);
    const token = await sign({ key: k2, sub: "u" });
    expect((await call(app, token)).status).toBe(401);
  });

  it("refetches the JWKS once when Cloudflare rotates to a new kid", async () => {
    let rotated = false;
    const fetchCount = { n: 0 };
    const app = buildApp(() => (rotated ? [k1.jwk, k2.jwk] : [k1.jwk]), undefined, fetchCount);
    expect((await call(app, await sign({ key: k1, sub: "u" }))).status).toBe(200);
    rotated = true;
    expect((await call(app, await sign({ key: k2, sub: "u" }))).status).toBe(200);
    expect(fetchCount.n).toBe(2);
  });

  it("returns 503 unavailable when RAG_AUDS or team domain is missing (fail closed)", async () => {
    const jwks = new JwksCache("https://unused/certs", {
      fetchJson: async () => {
        throw new Error("must not fetch");
      },
    });
    const app = new Hono();
    app.get("/health", (c) => c.json({ status: "healthy" }));
    const api = new Hono();
    api.use("*", createCfAccessMiddleware(parseAccessSettings(TEAM, ""), jwks));
    api.get("/whoami", (c) => c.json({ ok: true }));
    app.route("/internal/rag", api);

    const res = await app.request("/internal/rag/whoami", {
      headers: { [ACCESS_JWT_HEADER]: await sign({ key: k1, sub: "u" }) },
    });
    expect(res.status).toBe(503);
    expect(((await res.json()) as { error: string }).error).toBe("unavailable");
    expect((await app.request("/health")).status).toBe(200);
  });

  it("returns 503 unavailable when the JWKS cannot be fetched at all", async () => {
    const jwks = new JwksCache("https://x/certs", {
      fetchJson: async () => {
        throw new Error("egress blocked");
      },
    });
    const app = new Hono();
    app.use("*", createCfAccessMiddleware(parseAccessSettings(TEAM, AUD), jwks));
    app.get("/whoami", (c) => c.json({ ok: true }));
    const res = await app.request("/whoami", {
      headers: { [ACCESS_JWT_HEADER]: await sign({ key: k1, sub: "u" }) },
    });
    expect(res.status).toBe(503);
  });
});
