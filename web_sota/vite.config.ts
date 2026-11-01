import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const backendTarget =
  process.env.VITE_API_TARGET || "http://127.0.0.1:11074";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: Number(process.env.VITE_PORT) || 11251,
    proxy: {
      "/api": { target: backendTarget, changeOrigin: true },
      "/mcp": { target: backendTarget, changeOrigin: true },
      "/health": { target: backendTarget, changeOrigin: true },
    },
  },
});
