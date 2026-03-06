import { handle } from "hono/aws-lambda";
import { app, initStores } from "./index.js";
import { flushLaminar } from "./utils/observability.js";

const ready = initStores();

const honoHandler = handle(app);

export const handler: typeof honoHandler = async (event, context) => {
  await ready;
  const response = await honoHandler(event, context);
  await flushLaminar().catch((err) => console.warn("Laminar flush failed:", err));
  return response;
};
