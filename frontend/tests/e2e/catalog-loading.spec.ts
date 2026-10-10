import { expect, test } from '@playwright/test'

test('refresh updates objects and header without a browser reload', async ({ page }) => {
  // Explicit synthetic API fixture: proves UI transitions, not live-source coverage.
  let loaded = false
  const objects = [
    { catalog_id: '100001', name: 'SYNTHETIC LOADING TEST A', source: 'Synthetic test', category: 'active', elements: { epoch: '2026-10-10T00:00:00Z', inclination_rad: 1, eccentricity: .01, mean_motion_rev_day: 15 } },
    { catalog_id: '100002', name: 'SYNTHETIC LOADING TEST B', source: 'Synthetic test', category: 'active', elements: { epoch: '2026-10-10T00:00:00Z', inclination_rad: 1, eccentricity: .01, mean_motion_rev_day: 15 } },
  ]
  const status = () => ({ state: loaded ? 'ready' : 'degraded', record_count: loaded ? 2 : 1, catalog_version: loaded ? 'new' : 'old', coverage: 'Synthetic test coverage', categories: {}, source: { parsing_status: loaded ? 'parsed' : 'archived_fixture' } })
  await page.route('**/api/catalog/status', route => route.fulfill({ json: status() }))
  await page.route('**/api/catalog/refresh', async route => {
    await new Promise(resolve => setTimeout(resolve, 250))
    loaded = true
    await route.fulfill({ json: status() })
  })
  await page.route('**/api/objects?*', async route => {
    if (!loaded) return route.continue()
    await route.fulfill({ json: { items: objects, total: 2, limit: 1000, offset: 0, catalog_version: 'new' } })
  })
  await page.route('**/api/health', route => route.fulfill({ json: { datasets: { objects: loaded ? 2 : 1 } } }))
  await page.route('**/api/positions', route => route.fulfill({ json: [] }))
  await page.route('**/api/trajectories', route => route.fulfill({ json: { states: [] } }))
  await page.goto('/')
  await expect(page.getByText('Archived fallback — live catalog not loaded')).toBeVisible()
  await page.getByRole('button', { name: 'Retry live catalog', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Loading catalog…', exact: true })).toBeDisabled()
  await expect(page.getByText('Catalog loaded', { exact: true })).toBeVisible()
  await expect(page.getByText('2 OBJECTS', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /SYNTHETIC LOADING TEST B/ })).toBeVisible()
  await expect(page.getByText('2 matches · 2 catalog objects loaded')).toBeVisible()
})

test('source rejection shows the archived fallback and retry cooldown', async ({ page }) => {
  await page.route('**/api/catalog/status', route => route.fulfill({ json: {
    state: 'degraded', record_count: 1, catalog_version: 'archive', coverage: 'Test coverage', categories: {},
    source: { parsing_status: 'archived_fixture', error: 'Source returned HTTP 403; automatic retries stopped.', next_retry_at: new Date(Date.now() + 7200000).toISOString() },
  } }))
  await page.goto('/')
  await expect(page.getByText('Archived fallback — live catalog not loaded')).toBeVisible()
  await expect(page.getByText('Source returned HTTP 403; automatic retries stopped.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Retry live catalog' })).toBeDisabled()
  await expect(page.getByText(/Next permitted retry:/)).toBeVisible()
  await expect(page.getByText('ARCHIVED DATA', { exact: true })).toBeVisible()
})
