/**
 * Tests for qa-filter — shared filtering, sorting, and aggregation logic.
 */

import { describe, it, expect } from "vitest";
import { FAKE_ITEMS } from "../setup.js";
import {
  filterAndPaginateQa,
  categoriesFromItems,
  collectionsFromItems,
} from "../../src/store/qa-filter.js";

describe("filterAndPaginateQa", () => {
  it("returns all items with no filters", () => {
    const { items, total } = filterAndPaginateQa(FAKE_ITEMS, { limit: 100 });
    expect(total).toBe(FAKE_ITEMS.length);
    expect(items.length).toBe(FAKE_ITEMS.length);
  });

  it("filters by single category", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      category: "SEO Technical",
      limit: 100,
    });
    for (const item of items) {
      expect(item.category).toBe("SEO Technical");
    }
    expect(items.length).toBe(3);
  });

  it("filters by comma-separated categories", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      category: "SEO Technical,On-Page SEO",
      limit: 100,
    });
    for (const item of items) {
      expect(["SEO Technical", "On-Page SEO"]).toContain(item.category);
    }
    expect(items.length).toBe(4);
  });

  it("filters by keyword in question", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      keyword: "LCP",
      limit: 100,
    });
    expect(items.length).toBeGreaterThan(0);
    expect(items[0]!.question.toLowerCase()).toContain("lcp");
  });

  it("filters by keyword in answer", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      keyword: "JSON-LD",
      limit: 100,
    });
    expect(items.length).toBeGreaterThan(0);
  });

  it("filters by keyword in keywords array", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      keyword: "Core Web Vitals",
      limit: 100,
    });
    expect(items.length).toBe(1);
    expect(items[0]!.keywords).toContain("Core Web Vitals");
  });

  it("filters by difficulty", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      difficulty: "basic",
      limit: 100,
    });
    for (const item of items) {
      expect(item.difficulty).toBe("basic");
    }
  });

  it("filters by comma-separated difficulties", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      difficulty: "basic,advanced",
      limit: 100,
    });
    expect(items.length).toBe(FAKE_ITEMS.length);
  });

  it("filters by evergreen", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      evergreen: true,
      limit: 100,
    });
    for (const item of items) {
      expect(item.evergreen).toBe(true);
    }
  });

  it("filters by source_type", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      source_type: "article",
      limit: 100,
    });
    expect(items.length).toBe(1);
    expect(items[0]!.source_type).toBe("article");
  });

  it("filters by source_collection", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      source_collection: "genehong-medium",
      limit: 100,
    });
    expect(items.length).toBe(1);
    expect(items[0]!.source_collection).toBe("genehong-medium");
  });

  it("sorts by source_date desc (default)", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      sort_by: "source_date",
      limit: 100,
    });
    for (let i = 1; i < items.length; i++) {
      expect(items[i - 1]!.source_date >= items[i]!.source_date).toBe(true);
    }
  });

  it("sorts by source_date asc", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      sort_by: "source_date",
      sort_order: "asc",
      limit: 100,
    });
    for (let i = 1; i < items.length; i++) {
      expect(items[i - 1]!.source_date <= items[i]!.source_date).toBe(true);
    }
  });

  it("sorts by confidence desc", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      sort_by: "confidence",
      limit: 100,
    });
    for (let i = 1; i < items.length; i++) {
      expect(items[i - 1]!.confidence >= items[i]!.confidence).toBe(true);
    }
  });

  it("paginates with limit and offset", () => {
    const { items: page1, total } = filterAndPaginateQa(FAKE_ITEMS, {
      limit: 2,
      offset: 0,
    });
    expect(page1.length).toBe(2);
    expect(total).toBe(FAKE_ITEMS.length);

    const { items: page2 } = filterAndPaginateQa(FAKE_ITEMS, {
      limit: 2,
      offset: 2,
    });
    expect(page2[0]!.id).not.toBe(page1[0]!.id);
  });

  it("filters by extraction_model", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      extraction_model: "gpt-4o",
      limit: 100,
    });
    expect(items.length).toBe(1);
    expect(items[0]!.extraction_model).toBe("gpt-4o");
  });

  it("filters by extraction_model claude-code", () => {
    const { items } = filterAndPaginateQa(FAKE_ITEMS, {
      extraction_model: "claude-code",
      limit: 100,
    });
    expect(items.length).toBe(4);
    for (const item of items) {
      expect(item.extraction_model).toBe("claude-code");
    }
  });

  it("does not mutate the original array", () => {
    const original = [...FAKE_ITEMS];
    filterAndPaginateQa(FAKE_ITEMS, {
      sort_by: "confidence",
      limit: 100,
    });
    expect(FAKE_ITEMS).toEqual(original);
  });
});

describe("categoriesFromItems", () => {
  it("returns sorted categories by count desc", () => {
    const cats = categoriesFromItems(FAKE_ITEMS);
    expect(cats[0]).toBe("SEO Technical"); // 3 items
    expect(cats.length).toBe(3);
  });

  it("returns empty for empty input", () => {
    expect(categoriesFromItems([])).toEqual([]);
  });
});

describe("collectionsFromItems", () => {
  it("returns collections with count and source_type", () => {
    const colls = collectionsFromItems(FAKE_ITEMS);
    expect(colls.length).toBe(2);
    const meetings = colls.find((c) => c.source_collection === "seo-meetings");
    expect(meetings).toBeDefined();
    expect(meetings!.source_type).toBe("meeting");
    expect(meetings!.count).toBe(4);
  });

  it("returns empty for empty input", () => {
    expect(collectionsFromItems([])).toEqual([]);
  });
});
