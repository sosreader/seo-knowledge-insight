-- Phase 5: Custom synonyms table (retroactive migration)
-- This table was created manually in Supabase Dashboard.
-- This migration documents the schema for reproducibility.

CREATE TABLE IF NOT EXISTS synonym_custom (
  term        TEXT        PRIMARY KEY,
  synonyms    TEXT[]      NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE synonym_custom ENABLE ROW LEVEL SECURITY;

-- Note: anon full access is intentional — see 004_sessions_table.sql for rationale.
CREATE POLICY "anon_select_synonym_custom" ON synonym_custom FOR SELECT TO anon USING (true);
CREATE POLICY "anon_insert_synonym_custom" ON synonym_custom FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon_update_synonym_custom" ON synonym_custom FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_delete_synonym_custom" ON synonym_custom FOR DELETE TO anon USING (true);
