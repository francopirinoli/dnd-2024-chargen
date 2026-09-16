import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "node:path";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "D&D 2024 Character Creator",
        short_name: "D&D Creator",
        description: "Create D&D 2024 characters offline-capable",
        theme_color: "#0E0E11",
        background_color: "#0E0E11",
        display: "standalone",
        icons: [],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
        // Sheet background PNGs are large (>2 MB each) and only needed
        // by the printable sheet view — exclude from precache.
        globIgnores: ["**/pdf_template/**"],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true,            // bind 0.0.0.0 so forwarded ports work
    port: 5173,
    strictPort: true,
    hmr: process.env.CODESPACES
      ? {
          clientPort: 443,
          protocol: "wss",
        }
      : undefined,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
