import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    launchOptions: { executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] },
  },
  webServer: [
    { command: '../.venv/bin/uvicorn app.main:app --port 8000', cwd: '../backend', port: 8000, reuseExistingServer: true },
    { command: 'npm run dev -- --host 127.0.0.1', port: 5173, reuseExistingServer: true },
  ],
})
