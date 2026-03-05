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
  OPENAI_MODEL: z.string().default("gpt-5.2"),
  OPENAI_EMBEDDING_MODEL: z.string().default("text-embedding-3-small"),

  SEO_API_KEY: z.string().default(""),

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
  RATE_LIMIT_CHAT: z.coerce.number().int().positive().default(20),
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
