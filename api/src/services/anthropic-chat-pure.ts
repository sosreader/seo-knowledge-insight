/**
 * Anthropic Chat — Pure helpers shared by anthropic-chat.ts and anthropic-chat-stream.ts.
 *
 * Extracts Anthropic-specific message/system formatting to avoid duplication.
 */

import { buildSystemPrompt } from "./rag-chat-pure.js";
import type { MaturityLevel } from "../utils/maturity.js";
import type { RetrievalQuality } from "./retrieval-gate.js";

/** Build Anthropic `system` string (system prompt + KB context merged). */
export function buildAnthropicSystem(
  maturityLevel: MaturityLevel | null,
  retrievalQuality: RetrievalQuality,
  context: string,
): string {
  const systemPrompt = buildSystemPrompt(maturityLevel, retrievalQuality);
  if (!context) return systemPrompt;
  return `${systemPrompt}\n\n--- 相關 SEO 知識庫 ---\n${context}\n--- 知識庫結束 ---`;
}

/** Build Anthropic messages array (user/assistant only, no system role). */
export function buildAnthropicMessages(
  history: ReadonlyArray<{ readonly role: string; readonly content: string }> | null,
  message: string,
): Array<{ role: "user" | "assistant"; content: string }> {
  const messages: Array<{ role: "user" | "assistant"; content: string }> = [];
  if (history) {
    for (const h of history) {
      if (h.role === "user" || h.role === "assistant") {
        messages.push({ role: h.role, content: h.content });
      }
    }
  }
  messages.push({ role: "user", content: message });
  return messages;
}
