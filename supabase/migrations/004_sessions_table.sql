-- Phase 4: Sessions table (retroactive migration)
-- This table was created manually in Supabase Dashboard.
-- This migration documents the schema for reproducibility.

CREATE TABLE IF NOT EXISTS sessions (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT        NOT NULL DEFAULT 'New Chat',
  messages    JSONB       NOT NULL DEFAULT '[]'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: enabled with anon full access (API layer handles auth via X-API-Key)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Note: anon full access is intentional — all API requests are authenticated
-- at the application layer (X-API-Key middleware). The anon key is server-side only,
-- never exposed to the client bundle.
CREATE POLICY "anon_select_sessions" ON sessions FOR SELECT TO anon USING (true);
CREATE POLICY "anon_insert_sessions" ON sessions FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon_update_sessions" ON sessions FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_delete_sessions" ON sessions FOR DELETE TO anon USING (true);

CREATE INDEX IF NOT EXISTS sessions_updated_at_idx ON sessions (updated_at DESC);
