/**
 * mapWithConcurrency — 對一組輸入以有限並行度執行非同步映射，保留輸出順序。
 *
 * 用途：分頁抓取 Supabase 資料時，避免一次把所有分頁請求同時打出去打爆資料庫
 * （這正是 QA store cold start 曾經 500/503 的成因），同時比完全循序抓取快。
 */
export async function mapWithConcurrency<T, R>(
  items: readonly T[],
  concurrency: number,
  task: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let nextIndex = 0;

  async function worker(): Promise<void> {
    while (nextIndex < items.length) {
      const index = nextIndex;
      nextIndex += 1;
      results[index] = await task(items[index]!, index);
    }
  }

  const workerCount = Math.min(concurrency, items.length);
  await Promise.all(Array.from({ length: workerCount }, () => worker()));

  return results;
}
