import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";

export default defineConfig({
  plugins: [react()],
  css: {
    postcss: {
      plugins: [
        // ✅ Order matters. No postcss-import allowed.
        tailwindcss(),
        autoprefixer()
      ]
    },
    preprocessorOptions: {
      css: {
        // ✅ This disables postcss-import completely
        import: false
      }
    }
  },
  optimizeDeps: {
    exclude: ["tailwindcss"] // ✅ prevents Vite from trying to pre-bundle Tailwind
  }
});
