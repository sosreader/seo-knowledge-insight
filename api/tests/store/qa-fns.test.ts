/**
 * Tests for qa-fns.ts — pure store functions (no mock needed).
 */
import { describe, it, expect } from "vitest";
import {
  createStoreData,
  getById,
  getBySeq,
  listQa,
  categories,
  collections,
} from "../../src/store/qa-fns.js";
import type { QAItem } from "../../src/store/qa-store.js";

const makeItem = (overrides: Partial<QAItem> = {}): QAItem => ({
  id: "abc123",
  seq: 1,
  question: "What is SEO?",
  answer: "Search engine optimization.",
  keywords: ["SEO"],
  confidence: 0.9,
  category: "技術SEO",
  difficulty: "beginner",
  evergreen: true,
  source_title: "Guide",
  source_date: "2025-01-01",
  is_merged: false,
  synonyms: [],
  freshness_score: 1.0,
  search_hit_count: 0,
  notion_url: "",
  source_type: "meeting",
  source_collection: "seo-meetings",
  source_url: "",
  ...overrides,
});

const items: readonly QAItem[] = [
  makeItem({ id: "aaa", seq: 1, category: "技術SEO", source_collection: "seo-meetings", source_type: "meeting" }),
  makeItem({ id: "bbb", seq: 2, category: "內容策略", source_collection: "medium-genehong", source_type: "article" }),
  makeItem({ id: "ccc", seq: 3, category: "技術SEO", source_collection: "seo-meetings", source_type: "meeting" }),
];

describe("qa-fns", () => {
  describe("createStoreData", () => {
    it("builds indexes from items array", () => {
      const data = createStoreData(items);
      expect(data.items).toHaveLength(3);
      expect(data.idIndex.size).toBe(3);
      expect(data.seqIndex.size).toBe(3);
    });

    it("handles empty items", () => {
      const data = createStoreData([]);
      expect(data.items).toHaveLength(0);
      expect(data.idIndex.size).toBe(0);
    });
  });

  describe("getById", () => {
    const data = createStoreData(items);

    it("returns item by id", () => {
      const item = getById(data, "bbb");
      expect(item?.seq).toBe(2);
      expect(item?.category).toBe("內容策略");
    });

    it("returns undefined for missing id", () => {
      expect(getById(data, "zzz")).toBeUndefined();
    });
  });

  describe("getBySeq", () => {
    const data = createStoreData(items);

    it("returns item by seq number", () => {
      const item = getBySeq(data, 3);
      expect(item?.id).toBe("ccc");
    });

    it("returns undefined for missing seq", () => {
      expect(getBySeq(data, 999)).toBeUndefined();
    });
  });

  describe("listQa", () => {
    const data = createStoreData(items);

    it("returns all items with default params", () => {
      const result = listQa(data, {});
      expect(result.total).toBe(3);
      expect(result.items).toHaveLength(3);
    });

    it("filters by category", () => {
      const result = listQa(data, { category: "技術SEO" });
      expect(result.total).toBe(2);
    });

    it("paginates with limit and offset", () => {
      const result = listQa(data, { limit: 1, offset: 1 });
      expect(result.items).toHaveLength(1);
      expect(result.total).toBe(3);
    });
  });

  describe("categories", () => {
    const data = createStoreData(items);

    it("returns categories sorted by count descending", () => {
      const cats = categories(data);
      expect(cats[0]).toBe("技術SEO"); // 2 items
      expect(cats[1]).toBe("內容策略"); // 1 item
    });

    it("returns empty for no items", () => {
      const emptyData = createStoreData([]);
      expect(categories(emptyData)).toHaveLength(0);
    });
  });

  describe("collections", () => {
    const data = createStoreData(items);

    it("returns collections with counts", () => {
      const colls = collections(data);
      expect(colls).toHaveLength(2);

      const seoMeetings = colls.find((c) => c.source_collection === "seo-meetings");
      expect(seoMeetings?.count).toBe(2);
      expect(seoMeetings?.source_type).toBe("meeting");

      const medium = colls.find((c) => c.source_collection === "medium-genehong");
      expect(medium?.count).toBe(1);
    });

    it("returns empty for no items", () => {
      const emptyData = createStoreData([]);
      expect(collections(emptyData)).toHaveLength(0);
    });
  });
});
