import { Hono } from "hono";
import { readFileSync, existsSync, statSync, mkdirSync, writeFileSync, unlinkSync } from "node:fs";
import { resolve } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import {
  fetchRequestSchema,
  extractQARequestSchema,
  dedupeClassifyRequestSchema,
  metricsRequestSchema,
  crawledNotIndexedRequestSchema,
  metricsSaveSchema,
  snapshotIdSchema,
  sourceDocsQuerySchema,
  type MeetingsResponse,
  type MeetingPreviewResponse,
  type UnprocessedResponse,
  type SourceDocsResponse,
  type SourceDocPreviewResponse,
  type MetricsSnapshot,
} from "../schemas/pipeline.js";
import { execPython, execQaTools } from "../services/pipeline-runner.js";
import { loadMetrics, type MetricData } from "../services/metrics-parser.js";
import { analyzeAllMetrics, type TimeseriesPoint } from "../services/timeseries-analyzer.js";
import { loadCrawledNotIndexed, parseCrawledNotIndexedTsv } from "../services/crawled-not-indexed-parser.js";
import { analyzeCrawledNotIndexed } from "../services/crawled-not-indexed-analyzer.js";
import { scoreEvent } from "../utils/laminar-scoring.js";
import { paths } from "../config.js";
import { qaStore } from "../store/qa-store.js";
import { hasSupabase, supabaseSelect } from "../store/supabase-client.js";
import { SupabaseSnapshotStore } from "../store/supabase-snapshot-store.js";
import type { SourceDocEntry } from "../schemas/pipeline.js";
import {
  UUID_RE,
  SAFE_FILENAME_RE,
  SNAPSHOT_ID_RE,
  readMeetingsIndex,
  buildPipelineStatus,
  findUnprocessed,
  readFetchLogs,
  getCollectionDirMap,
  buildSourceDocs,
  generateSnapshotId,
  listSnapshots,
} from "./pipeline-fs.js";

const supabaseSnapshotStore = hasSupabase() ? new SupabaseSnapshotStore() : null;

/**
 * Derive source docs from qaStore items (Lambda fallback).
 * Groups QA items by (source_collection, source_title, source_date) to reconstruct
 * the list of source documents without file-system access.
 */
function buildSourceDocsFromStore(): readonly SourceDocEntry[] {
  const groups = new Map<string, { title: string; source_type: string; source_collection: string; source_url: string; source_date: string }>();

  for (const item of qaStore.allItems) {
    const key = `${item.source_collection}::${item.source_title}::${item.source_date}`;
    if (!groups.has(key)) {
      groups.set(key, {
        title: item.source_title,
        source_type: item.source_type,
        source_collection: item.source_collection,
        source_url: item.source_url,
        source_date: item.source_date,
      });
    }
  }

  return Array.from(groups.values())
    .sort((a, b) => (b.source_date || "").localeCompare(a.source_date || ""))
    .map((g) => ({
      file: `${g.title.replace(/\s+/g, "_")}.md`,
      title: g.title,
      source_type: (g.source_type === "meeting" ? "meeting" : "article") as "meeting" | "article",
      source_collection: g.source_collection,
      source_url: g.source_url,
      created_time: g.source_date ? `${g.source_date}T00:00:00.000Z` : "",
      size_bytes: 0,
      is_processed: true,
    }));
}

// --- Route ---

export const pipelineRoute = new Hono();

// GET /status
pipelineRoute.get("/status", (c) => {
  const status = buildPipelineStatus();
  return c.json(ok(status));
});

// GET /meetings
pipelineRoute.get("/meetings", (c) => {
  const items = readMeetingsIndex();
  const response: MeetingsResponse = { items, total: items.length };
  return c.json(ok(response));
});

// GET /meetings/:id/preview
pipelineRoute.get("/meetings/:id/preview", (c) => {
  const id = c.req.param("id");
  if (!UUID_RE.test(id)) {
    return c.json(fail("Invalid meeting ID format"), 400);
  }

  const meetings = readMeetingsIndex();
  const meeting = meetings.find((m) => m.id === id);
  if (!meeting) {
    return c.json(fail("Meeting not found"), 404);
  }

  const mdPath = resolve(paths.rawDataDir, meeting.md_file);

  if (!mdPath.startsWith(paths.rawDataDir)) {
    return c.json(fail("Invalid file path"), 400);
  }

  if (!existsSync(mdPath)) {
    return c.json(fail("Markdown file not found"), 404);
  }

  const content = readFileSync(mdPath, "utf-8");
  const size_bytes = statSync(mdPath).size;

  const response: MeetingPreviewResponse = {
    id: meeting.id,
    title: meeting.title,
    content,
    size_bytes,
  };
  return c.json(ok(response));
});

// GET /source-docs
pipelineRoute.get("/source-docs", (c) => {
  const parsed = sourceDocsQuerySchema.safeParse(Object.fromEntries(new URL(c.req.url).searchParams));
  if (!parsed.success) {
    return c.json(fail("Invalid query parameters"), 400);
  }

  const { source_type, source_collection, keyword, is_processed, limit, offset } = parsed.data;

  let docs = buildSourceDocs();
  // Fallback: derive from qaStore when file-system returns empty (Lambda)
  if (docs.length === 0 && qaStore.count > 0) {
    docs = buildSourceDocsFromStore();
  }

  if (source_type) {
    docs = docs.filter((d) => d.source_type === source_type);
  }
  if (source_collection) {
    docs = docs.filter((d) => d.source_collection === source_collection);
  }
  if (keyword) {
    const kw = keyword.toLowerCase();
    docs = docs.filter((d) => d.title.toLowerCase().includes(kw) || d.file.toLowerCase().includes(kw));
  }
  if (is_processed !== undefined) {
    docs = docs.filter((d) => d.is_processed === is_processed);
  }

  const total = docs.length;
  const items = docs.slice(offset, offset + limit);

  const response: SourceDocsResponse = { items, total, offset, limit };
  return c.json(ok(response));
});

// GET /source-docs/:collection/:file/preview
pipelineRoute.get("/source-docs/:collection/:file/preview", (c) => {
  const collection = c.req.param("collection");
  const file = c.req.param("file");

  const entry = getCollectionDirMap()[collection];
  if (!entry) {
    return c.json(fail("Unknown collection"), 400);
  }

  if (!SAFE_FILENAME_RE.test(file)) {
    return c.json(fail("Invalid filename"), 400);
  }

  const filePath = resolve(entry.dir, file);

  if (!filePath.startsWith(entry.dir)) {
    return c.json(fail("Invalid file path"), 400);
  }

  if (!existsSync(filePath)) {
    return c.json(fail("File not found"), 404);
  }

  const content = readFileSync(filePath, "utf-8");
  const size_bytes = statSync(filePath).size;

  const h1Match = content.match(/^#\s+(.+)/m);
  const title = h1Match ? h1Match[1].trim() : file.replace(/\.md$/, "").replace(/[-_]/g, " ");

  const response: SourceDocPreviewResponse = {
    file,
    title,
    collection,
    content,
    size_bytes,
  };
  return c.json(ok(response));
});

// GET /unprocessed
pipelineRoute.get("/unprocessed", (c) => {
  const items = findUnprocessed();
  const response: UnprocessedResponse = { items, total: items.length };
  return c.json(ok(response));
});

// GET /logs
pipelineRoute.get("/logs", (c) => {
  const limitParam = c.req.query("limit");
  const limit = limitParam ? Math.min(Number(limitParam), 1000) : 200;
  const logs = readFetchLogs(limit);
  return c.json(ok(logs));
});

// POST /fetch
pipelineRoute.post("/fetch", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = fetchRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const args: string[] = [];
  if (parsed.data.since) {
    args.push("--since", parsed.data.since);
  }

  const result = await execPython("01_fetch_notion.py", args);

  if (!result.success) {
    const msg = result.output.includes("timed out")
      ? "Fetch timed out"
      : "Fetch failed";
    console.error("Pipeline fetch failed:", result.output);
    return c.json(fail(msg), 500);
  }

  return c.json(ok(result));
});

// POST /extract-qa
pipelineRoute.post("/extract-qa", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = extractQARequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const args: string[] = [];
  if (parsed.data.limit) {
    args.push("--limit", String(parsed.data.limit));
  }
  if (parsed.data.file) {
    args.push("--file", parsed.data.file);
  }

  const result = await execPython("02_extract_qa.py", args);

  if (!result.success) {
    console.error("Pipeline extract-qa failed:", result.output);
    return c.json(fail("Extract QA failed"), 500);
  }

  return c.json(ok(result));
});

// POST /dedupe-classify
pipelineRoute.post("/dedupe-classify", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = dedupeClassifyRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const args: string[] = [];
  if (parsed.data.skip_dedup) {
    args.push("--skip-dedup");
  }
  if (parsed.data.skip_classify) {
    args.push("--skip-classify");
  }
  if (parsed.data.limit) {
    args.push("--limit", String(parsed.data.limit));
  }

  const result = await execPython("03_dedupe_classify.py", args);

  if (!result.success) {
    console.error("Pipeline dedupe-classify failed:", result.output);
    return c.json(fail("Dedupe/classify failed"), 500);
  }

  return c.json(ok(result));
});

// POST /fetch-articles
pipelineRoute.post("/fetch-articles", async (c) => {
  const [mediumResult, ithelpResult, googleResult] = await Promise.all([
    execPython("01b_fetch_medium.py", []),
    execPython("01c_fetch_ithelp.py", []),
    execPython("01d_fetch_google_cases.py", []),
  ]);

  const allSuccess =
    mediumResult.success && ithelpResult.success && googleResult.success;

  if (!allSuccess) {
    const failures = [mediumResult, ithelpResult, googleResult].filter(
      (r) => !r.success
    );
    console.error(
      "Pipeline fetch-articles partial failure:",
      failures.map((f) => f.output).join("\n")
    );
  }

  return c.json(
    ok({
      success: allSuccess,
      results: [
        {
          source: "medium",
          success: mediumResult.success,
          output: mediumResult.output,
          duration_ms: mediumResult.duration_ms,
        },
        {
          source: "ithelp",
          success: ithelpResult.success,
          output: ithelpResult.output,
          duration_ms: ithelpResult.duration_ms,
        },
        {
          source: "google-cases",
          success: googleResult.success,
          output: googleResult.output,
          duration_ms: googleResult.duration_ms,
        },
      ],
    })
  );
});

// POST /metrics/save
pipelineRoute.post("/metrics/save", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = metricsSaveSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { metrics, crawled_not_indexed, maturity, source, tab, label, weeks } = parsed.data;
  const id = generateSnapshotId();
  const created_at = new Date().toISOString();

  const snapshot: MetricsSnapshot = {
    id,
    created_at,
    label,
    source,
    tab,
    weeks,
    metrics,
    ...(crawled_not_indexed ? { crawled_not_indexed } : {}),
    ...(maturity ? { maturity } : {}),
  } as MetricsSnapshot;

  if (supabaseSnapshotStore) {
    try {
      await supabaseSnapshotStore.save(snapshot);
    } catch {
      return c.json(fail("Failed to save snapshot"), 500);
    }
    return c.json(ok({ id, created_at, label }), 201);
  }

  const dir = paths.metricsSnapshotsDir;
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  const filePath = resolve(dir, `${id}.json`);
  if (!filePath.startsWith(dir)) {
    return c.json(fail("Invalid snapshot path"), 400);
  }

  try {
    writeFileSync(filePath, JSON.stringify(snapshot, null, 2), "utf-8");
  } catch {
    return c.json(fail("Failed to save snapshot"), 500);
  }

  return c.json(ok({ id, created_at, label }), 201);
});

// GET /metrics/snapshots
pipelineRoute.get("/metrics/snapshots", async (c) => {
  if (supabaseSnapshotStore) {
    const snapshots = await supabaseSnapshotStore.list();
    return c.json(ok({ items: snapshots, total: snapshots.length }));
  }
  const snapshots = listSnapshots();
  return c.json(ok({ items: snapshots, total: snapshots.length }));
});

// DELETE /metrics/snapshots/:id
pipelineRoute.delete("/metrics/snapshots/:id", async (c) => {
  const id = c.req.param("id");
  const parsed = snapshotIdSchema.safeParse(id);
  if (!parsed.success) {
    return c.json(fail("Invalid snapshot ID format"), 400);
  }

  if (supabaseSnapshotStore) {
    const deleted = await supabaseSnapshotStore.delete(id);
    if (!deleted) {
      return c.json(fail("Snapshot not found"), 404);
    }
    return c.json(ok({ deleted: true, id }));
  }

  const dir = paths.metricsSnapshotsDir;
  const filePath = resolve(dir, `${id}.json`);
  if (!filePath.startsWith(dir)) {
    return c.json(fail("Invalid snapshot path"), 400);
  }

  if (!existsSync(filePath)) {
    return c.json(fail("Snapshot not found"), 404);
  }

  try {
    unlinkSync(filePath);
  } catch {
    return c.json(fail("Failed to delete snapshot"), 500);
  }

  return c.json(ok({ deleted: true, id }));
});

// POST /metrics
pipelineRoute.post("/metrics", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = metricsRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { source, tab } = parsed.data;

  try {
    const result = await loadMetrics(source, tab);
    return c.json(ok(result));
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error("Metrics loading failed:", msg);
    return c.json(fail("Metrics loading failed"), 500);
  }
});

// POST /crawled-not-indexed
pipelineRoute.post("/crawled-not-indexed", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = crawledNotIndexedRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { source, raw_tsv, tab } = parsed.data;

  try {
    const data = raw_tsv
      ? parseCrawledNotIndexedTsv(raw_tsv)
      : await loadCrawledNotIndexed(source!, tab);
    const insight = analyzeCrawledNotIndexed(data);

    // Async quality eval — does not block response
    if (data.paths.length > 0) {
      void (async () => {
        try {
          const { observe } = await import("@lmnr-ai/lmnr");
          const { evaluateCrawledNotIndexedAnalysis } = await import(
            "../services/crawled-not-indexed-evaluator.js"
          );
          const evalResult = evaluateCrawledNotIndexedAnalysis(insight.markdown, data);
          await observe({ name: "crawled_not_indexed_quality_eval" }, async () => {
            await Promise.all([
              scoreEvent("cni_path_coverage", evalResult.path_coverage),
              scoreEvent("cni_trend_accuracy", evalResult.trend_accuracy),
              scoreEvent("cni_has_severity", evalResult.has_severity_assessment),
              scoreEvent("cni_recommendation_specificity", evalResult.recommendation_specificity),
              scoreEvent("cni_data_fidelity", evalResult.data_fidelity),
              scoreEvent("cni_overall", evalResult.overall),
            ]);
          });
        } catch {
          // Scoring failures must never affect the main response path.
        }
      })();
    }

    return c.json(ok({
      data,
      insight: {
        overall_severity: insight.overall_severity,
        domain_change_pct: insight.domain_change_pct,
        not_indexed_change_pct: insight.not_indexed_change_pct,
        worsening_paths: insight.worsening_paths,
        improving_paths: insight.improving_paths,
        stable_paths: insight.stable_paths,
        summary_text: insight.summary_text,
      },
      markdown: insight.markdown,
    }));
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error("Crawled-not-indexed analysis failed:", msg);
    return c.json(fail("Crawled-not-indexed analysis failed"), 500);
  }
});

// GET /llm-usage — LLM cost/latency monitoring
pipelineRoute.get("/llm-usage", async (c) => {
  if (!hasSupabase()) {
    return c.json(fail("Supabase not configured"), 503);
  }

  const daysParam = c.req.query("days") ?? "30";
  const days = Math.min(Math.max(parseInt(daysParam, 10) || 30, 1), 90);
  const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();

  try {
    interface UsageRow {
      readonly endpoint: string;
      readonly model: string;
      readonly input_tokens: number;
      readonly output_tokens: number;
      readonly latency_ms: number;
      readonly created_at: string;
    }

    const rows = await supabaseSelect<UsageRow>(
      "llm_usage",
      `?select=endpoint,model,input_tokens,output_tokens,latency_ms,created_at&created_at=gte.${since}&order=created_at.desc&limit=1000`,
    );

    // Aggregate by endpoint + model
    const groups = new Map<string, { calls: number; input_tokens: number; output_tokens: number; total_latency_ms: number }>();
    for (const row of rows) {
      const key = `${row.endpoint}::${row.model}`;
      const g = groups.get(key) ?? { calls: 0, input_tokens: 0, output_tokens: 0, total_latency_ms: 0 };
      g.calls += 1;
      g.input_tokens += row.input_tokens;
      g.output_tokens += row.output_tokens;
      g.total_latency_ms += row.latency_ms;
      groups.set(key, g);
    }

    const summary = [...groups.entries()].map(([key, g]) => {
      const [endpoint, model] = key.split("::");
      return {
        endpoint,
        model,
        calls: g.calls,
        input_tokens: g.input_tokens,
        output_tokens: g.output_tokens,
        avg_latency_ms: Math.round(g.total_latency_ms / g.calls),
      };
    });

    return c.json(ok({ days, total_calls: rows.length, summary }));
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json(fail(`LLM usage query failed: ${msg}`), 500);
  }
});

/**
 * GET /metrics/trends — Timeseries anomaly detection across snapshots.
 *
 * Query params:
 *   metric  — optional metric name filter (e.g. "CTR", "曝光")
 *   weeks   — number of recent snapshots to analyze (default 8, max 12)
 */
pipelineRoute.get("/metrics/trends", async (c) => {
  if (!supabaseSnapshotStore) {
    return c.json(fail("Supabase not configured"), 503);
  }

  const metricFilter = c.req.query("metric") ?? "";
  const weeksParam = c.req.query("weeks") ?? "8";
  const weeks = Math.min(Math.max(parseInt(weeksParam, 10) || 8, 4), 12);

  try {
    const allSnapshots = await supabaseSnapshotStore.list();
    const sorted = [...allSnapshots]
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
      .slice(-weeks);

    if (sorted.length < 4) {
      return c.json(ok({
        message: `需要至少 4 週快照才能進行趨勢分析（目前 ${sorted.length} 筆）`,
        snapshots_count: sorted.length,
        anomalies: [],
      }));
    }

    // Load full snapshots with metrics
    const fullSnapshots = await Promise.all(
      sorted.map((s) => supabaseSnapshotStore!.getById(s.id)),
    );

    // Build timeseries per metric
    const metricsTimeseries: Record<string, TimeseriesPoint[]> = {};

    for (const snapshot of fullSnapshots) {
      if (!snapshot) continue;
      const metrics = snapshot.metrics as Record<string, MetricData>;

      for (const [name, data] of Object.entries(metrics)) {
        if (metricFilter && name !== metricFilter) continue;
        if (data.latest == null) continue;

        if (!metricsTimeseries[name]) {
          metricsTimeseries[name] = [];
        }
        metricsTimeseries[name].push({
          date: snapshot.created_at,
          value: data.latest,
        });
      }
    }

    const anomalies = analyzeAllMetrics(metricsTimeseries);

    return c.json(ok({
      snapshots_count: sorted.length,
      metrics_analyzed: Object.keys(metricsTimeseries).length,
      anomalies,
    }));
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json(fail(`Trend analysis failed: ${msg}`), 500);
  }
});
