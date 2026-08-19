/**
 * Agent deps factory — bridges qaStore to AgentDeps interface.
 */

import { qaStore } from "../store/qa-store.js";
import { getEmbedding } from "../services/embedding.js";
import { SupabaseQAStore } from "../store/supabase-qa-store.js";
import type { AgentDeps } from "./types.js";

export function createAgentDeps(): AgentDeps {
  return {
    searchKnowledgeBase: async (query: string, topK: number) => {
      const queryVec = await getEmbedding(query);
      const hits = await qaStore.hybridSearch(query, queryVec, topK);
      return hits.map(({ item, score }) => ({
        item: item as unknown as Record<string, unknown>,
        score,
      }));
    },

    getQaDetail: async (id: string) => {
      const item = qaStore.getById(id);
      if (!item) return null;
      // Supabase 後端的 in-memory item 沒帶 answer（省流量），detail 查詢才補撈。
      const hydrated =
        qaStore instanceof SupabaseQAStore
          ? await qaStore.hydrateAnswer(item)
          : item;
      return hydrated as unknown as Record<string, unknown>;
    },

    listCategories: () => {
      return [...qaStore.categories()];
    },

    getStats: () => ({
      total: qaStore.count,
      categories: qaStore.categories().length,
    }),
  };
}
