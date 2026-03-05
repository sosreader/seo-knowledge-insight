-- Phase 4: Eval runs table for tracking pipeline quality over time

CREATE TABLE IF NOT EXISTS eval_runs (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  run_at     TIMESTAMPTZ DEFAULT NOW(),
  trigger    TEXT        NOT NULL,   -- 'etl_complete' | 'manual' | 'scheduled'
  group_name TEXT        NOT NULL,   -- 'data-quality' | 'keyword-retrieval' | 'retrieval-enhancement'
  metrics    JSONB       NOT NULL,   -- { "hit_rate": 1.0, "mrr": 0.88, "qa_count": 1323, ... }
  passed     BOOLEAN     NOT NULL,
  qa_count   INTEGER,
  notes      TEXT
);

-- Index for recent runs lookup
CREATE INDEX IF NOT EXISTS eval_runs_run_at_idx     ON eval_runs (run_at DESC);
CREATE INDEX IF NOT EXISTS eval_runs_group_name_idx ON eval_runs (group_name);
CREATE INDEX IF NOT EXISTS eval_runs_passed_idx     ON eval_runs (passed);

-- RLS: read-only for anon, write via service key
ALTER TABLE eval_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "eval_runs_read_all" ON eval_runs
  FOR SELECT USING (true);
