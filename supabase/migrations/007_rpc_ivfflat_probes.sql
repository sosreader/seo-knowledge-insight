-- Phase 7: Improve RPC functions
-- 1. match_qa_items: switch to plpgsql + SET LOCAL ivfflat.probes = 5
-- 2. search_qa_items_keyword: add AND embedding IS NOT NULL for consistency

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
LANGUAGE plpgsql STABLE
SET search_path = public, pg_temp
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
    1 - (qi.embedding <=> query_embedding) AS similarity
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

-- Update keyword search: add embedding IS NOT NULL for consistency with match_qa_items
CREATE OR REPLACE FUNCTION search_qa_items_keyword(
  search_query         TEXT,
  match_count          INT,
  filter_category      TEXT DEFAULT NULL,
  filter_source_type   TEXT DEFAULT NULL,
  filter_collection    TEXT DEFAULT NULL
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
  search_hit_count  INTEGER
)
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
  SELECT
    id, seq, question, answer, keywords, confidence, category,
    difficulty, evergreen, source_title, source_date, source_type,
    source_collection, source_url, is_merged, extraction_model,
    synonyms, freshness_score, search_hit_count
  FROM qa_items
  WHERE
    (filter_category    IS NULL OR category          = filter_category)
    AND (filter_source_type IS NULL OR source_type   = filter_source_type)
    AND (filter_collection  IS NULL OR source_collection = filter_collection)
    AND embedding IS NOT NULL
    AND (
      to_tsvector('simple', question || ' ' || answer) @@ plainto_tsquery('simple', search_query)
      OR search_query = ANY(keywords)
      OR question ILIKE '%' || search_query || '%'
    )
  ORDER BY
    ts_rank(to_tsvector('simple', question || ' ' || answer), plainto_tsquery('simple', search_query)) DESC
  LIMIT match_count;
$$;
