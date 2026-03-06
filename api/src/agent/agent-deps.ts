/**
 * Agent deps factory — bridges qaStore to AgentDeps interface.
 */

import { qaStore } from "../store/qa-store.js";
import { getEmbedding } from "../services/embedding.js";
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

    getQaDetail: (id: string) => {
      const item = qaStore.getById(id);
      if (!item) return null;
      return item as unknown as Record<string, unknown>;
    },

    listCategories: () => {
      const cats = qaStore.categories();
      return cats.map((c) => c.category);
    },

    getStats: () => ({
      total: qaStore.count,
      categories: qaStore.categories().length,
    }),
  };
}
