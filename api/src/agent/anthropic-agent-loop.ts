/**
 * Anthropic Agent loop — Claude tool_use while-loop with termination conditions.
 *
 * Parallel implementation to agent-loop.ts (OpenAI function calling).
 * Termination: stop_reason === "end_turn" | MAX_TURNS | TIMEOUT | loop detection
 */

import { config } from "../config.js";
import { getAnthropicTools, type ToolName } from "./tool-definitions.js";
import { executeTool } from "./tool-executor.js";
import type { AgentConfig, AgentDeps, AgentResponse, ToolResult } from "./types.js";
import { itemToSource, type SourceItem } from "../schemas/chat.js";
import { observe } from "../utils/observability.js";
import { hasOpenAI } from "../utils/mode-detect.js";
import type { MessageParam, ToolResultBlockParam, Tool } from "@anthropic-ai/sdk/resources/messages.js";

const ALLOWED_TOOLS: ReadonlySet<string> = new Set<ToolName>([
  "search_knowledge_base",
  "get_qa_detail",
  "list_categories",
  "get_stats",
]);

const SYSTEM_PROMPT = `你是一位資深 SEO 顧問，可以使用工具搜尋 SEO 知識庫來回答問題。

搜尋策略：
1. 先分析問題，決定用什麼關鍵字搜尋
2. 如果第一次搜尋結果不足，換關鍵字或分類再搜
3. 可以搜尋多次（但不要超過必要的次數）
4. 取得足夠資訊後，直接回答

回答規則：
1. 直接針對問題給出具體建議
2. 引用知識庫中的案例或數字來支撐建議，在該句末尾標注來源編號（如 [1]、[2]），編號對應搜尋結果順序
3. 若知識庫沒有相關資訊，誠實說明並提供通用建議
4. 回答使用繁體中文，技術術語可以保留英文
5. 控制在 500 字以內，重點優先`;

const DEFAULT_CONFIG: AgentConfig = {
  maxTurns: 5,
  timeoutMs: 90_000,
  model: config.CHAT_ANTHROPIC_MODEL,
  temperature: 0.3,
};

function buildMetadata(
  model: string,
  inputTokens: number,
  outputTokens: number,
  startMs: number,
  retrievalCount: number,
  toolCallsCount: number,
  agentTurns: number,
): AgentResponse["metadata"] {
  return {
    model,
    provider: "anthropic",
    mode: "agent",
    embedding_model: hasOpenAI() ? config.OPENAI_EMBEDDING_MODEL : "none",
    input_tokens: inputTokens,
    output_tokens: outputTokens,
    total_tokens: inputTokens + outputTokens,
    duration_ms: Date.now() - startMs,
    retrieval_count: retrievalCount,
    reranker_used: false,
    tool_calls_count: toolCallsCount,
    agent_turns: agentTurns,
  };
}

function hasLoopDetection(toolCalls: readonly ToolResult[]): boolean {
  if (toolCalls.length < 2) return false;
  const last = toolCalls[toolCalls.length - 1]!;
  const prev = toolCalls[toolCalls.length - 2]!;
  return last.toolName === prev.toolName && JSON.stringify(last.args) === JSON.stringify(prev.args);
}

function collectSources(toolCalls: readonly ToolResult[]): readonly SourceItem[] {
  const seen = new Set<string>();
  const sources: SourceItem[] = [];

  for (const tc of toolCalls) {
    if (tc.toolName !== "search_knowledge_base") continue;
    try {
      const items = JSON.parse(tc.result) as Array<Record<string, unknown>>;
      if (!Array.isArray(items)) continue;
      for (const item of items) {
        const id = String(item.id ?? "");
        if (!id || seen.has(id)) continue;
        seen.add(id);
        sources.push(
          itemToSource(
            {
              id,
              question: String(item.question ?? ""),
              category: String(item.category ?? ""),
              source_title: String(item.source_title ?? ""),
              source_date: String(item.source_date ?? ""),
              source_type: String(item.source_type ?? ""),
              source_collection: String(item.source_collection ?? ""),
              source_url: String(item.source_url ?? ""),
            },
            Number(item.score ?? 0),
          ),
        );
      }
    } catch {
      // skip malformed result
    }
  }

  return sources;
}

export async function anthropicAgentChat(
  message: string,
  history: ReadonlyArray<{ role: string; content: string }> | null,
  deps: AgentDeps,
  configOverride?: Partial<AgentConfig>,
  maturityLevel?: string | null,
): Promise<AgentResponse> {
  const cfg = { ...DEFAULT_CONFIG, ...configOverride };
  const startMs = Date.now();
  const allToolCalls: ToolResult[] = [];

  // Build system prompt
  let systemPrompt = SYSTEM_PROMPT;
  if (maturityLevel) {
    const { buildMaturityContext, parseMaturityLevel } = await import("../utils/maturity.js");
    const parsed = parseMaturityLevel(maturityLevel);
    if (parsed) {
      systemPrompt = `${SYSTEM_PROMPT}\n\n${buildMaturityContext(parsed)}`;
    }
  }

  // Build initial messages (Anthropic: user/assistant only, no system role)
  const messages: MessageParam[] = [];
  if (history) {
    for (const h of history) {
      if (h.role === "user" || h.role === "assistant") {
        messages.push({ role: h.role, content: h.content });
      }
    }
  }
  messages.push({ role: "user", content: message });

  const { default: Anthropic } = await import("@anthropic-ai/sdk");
  const client = new Anthropic({ apiKey: config.ANTHROPIC_API_KEY });
  const tools = getAnthropicTools();

  let turns = 0;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;

  while (turns < cfg.maxTurns) {
    if (Date.now() - startMs > cfg.timeoutMs) break;

    turns++;

    const resp = await client.messages.create({
      model: cfg.model,
      system: systemPrompt,
      messages,
      tools: tools as Tool[],
      max_tokens: 2000,
      temperature: cfg.temperature,
    });

    totalInputTokens += resp.usage.input_tokens;
    totalOutputTokens += resp.usage.output_tokens;

    // Extract text and tool_use blocks
    const textBlocks = resp.content.filter((b) => b.type === "text");
    const toolUseBlocks = resp.content.filter((b) => b.type === "tool_use");

    // Terminal: no tool_use or stop_reason is end_turn
    if (toolUseBlocks.length === 0 || resp.stop_reason === "end_turn") {
      const answer = textBlocks.map((b) => "text" in b ? b.text : "").join("");
      const sources = collectSources(allToolCalls);

      return {
        answer,
        sources,
        mode: "agent",
        metadata: buildMetadata(resp.model, totalInputTokens, totalOutputTokens, startMs, sources.length, allToolCalls.length, turns),
      };
    }

    // Process tool_use blocks
    // Add assistant message with the full content (text + tool_use blocks)
    messages.push({
      role: "assistant",
      content: resp.content,
    });

    // Build tool_result for each tool_use
    const toolResults: ToolResultBlockParam[] = [];

    for (const block of toolUseBlocks) {
      if (block.type !== "tool_use") continue;
      const name = block.name;

      if (!ALLOWED_TOOLS.has(name)) {
        toolResults.push({
          type: "tool_result",
          tool_use_id: block.id ?? "",
          content: JSON.stringify({ error: "Unknown tool" }),
        });
        continue;
      }

      const args = (block.input ?? {}) as Record<string, unknown>;
      const toolResult = await executeTool(name as ToolName, args, deps);
      allToolCalls.push(toolResult);

      toolResults.push({
        type: "tool_result",
        tool_use_id: block.id ?? "",
        content: toolResult.result,
      });
    }

    // Append user message with tool_result blocks
    messages.push({
      role: "user",
      content: toolResults,
    });

    if (hasLoopDetection(allToolCalls)) break;
  }

  // Fell through max turns or timeout — final call without tools
  let finalAnswer = "";
  let finalModel = cfg.model;

  try {
    const finalMessages: MessageParam[] = [
      ...messages,
      { role: "user" as const, content: "你已收集到足夠的資訊。請根據已有的搜尋結果直接回答使用者的問題。" },
    ];

    const finalResp = await client.messages.create({
      model: cfg.model,
      system: systemPrompt,
      messages: finalMessages,
      max_tokens: 2000,
      temperature: cfg.temperature,
    });

    totalInputTokens += finalResp.usage.input_tokens;
    totalOutputTokens += finalResp.usage.output_tokens;
    finalAnswer = finalResp.content
      .filter((b) => b.type === "text")
      .map((b) => "text" in b ? b.text : "")
      .join("");
    finalModel = finalResp.model;
  } catch {
    finalAnswer = "";
  }

  const sources = collectSources(allToolCalls);

  return {
    answer: finalAnswer,
    sources,
    mode: "agent",
    metadata: buildMetadata(finalModel, totalInputTokens, totalOutputTokens, startMs, sources.length, allToolCalls.length, turns),
  };
}

export const anthropicAgentChatObserved = observe("anthropic_agent_chat", anthropicAgentChat);
