/**
 * rag-api CLI（`node dist/cli.js <command>`）。目前只有 update-freshness，供 K8s CronJob 使用。
 *
 * 輸出一律是單行 JSON（stdout），Loki 可直接解析；錯誤訊息只含固定代碼，不含連線字串或憑證。
 * exit code：0 成功；1 執行失敗（DB 不可用、任何批次失敗）；2 用法錯誤。
 */

import { DbTimeoutError, DbUnavailableError } from "../store/store-errors.js";
import { closePool } from "../store/pg-client.js";
import { updateFreshness, type UpdateFreshnessOptions } from "./update-freshness.js";

export const EXIT_OK = 0;
export const EXIT_FAILED = 1;
export const EXIT_USAGE = 2;

const USAGE = "usage: cli.js update-freshness [--dry-run] [--since YYYY-MM-DD] [--limit N]";
const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

export type Emit = (record: Record<string, unknown>) => void;

export interface CliDeps {
  readonly emit: Emit;
  readonly run: typeof updateFreshness;
  readonly close: () => Promise<void>;
  readonly now: () => Date;
}

const defaultDeps: CliDeps = {
  emit: (record) => console.log(JSON.stringify(record)),
  run: updateFreshness,
  close: closePool,
  now: () => new Date(),
};

type ParsedArgs = { ok: true; options: UpdateFreshnessOptions } | { ok: false; reason: string };

export function parseUpdateFreshnessArgs(args: readonly string[]): ParsedArgs {
  let dryRun = false;
  let since: string | undefined;
  let limit = 0;
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]!;
    if (arg === "--dry-run") {
      dryRun = true;
    } else if (arg === "--since") {
      since = args[++i];
      if (since === undefined || !ISO_DAY.test(since)) return { ok: false, reason: "--since 需要 YYYY-MM-DD" };
    } else if (arg === "--limit") {
      const raw = args[++i];
      limit = Number(raw);
      if (raw === undefined || !Number.isInteger(limit) || limit < 0) {
        return { ok: false, reason: "--limit 需要非負整數" };
      }
    } else {
      return { ok: false, reason: `不認得的參數：${arg}` };
    }
  }
  return { ok: true, options: { dryRun, since, limit } };
}

function errorCode(err: unknown): string {
  if (err instanceof DbUnavailableError || err instanceof DbTimeoutError) return err.message;
  return err instanceof Error ? err.name : "unknown_error";
}

async function runUpdateFreshness(args: readonly string[], deps: CliDeps): Promise<number> {
  const parsed = parseUpdateFreshnessArgs(args);
  if (!parsed.ok) {
    deps.emit({ event: "usage_error", reason: parsed.reason, usage: USAGE });
    return EXIT_USAGE;
  }
  const { dryRun, since, limit } = parsed.options;
  deps.emit({
    event: "update_freshness_start",
    dry_run: dryRun,
    since: since ?? null,
    limit: limit ?? 0,
    started_at: deps.now().toISOString(),
  });
  try {
    const result = await deps.run(parsed.options);
    deps.emit({ event: "update_freshness_done", ...result });
    return result.failed > 0 ? EXIT_FAILED : EXIT_OK;
  } catch (err) {
    deps.emit({ event: "update_freshness_failed", error: errorCode(err) });
    return EXIT_FAILED;
  } finally {
    await deps.close();
  }
}

export async function runCli(argv: readonly string[], deps: CliDeps = defaultDeps): Promise<number> {
  const [command, ...rest] = argv;
  if (command === "update-freshness") return runUpdateFreshness(rest, deps);
  deps.emit({ event: "usage_error", reason: `不認得的子命令：${command ?? "(無)"}`, usage: USAGE });
  return EXIT_USAGE;
}
