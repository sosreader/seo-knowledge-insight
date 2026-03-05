import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { join } from "node:path";
import { paths } from "../config.js";
import type { PipelineRunResult } from "../schemas/pipeline.js";

const execFileAsync = promisify(execFile);

const PYTHON = "python3";
const DEFAULT_TIMEOUT_MS = 120_000;

export async function execPython(
  scriptName: string,
  args: readonly string[] = [],
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<PipelineRunResult> {
  const scriptPath = join(paths.scriptsDir, scriptName);
  const start = Date.now();

  try {
    const { stdout, stderr } = await execFileAsync(
      PYTHON,
      [scriptPath, ...args],
      {
        cwd: paths.rootDir,
        timeout: timeoutMs,
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
      }
    );

    // stdout is structured output (JSON/text); stderr carries logging only.
    // Keep them separate so JSON.parse on output works correctly.
    const output = stdout.trim();
    if (stderr.trim()) {
      console.debug("[pipeline-runner] stderr:", stderr.trim());
    }
    return {
      success: true,
      output,
      duration_ms: Date.now() - start,
    };
  } catch (err: unknown) {
    const duration_ms = Date.now() - start;
    const msg = err instanceof Error ? err.message : "Unknown error";

    if (msg.includes("TIMEOUT") || msg.includes("timed out")) {
      return { success: false, output: "Script timed out", duration_ms };
    }

    // child_process error includes stdout/stderr
    const cpErr = err as { stdout?: string; stderr?: string };
    const output = [cpErr.stdout, cpErr.stderr, msg]
      .filter(Boolean)
      .join("\n")
      .trim();

    return { success: false, output, duration_ms };
  }
}

export async function execQaTools(
  subcommand: string,
  args: readonly string[] = []
): Promise<PipelineRunResult> {
  return execPython("qa_tools.py", [subcommand, ...args], 30_000);
}
