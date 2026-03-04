/**
 * RAG Chat — embedding query + GPT completion.
 *
 * Translated from Python app/core/chat.py
 */

import OpenAI from "openai";
import { config } from "../config.js";
import { getEmbedding } from "./embedding.js";
import { qaStore, type QAItem } from "../store/qa-store.js";
import type { SourceItem, ChatResponse } from "../schemas/chat.js";

const SYSTEM_PROMPT = `你是一位資深 SEO 顧問，根據以下 SEO 知識庫內容回答用戶的問題。
回答時請：
1. 直接針對問題給出具體建議，不要含糊其辭
2. 引用知識庫中的案例或數字來支撐建議
3. 若知識庫沒有相關資訊，誠實說明並提供通用建議
4. 回答使用繁體中文，技術術語可以保留英文`;

const STALENESS_THRESHOLD_MONTHS = 18;

function isStale(sourceDate: string): boolean {
  try {
    const d = new Date(sourceDate);
    if (isNaN(d.getTime())) return false;
    const ageMonths = (Date.now() - d.getTime()) / (1000 * 60 * 60 * 24 * 30);
    return ageMonths > STALENESS_THRESHOLD_MONTHS;
  } catch {
    return false;
  }
}

function formatContext(hits: ReadonlyArray<{ item: QAItem; score: number }>): string {
  return hits
    .map(({ item, score }, idx) => {
      const stalenessNote =
        !item.evergreen && isStale(item.source_date)
          ? " [注意：此建議超過 18 個月，請確認是否仍適用]"
          : "";
      return (
        `[${idx + 1}] Q: ${item.question}\n` +
        `    A: ${item.answer}${stalenessNote}\n` +
        `    (來源: ${item.source_title || item.source_date}, 相似度: ${score.toFixed(2)})`
      );
    })
    .join("\n\n");
}

function itemToSource(item: QAItem, score: number): SourceItem {
  return {
    id: item.id,
    question: item.question,
    category: item.category,
    source_title: item.source_title,
    source_date: item.source_date,
    score: Math.round(score * 10000) / 10000,
  };
}

let openaiClient: OpenAI | null = null;
function getOpenAI(): OpenAI {
  if (!openaiClient) {
    openaiClient = new OpenAI({ apiKey: config.OPENAI_API_KEY });
  }
  return openaiClient;
}

export async function ragChat(
  message: string,
  history: ReadonlyArray<{ role: string; content: string }> | null = null,
): Promise<ChatResponse> {
  // 1. Embed user question
  const queryVec = await getEmbedding(message);

  // 2. Hybrid search
  const hits = qaStore.hybridSearch(message, queryVec, config.CHAT_CONTEXT_K);

  // 3. Build context
  const context = formatContext(hits);

  // 4. Assemble messages
  const messages: Array<{ role: "system" | "user" | "assistant"; content: string }> = [
    { role: "system", content: SYSTEM_PROMPT },
  ];

  if (context) {
    messages.push({
      role: "system",
      content: `--- 相關 SEO 知識庫 ---\n${context}\n--- 知識庫結束 ---`,
    });
  }

  if (history) {
    for (const h of history) {
      messages.push({
        role: h.role as "user" | "assistant",
        content: h.content,
      });
    }
  }

  messages.push({ role: "user", content: message });

  // 5. Call GPT
  const resp = await getOpenAI().chat.completions.create({
    model: config.OPENAI_MODEL,
    messages,
    temperature: 0.3,
  });

  const answer = resp.choices[0]?.message?.content ?? "";
  const sources = hits.map(({ item, score }) => itemToSource(item, score));

  return { answer, sources };
}
