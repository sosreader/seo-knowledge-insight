const MIN_QUERY_TERM_LENGTH = 2;

export function queryTerms(text: string): readonly string[] {
  const CJK_RE = /^[\u4e00-\u9fff]+$/;
  const baseTerms = text
    .toLowerCase()
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length >= MIN_QUERY_TERM_LENGTH);

  const result: string[] = [];
  for (const term of baseTerms) {
    result.push(term);
    if (term.length >= 4 && CJK_RE.test(term)) {
      for (let i = 0; i < term.length - 1; i++) {
        result.push(term.slice(i, i + 2));
      }
    }
  }
  return result;
}

export function matchedQueryTerms(
  text: string,
  terms: readonly string[],
): ReadonlySet<string> {
  const haystack = text.toLowerCase();
  const matched = new Set<string>();

  for (const term of terms) {
    if (haystack.includes(term)) {
      matched.add(term);
    }
  }

  return matched;
}

export function categoryDiversityBoost(
  uncoveredQueryCategories: number,
): number {
  if (uncoveredQueryCategories <= 0) return 0;

  // Preserve the original single-category boost, then allow one additional step
  // when a candidate covers two uncovered query categories at once.
  return 0.12 + Math.min(uncoveredQueryCategories - 1, 1) * 0.06;
}

export function novelQueryTermBoost(
  novelTerms: number,
  totalQueryTerms: number,
): number {
  if (novelTerms <= 0 || totalQueryTerms <= 0) return 0;

  if (totalQueryTerms >= 8) {
    return Math.min(novelTerms * 0.01, 0.04);
  }

  if (totalQueryTerms >= 5) {
    return Math.min(novelTerms * 0.015, 0.06);
  }

  return Math.min(novelTerms * 0.02, 0.08);
}