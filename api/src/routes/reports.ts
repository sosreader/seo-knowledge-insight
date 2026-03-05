import { Hono } from "hono";
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { createHash } from "node:crypto";
import { join, resolve } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import { generateRequestSchema, type ReportSummary } from "../schemas/report.js";
import { paths } from "../config.js";
import { hasOpenAI } from "../utils/mode-detect.js";
import { generateReportLocal, saveReport } from "../services/report-generator-local.js";
import { evaluateReport } from "../services/report-evaluator.js";
import { scoreEvent } from "../utils/laminar-scoring.js";
import { qaStore } from "../store/qa-store.js";

const execFileAsync = promisify(execFile);
// Matches report_YYYYMMDD.md (legacy) and report_YYYYMMDD_<sha1-8>.md (content-addressed)
const REPORT_PATTERN = /^report_(\d{8}(?:_[0-9a-f]{8})?)\.md$/;
const DATE_RE = /^\d{8}(?:_[0-9a-f]{8})?$/;
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

const SNAPSHOT_ID_RE = /^[0-9]{8}-[0-9]{6}$/;

reportsRoute.post("/generate", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = generateRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  // ── Local mode: snapshot_id provided → use stored metrics directly ─
  // Always prefer local template when a snapshot is available,
  // regardless of OPENAI_API_KEY (metrics are already in the snapshot).
  if (parsed.data.snapshot_id) {
    const snapshotId = parsed.data.snapshot_id;
    if (!SNAPSHOT_ID_RE.test(snapshotId)) {
      return c.json(fail("Invalid snapshot_id format"), 400);
    }
    const snapshotPath = resolve(paths.metricsSnapshotsDir, `${snapshotId}.json`);
    if (!snapshotPath.startsWith(paths.metricsSnapshotsDir)) {
      return c.json(fail("Invalid snapshot path"), 400);
    }
    if (!existsSync(snapshotPath)) {
      return c.json(fail("Snapshot not found"), 404);
    }

    let snapshot: Record<string, unknown>;
    try {
      snapshot = JSON.parse(readFileSync(snapshotPath, "utf-8")) as Record<string, unknown>;
    } catch {
      return c.json(fail("Failed to read snapshot"), 500);
    }

    const snapshotMetrics = snapshot.metrics as Record<string, unknown> | undefined;
    if (!snapshotMetrics || typeof snapshotMetrics !== "object") {
      return c.json(fail("Snapshot has no metrics data"), 400);
    }

    const reportDate = new Date().toLocaleDateString("zh-TW", {
      year: "numeric", month: "2-digit", day: "2-digit",
    }).replace(/\//g, "/");

    let reportContent: string;
    try {
      const qaCount = qaStore.count;
      reportContent = await generateReportLocal(
        snapshotMetrics,
        reportDate,
        qaCount,
        parsed.data.situation_analysis,
        parsed.data.traffic_analysis,
      );
      const dateOnly = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const hash8 = createHash("sha1").update(reportContent).digest("hex").slice(0, 8);
      const dateKey = `${dateOnly}_${hash8}`;
      saveReport(reportContent, dateKey);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      console.error("Local report generation failed:", msg);
      return c.json(fail("Local report generation failed"), 500);
    }

    // Async quality eval — does not block response
    void (async () => {
      try {
        const alertNames = Object.keys(snapshotMetrics);
        const evalResult = evaluateReport(reportContent, alertNames);
        await Promise.all([
          scoreEvent("report_section_coverage", evalResult.section_coverage),
          scoreEvent("report_kb_citations", evalResult.kb_citation_count),
          scoreEvent("report_has_research", evalResult.has_research_citations),
          scoreEvent("report_has_links", evalResult.has_kb_links),
          scoreEvent("report_alert_coverage", evalResult.alert_coverage),
          scoreEvent("report_overall", evalResult.overall),
          scoreEvent("report_llm_augmented", evalResult.llm_augmented),
        ]);
      } catch {
        // Scoring failures must never affect the main response path.
      }
    })();

    const reports = listReportFiles();
    if (reports.length === 0) {
      return c.json(fail("No report found after generation"), 500);
    }
    const latest = reports[0]!;
    return c.json(ok({ date: latest.date, filename: latest.filename, size_bytes: latest.size_bytes }));
  }

  // ── OpenAI mode: spawn Python script with metrics_url ────────────
  if (!hasOpenAI()) {
    return c.json(fail("OPENAI_API_KEY not set. Use snapshot_id for local generation."), 400);
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
    if (parsed.data.weeks) {
      cmd.push("--weeks", String(parsed.data.weeks));
    }
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
