import path from "node:path"
import { fileURLToPath } from "node:url"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

const projectRoot = fileURLToPath(new URL(".", import.meta.url))

export default defineConfig(({ command }) => ({
  base: command === "build" ? "/dashboard/" : "/",
  build: {
    emptyOutDir: true,
    outDir: path.resolve(projectRoot, "../viz/dashboard"),
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(projectRoot, "./src"),
    },
  },
}))
