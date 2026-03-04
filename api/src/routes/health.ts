import { Hono } from "hono";

export const healthRoute = new Hono();

healthRoute.get("/health", (c) => {
  return c.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    version: "2.2.0",
  });
});
