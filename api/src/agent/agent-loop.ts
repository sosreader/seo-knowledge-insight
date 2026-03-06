/**
 * Agent loop — OpenAI function calling while-loop with termination conditions.
 *
 * Termination: finish_reason === "stop" | MAX_TURNS | TIMEOUT | loop detection
 */

import OpenAI from "openai";
import { config } from "../config.js";
import { getOpenAITools, type ToolName } from "./tool-definitions.js";

const ALLOWED_TOOLS: ReadonlySet<string> = new Set<ToolName>([
  "search_knowledge_base",
  "get_qa_detail",
  "list_categories",
  "get_stats",
]);
import { executeTool } from "./tool-executor.js";
import type { AgentConfig, AgentDeps, AgentResponse, ToolResult } from "./types.js";
import { itemToSource, type SourceItem, type MessageMetadata } from "../schemas/chat.js";
import { observe } from "../utils/observability.js";

const SYSTEM_PROMPT = `你是一位資深 SEO 顧問，可以使用工具搜尋 SEO 知識庫來回答問題。

搜尋策略：
1. 先分析問題，決定用什麼關鍵字搜尋
2. 如果第一次搜尋結果不足，換關鍵字或分類再搜
3. 可以搜尋多次（但不要超過必要的次數）
4. 取得足夠資訊後，直接回答

回答規則：
1. 直接針對問題給出具體建議
2. 引用知識庫中的案例或數字來支撐建議（標注來源）
3. 若知識庫沒有相關資訊，誠實說明並提供通用建議
4. 回答使用繁體中文，技術術語可以保留英文
5. 控制在 500 字以內，重點優先`;

const DEFAULT_CONFIG: AgentConfig = {
  maxTurns: 5,
  timeoutMs: 90_000,
  model: config.CHAT_MODEL,
  temperature: 0.3,
};

let openaiClient: OpenAI | null = null;
function getOpenAI(): OpenAI {
  if (!openaiClient) {
    openaiClient = new OpenAI({ apiKey: config.OPENAI_API_KEY });
  }
  return openaiClient;
}

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
    provider: "openai",
    mode: "agent",
    embedding_model: config.OPENAI_EMBEDDING_MODEL,
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

/** Detect repeated tool calls (same name + same args). */
function hasLoopDetection(toolCalls: readonly ToolResult[]): boolean {
  if (toolCalls.length < 2) return false;
  const last = toolCalls[toolCalls.length - 1]!;
  const prev = toolCalls[toolCalls.length - 2]!;
  return last.toolName === prev.toolName && JSON.stringify(last.args) === JSON.stringify(prev.args);
}

/** Collect unique sources from tool call results. */
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

export async function agentChat(
  message: string,
  history: ReadonlyArray<{ role: string; content: string }> | null,
  deps: AgentDeps,
  configOverride?: Partial<AgentConfig>,
): Promise<AgentResponse> {
  const cfg = { ...DEFAULT_CONFIG, ...configOverride };
  const startMs = Date.now();
  const allToolCalls: ToolResult[] = [];

  // Build initial messages
  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: SYSTEM_PROMPT },
  ];

  if (history) {
    for (const h of history) {
      messages.push({ role: h.role as "user" | "assistant", content: h.content });
    }
  }

  messages.push({ role: "user", content: message });

  const tools = getOpenAITools();
  let turns = 0;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;

  while (turns < cfg.maxTurns) {
    // Timeout check
    if (Date.now() - startMs > cfg.timeoutMs) break;

    turns++;

    const resp = await getOpenAI().chat.completions.create({
      model: cfg.model,
      messages,
      tools,
      temperature: cfg.temperature,
      max_completion_tokens: 2000,
    });

    const choice = resp.choices[0]!;
    const usage = resp.usage;
    totalInputTokens += usage?.prompt_tokens ?? 0;
    totalOutputTokens += usage?.completion_tokens ?? 0;

    // Terminal: LLM decided to stop (no tool calls)
    if (choice.finish_reason === "stop" || !choice.message.tool_calls?.length) {
      const answer = choice.message.content ?? "";
      const sources = collectSources(allToolCalls);

      return {
        answer,
        sources,
        mode: "agent",
        metadata: buildMetadata(resp.model ?? cfg.model, totalInputTokens, totalOutputTokens, startMs, sources.length, allToolCalls.length, turns),
      };
    }

    // Process tool calls
    messages.push(choice.message);

    for (const toolCall of choice.message.tool_calls) {
      const name = toolCall.function.name;

      // Runtime whitelist — reject unknown tool names from LLM
      if (!ALLOWED_TOOLS.has(name)) {
        messages.push({
          role: "tool",
          tool_call_id: toolCall.id,
          content: JSON.stringify({ error: "Unknown tool" }),
        });
        continue;
      }

      // Safe JSON.parse — LLM may return malformed arguments
      let args: Record<string, unknown>;
      try {
        args = JSON.parse(toolCall.function.arguments) as Record<string, unknown>;
      } catch {
        messages.push({
          role: "tool",
          tool_call_id: toolCall.id,
          content: JSON.stringify({ error: "Invalid tool arguments" }),
        });
        continue;
      }

      const toolResult = await executeTool(name as ToolName, args, deps);
      allToolCalls.push(toolResult);

      messages.push({
        role: "tool",
        tool_call_id: toolCall.id,
        content: toolResult.result,
      });
    }

    // Loop detection: if last two calls are identical, break
    if (hasLoopDetection(allToolCalls)) break;
  }

  // Fell through max turns or timeout — make one final call without tools
  let finalAnswer = "";
  let finalModel = cfg.model;

  try {
    const finalResp = await getOpenAI().chat.completions.create({
      model: cfg.model,
      messages: [
        ...messages,
        { role: "system", content: "你已收集到足夠的資訊。請根據已有的搜尋結果直接回答使用者的問題。" },
      ],
      temperature: cfg.temperature,
      max_completion_tokens: 2000,
    });

    const finalUsage = finalResp.usage;
    totalInputTokens += finalUsage?.prompt_tokens ?? 0;
    totalOutputTokens += finalUsage?.completion_tokens ?? 0;
    finalAnswer = finalResp.choices[0]?.message?.content ?? "";
    finalModel = finalResp.model ?? cfg.model;
  } catch {
    // Final synthesis failed — return with already-collected sources
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

/** Observed version — wraps agentChat as a Laminar span. */
export const agentChatObserved = observe("agent_chat", agentChat);
