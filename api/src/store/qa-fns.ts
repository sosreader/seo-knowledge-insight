/**
 * QA Store — Pure module functions (Functional Core).
 *
 * Standalone pure functions that operate on QAStoreData records.
 * QAStore class delegates to these; new code can import directly.
 *
 * All functions are pure (no I/O, no side effects).
 */

import type { QAItem } from "./qa-store.js";
import {
  filterAndPaginateQa,
  categoriesFromItems,
  collectionsFromItems,
  type ListQaParams,
} from "./qa-filter.js";

export interface QAStoreData {
  readonly items: readonly QAItem[];
  readonly idIndex: ReadonlyMap<string, QAItem>;
  readonly seqIndex: ReadonlyMap<number, QAItem>;
}

/** Build store data indexes from a flat items array. */
export function createStoreData(items: readonly QAItem[]): QAStoreData {
  return {
    items,
    idIndex: new Map(items.map((item) => [item.id, item])),
    seqIndex: new Map(items.map((item) => [item.seq, item])),
  };
}

/** Look up a QA item by stable_id (hex). */
export function getById(
  data: QAStoreData,
  id: string,
): QAItem | undefined {
  return data.idIndex.get(id);
}

/** Look up a QA item by sequential number. */
export function getBySeq(
  data: QAStoreData,
  seq: number,
): QAItem | undefined {
  return data.seqIndex.get(seq);
}

/** Filter and paginate QA items. */
export function listQa(
  data: QAStoreData,
  params: ListQaParams,
): { readonly items: readonly QAItem[]; readonly total: number } {
  return filterAndPaginateQa(data.items, params);
}

/** Get all categories sorted by count (descending). */
export function categories(
  data: QAStoreData,
): readonly string[] {
  return categoriesFromItems(data.items);
}

/** Get all collections with source_type and count. */
export function collections(
  data: QAStoreData,
): ReadonlyArray<{ readonly source_collection: string; readonly source_type: string; readonly count: number }> {
  return collectionsFromItems(data.items);
}
