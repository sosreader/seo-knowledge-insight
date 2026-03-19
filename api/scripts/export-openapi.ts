/**
 * Export OpenAPI spec to JSON file or stdout.
 *
 * Usage:
 *   tsx scripts/export-openapi.ts [--pretty] [output-path]
 */
import { writeFileSync } from "node:fs";
import { buildOpenAPISpec } from "../src/openapi.js";

const args = process.argv.slice(2);
const pretty = args.includes("--pretty");
const outPath = args.find((a) => a !== "--pretty");

const spec = buildOpenAPISpec();
const json = pretty ? JSON.stringify(spec, null, 2) : JSON.stringify(spec);

if (outPath) {
  writeFileSync(outPath, json + "\n", "utf-8");
  console.log(`Wrote ${outPath} (${json.length} bytes)`);
} else {
  process.stdout.write(json + "\n");
}
