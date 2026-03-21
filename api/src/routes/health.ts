import { Hono } from "hono";
import { resolveHealthCapabilities } from "../utils/capabilities.js";
import { API_VERSION } from "../openapi.js";

export const healthRoute = new Hono();

healthRoute.get("/health", (c) => {
  return c.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    version: API_VERSION,
    capabilities: resolveHealthCapabilities(c.req.header("user-agent")),
  });
});
