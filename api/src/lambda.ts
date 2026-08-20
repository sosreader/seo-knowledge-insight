import { handle } from "hono/aws-lambda";
import { app, initCore } from "./index.js";
import { flushLaminar } from "./utils/observability.js";

// Cold start 只做便宜的 initCore()（Laminar + capability log）。
// QA store／synonyms 改由 route middleware 在需要時才載入，
// 避免用不到 QA 的 route 被 25k 筆 qa_items 的分頁查詢擋住而超時。
const ready = initCore().catch((err) => {
  console.error("Lambda cold start initCore failed:", err);
});

// Use buffered Lambda responses for compatibility with the current
// Function URL runtime configuration in production.
const honoHandler = handle(app);

/**
 * Lambda entry point.
 *
 * Uses the buffered handler to keep non-streaming endpoints stable in Lambda.
 */
export const handler: typeof honoHandler = async (event, ...rest) => {
  await ready;
  const response = await honoHandler(event, ...rest);
  await flushLaminar().catch((err) =>
    console.warn("Laminar flush failed:", err),
  );
  return response;
};
