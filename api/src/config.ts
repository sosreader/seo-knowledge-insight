import { config as dotenvConfig } from "dotenv";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

dotenvConfig({ path: resolve(dirname(fileURLToPath(import.meta.url)), "../.env") });

const envSchema = z.object({
  PORT: z.coerce.number().int().positive().default(8002),
  HOST: z.string().default("0.0.0.0"),

  OPENAI_API_KEY: z.string().default(""),
  OPENAI_MODEL: z.string().default("gpt-5.2"),
  OPENAI_EMBEDDING_MODEL: z.string().default("text-embedding-3-small"),

  SEO_API_KEY: z.string().default(""),

  CORS_ORIGINS: z
    .string()
    .default("http://localhost:3000")
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
  qaJsonPath: resolve(ROOT_DIR, "output/qa_final.json"),
  qaEnrichedJsonPath: resolve(ROOT_DIR, "output/qa_enriched.json"),
  qaEmbeddingsPath: resolve(ROOT_DIR, "output/qa_embeddings.npy"),
  sessionsDir: resolve(ROOT_DIR, "output/sessions"),
  scriptsDir: resolve(ROOT_DIR, "scripts"),
  accessLogsDir: resolve(ROOT_DIR, "output/access_logs"),
} as const;
