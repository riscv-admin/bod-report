import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => {
  const repoName = process.env.GITHUB_REPOSITORY
    ? process.env.GITHUB_REPOSITORY.split("/")[1]
    : "";
  const defaultBase = repoName ? `/${repoName}/` : "/";
  const base = process.env.BASE_URL || defaultBase;
  const repoRoot = path.resolve(__dirname, "..");
  const localCsvPath = path
    .resolve(repoRoot, "specs_20260107_182508.csv")
    .replace(/\\/g, "/");
  const localCsvUrl = command === "serve" ? `/@fs/${localCsvPath}` : "";

  return {
    plugins: [react()],
    base,
    server: {
      fs: {
        allow: [repoRoot],
      },
    },
    define: {
      __LOCAL_CSV_URL__: JSON.stringify(localCsvUrl),
    },
  };
});
