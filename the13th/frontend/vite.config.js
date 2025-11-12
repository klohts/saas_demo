import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/", // ensures assets resolve correctly
  build: {
    outDir: "dist",
    assetsDir: "assets",
  },
});
