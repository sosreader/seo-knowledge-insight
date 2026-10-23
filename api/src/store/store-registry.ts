/**
 * Store Registry — centralized store singleton creation.
 *
 * rag-api（PG 模式）只有指標快照走 vocus-warehouse（app_metrics_snapshot）。
 * 週報（app_report）與會議準備（app_meeting_prep）不在 warehouse_rag 權限內：
 * PG 模式下 /reports、/meeting-prep 回 410 not_available_in_rag_api（見 middleware/rag-api-gone.ts），
 * 前端改經 warehouse-api /internal/app 讀取。本機檔案模式仍讀 output/。
 */

import { hasPg } from "./pg-client.js";
import { PgSnapshotStore } from "./pg-snapshot-store.js";

export const snapshotStore = hasPg() ? new PgSnapshotStore() : null;
