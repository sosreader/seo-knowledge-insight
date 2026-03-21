/**
 * Capabilities — explicit five-dimension capability detection.
 *
 * Replaces scattered hasOpenAI() / hasSupabase() / isAgentEnabled() checks
 * with a single structured record that makes the execution context visible.
 */

import { hasOpenAI, isAgentEnabled } from "./mode-detect.js";
import { hasSupabase } from "../store/supabase-client.js";

/** Runtime environment. Server-level only returns "lambda" | "local-server".
 *  "cli" is reserved for Caller dimension (inferCaller), not server runtime. */
export type Runtime = "lambda" | "local-server" | "cli";

/** LLM provider. Server-level only returns "openai" | "none".
 *  "claude-code" is used by Python-layer (qa_tools.py, openai_helper.py)
 *  when Claude Code itself acts as the LLM engine. */
export type LLMProvider = "openai" | "claude-code" | "none";
export type StoreBackend = "supabase" | "file";
export type AgentMode = "enabled" | "disabled";
export type Caller = "browser" | "cli" | "claude-code" | "lambda" | "unknown";

export interface Capabilities {
  readonly runtime: Runtime;
  readonly llm: LLMProvider;
  readonly store: StoreBackend;
  readonly agent: AgentMode;
  readonly caller: Caller;
}

/**
 * Server-level capabilities — reads current config on each call.
 * Cost is negligible (3 boolean checks on constant config values).
 */
export function resolveServerCapabilities(): Omit<Capabilities, "caller"> {
  const isLambda =
    !!process.env.AWS_LAMBDA_FUNCTION_NAME ||
    !!process.env.AWS_EXECUTION_ENV;

  return {
    runtime: isLambda ? "lambda" : "local-server",
    llm: hasOpenAI() ? "openai" : "none",
    store: hasSupabase() ? "supabase" : "file",
    agent: isAgentEnabled() ? "enabled" : "disabled",
  };
}

/**
 * Request-level capabilities (per request, includes caller from User-Agent).
 *
 * `llm` always reflects the server's own capability (same as server-level).
 * Caller identity is a separate concern — use `caller` dimension for that,
 * and `mode` request parameter for LLM mode negotiation.
 */
export function resolveCapabilities(userAgent?: string): Capabilities {
  return {
    ...resolveServerCapabilities(),
    caller: inferCaller(userAgent),
  };
}

/** Infer caller type from User-Agent header (RFC 9110). */
export function inferCaller(userAgent?: string): Caller {
  if (!userAgent) return "unknown";
  const ua = userAgent.toLowerCase();
  if (ua.includes("claude-code")) return "claude-code";
  if (ua.includes("seo-cli")) return "cli";
  if (ua.includes("mozilla")) return "browser";
  if (ua.includes("lambda") || ua.includes("aws")) return "lambda";
  return "unknown";
}

/**
 * Health-endpoint capabilities — effective LLM considering the caller.
 *
 * When Claude Code calls and the server has no LLM of its own,
 * Claude Code itself serves as the LLM engine → `llm: "claude-code"`.
 * All other dimensions are identical to `resolveCapabilities()`.
 *
 * This function is ONLY for the /health display. Route decision logic
 * must continue using `resolveServerCapabilities()` or `resolveCapabilities()`.
 */
export function resolveHealthCapabilities(userAgent?: string): Capabilities {
  const caps = resolveCapabilities(userAgent);
  const effectiveLlm =
    caps.caller === "claude-code" && caps.llm === "none"
      ? "claude-code"
      : caps.llm;
  return { ...caps, llm: effectiveLlm };
}

/** Format capabilities as a human-readable tag for logging. */
export function formatCapabilityTag(caps: Capabilities | Omit<Capabilities, "caller">): string {
  const parts = [
    `runtime:${caps.runtime}`,
    `llm:${caps.llm}`,
    `store:${caps.store}`,
    `agent:${caps.agent}`,
  ];
  if ("caller" in caps) {
    parts.push(`caller:${caps.caller}`);
  }
  return `[${parts.join(" | ")}]`;
}
