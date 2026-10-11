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
  await page.route('**/api/positions', async route => {
    const body = route.request().postDataJSON()
    const requestNumber = ++tracking.requests
    tracking.inFlight++
    tracking.maxInFlight = Math.max(tracking.maxInFlight, tracking.inFlight)
    if (requestNumber > 1) await new Promise(resolve => setTimeout(resolve, 1800))
    await route.fulfill({ json: body.object_ids.map((id: string, index: number) => ({
      object_id: id, errors: [], states: [{
        timestamp: body.timestamps[0], frame: 'ITRS',
        position_m: [7_000_000 + index * 500_000, -4_000_000, requestNumber * 500_000], velocity_m_s: [0, 7500, 0],
        metadata: { source: 'Synthetic test', model: 'UI regression', model_version: '1', availability: 'available', assumptions: [], warnings: [] },
      }],
    })) })
    tracking.inFlight--
    tracking.completed++
  })
  await page.goto('/')
  await expect(page.getByLabel('Orbital position snapshot')).toContainText('2 objects')
  return tracking
}

test('slow playback retains dots, completes updates and does not overlap requests', async ({ page }) => {
  const tracking = await mockPlayback(page)
  const snapshot = page.getByLabel('Orbital position snapshot')
  const initial = await snapshot.textContent()
  await page.evaluate(() => {
    const target = document.querySelector('[aria-label="Orbital position snapshot"]')!
    const observations: string[] = []
    Object.assign(window, { playbackSnapshots: observations })
    new MutationObserver(() => observations.push(target.textContent ?? '')).observe(target, { childList: true, subtree: true, characterData: true })
  })
  await page.getByRole('button', { name: 'Play', exact: true }).click()
  await expect(page.getByText('Calculating orbital positions…')).toBeVisible()
  await expect(snapshot).toHaveText(initial!)
  await expect.poll(() => tracking.completed).toBeGreaterThanOrEqual(3)
  await expect(snapshot).not.toHaveText(initial!)
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  await expect.poll(() => tracking.inFlight).toBe(0)
  expect(tracking.maxInFlight).toBe(1)
  expect(await page.evaluate(() => (window as unknown as { playbackSnapshots: string[] }).playbackSnapshots.every(value => value.includes('2 objects')))).toBe(true)
  const completedSnapshot = await snapshot.textContent()
  const requestsAtPause = tracking.requests
  await page.waitForTimeout(1300)
  expect(tracking.requests).toBe(requestsAtPause)
  await expect(snapshot).toHaveText(completedSnapshot!)
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
