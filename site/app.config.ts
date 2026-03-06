import { defineConfig } from "@solidjs/start/config";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  vite: {
    plugins: [tailwindcss()],
  },
  server: {
    // Externalize better-sqlite3 native module from nitro bundling
    externals: {
      inline: [],
      external: ["better-sqlite3"],
    },
  },
});
