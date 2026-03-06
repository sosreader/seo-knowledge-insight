import { defineConfig } from "tsup";

export default defineConfig([
  // Node.js server build (default, external node_modules)
  {
    entry: { index: "src/index.ts" },
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
    // Provide global `require` for CJS deps (e.g. dotenv) bundled in ESM
    banner: {
      js: [
        "import { createRequire as __cr } from 'node:module';",
        "const require = __cr(import.meta.url);",
      ].join(""),
    },
  },
]);
