import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    assetsDir: "assets",
    sourcemap: false,
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      }
    }
  },
  // ✅ This makes SPA routing work under FastAPI when served as static
  base: "/",
});
