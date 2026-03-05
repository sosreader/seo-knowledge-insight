-- Phase 3: pgvector RPC function for hybrid search
-- Called from TypeScript SupabaseQAStore.hybridSearch()

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
LANGUAGE sql STABLE
AS $$
  SELECT
    id,
    seq,
    question,
    answer,
    keywords,
    confidence,
    category,
    difficulty,
    evergreen,
    source_title,
    source_date,
    source_type,
    source_collection,
    source_url,
    is_merged,
    extraction_model,
    synonyms,
    freshness_score,
    search_hit_count,
    1 - (embedding <=> query_embedding) AS similarity
  FROM qa_items
  WHERE
    (filter_category    IS NULL OR category          = filter_category)
    AND (filter_source_type IS NULL OR source_type   = filter_source_type)
    AND (filter_collection  IS NULL OR source_collection = filter_collection)
    AND embedding IS NOT NULL
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Full-text keyword search RPC (for keyword-only mode)
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
    AND (
      to_tsvector('simple', question || ' ' || answer) @@ plainto_tsquery('simple', search_query)
      OR search_query = ANY(keywords)
      OR question ILIKE '%' || search_query || '%'
    )
  ORDER BY
    ts_rank(to_tsvector('simple', question || ' ' || answer), plainto_tsquery('simple', search_query)) DESC
  LIMIT match_count;
$$;
