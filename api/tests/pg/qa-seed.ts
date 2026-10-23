/** app_qa_item 種子資料（以 superuser 寫入；warehouse_rag 沒有 INSERT）。 */
import type pg from "pg";

export const DIM = 1536;

/** 第 axis 維為 1 的單位向量（餘弦距離好算：同軸相似度 1、異軸 0）。 */
export function axisVector(axis: number, tilt: number = 0): number[] {
  const v = new Array<number>(DIM).fill(0);
  v[axis] = 1;
  if (tilt) v[(axis + 1) % DIM] = tilt;
  return v;
}

export interface SeedQa {
  readonly id: string;
  readonly seq: number;
  readonly question: string;
  readonly answer?: string;
  readonly category?: string;
  readonly keywords?: readonly string[];
  readonly synonyms?: readonly string[];
  readonly freshness?: number;
  readonly source_type?: string;
  readonly maturity?: string | null;
  readonly embedding: readonly number[] | null;
}

export async function seedQa(admin: pg.Client, rows: readonly SeedQa[]): Promise<void> {
  for (const r of rows) {
    await admin.query(
      `INSERT INTO app_qa_item (id, seq, question, answer, category, keywords, synonyms,
         freshness_score, source_type, maturity_relevance, embedding)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::vector)`,
      [
        r.id,
        r.seq,
        r.question,
        r.answer ?? `answer for ${r.question}`,
        r.category ?? "SEO",
        r.keywords ?? [],
        r.synonyms ?? [],
        r.freshness ?? 1,
        r.source_type ?? "meeting",
        r.maturity ?? null,
        r.embedding ? `[${r.embedding.join(",")}]` : null,
      ],
    );
  }
}
