# Snapshot Registry

All snapshots live in `output/metrics_snapshots/`.

| ID | Date | Size | Valid | Notes |
|----|------|------|-------|-------|
| 20260305-081902 | 2026-03-05 | 38 KB | Yes | Normal |
| 20260305-172646 | 2026-03-05 | 38 KB | Yes | Same-day second snapshot |
| 20260306-184735 | 2026-03-06 | 114 B | **No** | Corrupted (only 114 bytes) |
| 20260306-184745 | 2026-03-06 | 39 KB | Yes | Normal |

Valid count: **3** (use `round_number % 3` for rotation)

Valid snapshots in rotation order:
1. `20260305-081902.json`
2. `20260305-172646.json`
3. `20260306-184745.json`
