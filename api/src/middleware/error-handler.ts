import type { ErrorHandler } from "hono";
import { fail } from "../schemas/api-response.js";

export const errorHandler: ErrorHandler = (err, c) => {
  console.error(`Unhandled error: ${err.message}`);

  // Do not leak stack trace to client
  return c.json(fail("Internal server error"), 500);
};
