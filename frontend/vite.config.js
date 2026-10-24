import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import publicPages from "./scripts/public-pages.mjs";

const backend = process.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

export default defineConfig({
  // publicPages: a copy of index.html per public page, with its title and link-preview tags.
  plugins: [react(), publicPages()],
  server: {
    port: 5173,
    proxy: {
      "/api": backend,
      "/django-admin": backend,
      "/static": backend,
      "/robots.txt": backend,
      "/sitemap.xml": backend,
    },
  },
  preview: {
    port: 4173,
    // Uploaded files have no /media URL: they come from the access-checked /api/files/ links.
    proxy: { "/api": backend },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("katex")) return "katex";
          if (/node_modules\/(react|react-dom|scheduler|react-router|react-router-dom|cookie|set-cookie-parser)\//.test(id)) return "react";
          // Everything else (the Markdown/maths pipeline) is split automatically and
          // only loaded by the pages that render lessons.
          return undefined;
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    // scripts/: the build's own checks (check-bundle.mjs).
    include: ["src/**/*.test.{js,jsx}", "scripts/**/*.test.js"],
    setupFiles: ["./src/test-setup.js"],
  },
});
