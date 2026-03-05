-- Phase 1: Enable pgvector + create qa_items table
-- Run this in Supabase SQL Editor (or via Supabase MCP)

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Main QA items table
CREATE TABLE IF NOT EXISTS qa_items (
  id                 TEXT PRIMARY KEY,          -- stable_id (16-char hex SHA256)
  seq                INTEGER,
  question           TEXT NOT NULL,
  answer             TEXT NOT NULL,
  keywords           TEXT[]         DEFAULT '{}',
  confidence         REAL           DEFAULT 0,
  category           TEXT           DEFAULT '',
  difficulty         TEXT           DEFAULT '',
  evergreen          BOOLEAN        DEFAULT FALSE,
  source_title       TEXT           DEFAULT '',
  source_date        TEXT           DEFAULT '',
  source_type        TEXT           DEFAULT 'meeting',
  source_collection  TEXT           DEFAULT 'seo-meetings',
  source_url         TEXT           DEFAULT '',
  is_merged          BOOLEAN        DEFAULT FALSE,
  extraction_model   TEXT,
  synonyms           TEXT[]         DEFAULT '{}',
  freshness_score    REAL           DEFAULT 1.0,
  search_hit_count   INTEGER        DEFAULT 0,
  embedding          vector(1536),
  created_at         TIMESTAMPTZ    DEFAULT NOW(),
  updated_at         TIMESTAMPTZ    DEFAULT NOW()
);

-- 3. pgvector index (IVFFlat, suitable for 1k–100k rows)
--    lists=50 recommended for ~1300 rows
CREATE INDEX IF NOT EXISTS qa_items_embedding_idx
  ON qa_items USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 50);

-- 4. Filter indexes
CREATE INDEX IF NOT EXISTS qa_items_source_type_idx        ON qa_items (source_type);
CREATE INDEX IF NOT EXISTS qa_items_category_idx           ON qa_items (category);
CREATE INDEX IF NOT EXISTS qa_items_source_collection_idx  ON qa_items (source_collection);
CREATE INDEX IF NOT EXISTS qa_items_difficulty_idx         ON qa_items (difficulty);
CREATE INDEX IF NOT EXISTS qa_items_evergreen_idx          ON qa_items (evergreen);
CREATE INDEX IF NOT EXISTS qa_items_seq_idx                ON qa_items (seq);

-- 5. Full-text search index (for keyword search fallback)
CREATE INDEX IF NOT EXISTS qa_items_fts_idx
  ON qa_items USING gin(to_tsvector('simple', question || ' ' || answer));

-- 6. Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER qa_items_updated_at
  BEFORE UPDATE ON qa_items
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 7. Row Level Security (read-only for anon key, full access for service key)
ALTER TABLE qa_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "qa_items_read_all" ON qa_items
  FOR SELECT USING (true);

-- NOTE: INSERT/UPDATE/DELETE requires service_role key (bypasses RLS)
