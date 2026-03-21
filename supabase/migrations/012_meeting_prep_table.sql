-- 012: Meeting Prep table
-- Stores meeting-prep reports with embedded metadata (JSONB).
-- Mirrors the reports table pattern (date_key PK, upsert-friendly).

CREATE TABLE IF NOT EXISTS meeting_prep (
  date_key    TEXT        PRIMARY KEY,
  filename    TEXT        NOT NULL,
  content     TEXT        NOT NULL,
  size_bytes  INTEGER     NOT NULL,
  meta        JSONB       NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS meeting_prep_created_at_idx
  ON meeting_prep (created_at DESC);

CREATE INDEX IF NOT EXISTS meeting_prep_meta_gin_idx
  ON meeting_prep USING gin(meta jsonb_path_ops);

ALTER TABLE meeting_prep ENABLE ROW LEVEL SECURITY;

-- RLS: anon can read (API auth middleware protects access), writes restricted to service_role
CREATE POLICY "meeting_prep_read_all" ON meeting_prep
  FOR SELECT USING (true);

CREATE POLICY "meeting_prep_service_write" ON meeting_prep
  FOR INSERT USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "meeting_prep_service_update" ON meeting_prep
  FOR UPDATE USING (auth.role() = 'service_role');

CREATE POLICY "meeting_prep_service_delete" ON meeting_prep
  FOR DELETE USING (auth.role() = 'service_role');

-- updated_at trigger (reuses function from migration 001)
CREATE TRIGGER meeting_prep_updated_at
  BEFORE UPDATE ON meeting_prep
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
