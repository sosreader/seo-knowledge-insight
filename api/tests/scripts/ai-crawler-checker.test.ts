/**
 * Tests for ai-crawler-checker — robots.txt AI bot detection.
 */

import { describe, it, expect } from "vitest";
import { parseRobotsTxt, type CrawlerCheckResult } from "../../scripts/ai-crawler-checker.js";

const TEST_BOTS = [
  { name: "GPTBot", description: "OpenAI" },
  { name: "ClaudeBot", description: "Anthropic" },
  { name: "Google-Extended", description: "Google Gemini" },
] as const;

function findBot(results: readonly CrawlerCheckResult[], name: string): CrawlerCheckResult | undefined {
  return results.find((r) => r.bot === name);
}

describe("parseRobotsTxt", () => {
  it("marks bots as not_specified when robots.txt is empty", () => {
    const results = parseRobotsTxt("", TEST_BOTS);
    expect(results).toHaveLength(3);
    expect(results.every((r) => r.status === "not_specified")).toBe(true);
  });

  it("detects blocked bots with Disallow: /", () => {
    const content = `
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /
    `;
    const results = parseRobotsTxt(content, TEST_BOTS);
    expect(findBot(results, "GPTBot")?.status).toBe("blocked");
    expect(findBot(results, "ClaudeBot")?.status).toBe("blocked");
    expect(findBot(results, "Google-Extended")?.status).toBe("not_specified");
  });

  it("detects allowed bots with Allow: /", () => {
    const content = `
User-agent: GPTBot
Allow: /
    `;
    const results = parseRobotsTxt(content, TEST_BOTS);
    expect(findBot(results, "GPTBot")?.status).toBe("allowed");
  });

  it("detects allowed bots with empty Disallow", () => {
    const content = `
User-agent: GPTBot
Disallow:
    `;
    const results = parseRobotsTxt(content, TEST_BOTS);
    expect(findBot(results, "GPTBot")?.status).toBe("allowed");
  });

  it("handles wildcard block affecting unspecified bots", () => {
    const content = `
User-agent: *
Disallow: /
    `;
    const results = parseRobotsTxt(content, TEST_BOTS);
    // All bots should be blocked via wildcard
    expect(results.every((r) => r.status === "blocked")).toBe(true);
  });

  it("specific bot rule overrides wildcard", () => {
    const content = `
User-agent: *
Disallow: /

User-agent: GPTBot
Allow: /
    `;
    const results = parseRobotsTxt(content, TEST_BOTS);
    expect(findBot(results, "GPTBot")?.status).toBe("allowed");
    expect(findBot(results, "ClaudeBot")?.status).toBe("blocked");
  });

  it("handles case-insensitive user-agent matching", () => {
    const content = `
User-agent: gptbot
Disallow: /
    `;
    const results = parseRobotsTxt(content, TEST_BOTS);
    expect(findBot(results, "GPTBot")?.status).toBe("blocked");
  });

  it("handles partial path restrictions as allowed", () => {
    const content = `
User-agent: GPTBot
Disallow: /private/
Disallow: /admin/
    `;
    const results = parseRobotsTxt(content, TEST_BOTS);
    expect(findBot(results, "GPTBot")?.status).toBe("allowed");
    expect(findBot(results, "GPTBot")?.detail).toContain("部分路徑限制");
  });

  it("handles comments and blank lines", () => {
    const content = `
# This is a robots.txt file
# Block AI bots

User-agent: ClaudeBot
Disallow: /

# Allow GPTBot
User-agent: GPTBot
Allow: /
    `;
    const results = parseRobotsTxt(content, TEST_BOTS);
    expect(findBot(results, "ClaudeBot")?.status).toBe("blocked");
    expect(findBot(results, "GPTBot")?.status).toBe("allowed");
  });

  it("handles real-world complex robots.txt", () => {
    const content = `
User-agent: *
Allow: /
Disallow: /search
Disallow: /admin

User-agent: GPTBot
User-agent: ChatGPT-User
Disallow: /

User-agent: ClaudeBot
Allow: /

User-agent: Bytespider
Disallow: /
    `;
    const results = parseRobotsTxt(content, TEST_BOTS);
    expect(findBot(results, "GPTBot")?.status).toBe("blocked");
    expect(findBot(results, "ClaudeBot")?.status).toBe("allowed");
    // Google-Extended not specified, wildcard allows
    expect(findBot(results, "Google-Extended")?.status).toBe("not_specified");
  });
});
