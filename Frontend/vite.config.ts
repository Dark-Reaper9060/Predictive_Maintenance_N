import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    proxy: {
      "/equipments": {
        target: "http://127.0.0.1:8448",
        changeOrigin: true,
        secure: false,
      },
      "/monitoring": {
        target: "http://127.0.0.1:8448",
        changeOrigin: true,
        secure: false,
      },
      "/maintenance": {
        target: "http://127.0.0.1:8448",
        changeOrigin: true,
        secure: false,
      },
      "/ai_analysis": {
        target: "http://127.0.0.1:8448",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
