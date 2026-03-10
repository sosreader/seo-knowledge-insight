#!/usr/bin/env npx tsx
/**
 * feedback-to-golden — Convert negative feedback to golden dataset candidates.
 *
 * Reads Supabase `learnings` records with feedback = "not_relevant" or
 * feedback_category in ["wrong_answer", "wrong_source"], and outputs
 * candidate entries for eval/golden_retrieval.json.
 *
 * Usage:
 *   npx tsx scripts/feedback-to-golden.ts
 *   npx tsx scripts/feedback-to-golden.ts --output eval/golden_candidates.json
 */

import { config as dotenvConfig } from "dotenv";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { writeFileSync } from "node:fs";
import { parseArgs } from "node:util";

const __dir = dirname(fileURLToPath(import.meta.url));
dotenvConfig({ path: resolve(__dir, "../.env") });
dotenvConfig({ path: resolve(__dir, "../../.env") });

const SUPABASE_URL = process.env.SUPABASE_URL?.replace(/\/$/, "") ?? "";
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY ?? "";

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error("SUPABASE_URL and SUPABASE_ANON_KEY required.");
  process.exit(1);
}

const { values } = parseArgs({
  options: {
    output: { type: "string", default: resolve(__dir, "../../eval/golden_candidates.json") },
  },
});

interface LearningRecord {
  readonly query: string;
  readonly qa_id: string;
  readonly feedback: string;
  readonly feedback_category?: string;
  readonly top_score?: number;
  readonly created_at: string;
}

async function fetchNegativeFeedback(): Promise<readonly LearningRecord[]> {
  const url =
    `${SUPABASE_URL}/rest/v1/learnings` +
    `?select=query,qa_id,feedback,feedback_category,top_score,created_at` +
    `&or=(feedback.eq.not_relevant,feedback_category.in.("wrong_answer","wrong_source","outdated"))` +
    `&order=created_at.desc` +
    `&limit=100`;

  const resp = await fetch(url, {
    headers: {
      apikey: SUPABASE_ANON_KEY,
      Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
    },
  });

  if (!resp.ok) {
    console.error(`Supabase fetch failed: ${resp.status} ${await resp.text()}`);
    return [];
  }

  return resp.json() as Promise<LearningRecord[]>;
}

function toGoldenCandidate(record: LearningRecord) {
  return {
    query: record.query,
    scenario: `[feedback] ${record.feedback}${record.feedback_category ? ` / ${record.feedback_category}` : ""}`,
    expected_keywords: [],
    expected_categories: [],
    _source: "feedback",
    _qa_id: record.qa_id,
    _top_score: record.top_score,
    _feedback_date: record.created_at,
    _needs_review: true,
  };
}

async function main() {
  const records = await fetchNegativeFeedback();
  console.log(`Found ${records.length} negative feedback records.`);

  if (records.length === 0) {
    console.log("No candidates to generate.");
    return;
  }

  const candidates = records.map(toGoldenCandidate);
  const outputPath = values.output!;
  writeFileSync(outputPath, JSON.stringify(candidates, null, 2) + "\n", "utf-8");
  console.log(`Wrote ${candidates.length} candidates to ${outputPath}`);
  console.log("Review and manually merge approved cases into eval/golden_retrieval.json.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
