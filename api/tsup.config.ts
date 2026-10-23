import { defineConfig } from "tsup";

export default defineConfig([
  // Node.js server build (default, external node_modules)
  {
    // cli：K8s CronJob 用（node dist/cli.js update-freshness），與 index 共用同一個 image
    entry: { index: "src/index.ts", cli: "src/cli.ts" },
    format: ["esm"],
    target: "node22",
    outDir: "dist",
    clean: true,
    sourcemap: true,
    dts: false,
    splitting: false,
  },
  // Lambda build (self-contained ESM bundle)
  {
    entry: { lambda: "src/lambda.ts" },
    format: ["esm"],
    target: "node22",
    outDir: "dist-lambda",
    clean: true,
    sourcemap: false,
    dts: false,
    splitting: false,
    noExternal: [/.*/],
    // Exclude Laminar + OpenTelemetry from Lambda bundle — they can't be
    // bundled (30+ transitive deps with CJS/dynamic-require issues).
    // observability.ts skips init on Lambda via AWS_LAMBDA_FUNCTION_NAME check.
    external: ["@lmnr-ai/lmnr", /^@opentelemetry\//],
    // Provide global `require` for CJS deps (e.g. dotenv) bundled in ESM
    banner: {
      js: [
        "import { createRequire as __cr } from 'node:module';",
        "const require = __cr(import.meta.url);",
      ].join(""),
    },
  },
]);
