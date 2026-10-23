// CLI 進入點（tsup entry → dist/cli.js）。邏輯在 jobs/cli.ts，這裡只轉 exit code，所以不納入覆蓋率。
import { runCli } from "./jobs/cli.js";

process.exitCode = await runCli(process.argv.slice(2));
