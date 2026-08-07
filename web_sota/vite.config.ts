import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 11075,
    proxy: {
      "/api": { target: "http://127.0.0.1:11074", changeOrigin: true },
      "/mcp": { target: "http://127.0.0.1:11074", changeOrigin: true },
    },
  },
});
