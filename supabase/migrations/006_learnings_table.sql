-- Phase 6: Learnings table (retroactive migration)
-- This table was created manually in Supabase Dashboard.
-- This migration documents the schema for reproducibility.

CREATE TABLE IF NOT EXISTS learnings (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  type        TEXT        NOT NULL,       -- 'positive' | 'negative' | 'correction'
  query       TEXT        NOT NULL,       -- original search query
  qa_id       TEXT,                       -- linked QA item stable_id
  feedback    TEXT,                       -- user feedback text
  top_score   REAL,                       -- search score at time of feedback
  context     TEXT,                       -- additional context
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE learnings ENABLE ROW LEVEL SECURITY;

-- Note: anon full access is intentional — see 004_sessions_table.sql for rationale.
CREATE POLICY "anon_select_learnings" ON learnings FOR SELECT TO anon USING (true);
CREATE POLICY "anon_insert_learnings" ON learnings FOR INSERT TO anon WITH CHECK (true);

CREATE INDEX IF NOT EXISTS learnings_created_at_idx ON learnings (created_at DESC);
CREATE INDEX IF NOT EXISTS learnings_qa_id_idx ON learnings (qa_id) WHERE qa_id IS NOT NULL;
