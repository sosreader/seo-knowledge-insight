/**
 * SupabaseSynonymsStore — Supabase-backed custom synonyms layer.
 *
 * Two layers (same as file-based SynonymsStore):
 *   - static: STATIC_SYNONYMS in code (read-only)
 *   - custom: synonym_custom table in Supabase (CRUD)
 */

import { supabaseSelect, supabaseHeaders, SUPABASE_TIMEOUT_MS } from "./supabase-client.js";
import { config } from "../config.js";
import { STATIC_SYNONYMS } from "./synonyms-store.js";
import type { SynonymItem } from "./synonyms-store.js";

interface SynonymRow {
  term: string;
  synonyms: string[];
  created_at: string;
  updated_at: string;
}

export class SupabaseSynonymsStore {
  private customCache: Map<string, string[]> = new Map();
  private _loaded = false;

  get loaded(): boolean {
    return this._loaded;
  }

  /** Load custom synonyms from Supabase at startup. */
  async load(): Promise<void> {
    const rows = await supabaseSelect<SynonymRow>(
      "synonym_custom",
      "?select=term,synonyms&order=term.asc",
    );
    this.customCache = new Map(rows.map((r) => [r.term, r.synonyms]));
    this._loaded = true;
    console.log(
      `SupabaseSynonymsStore loaded: ${this.customCache.size} custom entries`,
    );
  }

  /** List all synonyms — custom overrides static. Sorted by term. */
  list(): readonly SynonymItem[] {
    const merged = new Map<string, SynonymItem>();

    for (const [term, synonyms] of Object.entries(STATIC_SYNONYMS)) {
      merged.set(term, { term, synonyms, source: "static" });
    }

    for (const [term, synonyms] of this.customCache) {
      merged.set(term, { term, synonyms, source: "custom" });
    }

    return [...merged.values()].sort((a, b) =>
      a.term.localeCompare(b.term, "zh-TW"),
    );
  }

  get(term: string): SynonymItem | undefined {
    const custom = this.customCache.get(term);
    if (custom) {
      return { term, synonyms: custom, source: "custom" };
    }
    if (term in STATIC_SYNONYMS) {
      return {
        term,
        synonyms: STATIC_SYNONYMS[term as keyof typeof STATIC_SYNONYMS]!,
        source: "static",
      };
    }
    return undefined;
  }

  async create(term: string, synonyms: string[]): Promise<SynonymItem> {
    const resp = await fetch(
      `${config.SUPABASE_URL}/rest/v1/synonym_custom`,
      {
        method: "POST",
        headers: {
          ...supabaseHeaders(),
          Prefer: "return=minimal,resolution=merge-duplicates",
        },
        body: JSON.stringify({
          term,
          synonyms,
          updated_at: new Date().toISOString(),
        }),
        signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
      },
    );

    if (!resp.ok) {
      throw new Error(`Failed to create synonym (${resp.status})`);
    }

    this.customCache.set(term, synonyms);
    return { term, synonyms, source: "custom" };
  }

  async update(term: string, synonyms: string[]): Promise<SynonymItem> {
    const resp = await fetch(
      `${config.SUPABASE_URL}/rest/v1/synonym_custom?term=eq.${encodeURIComponent(term)}`,
      {
        method: "PATCH",
        headers: { ...supabaseHeaders(), Prefer: "return=minimal" },
        body: JSON.stringify({
          synonyms,
          updated_at: new Date().toISOString(),
        }),
        signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
      },
    );

    if (!resp.ok) {
      // Maybe doesn't exist yet — try upsert
      return this.create(term, synonyms);
    }

    this.customCache.set(term, synonyms);
    return { term, synonyms, source: "custom" };
  }

  async delete(term: string): Promise<boolean> {
    if (!this.customCache.has(term)) {
      return false;
    }

    const resp = await fetch(
      `${config.SUPABASE_URL}/rest/v1/synonym_custom?term=eq.${encodeURIComponent(term)}`,
      {
        method: "DELETE",
        headers: supabaseHeaders(),
        signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
      },
    );

    if (resp.ok) {
      this.customCache.delete(term);
      return true;
    }
    return false;
  }

  isCustom(term: string): boolean {
    return this.customCache.has(term);
  }

  isStatic(term: string): boolean {
    return term in STATIC_SYNONYMS;
  }

  getCustom(): Readonly<Record<string, string[]>> {
    return Object.fromEntries(this.customCache);
  }
}
