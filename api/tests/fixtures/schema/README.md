# Schema fixture（vocus-warehouse migrations）

PG 整合測試（`tests/pg/`）用的 schema，原樣複製自 vocus-warehouse，**不要手改**：

| 檔案 | 來源 |
| --- | --- |
| `0009_app_tables.sql` | `sosreader/vocus-warehouse` `db/migrations/0009_app_tables.sql` @ `454c83223b0cbf7c7449b7b4d170a61fa3213bd5` |
| `0010_extension_vector.sql` | 同 commit `db/migrations/0010_extension_vector.sql` |
| `0011_rag_tables.sql` | 同 commit `db/migrations/0011_rag_tables.sql`（PR 92，RAG 七表＋`warehouse_rag`） |

`tests/pg/global-setup.ts` 以 `pgvector/pgvector:pg17` 容器建角色（`warehouse_admin`、`warehouse_app`、
`warehouse_reader`、`warehouse_rag`），以 superuser 套 0010、以 `SET ROLE warehouse_admin` 套 0009／0011，
做成 template DB；每個測試檔複製一份獨立 DB，並以 **`warehouse_rag` 身分**連線，GRANT 不足的寫法會在測試中直接失敗。

更新方式：VW 有新 migration 動到這些表時，從 VW `origin/main` 重新複製並更新上表 commit。
