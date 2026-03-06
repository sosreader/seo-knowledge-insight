-- Fix match_qa_items RPC (BUG-006):
-- 1. STABLE → VOLATILE (SET LOCAL requires transaction write, incompatible with STABLE)
-- 2. search_path add 'extensions' (pgvector operators live in extensions schema)
-- 3. similarity cast ::real (double precision from <=> → real to match RETURNS TABLE)
--
-- Applied to production 2026-03-06. This migration records the fix.

CREATE OR REPLACE FUNCTION match_qa_items(
  query_embedding      vector(1536),
  match_count          INT,
  filter_category      TEXT    DEFAULT NULL,
  filter_source_type   TEXT    DEFAULT NULL,
  filter_collection    TEXT    DEFAULT NULL
)
RETURNS TABLE (
  id                TEXT,
  seq               INTEGER,
  question          TEXT,
  answer            TEXT,
  keywords          TEXT[],
  confidence        REAL,
  category          TEXT,
  difficulty        TEXT,
  evergreen         BOOLEAN,
  source_title      TEXT,
  source_date       TEXT,
  source_type       TEXT,
  source_collection TEXT,
  source_url        TEXT,
  is_merged         BOOLEAN,
  extraction_model  TEXT,
  synonyms          TEXT[],
  freshness_score   REAL,
  search_hit_count  INTEGER,
  similarity        REAL
)
LANGUAGE plpgsql VOLATILE
SET search_path = public, extensions, pg_temp
AS $$
BEGIN
  -- Explore 10% of IVFFlat clusters (lists=50, probes=5) for better recall
  SET LOCAL ivfflat.probes = 5;

  RETURN QUERY
  SELECT
    qi.id,
    qi.seq,
    qi.question,
    qi.answer,
    qi.keywords,
    qi.confidence,
    qi.category,
    qi.difficulty,
    qi.evergreen,
    qi.source_title,
    qi.source_date,
    qi.source_type,
    qi.source_collection,
    qi.source_url,
    qi.is_merged,
    qi.extraction_model,
    qi.synonyms,
    qi.freshness_score,
    qi.search_hit_count,
    (1 - (qi.embedding <=> query_embedding))::real AS similarity
  FROM qa_items qi
  WHERE
    (filter_category    IS NULL OR qi.category          = filter_category)
    AND (filter_source_type IS NULL OR qi.source_type   = filter_source_type)
    AND (filter_collection  IS NULL OR qi.source_collection = filter_collection)
    AND qi.embedding IS NOT NULL
  ORDER BY qi.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
