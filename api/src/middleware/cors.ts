import { cors } from "hono/cors";
import { config } from "../config.js";

export const corsMiddleware = cors({
  origin: config.CORS_ORIGINS,
  allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowHeaders: ["Content-Type", "X-API-Key"],
  maxAge: 86400,
});
