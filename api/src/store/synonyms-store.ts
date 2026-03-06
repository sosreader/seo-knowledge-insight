/**
 * SynonymsStore — manages custom synonym overrides.
 *
 * Two layers:
 *   - static: built-in _SUPPLEMENTAL_SYNONYMS (mirrors Python synonym_dict.py)
 *   - custom: user-defined overrides, persisted to output/synonym_custom.json
 *
 * Custom entries take priority over static entries in the merged view.
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";

export interface SynonymItem {
  readonly term: string;
  readonly synonyms: readonly string[];
  readonly source: "static" | "custom";
}

/**
 * Built-in synonym dict — mirrors Python utils/synonym_dict.py _SUPPLEMENTAL_SYNONYMS.
 * Update both files when adding new static entries.
 */
export const STATIC_SYNONYMS: Readonly<Record<string, readonly string[]>> = {
  "AMP": ["Accelerated Mobile Pages", "加速行動網頁", "AMP Article", "AMP non-Rich"],
  "canonical": ["正規化", "canonical URL", "標準網址", "重覆頁面", "Google選擇", "rel canonical"],
  "CTR": ["點擊率", "click-through rate", "Click Through Rate"],
  "Core Web Vitals": ["CWV", "網頁核心指標", "LCP", "INP", "CLS", "良好體驗"],
  "結構化資料": ["Structured Data", "Schema.org", "JSON-LD", "rich snippet", "Rich Result", "結構化標記"],
  "爬蟲": ["Crawler", "Googlebot", "Spider", "Crawl Budget", "抓取", "crawl"],
  "反向連結": ["Backlink", "外部連結", "inbound link", "referring domain", "backlinks"],
  "hreflang": ["多語系", "語言標記", "地區設定", "國際 SEO", "x-default"],
  "noindex": ["不索引", "排除索引", "robots meta", "disallow", "noindex tag"],
  "sitemap": ["網站地圖", "Sitemap.xml", "提交索引", "XML sitemap"],
  "SERP": ["搜尋結果頁", "Search Engine Results Page", "搜尋版位", "搜尋結果"],
  "E-E-A-T": ["專業度", "權威性", "可信度", "作者資訊", "EEAT", "E-A-T"],
  "Discover": ["Google Discover", "Google 探索", "探索推薦", "探索流量"],
  "曝光": ["曝光數", "Impression", "impressions", "曝光量"],
  "點擊": ["點擊數", "Click", "clicks", "點擊量"],
  "索引": ["Index", "索引狀態", "Coverage", "收錄", "index coverage"],
  "有效": ["有效頁面", "Submitted and indexed", "Coverage 有效"],
  "重新導向": ["Redirect", "301", "302", "轉址", "redirect chain"],
  "robots.txt": ["robots", "crawl disallow", "爬蟲封鎖", "Googlebot 封鎖"],
  "Google Search Console": ["GSC", "搜尋主控台", "Search Console", "站長工具"],
  "TTFB": ["伺服器回應時間", "回應時間", "Time to First Byte", "首位元組時間"],
  "WAF": ["Web Application Firewall", "網頁應用程式防火牆", "防火牆規則"],
  "工作階段": ["Session", "sessions", "工作階段數", "Organic Search工作階段"],
  "Organic Search": ["自然搜尋", "有機搜尋", "搜尋流量", "Organic"],
  "Coverage": ["索引覆蓋率", "有效頁面", "收錄率", "索引率"],
  "內容供給": ["當週文章", "文章數量", "文章頻率", "供給量"],
  "索引覆蓋率": ["Coverage", "有效 (Coverage)", "已索引頁面"],
  "版位": ["SERP 版位", "搜尋版位", "搜尋位置", "版位變化"],
  "Google News": ["Google 新聞", "焦點新聞", "News", "新聞流量", "Top Stories"],
  "搜尋外觀": ["Search Appearance", "外觀", "SERP Feature", "搜尋結果外觀", "搜尋版位外觀"],
  "GA4": ["Google Analytics 4", "GA", "分析工具", "事件追蹤", "GA4 事件"],
  "Direct": ["直接流量", "Direct traffic", "直接造訪", "歸因 Direct"],
  "圖片搜尋": ["Image Search", "Image SEO", "圖片 SEO", "Image", "alt 屬性", "alt text"],
  "行動版": ["手機版", "Mobile", "手機", "行動裝置", "mobile-friendly"],
  "內部連結": ["Internal Link", "內部連結架構", "站內連結", "連結架構", "內連"],
  "metadata": ["中繼資料", "meta tag", "meta 標籤", "頁面描述", "meta description"],
  "路徑": ["URL 路徑", "頁面路徑", "path", "URL path", "網址路徑"],
};

class SynonymsStore {
  private customSynonyms: Record<string, string[]> = {};
  private customJsonPath: string = "";

  /**
   * Initialize with path to synonym_custom.json.
   * Loads existing custom synonyms if the file exists.
   */
  init(path: string): void {
    this.customJsonPath = path;
    this.loadFromFile();
  }

  private loadFromFile(): void {
    if (!existsSync(this.customJsonPath)) {
      this.customSynonyms = {};
      return;
    }
    try {
      const raw = readFileSync(this.customJsonPath, "utf-8");
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        this.customSynonyms = parsed as Record<string, string[]>;
      } else {
        this.customSynonyms = {};
      }
    } catch {
      console.warn("SynonymsStore: failed to parse synonym_custom.json, starting empty");
      this.customSynonyms = {};
    }
  }

  /** Reload from file (call after external writes). */
  reload(): void {
    this.loadFromFile();
  }

  /** Persist current customSynonyms to file. */
  private saveToFile(): void {
    const dir = dirname(this.customJsonPath);
    mkdirSync(dir, { recursive: true });
    writeFileSync(this.customJsonPath, JSON.stringify(this.customSynonyms, null, 2), "utf-8");
  }

  /**
   * List all synonyms — custom entries override static entries.
   * Returns sorted by term.
   */
  list(): readonly SynonymItem[] {
    const merged = new Map<string, SynonymItem>();

    // Add static first
    for (const [term, synonyms] of Object.entries(STATIC_SYNONYMS)) {
      merged.set(term, { term, synonyms, source: "static" });
    }

    // Custom overrides static
    for (const [term, synonyms] of Object.entries(this.customSynonyms)) {
      if (merged.has(term)) {
        // Overrides static entry — still custom source
        merged.set(term, { term, synonyms, source: "custom" });
      } else {
        // New custom entry
        merged.set(term, { term, synonyms, source: "custom" });
      }
    }

    return [...merged.values()].sort((a, b) => a.term.localeCompare(b.term, "zh-TW"));
  }

  /** Get a single term entry, or undefined if not found. */
  get(term: string): SynonymItem | undefined {
    if (term in this.customSynonyms) {
      return { term, synonyms: this.customSynonyms[term]!, source: "custom" };
    }
    if (term in STATIC_SYNONYMS) {
      return { term, synonyms: STATIC_SYNONYMS[term]!, source: "static" };
    }
    return undefined;
  }

  /**
   * Create a new custom synonym entry.
   * Returns false if term already exists in custom.
   */
  create(term: string, synonyms: string[]): SynonymItem {
    this.customSynonyms = { ...this.customSynonyms, [term]: synonyms };
    this.saveToFile();
    return { term, synonyms, source: "custom" };
  }

  /**
   * Update (overwrite) synonyms for a term.
   * Works for both static and custom terms — writes to custom layer.
   */
  update(term: string, synonyms: string[]): SynonymItem {
    this.customSynonyms = { ...this.customSynonyms, [term]: synonyms };
    this.saveToFile();
    return { term, synonyms, source: "custom" };
  }

  /**
   * Delete custom override for a term.
   * If term is static-only → returns false (cannot delete static).
   * If term is custom → removes from custom layer and saves.
   */
  delete(term: string): boolean {
    if (!(term in this.customSynonyms)) {
      return false; // Nothing to delete (term is static-only or doesn't exist)
    }
    const { [term]: _removed, ...rest } = this.customSynonyms;
    this.customSynonyms = rest;
    this.saveToFile();
    return true;
  }

  /** Whether a term exists in the custom layer. */
  isCustom(term: string): boolean {
    return term in this.customSynonyms;
  }

  /** Whether a term exists in the static layer. */
  isStatic(term: string): boolean {
    return term in STATIC_SYNONYMS;
  }

  /** Get current custom synonyms map (for query expansion). */
  getCustom(): Readonly<Record<string, string[]>> {
    return this.customSynonyms;
  }
}

import { hasSupabase } from "./supabase-client.js";
import { SupabaseSynonymsStore } from "./supabase-synonyms-store.js";

/**
 * Unified async synonyms store interface.
 * Read methods are sync (in-memory cache); write methods are async.
 */
export interface AsyncSynonymsStore {
  readonly loaded?: boolean;
  load?(): Promise<void>;
  init?(path: string): void;
  list(): readonly SynonymItem[];
  get(term: string): SynonymItem | undefined;
  create(term: string, synonyms: string[]): SynonymItem | Promise<SynonymItem>;
  update(term: string, synonyms: string[]): SynonymItem | Promise<SynonymItem>;
  delete(term: string): boolean | Promise<boolean>;
  isCustom(term: string): boolean;
  isStatic(term: string): boolean;
  getCustom(): Readonly<Record<string, string[]>>;
}

/** Factory: returns SupabaseSynonymsStore or file-based SynonymsStore. */
export function createSynonymsStore(): AsyncSynonymsStore {
  if (hasSupabase()) {
    console.log("SynonymsStore: using Supabase");
    return new SupabaseSynonymsStore();
  }
  console.log("SynonymsStore: using file-based");
  return new SynonymsStore();
}

export const synonymsStore = createSynonymsStore();
