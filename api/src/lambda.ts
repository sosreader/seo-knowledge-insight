import { handle } from "hono/aws-lambda";
import { app, initStores } from "./index.js";
import { flushLaminar } from "./utils/observability.js";

const ready = initStores().catch((err) => {
  console.error("Lambda cold start initStores failed:", err);
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
