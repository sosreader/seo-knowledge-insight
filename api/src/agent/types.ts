/**
 * Agent types — shared interfaces for the agentic RAG loop.
 */

import type { SourceItem, MessageMetadata } from "../schemas/chat.js";

export interface AgentConfig {
  readonly maxTurns: number;
  readonly timeoutMs: number;
  readonly model: string;
  readonly temperature: number;
}

export interface ToolResult {
  readonly toolName: string;
  readonly args: Record<string, unknown>;
  readonly result: string;
  readonly durationMs: number;
}

export interface AgentResponse {
  readonly answer: string;
  readonly sources: readonly SourceItem[];
  readonly mode: "agent";
  readonly metadata: MessageMetadata & {
    readonly tool_calls_count: number;
    readonly agent_turns: number;
    readonly tool_calls: readonly ToolResult[];
  };
}

export interface AgentDeps {
  readonly searchKnowledgeBase: (query: string, topK: number) => Promise<ReadonlyArray<{ item: Record<string, unknown>; score: number }>>;
  readonly getQaDetail: (id: string) => Record<string, unknown> | null;
  readonly listCategories: () => readonly string[];
  readonly getStats: () => { readonly total: number; readonly categories: number };
}
