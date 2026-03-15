/**
 * Shared QA filtering, sorting, and aggregation logic.
 * Used by both QAStore (file-based) and SupabaseQAStore (pgvector).
 */

import type { QAItem } from "./qa-store.js";

export interface ListQaParams {
  readonly category?: string | null;
  readonly primary_category?: string | null;
  readonly keyword?: string | null;
  readonly difficulty?: string | null;
  readonly evergreen?: boolean | null;
  readonly source_type?: string | null;
  readonly source_collection?: string | null;
  readonly extraction_model?: string | null;
  readonly maturity_relevance?: string | null;
  readonly intent_label?: string | null;
  readonly scenario_tag?: string | null;
  readonly serving_tier?: string | null;
  readonly evidence_scope?: string | null;
  readonly sort_by?: string | null;
  readonly sort_order?: string | null;
  readonly limit?: number;
  readonly offset?: number;
}

export function filterAndPaginateQa(
  items: readonly QAItem[],
  params: ListQaParams,
): { items: readonly QAItem[]; total: number } {
  const {
    category,
    primary_category,
    keyword,
    difficulty,
    evergreen,
    source_type,
    source_collection,
    extraction_model,
    maturity_relevance,
    intent_label,
    scenario_tag,
    serving_tier,
    evidence_scope,
    sort_by,
    sort_order,
    limit = 20,
    offset = 0,
  } = params;

  let results: readonly QAItem[] = items;

  if (category) {
    const catSet = new Set(category.includes(",") ? category.split(",") : [category]);
    results = results.filter((i) => catSet.has(i.category));
  }
  if (primary_category) {
    const primarySet = new Set(primary_category.includes(",") ? primary_category.split(",") : [primary_category]);
    results = results.filter((i) => primarySet.has(i.primary_category ?? i.category));
  }
  if (keyword) {
    const kwLower = keyword.toLowerCase();
    results = results.filter(
      (i) =>
        i.question.toLowerCase().includes(kwLower) ||
        i.answer.toLowerCase().includes(kwLower) ||
        i.keywords.some((k) => k.toLowerCase().includes(kwLower)),
    );
  }
  if (difficulty) {
    const diffSet = new Set(difficulty.includes(",") ? difficulty.split(",") : [difficulty]);
    results = results.filter((i) => diffSet.has(i.difficulty));
  }
  if (evergreen !== null && evergreen !== undefined) {
    results = results.filter((i) => i.evergreen === evergreen);
  }
  if (source_type) {
    results = results.filter((i) => i.source_type === source_type);
  }
  if (source_collection) {
    results = results.filter((i) => i.source_collection === source_collection);
  }
  if (extraction_model) {
    results = results.filter((i) => i.extraction_model === extraction_model);
  }
  if (maturity_relevance) {
    results = results.filter((i) => i.maturity_relevance === maturity_relevance);
  }
  if (intent_label) {
    const intentSet = new Set(intent_label.includes(",") ? intent_label.split(",") : [intent_label]);
    results = results.filter((i) => (i.intent_labels ?? []).some((label) => intentSet.has(label)));
  }
  if (scenario_tag) {
    const scenarioSet = new Set(scenario_tag.includes(",") ? scenario_tag.split(",") : [scenario_tag]);
    results = results.filter((i) => (i.scenario_tags ?? []).some((tag) => scenarioSet.has(tag)));
  }
  if (serving_tier) {
    const tierSet = new Set(serving_tier.includes(",") ? serving_tier.split(",") : [serving_tier]);
    results = results.filter((i) => tierSet.has(i.serving_tier ?? "canonical"));
  }
  if (evidence_scope) {
    const scopeSet = new Set(evidence_scope.includes(",") ? evidence_scope.split(",") : [evidence_scope]);
    results = results.filter((i) => (i.evidence_scope ?? []).some((scope) => scopeSet.has(scope)));
  }

  if (sort_by === "source_date") {
    const dir = sort_order === "asc" ? 1 : -1;
    const sorted = [...results];
    sorted.sort((a, b) => dir * a.source_date.localeCompare(b.source_date));
    results = sorted;
  } else if (sort_by === "confidence") {
    const dir = sort_order === "asc" ? 1 : -1;
    const sorted = [...results];
    sorted.sort((a, b) => dir * (a.confidence - b.confidence));
    results = sorted;
  }

  return { items: results.slice(offset, offset + limit), total: results.length };
}

export function categoriesFromItems(items: readonly QAItem[]): readonly string[] {
  const counts = new Map<string, number>();
  for (const item of items) {
    counts.set(item.category, (counts.get(item.category) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([cat]) => cat);
}

export function collectionsFromItems(
  items: readonly QAItem[],
): ReadonlyArray<{ source_collection: string; source_type: string; count: number }> {
  const counts = new Map<string, { source_type: string; count: number }>();
  for (const item of items) {
    const existing = counts.get(item.source_collection);
    if (existing) {
      counts.set(item.source_collection, { source_type: existing.source_type, count: existing.count + 1 });
    } else {
      counts.set(item.source_collection, { source_type: item.source_type, count: 1 });
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1].count - a[1].count)
    .map(([collection, { source_type, count }]) => ({ source_collection: collection, source_type, count }));
}
