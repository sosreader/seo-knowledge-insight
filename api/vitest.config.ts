import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["tests/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      exclude: ["src/**/*.d.ts", "src/lambda.ts", "src/index.ts"],
      thresholds: {
        lines: 79,
        functions: 80,
        branches: 60,
        statements: 78,
      },
    },
  },
});
