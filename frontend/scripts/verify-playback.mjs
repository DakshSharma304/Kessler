// Read-only browser check against a running, loaded app; no mocked orbital data.
// KESSLER_VERIFY_URL=http://127.0.0.1:5176 PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium node scripts/verify-playback.mjs
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'

const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
})
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
const output = resolve(process.env.KESSLER_VERIFY_OUTPUT ?? '../docs/audit/interpolation')
mkdirSync(output, { recursive: true })

await page.addInitScript(() => {
  window.gpuInterpolation = []
  for (const type of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
    if (!type) continue
    const prototype = type.prototype, locations = new WeakMap()
    const getLocation = prototype.getUniformLocation, setFloat = prototype.uniform1f
    prototype.getUniformLocation = function (program, name) {
      const location = getLocation.call(this, program, name)
      if (location) locations.set(location, name)
      return location
    }
    prototype.uniform1f = function (location, value) {
      if (locations.get(location) === 'fraction') window.gpuInterpolation.push({ at: performance.now(), value })
      return setFloat.call(this, location, value)
    }
  }
})
const requests = [], failures = []
let pending = 0, maxPending = 0
page.on('pageerror', error => failures.push(error.message))
page.on('request', request => {
  if (!request.url().endsWith('/api/visualization/window')) return
  pending++; maxPending = Math.max(maxPending, pending)
  requests.push({ at: Date.now(), start: request.postDataJSON().start })
})
page.on('requestfinished', request => { if (request.url().endsWith('/api/visualization/window')) pending-- })
page.on('requestfailed', request => { if (request.url().endsWith('/api/visualization/window')) pending-- })

try {
  await page.goto(process.env.KESSLER_VERIFY_URL ?? 'http://127.0.0.1:5173')
  const snapshot = page.getByLabel('Orbital position snapshot')
  await snapshot.filter({ hasText: /Position snapshot: [1-9]/ }).waitFor({ timeout: 90_000 })
  // Allow adaptive rendering resolution to settle before measuring.
  await page.waitForTimeout(5000)
  await page.getByRole('button', { name: 'Play', exact: true }).click()
  await page.evaluate(() => { window.gpuInterpolation = [] })
  await page.waitForTimeout(4000)
  await page.screenshot({ path: resolve(output, 'playing.png') })
  const before = await snapshot.textContent()
  await page.waitForTimeout(1000)
  await page.screenshot({ path: resolve(output, 'advanced.png') })
  await page.waitForTimeout(19_000)
  const during = await snapshot.textContent()
  const fpsLabel = await page.getByLabel('Animation frame rate').textContent()
  const samples = await page.evaluate(() => window.gpuInterpolation)
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  await page.getByRole('button', { name: 'Play', exact: true }).waitFor()
  await page.waitForTimeout(500)
  const paused = await snapshot.textContent()
  await page.waitForTimeout(1200)
  const pausedStable = paused === await snapshot.textContent()
  const differences = samples.slice(1).map((item, index) => item.at - samples[index].at).filter(value => value > 0).sort((a, b) => a - b)
  const metrics = {
    before, during, pausedStable, fpsLabel, requests, maxPending,
    shaderUpdates: samples.length,
    shaderFps: samples.length > 1 ? (samples.length - 1) * 1000 / (samples.at(-1).at - samples[0].at) : 0,
    medianFrameMs: differences[Math.floor(differences.length * .5)],
    p95FrameMs: differences[Math.floor(differences.length * .95)],
    uniqueFractions: new Set(samples.map(sample => sample.value)).size,
    canvas: await page.locator('canvas').evaluate(canvas => ({ width: canvas.width, height: canvas.height })), failures,
  }
  console.log(JSON.stringify(metrics, null, 2))
  if (!pausedStable || failures.length || metrics.uniqueFractions < 15 || maxPending > 1) process.exitCode = 1
} finally {
  await browser.close()
}
