import { Hono } from "hono";
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { join } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import { generateRequestSchema, type ReportSummary } from "../schemas/report.js";
import { paths } from "../config.js";

const execFileAsync = promisify(execFile);
const REPORT_PATTERN = /^report_(\d{8})\.md$/;
const DATE_RE = /^\d{8}$/;
const ALLOWED_URL_SCHEMES = new Set(["https:", "http:"]);
const ALLOWED_URL_HOSTS = new Set(["docs.google.com", "sheets.google.com"]);

function listReportFiles(): readonly ReportSummary[] {
  const dir = paths.outputDir;
  if (!existsSync(dir)) return [];

  const files = readdirSync(dir)
    .filter((f) => REPORT_PATTERN.test(f))
    .map((f) => {
      const m = REPORT_PATTERN.exec(f)!;
      return {
        date: m[1]!,
        filename: f,
        size_bytes: statSync(join(dir, f)).size,
        mtime: statSync(join(dir, f)).mtimeMs,
      };
    })
    .sort((a, b) => b.mtime - a.mtime);

  return files.map(({ date, filename, size_bytes }) => ({ date, filename, size_bytes }));
}

export const reportsRoute = new Hono();

reportsRoute.get("/", (c) => {
  const items = listReportFiles();
  return c.json(ok({ items, total: items.length }));
});

reportsRoute.get("/:date", (c) => {
  const date = c.req.param("date");
  if (!DATE_RE.test(date)) {
    return c.json(fail("Invalid date format, expected YYYYMMDD"), 400);
  }

  const filename = `report_${date}.md`;
  const filepath = join(paths.outputDir, filename);

  if (!existsSync(filepath)) {
    return c.json(fail(`Report ${filename} not found`), 404);
  }

  const content = readFileSync(filepath, "utf-8");
  const size_bytes = statSync(filepath).size;

  return c.json(ok({ date, filename, content, size_bytes }));
});

reportsRoute.post("/generate", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = generateRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const cmd = ["python3", join(paths.scriptsDir, "04_generate_report.py")];

  if (parsed.data.metrics_url) {
    try {
      const url = new URL(parsed.data.metrics_url);
      if (!ALLOWED_URL_SCHEMES.has(url.protocol)) {
        return c.json(fail("metrics_url must use http or https"), 400);
      }
      if (!ALLOWED_URL_HOSTS.has(url.hostname)) {
        return c.json(fail("metrics_url host not allowed"), 400);
      }
    } catch {
      return c.json(fail("Invalid metrics_url"), 400);
    }
    cmd.push("--input", parsed.data.metrics_url);
  }

  try {
    await execFileAsync(cmd[0]!, cmd.slice(1), {
      cwd: paths.rootDir,
      timeout: 120_000,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    if (msg.includes("TIMEOUT") || msg.includes("timed out")) {
      return c.json(fail("Report generation timed out"), 504);
    }
    console.error("Report generation failed:", msg);
    return c.json(fail("Report generation failed"), 500);
  }

  const reports = listReportFiles();
  if (reports.length === 0) {
    return c.json(fail("No report found after generation"), 500);
  }

  const latest = reports[0]!;
  return c.json(ok({ date: latest.date, filename: latest.filename, size_bytes: latest.size_bytes }));
});
