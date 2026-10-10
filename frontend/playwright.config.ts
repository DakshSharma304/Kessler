import { defineConfig } from '@playwright/test'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const apiPort = 8002
const uiPort = 5175
const uiOrigin = `http://127.0.0.1:${uiPort}`
const dataDirectory = mkdtempSync(join(tmpdir(), 'kessler-e2e-'))

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: uiOrigin,
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
  },
  webServer: [
    { command: `../.venv/bin/uvicorn app.main:app --port ${apiPort}`, cwd: '../backend', port: apiPort, reuseExistingServer: false,
      env: { KESSLER_DATA_DIR: dataDirectory, KESSLER_AUTO_REFRESH_CATALOG: 'false', KESSLER_CORS_ORIGINS: uiOrigin } },
    { command: `npm run dev -- --host 127.0.0.1 --port ${uiPort} --strictPort`, port: uiPort, reuseExistingServer: false,
      env: { VITE_API_URL: `http://127.0.0.1:${apiPort}` } },
  ],
})
