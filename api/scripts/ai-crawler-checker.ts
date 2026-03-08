#!/usr/bin/env npx tsx
/**
 * AI Crawler Readiness Checker — CLI tool to check robots.txt for AI bot settings.
 *
 * Usage:
 *   npx tsx api/scripts/ai-crawler-checker.ts https://example.com
 *   make check-ai-crawlers URL=https://example.com
 *
 * Security: CLI only (not exposed as API endpoint to avoid SSRF risk).
 */

// ── Types ──

export type CrawlerStatus = "allowed" | "blocked" | "not_specified";

export interface CrawlerCheckResult {
  readonly bot: string;
  readonly status: CrawlerStatus;
  readonly detail: string;
}

export interface CheckReport {
  readonly url: string;
  readonly robots_url: string;
  readonly crawlers: readonly CrawlerCheckResult[];
  readonly overall_readiness: "ready" | "partial" | "blocked";
}

// ── Constants ──

const AI_BOTS = [
  { name: "GPTBot", description: "OpenAI (ChatGPT, SearchGPT)" },
  { name: "ChatGPT-User", description: "ChatGPT browse mode" },
  { name: "ClaudeBot", description: "Anthropic (Claude)" },
  { name: "anthropic-ai", description: "Anthropic web crawler" },
  { name: "Google-Extended", description: "Google Gemini training" },
  { name: "Bytespider", description: "ByteDance (TikTok)" },
  { name: "PerplexityBot", description: "Perplexity AI" },
  { name: "Applebot-Extended", description: "Apple Intelligence" },
  { name: "cohere-ai", description: "Cohere LLM" },
  { name: "Meta-ExternalAgent", description: "Meta AI" },
] as const;

// ── Core ──

/**
 * Parse robots.txt content and check AI bot access rules.
 */
export function parseRobotsTxt(content: string, bots: readonly { name: string; description: string }[] = AI_BOTS): readonly CrawlerCheckResult[] {
  const lines = content.split("\n").map((l) => l.trim());

  // Parse all User-agent blocks
  const rules = new Map<string, string[]>();
  let currentAgents: string[] = [];

  for (const line of lines) {
    if (line.startsWith("#") || line === "") {
      if (line === "" && currentAgents.length > 0) {
        currentAgents = [];
      }
      continue;
    }

    const colonIdx = line.indexOf(":");
    if (colonIdx === -1) continue;

    const directive = line.slice(0, colonIdx).trim().toLowerCase();
    const value = line.slice(colonIdx + 1).trim();

    if (directive === "user-agent") {
      currentAgents.push(value.toLowerCase());
      if (!rules.has(value.toLowerCase())) {
        rules.set(value.toLowerCase(), []);
      }
    } else if (directive === "disallow" || directive === "allow") {
      for (const agent of currentAgents) {
        rules.get(agent)?.push(`${directive}:${value}`);
      }
    }
  }

  return bots.map((bot) => {
    const botLower = bot.name.toLowerCase();
    const botRules = rules.get(botLower);

    if (!botRules) {
      // Check wildcard rules
      const wildcardRules = rules.get("*");
      if (wildcardRules) {
        const isBlocked = wildcardRules.some((r) => r === "disallow:/");
        if (isBlocked) {
          return {
            bot: bot.name,
            status: "blocked" as CrawlerStatus,
            detail: `${bot.description} — 被 User-agent: * Disallow: / 封鎖`,
          };
        }
      }
      return {
        bot: bot.name,
        status: "not_specified" as CrawlerStatus,
        detail: `${bot.description} — 未在 robots.txt 中指定，預設允許`,
      };
    }

    // Check specific rules for this bot
    const hasDisallowAll = botRules.some((r) => r === "disallow:/");
    const hasAllowAll = botRules.some((r) => r === "allow:/");
    const hasDisallowEmpty = botRules.some((r) => r === "disallow:");

    if (hasDisallowAll && !hasAllowAll) {
      return {
        bot: bot.name,
        status: "blocked" as CrawlerStatus,
        detail: `${bot.description} — 已封鎖（Disallow: /）`,
      };
    }

    if (hasAllowAll || hasDisallowEmpty) {
      return {
        bot: bot.name,
        status: "allowed" as CrawlerStatus,
        detail: `${bot.description} — 已允許`,
      };
    }

    // Has partial rules
    return {
      bot: bot.name,
      status: "allowed" as CrawlerStatus,
      detail: `${bot.description} — 部分路徑限制`,
    };
  });
}

/**
 * Fetch robots.txt from a URL and analyze AI bot settings.
 */
export async function checkAICrawlers(siteUrl: string): Promise<CheckReport> {
  const parsed = new URL(siteUrl);
  const robotsUrl = `${parsed.protocol}//${parsed.host}/robots.txt`;

  const resp = await fetch(robotsUrl, {
    headers: { "User-Agent": "SEO-Knowledge-Insight-Checker/1.0" },
    signal: AbortSignal.timeout(10_000),
  });

  if (!resp.ok) {
    // No robots.txt → all bots allowed by default
    const crawlers = AI_BOTS.map((bot) => ({
      bot: bot.name,
      status: "allowed" as CrawlerStatus,
      detail: `${bot.description} — robots.txt 不存在，預設允許`,
    }));

    return {
      url: siteUrl,
      robots_url: robotsUrl,
      crawlers,
      overall_readiness: "ready",
    };
  }

  const content = await resp.text();
  const crawlers = parseRobotsTxt(content);

  const blockedCount = crawlers.filter((c) => c.status === "blocked").length;
  const overall =
    blockedCount === 0
      ? "ready"
      : blockedCount >= crawlers.length / 2
        ? "blocked"
        : "partial";

  return { url: siteUrl, robots_url: robotsUrl, crawlers, overall_readiness: overall };
}

// ── CLI ──

async function main() {
  const url = process.argv[2];
  if (!url) {
    console.error("Usage: npx tsx api/scripts/ai-crawler-checker.ts <URL>");
    console.error("Example: npx tsx api/scripts/ai-crawler-checker.ts https://vocus.cc");
    process.exit(1);
  }

  try {
    new URL(url);
  } catch {
    console.error(`Invalid URL: ${url}`);
    process.exit(1);
  }

  console.log(`Checking AI crawler readiness for: ${url}\n`);

  const report = await checkAICrawlers(url);

  console.log(`robots.txt: ${report.robots_url}`);
  console.log(`Overall readiness: ${report.overall_readiness.toUpperCase()}\n`);
  console.log("─".repeat(70));

  for (const c of report.crawlers) {
    const icon = c.status === "allowed" ? "✅" : c.status === "blocked" ? "❌" : "⚪";
    console.log(`${icon} ${c.bot.padEnd(22)} ${c.status.padEnd(15)} ${c.detail}`);
  }

  console.log("─".repeat(70));

  const blocked = report.crawlers.filter((c) => c.status === "blocked");
  const notSpecified = report.crawlers.filter((c) => c.status === "not_specified");

  if (blocked.length > 0) {
    console.log(`\n⚠️  ${blocked.length} AI bots are blocked. Consider allowing them for AI visibility.`);
  }
  if (notSpecified.length > 0) {
    console.log(`ℹ️  ${notSpecified.length} AI bots not specified (allowed by default).`);
  }
  if (blocked.length === 0) {
    console.log("\n✅ All major AI bots are allowed or not restricted.");
  }
}

// Only run CLI when executed directly
const isDirectRun = process.argv[1]?.includes("ai-crawler-checker");
if (isDirectRun) {
  main().catch((err) => {
    console.error("Error:", err instanceof Error ? err.message : err);
    process.exit(1);
  });
}
