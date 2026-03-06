/**
 * Laminar observability — initializes tracing for the Hono API server.
 *
 * All SDK calls are wrapped in try/catch so Laminar failures never
 * affect the main application flow.
 */

import { config } from "../config.js";

let initialized = false;

/**
 * Initialize Laminar tracing.  Safe to call multiple times.
 * Silently skips when LMNR_PROJECT_API_KEY is empty.
 */
export async function initLaminar(): Promise<void> {
  if (initialized) return;

  // Lambda bundles can't resolve @opentelemetry/resources (transitive dep of @lmnr-ai/lmnr).
  // Skip Laminar entirely on Lambda to avoid confusing partial-init errors.
  if (process.env.AWS_LAMBDA_FUNCTION_NAME) {
    return;
  }

  const apiKey = config.LMNR_PROJECT_API_KEY;
  if (!apiKey) {
    console.log(
      "LMNR_PROJECT_API_KEY unset — skipping Laminar init (traces won't be sent)",
    );
    return;
  }

  try {
    const { Laminar } = await import("@lmnr-ai/lmnr");
    const OpenAI = (await import("openai")).default;
    Laminar.initialize({
      projectApiKey: apiKey,
      instrumentModules: { OpenAI },
    });
    initialized = true;
    console.log("Laminar initialized for Hono API server");
  } catch (err) {
    console.warn("Laminar.initialize() failed:", (err as Error).message ?? String(err));
  }
}

/**
 * Wrap an async function as a named Laminar span.
 * When Laminar is not initialized, returns the function unchanged.
 *
 * Note: observe() checks `initialized` at *call time*, not at wrap time,
 * because initLaminar() is async and runs after module-level imports.
 */
export function observe<TArgs extends unknown[], TReturn>(
  name: string,
  fn: (...args: TArgs) => Promise<TReturn>,
): (...args: TArgs) => Promise<TReturn> {
  return async (...args: TArgs): Promise<TReturn> => {
    if (!initialized) return fn(...args);
    try {
      const { observe: lmnrObserve } = await import("@lmnr-ai/lmnr");
      return await lmnrObserve({ name }, fn, ...args);
    } catch {
      return fn(...args);
    }
  };
}

/**
 * Flush pending spans before shutdown.  Safe to call when not initialized.
 */
export async function flushLaminar(): Promise<void> {
  if (!initialized) return;
  try {
    const { Laminar } = await import("@lmnr-ai/lmnr");
    await Laminar.flush();
  } catch (err) {
    console.warn("Laminar.flush() failed:", (err as Error).message ?? String(err));
  }
}

/** Whether Laminar has been successfully initialized. */
export function isLaminarInitialized(): boolean {
  return initialized;
}

/**
 * Reset initialization state.  For testing only.
 */
export function _resetForTest(): void {
  initialized = false;
}
