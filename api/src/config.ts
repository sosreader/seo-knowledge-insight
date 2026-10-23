import { config as dotenvConfig } from "dotenv";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

// Load api/.env first (Docker/production), then root .env as fallback (local dev).
// dotenv does NOT override existing vars, so api/.env takes precedence.
const __configDir = dirname(fileURLToPath(import.meta.url));
dotenvConfig({ path: resolve(__configDir, "../.env") });
dotenvConfig({ path: resolve(__configDir, "../../.env") });

const envSchema = z.object({
  PORT: z.coerce.number().int().positive().default(8002),
  HOST: z.string().default("0.0.0.0"),

  OPENAI_API_KEY: z.string().default(""),
  OPENAI_MODEL: z.string().default("gpt-6-luna"),
  REPORT_MODEL: z.string().default("gpt-6-sol"),
  OPENAI_EMBEDDING_MODEL: z.string().default("text-embedding-3-small"),
  CHAT_MODEL: z.string().default("gpt-6-luna"),

  // OpenAI 相容端點。空值 → OpenAI 官方；本機可指向 Ollama 的 /v1（例：http://localhost:11434/v1）。
  // OPENAI_API_KEY 與 LLM_BASE_URL 皆空 → LLM disabled：chat／agent／hybrid・semantic search／reranker 回 501 llm_disabled。
  LLM_BASE_URL: z.string().default(""),
  // 覆寫 CHAT_MODEL／OPENAI_EMBEDDING_MODEL（本機 Ollama 的模型名不同）；空值沿用舊設定。
  LLM_CHAT_MODEL: z.string().default(""),
  LLM_EMBEDDING_MODEL: z.string().default(""),

  // Lambda 模式（AUTH_MODE=api-key，Lambda 預設）與本機 docker-compose 用的 X-API-Key。
  SEO_API_KEY: z.string().default(""),

  // 驗證模式：cf-access（容器預設）｜api-key（Lambda 預設）。見 middleware/auth-mode.ts。
  AUTH_MODE: z.string().default(""),
  // Cloudflare Access team domain（可不含 scheme），ConfigMap vocus-warehouse-access 的 team_domain。
  CF_ACCESS_TEAM_DOMAIN: z.string().default(""),
  // 本服務接受的 Access AUD（逗號分隔），ConfigMap 的 rag_auds。空值 → 非 /health 路由一律 503。
  RAG_AUDS: z.string().default(""),

  LMNR_PROJECT_API_KEY: z.string().default(""),

  CORS_ORIGINS: z
    .string()
    .default("http://localhost:3000,http://localhost:3001")
    .transform((v) =>
      v
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    ),

  CHAT_CONTEXT_K: z.coerce.number().int().positive().default(5),

  RATE_LIMIT_DEFAULT: z.coerce.number().int().positive().default(60),
  // chat 類路由（/chat、/sessions/:id/messages）每身分共用：每分鐘 RATE_LIMIT_CHAT、每日 RATE_LIMIT_CHAT_DAILY
  RATE_LIMIT_CHAT: z.coerce.number().int().positive().default(10),
  RATE_LIMIT_CHAT_DAILY: z.coerce.number().int().positive().default(200),
  RATE_LIMIT_GENERATE: z.coerce.number().int().positive().default(5),

  ANTHROPIC_API_KEY: z.string().default(""),
  CONTEXT_EMBEDDING_WEIGHT: z.coerce.number().min(0).max(1).default(0.6),
  RERANKER_ENABLED: z
    .string()
    .default("auto")
    .transform((v) => {
      if (v === "true") return true;
      if (v === "false") return false;
      return "auto" as const;
    }),

  // Agent mode (Phase 2: agentic RAG)
  AGENT_ENABLED: z
    .string()
    .default("auto")
    .transform((v) => {
      if (v === "true") return true;
      if (v === "false") return false;
      return "auto" as const;
    }),
  AGENT_MAX_TURNS: z.coerce.number().int().min(1).max(10).default(5),
  AGENT_TIMEOUT_MS: z.coerce.number().int().min(5000).max(300000).default(90000),

  // vocus-warehouse（warehouse_rag）：K8s Secret vocus-warehouse-db-rag 掛載的檔案或目錄路徑。
  // 有設 → PG 模式（rag-api）；未設 → 本機檔案模式（output/）。見 store/pg-client.ts。
  VW_DB_SECRET_FILE_RAG: z.string().default(""),
  // QA／synonyms store 定期重載間隔（毫秒），預設 6 小時（21600000）。
  // 0 或非正整數 → 停用。解析見 services/store-reloader.ts 的 resolveReloadIntervalMs()。
  RAG_RELOAD_INTERVAL_MS: z.string().default(""),
  // sslmode=verify-full 的 CA bundle；image 內由 Dockerfile 下載（同 vocus-warehouse）。
  PGSSLROOTCERT: z.string().default("/etc/ssl/rds/global-bundle.pem"),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  console.error("Invalid environment variables:", parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const config = parsed.data;

// Data paths (relative to api/ parent = project root)
const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = resolve(__dirname, "../..");

export const paths = {
  rootDir: ROOT_DIR,
  outputDir: resolve(ROOT_DIR, "output"),
  rawDataDir: resolve(ROOT_DIR, "raw_data"),
  rawMediumMdDir: resolve(ROOT_DIR, "raw_data/medium_markdown"),
  rawIthelpMdDir: resolve(ROOT_DIR, "raw_data/ithelp_markdown"),
  rawGoogleCasesMdDir: resolve(ROOT_DIR, "raw_data/google_cases_markdown"),
  rawAhrefsMdDir: resolve(ROOT_DIR, "raw_data/ahrefs_markdown"),
  rawSejMdDir: resolve(ROOT_DIR, "raw_data/sej_markdown"),
  rawGrowthmemoMdDir: resolve(ROOT_DIR, "raw_data/growthmemo_markdown"),
  rawGoogleBlogMdDir: resolve(ROOT_DIR, "raw_data/google_blog_markdown"),
  rawGoogleBlogZhtwMdDir: resolve(ROOT_DIR, "raw_data/google_blog_zhtw_markdown"),
  rawWebdevMdDir: resolve(ROOT_DIR, "raw_data/webdev_markdown"),
  rawScreamingfrogMdDir: resolve(ROOT_DIR, "raw_data/screamingfrog_markdown"),
  fetchLogsDir: resolve(ROOT_DIR, "output/fetch_logs"),
  qaJsonPath: resolve(ROOT_DIR, "output/qa_final.json"),
  qaEnrichedJsonPath: resolve(ROOT_DIR, "output/qa_enriched.json"),
  qaEmbeddingsPath: resolve(ROOT_DIR, "output/qa_embeddings.npy"),
  qaPerArticleDir: resolve(ROOT_DIR, "output/qa_per_article"),
  sessionsDir: resolve(ROOT_DIR, "output/sessions"),
  scriptsDir: resolve(ROOT_DIR, "scripts"),
  accessLogsDir: resolve(ROOT_DIR, "output/access_logs"),
  evalsDir: resolve(ROOT_DIR, "output/evals"),
  synonymCustomJsonPath: resolve(ROOT_DIR, "output/synonym_custom.json"),
  metricsSnapshotsDir: resolve(ROOT_DIR, "output/metrics_snapshots"),
} as const;
