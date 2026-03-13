-- Add maturity_relevance column to qa_items
-- Tracks the SEO maturity level (L1-L4) most relevant to each QA item
-- Source of truth: meeting_prep_meta.maturity scores

ALTER TABLE qa_items
  ADD COLUMN IF NOT EXISTS maturity_relevance TEXT
  CHECK (maturity_relevance IN ('L1', 'L2', 'L3', 'L4'))
  DEFAULT NULL;

-- B-tree index for filter queries
CREATE INDEX IF NOT EXISTS idx_qa_items_maturity_relevance
  ON qa_items (maturity_relevance)
  WHERE maturity_relevance IS NOT NULL;

-- Add metadata JSONB column to sessions for maturity_level persistence
ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
