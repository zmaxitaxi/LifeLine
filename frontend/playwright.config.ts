import { defineConfig, devices } from "@playwright/test";
const apiPort = process.env.LIFELINE_API_PORT ?? "8000";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 30000,
  use: { baseURL: "http://127.0.0.1:5173", ...devices["Desktop Chrome"] },
  reporter: "list",
  outputDir:
    process.env.LIFELINE_TEST_OUTPUT ?? "/tmp/lifeline-playwright-results",
  webServer: [
    {
      command: `../.venv/bin/python -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/api/health`,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
