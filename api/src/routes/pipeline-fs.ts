/**
 * Pipeline file-system helpers — read meetings, count files, build status,
 * find unprocessed docs, read fetch logs, parse frontmatter, snapshot CRUD.
 *
 * Extracted from pipeline.ts to keep route file under 400 lines.
 */
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";
import { paths } from "../config.js";
import { qaStore } from "../store/qa-store.js";
import { hasSupabase } from "../store/supabase-client.js";
import type {
  MeetingEntry,
  UnprocessedItem,
  FetchLogEntry,
  FetchLogsResponse,
  PipelineStepStatus,
  PipelineStatusResponse,
  SourceDocEntry,
  MetricsSnapshotMeta,
} from "../schemas/pipeline.js";

const meetingEntrySchema = z.object({
  title: z.string(),
  id: z.string(),
  created_time: z.string(),
  last_edited_time: z.string(),
  url: z.string(),
  json_file: z.string(),
  md_file: z.string(),
  status: z.string().optional(),
});

export const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const FETCH_LOG_PATTERN = /^fetch_\d{4}-\d{2}-\d{2}\.jsonl$/;
export const SAFE_FILENAME_RE = /^[a-zA-Z0-9._\u4e00-\u9fff-]+\.md$/;
export const SNAPSHOT_ID_RE = /^[0-9]{8}-[0-9]{6}$/;

// --- Meetings ---

export function readMeetingsIndex(): readonly MeetingEntry[] {
  const indexPath = join(paths.rawDataDir, "meetings_index.json");
  if (!existsSync(indexPath)) return [];

  try {
    const raw = readFileSync(indexPath, "utf-8");
    const parsed = z.array(meetingEntrySchema).safeParse(JSON.parse(raw));
    if (!parsed.success) return [];
    return parsed.data.map((e) => ({
      ...e,
      status: e.status ?? "fetched",
    }));
  } catch {
    return [];
  }
}

// --- Counting helpers ---

function countMdFiles(dir: string): number {
  if (!existsSync(dir)) return 0;
  return readdirSync(dir).filter((f) => f.endsWith(".md")).length;
}

function countQAPerMeeting(): number {
  const dir = join(paths.outputDir, "qa_per_meeting");
  if (!existsSync(dir)) return 0;
  return readdirSync(dir).filter((f) => f.endsWith("_qa.json")).length;
}

function countQAFinal(): number {
  if (!existsSync(paths.qaJsonPath)) return 0;
  try {
    const raw = readFileSync(paths.qaJsonPath, "utf-8");
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (typeof parsed.total_count === "number") return parsed.total_count;
    if (Array.isArray(parsed.qa_database)) return parsed.qa_database.length;
    if (Array.isArray(parsed)) return parsed.length;
    return 0;
  } catch {
    return 0;
  }
}

// --- Pipeline status ---

function buildPipelineStatusFromStore(): PipelineStatusResponse {
  const collections = qaStore.collections();
  const totalCount = qaStore.count;

  const collectionCountMap = new Map(
    collections.map((c) => [c.source_collection, c.count]),
  );

  const notionCount = collectionCountMap.get("notion-seo-meetings") ?? collectionCountMap.get("seo-meetings") ?? 0;
  const mediumCount =
    (collectionCountMap.get("medium-genehong") ?? 0) +
    (collectionCountMap.get("genehong-medium") ?? 0);
  const ithelpCount = collectionCountMap.get("ithelp-gsc-kpi") ?? collectionCountMap.get("ithelp-sc-kpi") ?? 0;
  const googleCount = collectionCountMap.get("google-case-studies") ?? 0;
  const ahrefsCount = collectionCountMap.get("ahrefs-blog") ?? 0;
  const sejCount = collectionCountMap.get("sej") ?? 0;
  const growthmemoCount = collectionCountMap.get("growth-memo") ?? 0;
  const googleBlogCount = collectionCountMap.get("google-search-central") ?? 0;
  const webdevCount = collectionCountMap.get("web-dev") ?? 0;
  const screamingfrogCount = collectionCountMap.get("screaming-frog") ?? 0;

  const steps: PipelineStepStatus[] = [
    {
      name: "fetch-notion",
      label: "Notion 擷取",
      count: notionCount,
      detail: `${notionCount} 筆 Q&A（來自 Notion 會議）`,
    },
    {
      name: "fetch-medium",
      label: "Medium 擷取",
      count: mediumCount,
      detail: `${mediumCount} 筆 Q&A（來自 Medium）`,
    },
    {
      name: "fetch-ithelp",
      label: "iThome 擷取",
      count: ithelpCount,
      detail: `${ithelpCount} 筆 Q&A（來自 iThome）`,
    },
    {
      name: "fetch-google",
      label: "Google 個案擷取",
      count: googleCount,
      detail: `${googleCount} 筆 Q&A（來自 Google Cases）`,
    },
    {
      name: "fetch-ahrefs",
      label: "Ahrefs 擷取",
      count: ahrefsCount,
      detail: `${ahrefsCount} 筆 Q&A（來自 Ahrefs Blog）`,
    },
    {
      name: "fetch-sej",
      label: "SEJ 擷取",
      count: sejCount,
      detail: `${sejCount} 筆 Q&A（來自 Search Engine Journal）`,
    },
    {
      name: "fetch-growthmemo",
      label: "Growth Memo 擷取",
      count: growthmemoCount,
      detail: `${growthmemoCount} 筆 Q&A（來自 Growth Memo）`,
    },
    {
      name: "fetch-google-blog",
      label: "Google Blog 擷取",
      count: googleBlogCount,
      detail: `${googleBlogCount} 筆 Q&A（來自 Google Search Central Blog）`,
    },
    {
      name: "fetch-webdev",
      label: "Web.dev 擷取",
      count: webdevCount,
      detail: `${webdevCount} 筆 Q&A（來自 web.dev）`,
    },
    {
      name: "fetch-screaming-frog",
      label: "Screaming Frog 擷取",
      count: screamingfrogCount,
      detail: `${screamingfrogCount} 筆 Q&A（來自 Screaming Frog Blog）`,
    },
    {
      name: "extract-qa",
      label: "Q&A 萃取",
      count: totalCount,
      detail: `共 ${totalCount} 筆 Q&A（已萃取）`,
    },
    {
      name: "dedupe-classify",
      label: "去重 + 分類",
      count: totalCount,
      detail: `${totalCount} 筆 Q&A（去重 + 分類後）`,
    },
  ];

  return { steps };
}

function buildPipelineStatusFromFiles(): PipelineStatusResponse {
  const meetings = readMeetingsIndex();
  const mdDir = join(paths.rawDataDir, "markdown");
  const mdCount = countMdFiles(mdDir);

  const mediumMdCount = countMdFiles(paths.rawMediumMdDir);
  const ithelpMdCount = countMdFiles(paths.rawIthelpMdDir);
  const googleMdCount = countMdFiles(paths.rawGoogleCasesMdDir);
  const ahrefsMdCount = countMdFiles(paths.rawAhrefsMdDir);
  const sejMdCount = countMdFiles(paths.rawSejMdDir);
  const growthmemoMdCount = countMdFiles(paths.rawGrowthmemoMdDir);
  const googleBlogMdCount = countMdFiles(paths.rawGoogleBlogMdDir);
  const webdevMdCount = countMdFiles(paths.rawWebdevMdDir);
  const screamingfrogMdCount = countMdFiles(paths.rawScreamingfrogMdDir);

  const totalExtracted = countQAPerMeeting();
  const totalMd = mdCount + mediumMdCount + ithelpMdCount + googleMdCount + ahrefsMdCount + sejMdCount + growthmemoMdCount + googleBlogMdCount + webdevMdCount + screamingfrogMdCount;
  const finalCount = countQAFinal();

  const steps: PipelineStepStatus[] = [
    {
      name: "fetch-notion",
      label: "Notion 擷取",
      count: mdCount,
      detail: `${meetings.length} 筆會議，${mdCount} 份 Markdown`,
    },
    {
      name: "fetch-medium",
      label: "Medium 擷取",
      count: mediumMdCount,
      detail: `${mediumMdCount} 篇文章`,
    },
    {
      name: "fetch-ithelp",
      label: "iThome 擷取",
      count: ithelpMdCount,
      detail: `${ithelpMdCount} 篇文章`,
    },
    {
      name: "fetch-google",
      label: "Google 個案擷取",
      count: googleMdCount,
      detail: `${googleMdCount} 篇個案研究`,
    },
    {
      name: "fetch-ahrefs",
      label: "Ahrefs 擷取",
      count: ahrefsMdCount,
      detail: `${ahrefsMdCount} 篇文章`,
    },
    {
      name: "fetch-sej",
      label: "SEJ 擷取",
      count: sejMdCount,
      detail: `${sejMdCount} 篇文章`,
    },
    {
      name: "fetch-growthmemo",
      label: "Growth Memo 擷取",
      count: growthmemoMdCount,
      detail: `${growthmemoMdCount} 篇文章`,
    },
    {
      name: "fetch-google-blog",
      label: "Google Blog 擷取",
      count: googleBlogMdCount,
      detail: `${googleBlogMdCount} 篇官方公告`,
    },
    {
      name: "fetch-webdev",
      label: "Web.dev 擷取",
      count: webdevMdCount,
      detail: `${webdevMdCount} 篇文章`,
    },
    {
      name: "fetch-screaming-frog",
      label: "Screaming Frog 擷取",
      count: screamingfrogMdCount,
      detail: `${screamingfrogMdCount} 篇文章`,
    },
    {
      name: "extract-qa",
      label: "Q&A 萃取",
      count: totalExtracted,
      detail: `已萃取 ${totalExtracted} / ${totalMd} 份`,
    },
    {
      name: "dedupe-classify",
      label: "去重 + 分類",
      count: finalCount,
      detail: `${finalCount} 筆 Q&A（去重 + 分類後）`,
    },
  ];

  return { steps };
}

export function buildPipelineStatus(): PipelineStatusResponse {
  if (hasSupabase() && qaStore.loaded) {
    return buildPipelineStatusFromStore();
  }
  return buildPipelineStatusFromFiles();
}

// --- Unprocessed ---

export function findUnprocessed(): readonly UnprocessedItem[] {
  const qaDir = join(paths.outputDir, "qa_per_meeting");
  const sources: ReadonlyArray<{
    readonly mdDir: string;
    readonly qaDir: string;
    readonly sourceCollection: string;
  }> = [
    {
      mdDir: join(paths.rawDataDir, "markdown"),
      qaDir,
      sourceCollection: "seo-meetings",
    },
    {
      mdDir: paths.rawMediumMdDir,
      qaDir,
      sourceCollection: "genehong-medium",
    },
    {
      mdDir: paths.rawIthelpMdDir,
      qaDir,
      sourceCollection: "ithelp-sc-kpi",
    },
    {
      mdDir: paths.rawGoogleCasesMdDir,
      qaDir,
      sourceCollection: "google-case-studies",
    },
  ];

  const results: UnprocessedItem[] = [];

  for (const { mdDir, qaDir: qd, sourceCollection } of sources) {
    if (!existsSync(mdDir)) continue;

    const mdFiles = readdirSync(mdDir).filter((f) => f.endsWith(".md"));
    const processedSet = new Set(
      existsSync(qd)
        ? readdirSync(qd)
            .filter((f) => f.endsWith("_qa.json"))
            .map((f) => f.replace(/_qa\.json$/, ".md"))
        : []
    );

    for (const f of mdFiles) {
      if (!processedSet.has(f)) {
        const fm = parseArticleFrontmatter(join(mdDir, f));
        results.push({
          file: f,
          title: fm.title ?? f.replace(/\.md$/, "").replace(/_/g, " "),
          source_collection: sourceCollection,
        });
      }
    }
  }

  return results;
}

// --- Fetch logs ---

export function readFetchLogs(limit = 200): FetchLogsResponse {
  const logsDir = paths.fetchLogsDir;
  if (!existsSync(logsDir)) return { files: [], entries: [], total: 0 };

  const files = readdirSync(logsDir)
    .filter((f) => FETCH_LOG_PATTERN.test(f))
    .sort()
    .reverse();

  const entries: FetchLogEntry[] = [];

  for (const file of files) {
    if (entries.length >= limit) break;
    try {
      const content = readFileSync(join(logsDir, file), "utf-8");
      const lines = content.trim().split("\n").filter(Boolean);
      for (const line of lines) {
        if (entries.length >= limit) break;
        entries.push(JSON.parse(line) as FetchLogEntry);
      }
    } catch {
      // skip malformed log files
    }
  }

  return { files, entries, total: entries.length };
}

// --- Article frontmatter ---

export function parseArticleFrontmatter(filePath: string): { title: string | null; publishedAt: string | null; sourceUrl: string | null } {
  let title: string | null = null;
  let publishedAt: string | null = null;
  let sourceUrl: string | null = null;
  try {
    const content = readFileSync(filePath, "utf-8");
    const lines = content.split("\n").slice(0, 10);
    for (const line of lines) {
      const h1Match = line.match(/^#\s+(.+)/);
      if (h1Match && !title) title = h1Match[1].trim();

      const dateMatch = line.match(/\*\*發佈日期\*\*:\s*(\d{4}-\d{2}-\d{2})/);
      if (dateMatch) publishedAt = `${dateMatch[1]}T00:00:00.000Z`;

      const urlMatch = line.match(/\*\*來源 URL\*\*:\s*(https?:\/\/\S+)/);
      if (urlMatch) sourceUrl = urlMatch[1];
    }
  } catch {
    // ignore read errors
  }
  return { title, publishedAt, sourceUrl };
}

// --- Collection → Directory mapping ---

export function getCollectionDirMap(): Readonly<Record<string, { dir: string; sourceType: "meeting" | "article" }>> {
  return {
    "seo-meetings": { dir: join(paths.rawDataDir, "markdown"), sourceType: "meeting" },
    "genehong-medium": { dir: paths.rawMediumMdDir, sourceType: "article" },
    "ithelp-sc-kpi": { dir: paths.rawIthelpMdDir, sourceType: "article" },
    "google-case-studies": { dir: paths.rawGoogleCasesMdDir, sourceType: "article" },
    "ahrefs-blog": { dir: paths.rawAhrefsMdDir, sourceType: "article" },
    "sej": { dir: paths.rawSejMdDir, sourceType: "article" },
    "growth-memo": { dir: paths.rawGrowthmemoMdDir, sourceType: "article" },
  };
}

// --- Source docs ---

export function buildSourceDocs(): readonly SourceDocEntry[] {
  const meetings = readMeetingsIndex();
  const meetingsByMd = new Map(meetings.map((m) => [m.md_file.replace(/^markdown\//, ""), m]));

  const qaPerMeetingDir = join(paths.outputDir, "qa_per_meeting");
  const processedSet = new Set(
    existsSync(qaPerMeetingDir)
      ? readdirSync(qaPerMeetingDir)
          .filter((f) => f.endsWith("_qa.json"))
          .map((f) => f.replace(/_qa\.json$/, ".md"))
      : []
  );

  const results: SourceDocEntry[] = [];

  for (const [collection, { dir, sourceType }] of Object.entries(getCollectionDirMap())) {
    if (!existsSync(dir)) continue;

    const mdFiles = readdirSync(dir).filter((f) => f.endsWith(".md"));

    for (const file of mdFiles) {
      const filePath = join(dir, file);
      let stat;
      try {
        stat = statSync(filePath);
      } catch {
        continue;
      }

      const meeting = sourceType === "meeting" ? meetingsByMd.get(file) : undefined;

      let title: string;
      let createdTime: string;
      let sourceUrl: string;
      if (meeting) {
        title = meeting.title;
        createdTime = meeting.created_time;
        sourceUrl = meeting.url;
      } else {
        const fm = parseArticleFrontmatter(filePath);
        title = fm.title ?? file.replace(/\.md$/, "").replace(/[-_]/g, " ");
        createdTime = fm.publishedAt ?? stat.mtime.toISOString();
        sourceUrl = fm.sourceUrl ?? "";
      }

      results.push({
        file,
        title,
        source_type: sourceType,
        source_collection: collection,
        source_url: sourceUrl,
        created_time: createdTime,
        size_bytes: stat.size,
        is_processed: processedSet.has(file),
      });
    }
  }

  return results;
}

// --- Snapshot helpers ---

export function generateSnapshotId(): string {
  const now = new Date();
  const pad2 = (n: number) => String(n).padStart(2, "0");
  const date =
    String(now.getFullYear()) +
    pad2(now.getMonth() + 1) +
    pad2(now.getDate());
  const time =
    pad2(now.getHours()) +
    pad2(now.getMinutes()) +
    pad2(now.getSeconds());
  return `${date}-${time}`;
}

export function listSnapshots(): readonly MetricsSnapshotMeta[] {
  const dir = paths.metricsSnapshotsDir;
  if (!existsSync(dir)) return [];

  const files = readdirSync(dir)
    .filter((f) => /^[0-9]{8}-[0-9]{6}\.json$/.test(f))
    .sort()
    .reverse();

  const results: MetricsSnapshotMeta[] = [];
  for (const file of files) {
    try {
      const raw = readFileSync(join(dir, file), "utf-8");
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      results.push({
        id: String(parsed.id ?? ""),
        created_at: String(parsed.created_at ?? ""),
        label: String(parsed.label ?? ""),
        source: String(parsed.source ?? ""),
        tab: String(parsed.tab ?? ""),
        weeks: Number(parsed.weeks ?? 2),
      });
    } catch {
      // skip malformed snapshot files
    }
  }
  return results;
}
