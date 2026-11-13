import { defineConfig, devices } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { testPython } from "./test-python";
const apiPort = process.env.LIFELINE_API_PORT ?? "8012";
const uiPort = process.env.LIFELINE_UI_PORT ?? "5182";
const failureFile = join(tmpdir(), `lifeline-ui-weather-failure-${apiPort}`);
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 45000,
  use: { baseURL: `http://127.0.0.1:${uiPort}`, ...devices["Desktop Chrome"] },
  reporter: "list",
  outputDir:
    process.env.LIFELINE_TEST_OUTPUT ??
    join(tmpdir(), "lifeline-two-page-playwright"),
  webServer: [
    {
      command: `"${testPython}" -m uvicorn session_server:app --app-dir e2e/support --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/api/health`,
      reuseExistingServer: false,
      env: { LIFELINE_TEST_WEATHER_FAILURE_FILE: failureFile },
    },
    {
      command: `npm run dev -- --port ${uiPort}`,
      url: `http://127.0.0.1:${uiPort}`,
      reuseExistingServer: false,
      env: { LIFELINE_API_PORT: apiPort },
    },
  ],
});
