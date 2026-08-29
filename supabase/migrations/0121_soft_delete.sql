-- 012_soft_delete.sql
-- Soft delete support: deleted_at column + partial indexes + RLS update
-- Affected tables: reports, sessions, metrics_snapshots
-- Excluded: synonym_custom (config data), meeting_prep (no DELETE endpoint)

-- === 1. Add deleted_at column ===

ALTER TABLE reports           ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;
ALTER TABLE sessions          ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;
ALTER TABLE metrics_snapshots ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;

-- === 2. Partial indexes for active (non-deleted) rows ===

CREATE INDEX IF NOT EXISTS reports_active_idx
  ON reports (date_key DESC) WHERE deleted_at IS NULL;

-- Drop redundant non-partial index (superseded by partial index)
DROP INDEX IF EXISTS sessions_updated_at_idx;
CREATE INDEX IF NOT EXISTS sessions_active_idx
  ON sessions (updated_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS snapshots_active_idx
  ON metrics_snapshots (created_at DESC) WHERE deleted_at IS NULL;

-- === 3. RLS — sessions (policy names from 004_sessions_table.sql) ===

-- SELECT: only non-deleted rows visible to anon
ALTER POLICY "anon_select_sessions" ON sessions
  USING (deleted_at IS NULL);

-- UPDATE: anon cannot touch deleted rows
ALTER POLICY "anon_update_sessions" ON sessions
  USING (deleted_at IS NULL) WITH CHECK (deleted_at IS NULL);

-- DELETE: revoke hard-delete from anon (app uses PATCH deleted_at via service key)
DROP POLICY IF EXISTS "anon_delete_sessions" ON sessions;

-- === 4. RLS — reports (policy name from pg_policies query) ===

ALTER POLICY "Allow anon read" ON reports
  USING (deleted_at IS NULL);

-- === 5. RLS — metrics_snapshots (policy name from pg_policies query) ===

ALTER POLICY "Allow anon read" ON metrics_snapshots
  USING (deleted_at IS NULL);
