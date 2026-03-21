import { Hono } from "hono";
import { readFileSync, existsSync, statSync } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { createHash } from "node:crypto";
import { join, resolve } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import { generateRequestSchema } from "../schemas/report.js";
import { paths } from "../config.js";
import { resolveCapabilities } from "../utils/capabilities.js";
import { generateReportLocal, saveReport, getAlertMetricNames } from "../services/report-generator-local.js";
import { generateReportLlm } from "../services/report-llm.js";
import { evaluateReportV2 } from "../services/report-evaluator.js";
import { scoreEvent } from "../utils/laminar-scoring.js";
import { qaStore } from "../store/qa-store.js";
import { reportStore, snapshotStore } from "../store/store-registry.js";
import { parseReportMeta, listReportFiles } from "../utils/report-file.js";

const execFileAsync = promisify(execFile);
const DATE_RE = /^\d{8}(?:_[0-9a-f]{8})?$/;
const ALLOWED_URL_SCHEMES = new Set(["https:", "http:"]);
const ALLOWED_URL_HOSTS = new Set(["docs.google.com", "sheets.google.com"]);

export const reportsRoute = new Hono();

reportsRoute.get("/", async (c) => {
  if (reportStore) {
    const items = await reportStore.list();
    return c.json(ok({ items, total: items.length }));
  }
  const items = listReportFiles();
  return c.json(ok({ items, total: items.length }));
});

reportsRoute.get("/:date", async (c) => {
  const date = c.req.param("date");
  if (!DATE_RE.test(date)) {
    return c.json(fail("Invalid date format, expected YYYYMMDD"), 400);
  }

  if (reportStore) {
    const result = await reportStore.getByDate(date);
    if (!result) {
      return c.json(fail(`Report report_${date}.md not found`), 404);
    }
    const meta = parseReportMeta(result.content) ?? result.summary.meta;
    return c.json(ok({ date, filename: result.summary.filename, content: result.content, size_bytes: result.summary.size_bytes, meta }));
  }

  const filename = `report_${date}.md`;
  const filepath = join(paths.outputDir, filename);

  if (!existsSync(filepath)) {
    return c.json(fail(`Report ${filename} not found`), 404);
  }

  const content = readFileSync(filepath, "utf-8");
  const size_bytes = statSync(filepath).size;
  const meta = parseReportMeta(content);

  return c.json(ok({ date, filename, content, size_bytes, meta }));
});

const SNAPSHOT_ID_RE = /^[0-9]{8}-[0-9]{6}$/;

reportsRoute.post("/generate", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = generateRequestSchema.safeParse(body);
  const caps = resolveCapabilities(c.req.header("user-agent"));

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  // ── Resolve snapshot (shared between local & OpenAI modes) ──────
  let snapshotPath: string | null = null;
  let snapshot: Record<string, unknown> | null = null;
  let snapshotMetrics: Record<string, unknown> | null = null;

  if (parsed.data.snapshot_id) {
    const snapshotId = parsed.data.snapshot_id;
    if (!SNAPSHOT_ID_RE.test(snapshotId)) {
      return c.json(fail("Invalid snapshot_id format"), 400);
    }

    // Try Supabase first, then fall back to file system
    if (snapshotStore) {
      const found = await snapshotStore.getById(snapshotId);
      if (!found) {
        return c.json(fail("Snapshot not found"), 404);
      }
      snapshot = found as unknown as Record<string, unknown>;
      snapshotMetrics = found.metrics as Record<string, unknown> | undefined ?? null;
    } else {
      snapshotPath = resolve(paths.metricsSnapshotsDir, `${snapshotId}.json`);
      if (!snapshotPath.startsWith(paths.metricsSnapshotsDir)) {
        return c.json(fail("Invalid snapshot path"), 400);
      }
      if (!existsSync(snapshotPath)) {
        return c.json(fail("Snapshot not found"), 404);
      }

      try {
        snapshot = JSON.parse(readFileSync(snapshotPath, "utf-8")) as Record<string, unknown>;
      } catch {
        return c.json(fail("Failed to read snapshot"), 500);
      }
      snapshotMetrics = snapshot.metrics as Record<string, unknown> | undefined ?? null;
    }

    if (!snapshotMetrics || typeof snapshotMetrics !== "object") {
      return c.json(fail("Snapshot has no metrics data"), 400);
    }
  }

  // ── OpenAI mode: snapshot_id + use_openai + OPENAI_API_KEY ─────
  if (parsed.data.use_openai && caps.llm === "none") {
    return c.json(fail("OPENAI_API_KEY not set"), 400);
  }
  if (parsed.data.use_openai && !snapshotMetrics) {
    return c.json(fail("snapshot_id is required for OpenAI mode"), 400);
  }
  if (parsed.data.use_openai && snapshotMetrics && caps.llm === "openai") {
    const weeks = parsed.data.weeks
      ?? (snapshot && typeof snapshot.weeks === "number" ? snapshot.weeks : 1);

    try {
      const result = await generateReportLlm(
        snapshotMetrics as Record<string, unknown>,
        weeks,
      );

      const dateOnly = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const hash8 = createHash("sha1").update(result.content).digest("hex").slice(0, 8);
      const dateKey = `${dateOnly}_${hash8}`;

      if (reportStore) {
        const exists = await reportStore.exists(dateKey);
        if (!exists) {
          const meta = parseReportMeta(result.content);
          await reportStore.save(dateKey, result.content, meta);
        }
      } else {
        const reportFilename = `report_${dateKey}.md`;
        if (!existsSync(join(paths.outputDir, reportFilename))) {
          saveReport(result.content, dateKey);
        }
      }

      if (reportStore) {
        const reports = await reportStore.list();
        if (reports.length === 0) {
          return c.json(fail("No report found after generation"), 500);
        }
        const latest = reports[0]!;
        return c.json(ok({ date: latest.date, filename: latest.filename, size_bytes: latest.size_bytes }));
      }
      const reports = listReportFiles();
      if (reports.length === 0) {
        return c.json(fail("No report found after generation"), 500);
      }
      const latest = reports[0]!;
      return c.json(ok({ date: latest.date, filename: latest.filename, size_bytes: latest.size_bytes }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      if (msg.includes("timeout") || msg.includes("TIMEOUT")) {
        return c.json(fail("Report generation timed out"), 504);
      }
      console.error("OpenAI report generation failed:", msg);
      return c.json(fail("OpenAI report generation failed"), 500);
    }
  }

  // ── Local mode: snapshot_id provided → use stored metrics directly ─
  if (snapshotMetrics && snapshot) {
    const reportDate = new Date().toLocaleDateString("zh-TW", {
      year: "numeric", month: "2-digit", day: "2-digit",
    }).replace(/\//g, "/");

    let reportContent: string;
    let cacheHit = false;
    try {
      const qaCount = qaStore.count;
      const snapshotWeeks = typeof snapshot.weeks === "number" ? snapshot.weeks : null;
      // Extract crawled-not-indexed data from snapshot (backward-compat: old snapshots stored as .indexing)
      const snapshotCrawledNotIndexed = (snapshot as Record<string, unknown>)?.crawled_not_indexed ?? (snapshot as Record<string, unknown>)?.indexing ?? null;
      const snapshotMaturity = (snapshot as Record<string, unknown>)?.maturity as Readonly<Record<string, string>> | null ?? null;
      // Precedence: snapshot.maturity > request.maturity_context > null
      const effectiveMaturity = snapshotMaturity ?? parsed.data.maturity_context ?? null;

      reportContent = await generateReportLocal(
        snapshotMetrics,
        reportDate,
        qaCount,
        {
          situation: parsed.data.situation_analysis,
          traffic: parsed.data.traffic_analysis,
          technical: parsed.data.technical_analysis,
          crawledNotIndexed: parsed.data.crawled_not_indexed_analysis,
          intent: parsed.data.intent_analysis,
          action: parsed.data.action_analysis,
        },
        snapshotWeeks,
        snapshotCrawledNotIndexed as import("../services/crawled-not-indexed-parser.js").CrawledNotIndexedResult | null,
        effectiveMaturity as Readonly<Record<string, string>> | null,
      );
      const dateOnly = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const hash8 = createHash("sha1").update(reportContent).digest("hex").slice(0, 8);
      const dateKey = `${dateOnly}_${hash8}`;
      if (reportStore) {
        cacheHit = await reportStore.exists(dateKey);
        if (!cacheHit) {
          const meta = parseReportMeta(reportContent);
          await reportStore.save(dateKey, reportContent, meta);
        }
      } else {
        const reportFilename = `report_${dateKey}.md`;
        cacheHit = existsSync(join(paths.outputDir, reportFilename));
        if (!cacheHit) {
          saveReport(reportContent, dateKey);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      console.error("Local report generation failed:", msg);
      return c.json(fail("Local report generation failed"), 500);
    }

    // Async quality eval — skip on cache hit, does not block response.
    // Wrapped in observe() so all 7 scoreEvents share one parent trace
    // instead of creating 7 orphan root spans in Laminar.
    if (!cacheHit) {
      void (async () => {
        try {
          const { observe } = await import("@lmnr-ai/lmnr");
          const alertNames = getAlertMetricNames(snapshotMetrics as Record<string, unknown>);
          const v2Result = evaluateReportV2(reportContent, alertNames);
          const evalResult = v2Result.l1;
          await observe({ name: "report_quality_eval" }, async () => {
            await Promise.all([
              // L1 scores (backward-compatible)
              scoreEvent("report_section_coverage", evalResult.section_coverage),
              scoreEvent("report_kb_citations", evalResult.kb_citation_count),
              scoreEvent("report_has_research", evalResult.has_research_citations),
              scoreEvent("report_has_links", evalResult.has_kb_links),
              scoreEvent("report_alert_coverage", evalResult.alert_coverage),
              scoreEvent("report_overall", evalResult.overall),
              scoreEvent("report_llm_augmented", evalResult.llm_augmented),
              scoreEvent("report_has_crawled_not_indexed", evalResult.has_crawled_not_indexed_section),
              // L2 scores
              scoreEvent("report_cross_metric_reasoning", v2Result.l2.cross_metric_reasoning),
              scoreEvent("report_action_specificity", v2Result.l2.action_specificity),
              scoreEvent("report_data_evidence_ratio", v2Result.l2.data_evidence_ratio),
              scoreEvent("report_citation_integration", v2Result.l2.citation_integration),
              scoreEvent("report_quadrant_judgment", v2Result.l2.quadrant_judgment),
              scoreEvent("report_section_depth_variance", v2Result.l2.section_depth_variance),
              // Composite V2
              scoreEvent("report_composite_v2", v2Result.composite_v2),
            ]);
          });
        } catch {
          // Scoring failures must never affect the main response path.
        }
      })();
    }

    if (reportStore) {
      const reports = await reportStore.list();
      if (reports.length === 0) {
        return c.json(fail("No report found after generation"), 500);
      }
      const latest = reports[0]!;
      return c.json(ok({ date: latest.date, filename: latest.filename, size_bytes: latest.size_bytes, cache_hit: cacheHit }));
    }
    const reports = listReportFiles();
    if (reports.length === 0) {
      return c.json(fail("No report found after generation"), 500);
    }
    const latest = reports[0]!;
    return c.json(ok({ date: latest.date, filename: latest.filename, size_bytes: latest.size_bytes, cache_hit: cacheHit }));
  }

  // ── OpenAI mode: spawn Python script with metrics_url ────────────
  if (caps.llm === "none") {
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
