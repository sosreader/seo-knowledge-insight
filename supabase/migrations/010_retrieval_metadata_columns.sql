-- Add retrieval-dimension metadata columns used by the TypeScript API.
-- This migration brings qa_items schema in line with the Phase 4 retrieval model.

ALTER TABLE qa_items
  ADD COLUMN IF NOT EXISTS primary_category TEXT,
  ADD COLUMN IF NOT EXISTS categories TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS intent_labels TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS scenario_tags TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS serving_tier TEXT DEFAULT 'canonical',
  ADD COLUMN IF NOT EXISTS retrieval_phrases TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS retrieval_surface_text TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS content_granularity TEXT,
  ADD COLUMN IF NOT EXISTS evidence_scope TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS booster_target_queries TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS hard_negative_terms TEXT[] DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_qa_items_primary_category
  ON qa_items (primary_category)
  WHERE primary_category IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_qa_items_categories_gin
  ON qa_items USING gin (categories);

CREATE INDEX IF NOT EXISTS idx_qa_items_intent_labels_gin
  ON qa_items USING gin (intent_labels);

CREATE INDEX IF NOT EXISTS idx_qa_items_scenario_tags_gin
  ON qa_items USING gin (scenario_tags);

CREATE INDEX IF NOT EXISTS idx_qa_items_serving_tier
  ON qa_items (serving_tier);

CREATE OR REPLACE FUNCTION increment_search_hit_count(qa_ids TEXT[])
RETURNS VOID
LANGUAGE sql
SECURITY DEFINER
AS $$
  UPDATE qa_items
  SET search_hit_count = COALESCE(search_hit_count, 0) + 1
  WHERE id = ANY(qa_ids);
$$;

GRANT EXECUTE ON FUNCTION increment_search_hit_count(TEXT[]) TO anon;
GRANT EXECUTE ON FUNCTION increment_search_hit_count(TEXT[]) TO authenticated;