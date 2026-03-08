import { handle, streamHandle } from "hono/aws-lambda";
import { app, initStores } from "./index.js";
import { flushLaminar } from "./utils/observability.js";

const ready = initStores().catch((err) => {
  console.error("Lambda cold start initStores failed:", err);
});

/**
 * Buffered handler — used for non-streaming requests.
 * streamHandle() also works for buffered responses when
 * Lambda invoke mode is RESPONSE_STREAM.
 */
const honoHandler = streamHandle(app);

/**
 * Lambda entry point.
 *
 * Uses streamHandle() to support both buffered and streaming responses.
 * For streaming SSE endpoints (e.g. /chat/stream), Lambda Function URL
 * must be configured with InvokeMode: RESPONSE_STREAM.
 * Non-streaming endpoints continue to work normally via streamHandle().
 */
export const handler: typeof honoHandler = async (event, ...rest) => {
  await ready;
  const response = await honoHandler(event, ...rest);
  await flushLaminar().catch((err) => console.warn("Laminar flush failed:", err));
  return response;
};
