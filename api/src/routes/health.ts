import { Hono } from "hono";
import { resolveHealthCapabilities } from "../utils/capabilities.js";

export const healthRoute = new Hono();

healthRoute.get("/health", (c) => {
  return c.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    version: "2.2.0",
    capabilities: resolveHealthCapabilities(c.req.header("user-agent")),
  });
});
