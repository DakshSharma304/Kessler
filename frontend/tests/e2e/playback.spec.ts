import { expect, test, type Page } from '@playwright/test'

async function mockPlayback(page: Page) {
  // Synthetic motion fixture for UI regression only, not orbital/scientific validation.
  const objects = ['A', 'B'].map((name, index) => ({
    catalog_id: String(100001 + index), name: `SYNTHETIC PLAYBACK ${name}`,
    source: 'Synthetic test', category: 'active',
    elements: { epoch: '2026-10-10T00:00:00Z', inclination_rad: 1, eccentricity: .01, mean_motion_rev_day: 15 },
  }))
  const tracking = { requests: 0, completed: 0, inFlight: 0, maxInFlight: 0 }
  await page.route('**/api/catalog/status', route => route.fulfill({ json: {
    state: 'ready', record_count: 2, catalog_version: 'playback-test', coverage: 'Synthetic test coverage', categories: {},
    source: { parsing_status: 'parsed', availability: 'available' },
  } }))
  await page.route('**/api/objects?*', route => route.fulfill({ json: { items: objects, total: 2, limit: 1000, offset: 0, catalog_version: 'playback-test' } }))
  await page.route('**/api/health', route => route.fulfill({ json: { datasets: { objects: 2 } } }))
  await page.route('**/api/trajectories', route => route.fulfill({ json: { states: [] } }))
  await page.route('**/api/visualization/window', async route => {
    const body = route.request().postDataJSON()
    const requestNumber = ++tracking.requests
    tracking.inFlight++
    tracking.maxInFlight = Math.max(tracking.maxInFlight, tracking.inFlight)
    if (requestNumber > 1) await new Promise(resolve => setTimeout(resolve, 1800))
    const timestamps = [0, 300, 600, 900, 1200].map(seconds => new Date(Date.parse(body.start) + seconds * 1000).toISOString())
    await route.fulfill({ json: {
      timestamps, frame: 'ITRS', catalog_version: 'playback-test', display_only: true, interpolation: 'Synthetic test', errors: [],
      tracks: body.object_ids.map((id: string, index: number) => ({
        object_id: id,
        positions_m: timestamps.map((_: string, sample: number) => [7_000_000 + index * 500_000, -4_000_000, requestNumber * 500_000 + sample * 300_000]),
        velocities_m_s: timestamps.map(() => [0, 0, 1000]),
        metadata: { source: 'Synthetic test', model: 'UI regression', model_version: '1', availability: 'available', assumptions: [], warnings: [] },
      })),
    } })
    tracking.inFlight--
    tracking.completed++
  })
  await page.goto('/')
  await expect(page.getByLabel('Orbital position snapshot')).toContainText('2 objects')
  return tracking
}

test('GPU playback starts automatically without controls and retains dots while prefetching', async ({ page }) => {
  test.setTimeout(45_000)
  const tracking = await mockPlayback(page)
  const snapshot = page.getByLabel('Orbital position snapshot')
  const initial = await snapshot.textContent()
  await page.evaluate(() => {
    const target = document.querySelector('[aria-label="Orbital position snapshot"]')!
    const observations: string[] = []
    Object.assign(window, { playbackSnapshots: observations })
    new MutationObserver(() => observations.push(target.textContent ?? '')).observe(target, { childList: true, subtree: true, characterData: true })
  })
  await expect(page.getByRole('button', { name: /^(Play|Pause|Freeze time)$/i })).toHaveCount(0)
  await expect(snapshot).not.toHaveText(initial!)
  // Smooth time updates happen inside one fetched window, not one POST per step.
  expect(tracking.requests).toBe(1)
  await expect(page.getByText('Buffering the next animation window…')).toBeVisible({ timeout: 20_000 })
  await expect(snapshot).toContainText('2 objects')
  await expect.poll(() => tracking.completed).toBeGreaterThanOrEqual(2)
  await expect(snapshot).not.toHaveText(initial!)
  await expect.poll(() => tracking.inFlight).toBe(0)
  expect(tracking.maxInFlight).toBe(1)
  expect(await page.evaluate(() => (window as unknown as { playbackSnapshots: string[] }).playbackSnapshots.every(value => value.includes('2 objects')))).toBe(true)
  const completedSnapshot = await snapshot.textContent()
  await page.waitForTimeout(1300)
  await expect(snapshot).not.toHaveText(completedSnapshot!)
  await expect(page.getByLabel('Animation frame rate')).toContainText('FPS')
})

test('changing filters does not retain excluded dots and Now requests the exact timestamp', async ({ page }) => {
  const tracking = await mockPlayback(page)
  await page.getByLabel('Search objects').fill('SYNTHETIC PLAYBACK B')
  await expect(page.getByText('Calculating orbital positions…')).toBeVisible()
  await expect(page.getByLabel('Orbital position snapshot')).toContainText('0 objects')
  await expect(page.getByLabel('Orbital position snapshot')).toContainText('1 objects')
  const requestsBeforeNow = tracking.requests
  await page.getByRole('button', { name: 'Now', exact: true }).click()
  await expect.poll(() => tracking.requests).toBe(requestsBeforeNow + 1)
  await expect(page.getByLabel('Orbital position snapshot')).toContainText('1 objects')
})
