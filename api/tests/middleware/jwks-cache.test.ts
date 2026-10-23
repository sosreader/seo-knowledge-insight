import { describe, it, expect } from "vitest";
import { generateKeyPair, exportJWK } from "jose";
import {
  JwksCache,
  JwksUnavailableError,
  parseJwks,
  certsUrl,
} from "../../src/middleware/jwks-cache.js";

async function rsaJwk(kid: string) {
  const { publicKey } = await generateKeyPair("RS256", { extractable: true });
  return { ...(await exportJWK(publicKey)), kid, alg: "RS256", use: "sig" };
}

function fakeClock(start = 1_000_000) {
  let now = start;
  return {
    now: () => now,
    advance: (ms: number) => {
      now += ms;
    },
  };
}

describe("certsUrl", () => {
  it("builds the team JWKS URL", () => {
    expect(certsUrl("team.cloudflareaccess.com")).toBe(
      "https://team.cloudflareaccess.com/cdn-cgi/access/certs",
    );
  });
});

describe("parseJwks", () => {
  it("keeps RSA keys with kid and drops the rest", async () => {
    const good = await rsaJwk("k1");
    const keys = parseJwks({
      keys: [good, { kty: "EC", kid: "ec" }, { ...good, kid: "" }, "junk"],
    });
    expect(keys.map((k) => k.kid)).toEqual(["k1"]);
  });

  it("throws when keys is missing or no usable key remains", () => {
    expect(() => parseJwks({})).toThrow(JwksUnavailableError);
    expect(() => parseJwks(null)).toThrow(JwksUnavailableError);
    expect(() => parseJwks({ keys: [{ kty: "EC", kid: "x" }] })).toThrow(JwksUnavailableError);
  });
});

describe("JwksCache", () => {
  it("fetches once and serves from cache within the TTL", async () => {
    const k1 = await rsaJwk("k1");
    let calls = 0;
    const clock = fakeClock();
    const cache = new JwksCache("https://x/certs", {
      fetchJson: async () => {
        calls += 1;
        return { keys: [k1] };
      },
      now: clock.now,
    });
    expect((await cache.getKey("k1"))?.kid).toBe("k1");
    clock.advance(59 * 60 * 1000);
    expect((await cache.getKey("k1"))?.kid).toBe("k1");
    expect(calls).toBe(1);
  });

  it("refetches after the TTL and keeps old keys when the refetch fails", async () => {
    const k1 = await rsaJwk("k1");
    let calls = 0;
    const clock = fakeClock();
    const cache = new JwksCache("https://x/certs", {
      fetchJson: async () => {
        calls += 1;
        if (calls > 1) throw new Error("network down");
        return { keys: [k1] };
      },
      now: clock.now,
    });
    await cache.getKey("k1");
    clock.advance(61 * 60 * 1000);
    expect((await cache.getKey("k1"))?.kid).toBe("k1");
    expect(calls).toBe(2);
  });

  it("refetches once on an unknown kid (key rotation)", async () => {
    const k1 = await rsaJwk("k1");
    const k2 = await rsaJwk("k2");
    let calls = 0;
    const clock = fakeClock();
    const cache = new JwksCache("https://x/certs", {
      fetchJson: async () => {
        calls += 1;
        return calls === 1 ? { keys: [k1] } : { keys: [k1, k2] };
      },
      now: clock.now,
    });
    await cache.getKey("k1");
    clock.advance(31_000);
    expect((await cache.getKey("k2"))?.kid).toBe("k2");
    expect(calls).toBe(2);
  });

  it("does not refetch for unknown kids inside the minimum interval", async () => {
    const k1 = await rsaJwk("k1");
    let calls = 0;
    const clock = fakeClock();
    const cache = new JwksCache("https://x/certs", {
      fetchJson: async () => {
        calls += 1;
        return { keys: [k1] };
      },
      now: clock.now,
    });
    await cache.getKey("k1");
    clock.advance(5_000);
    expect(await cache.getKey("forged")).toBeNull();
    expect(await cache.getKey("forged-2")).toBeNull();
    expect(calls).toBe(1);
  });

  it("throws JwksUnavailableError when nothing was ever fetched", async () => {
    const cache = new JwksCache("https://x/certs", {
      fetchJson: async () => {
        throw new Error("dns");
      },
    });
    await expect(cache.getKey("k1")).rejects.toBeInstanceOf(JwksUnavailableError);
  });

  it("collapses concurrent refreshes into one fetch", async () => {
    const k1 = await rsaJwk("k1");
    let calls = 0;
    const cache = new JwksCache("https://x/certs", {
      fetchJson: async () => {
        calls += 1;
        await new Promise((r) => setTimeout(r, 5));
        return { keys: [k1] };
      },
    });
    await Promise.all([cache.getKey("k1"), cache.getKey("k1"), cache.getKey("k1")]);
    expect(calls).toBe(1);
  });

  it("default fetcher rejects non-OK responses", async () => {
    const original = globalThis.fetch;
    globalThis.fetch = (async () => new Response("nope", { status: 500 })) as typeof fetch;
    try {
      const cache = new JwksCache("https://x/certs");
      await expect(cache.getKey("k1")).rejects.toBeInstanceOf(JwksUnavailableError);
    } finally {
      globalThis.fetch = original;
    }
  });

  it("default fetcher parses a JSON body", async () => {
    const k1 = await rsaJwk("k1");
    const original = globalThis.fetch;
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ keys: [k1] }), { status: 200 })) as typeof fetch;
    try {
      const cache = new JwksCache("https://x/certs");
      expect((await cache.getKey("k1"))?.kid).toBe("k1");
    } finally {
      globalThis.fetch = original;
    }
  });
});
