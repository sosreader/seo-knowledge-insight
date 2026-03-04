/**
 * CJK tokenizer — splits Chinese/Japanese/Korean text into n-grams
 * and English text into whitespace-separated tokens.
 *
 * Used by keywordOnlySearch to handle CJK queries where whitespace
 * tokenization produces zero tokens.
 */

const CJK_RANGE =
  /[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]/;

/**
 * Tokenize text: CJK characters become 2-grams + single chars,
 * non-CJK segments split by whitespace (tokens >= 2 chars).
 */
export function tokenizeCJK(text: string): readonly string[] {
  const lower = text.toLowerCase();
  const tokens: string[] = [];
  let nonCjkBuf = "";

  for (let i = 0; i < lower.length; i++) {
    const ch = lower[i]!;
    if (CJK_RANGE.test(ch)) {
      // Flush non-CJK buffer
      if (nonCjkBuf.length > 0) {
        pushNonCjkTokens(nonCjkBuf, tokens);
        nonCjkBuf = "";
      }
      // Single char
      tokens.push(ch);
      // 2-gram with next CJK char
      if (i + 1 < lower.length && CJK_RANGE.test(lower[i + 1]!)) {
        tokens.push(ch + lower[i + 1]!);
      }
    } else {
      nonCjkBuf += ch;
    }
  }

  // Flush remaining
  if (nonCjkBuf.length > 0) {
    pushNonCjkTokens(nonCjkBuf, tokens);
  }

  return tokens;
}

function pushNonCjkTokens(buf: string, tokens: string[]): void {
  for (const t of buf.split(/\s+/)) {
    if (t.length >= 2) {
      tokens.push(t);
    }
  }
}
