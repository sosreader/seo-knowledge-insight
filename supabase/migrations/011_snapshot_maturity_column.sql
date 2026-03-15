-- Add maturity JSONB column to metrics_snapshots.
-- Stores client SEO maturity dimensions (e.g. {"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"})
-- from meeting-prep reports, used by report generator to produce maturity block.

ALTER TABLE metrics_snapshots ADD COLUMN IF NOT EXISTS maturity JSONB;
