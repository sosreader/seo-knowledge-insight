import { describe, it, expect } from "vitest";
import { tokenizeCJK } from "../../src/utils/cjk-tokenizer.js";

describe("tokenizeCJK", () => {
  it("tokenizes pure English text by whitespace", () => {
    const tokens = tokenizeCJK("hello world");
    expect(tokens).toEqual(["hello", "world"]);
  });

  it("filters out single-char English tokens", () => {
    const tokens = tokenizeCJK("a big test");
    expect(tokens).toEqual(["big", "test"]);
  });

  it("tokenizes pure CJK into single chars and 2-grams", () => {
    const tokens = tokenizeCJK("搜尋引擎");
    // single: 搜 尋 引 擎
    // 2-gram: 搜尋 尋引 引擎
    expect(tokens).toContain("搜");
    expect(tokens).toContain("尋");
    expect(tokens).toContain("引");
    expect(tokens).toContain("擎");
    expect(tokens).toContain("搜尋");
    expect(tokens).toContain("尋引");
    expect(tokens).toContain("引擎");
    expect(tokens).toHaveLength(7);
  });

  it("handles mixed CJK and English", () => {
    const tokens = tokenizeCJK("SEO 優化策略");
    expect(tokens).toContain("seo");
    expect(tokens).toContain("優化");
    expect(tokens).toContain("化策");
    expect(tokens).toContain("策略");
  });

  it("returns empty for empty string", () => {
    expect(tokenizeCJK("")).toEqual([]);
  });

  it("lowercases all tokens", () => {
    const tokens = tokenizeCJK("Google SEO");
    expect(tokens).toContain("google");
    expect(tokens).toContain("seo");
  });

  it("handles Japanese hiragana/katakana", () => {
    const tokens = tokenizeCJK("テスト");
    expect(tokens).toContain("テ");
    expect(tokens).toContain("テス");
    expect(tokens).toContain("スト");
  });
});
