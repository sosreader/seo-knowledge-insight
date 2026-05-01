/**
 * Shared test fixtures and helpers.
 */

import type { QAItem } from "../src/store/qa-store.js";

export const FAKE_ITEMS: readonly QAItem[] = [
  {
    id: "a1b2c3d4e5f67890",
    seq: 1,
    question: "What is LCP and how to improve it?",
    answer: "LCP (Largest Contentful Paint) measures loading performance. Optimize images and server response time.",
    keywords: ["LCP", "Core Web Vitals", "performance"],
    confidence: 0.95,
    category: "SEO Technical",
    difficulty: "advanced",
    evergreen: true,
    source_title: "Meeting 2025-01",
    source_date: "2025-01-15",
    is_merged: false,
    synonyms: ["largest contentful paint"],
    freshness_score: 1.0,
    search_hit_count: 5,
    notion_url: "",
    source_type: "meeting",
    source_collection: "seo-meetings",
    source_url: "",
    extraction_model: "claude-code",
    extraction_provenance: {
      source_models: ["claude-code"],
      source_stable_ids: ["a1b2c3d4e5f67890"],
      source_count: 1,
      merge_model: null,
      merge_strategy: "passthrough",
      provenance_status: "single-source",
    },
    maturity_relevance: "L1",
    primary_category: "SEO Technical",
    categories: ["SEO Technical", "Performance"],
    intent_labels: ["implementation", "diagnosis"],
    scenario_tags: ["core-web-vitals"],
    serving_tier: "canonical",
    retrieval_phrases: ["lcp performance", "core web vitals"],
    retrieval_surface_text: "What is LCP and how to improve it?\nLCP core web vitals performance optimize images server response time",
    content_granularity: "tactical",
    evidence_scope: ["technical"],
    booster_target_queries: [],
    hard_negative_terms: [],
  },
  {
    id: "b2c3d4e5f6789012",
    seq: 2,
    question: "How to write title tags for SEO?",
    answer: "Include target keyword near the beginning, keep under 60 characters, make it compelling.",
    keywords: ["title tag", "meta", "on-page SEO"],
    confidence: 0.9,
    category: "On-Page SEO",
    difficulty: "basic",
    evergreen: true,
    source_title: "Meeting 2025-02",
    source_date: "2025-02-10",
    is_merged: false,
    synonyms: ["meta title"],
    freshness_score: 0.95,
    search_hit_count: 3,
    notion_url: "",
    source_type: "meeting",
    source_collection: "seo-meetings",
    source_url: "",
    extraction_model: "claude-code",
    maturity_relevance: "L2",
    primary_category: "On-Page SEO",
    categories: ["On-Page SEO", "Content"],
    intent_labels: ["implementation"],
    scenario_tags: [],
    serving_tier: "supporting",
    retrieval_phrases: ["title tag seo", "meta title"],
    retrieval_surface_text: "How to write title tags for SEO?\ntitle tag meta on-page seo compelling keyword",
    content_granularity: "tactical",
    evidence_scope: ["content"],
    booster_target_queries: [],
    hard_negative_terms: [],
  },
  {
    id: "c3d4e5f678901234",
    seq: 3,
    question: "What is structured data and how to implement it?",
    answer: "Structured data uses Schema.org vocabulary in JSON-LD format to help search engines understand content.",
    keywords: ["structured data", "schema.org", "JSON-LD", "rich snippets"],
    confidence: 0.88,
    category: "SEO Technical",
    difficulty: "advanced",
    evergreen: true,
    source_title: "Meeting 2025-03",
    source_date: "2025-03-05",
    is_merged: false,
    synonyms: ["schema markup"],
    freshness_score: 1.0,
    search_hit_count: 2,
    notion_url: "",
    source_type: "meeting",
    source_collection: "seo-meetings",
    source_url: "",
    extraction_model: "claude-code",
    maturity_relevance: "L3",
    primary_category: "SEO Technical",
    categories: ["SEO Technical", "Structured Data"],
    intent_labels: ["implementation", "measurement"],
    scenario_tags: ["faq-rich-result"],
    serving_tier: "canonical",
    retrieval_phrases: ["structured data schema", "json ld schema"],
    retrieval_surface_text: "What is structured data and how to implement it?\nstructured data schema json-ld rich snippets faq rich result",
    content_granularity: "tactical",
    evidence_scope: ["technical"],
    booster_target_queries: [],
    hard_negative_terms: [],
  },
  {
    id: "d4e5f67890123456",
    seq: 4,
    question: "How to optimize for mobile SEO?",
    answer: "Use responsive design, optimize page speed, ensure touch-friendly elements, and test with Google's mobile-friendly tool.",
    keywords: ["mobile SEO", "responsive design", "page speed"],
    confidence: 0.85,
    category: "SEO Technical",
    difficulty: "basic",
    evergreen: false,
    source_title: "Meeting 2025-04",
    source_date: "2025-04-01",
    is_merged: false,
    synonyms: [],
    freshness_score: 0.8,
    search_hit_count: 1,
    notion_url: "",
    source_type: "meeting",
    source_collection: "seo-meetings",
    source_url: "",
    extraction_model: "gpt-4o",
    maturity_relevance: undefined,
    primary_category: "SEO Technical",
    categories: ["SEO Technical", "Mobile SEO"],
    intent_labels: ["implementation"],
    scenario_tags: [],
    serving_tier: "supporting",
    retrieval_phrases: ["mobile seo", "responsive design page speed"],
    retrieval_surface_text: "How to optimize for mobile SEO?\nmobile seo responsive design page speed touch friendly",
    content_granularity: "tactical",
    evidence_scope: ["technical"],
    booster_target_queries: [],
    hard_negative_terms: [],
  },
  {
    id: "e5f6789012345678",
    seq: 5,
    question: "How does AI affect SEO strategy in 2025?",
    answer: "AI changes search behavior through SGE, requiring focus on E-E-A-T, unique insights, and structured data.",
    keywords: ["AI", "SGE", "E-E-A-T", "search strategy"],
    confidence: 0.92,
    category: "SEO Strategy",
    difficulty: "advanced",
    evergreen: false,
    source_title: "AI 時代的 Technical SEO",
    source_date: "2025-12-12",
    is_merged: false,
    synonyms: ["artificial intelligence SEO"],
    freshness_score: 1.0,
    search_hit_count: 0,
    notion_url: "",
    source_type: "article",
    source_collection: "genehong-medium",
    source_url: "https://genehong.medium.com/ai-technical-seo",
    extraction_model: "claude-code",
    extraction_provenance: {
      source_models: ["claude-code", "local-heuristic"],
      source_stable_ids: ["e5f6789012345678", "feedfacefeedface"],
      source_count: 2,
      merge_model: "gpt-5.4-nano",
      merge_strategy: "semantic-merge",
      provenance_status: "mixed-source",
    },
    maturity_relevance: "L4",
    primary_category: "SEO Strategy",
    categories: ["SEO Strategy", "AI SEO"],
    intent_labels: ["platform-decision", "reporting"],
    scenario_tags: [],
    serving_tier: "booster",
    retrieval_phrases: ["ai seo strategy", "sge eeat"],
    retrieval_surface_text: "How does AI affect SEO strategy in 2025?\nai sge eeat search strategy ai seo",
    content_granularity: "strategic",
    evidence_scope: ["content", "platform"],
    booster_target_queries: ["ai seo", "sge"],
    hard_negative_terms: [],
  },
];

/**
 * Generate fake embeddings as Float32Array.
 * Each vector is random but deterministic (seeded by index).
 */
export function generateFakeEmbeddings(count: number, dim: number = 4): Float32Array {
  const data = new Float32Array(count * dim);
  for (let i = 0; i < count; i++) {
    for (let d = 0; d < dim; d++) {
      // Deterministic pseudo-random
      data[i * dim + d] = Math.sin((i + 1) * (d + 1) * 0.7) * 0.5 + 0.5;
    }
  }
  return data;
}

/**
 * Create a minimal .npy buffer from a Float32Array.
 */
export function createNpyBuffer(data: Float32Array, rows: number, cols: number): Buffer {
  const header = `{'descr': '<f4', 'fortran_order': False, 'shape': (${rows}, ${cols}), }`;
  // Pad to 64-byte alignment
  const totalHeaderLen = 10 + header.length;
  const padding = 64 - (totalHeaderLen % 64);
  const paddedHeader = header + " ".repeat(padding - 1) + "\n";
  const headerLen = paddedHeader.length;

  const buf = Buffer.alloc(10 + headerLen + data.byteLength);
  // Magic
  buf.write("\x93NUMPY", 0, "latin1");
  buf[6] = 1; // major version
  buf[7] = 0; // minor version
  buf.writeUInt16LE(headerLen, 8);
  buf.write(paddedHeader, 10, "latin1");

  // Copy float32 data
  const dataView = new Float32Array(buf.buffer, buf.byteOffset + 10 + headerLen, rows * cols);
  dataView.set(data);

  return buf;
}
