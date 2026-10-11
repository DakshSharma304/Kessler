import { expect, test } from '@playwright/test'

test('application shell connects to backend', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('KESSLER')).toBeVisible()
  await expect(page.getByText('1 OBJECTS', { exact: true })).toBeVisible()
  await expect(page.getByText('VANGUARD 1').first()).toBeVisible()
  await expect(page.getByText('ARCHIVED DATA')).toBeVisible()
})

test('navigation exposes honest empty coverage and methods', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Close Approaches' }).click()
  await expect(page.getByText(/No reported close approaches/)).toBeVisible()
  await page.getByRole('button', { name: 'Data & Methods' }).click()
  await expect(page.getByText('Scientific models')).toBeVisible()
  await expect(page.getByText('SGP4', { exact: true })).toBeVisible()
})

test('avoidance planner runs a fresh backend optimization', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Avoidance Planner' }).click()
  await page.getByRole('button', { name: 'Find Best Maneuvers' }).click()
  await expect(page.getByText(/candidates numerically propagated/)).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText('UNSCREENED').first()).toBeVisible()
})

test('cleanup planner calls the backend optimizer', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Cleanup Planner' }).click()
  await page.getByRole('button', { name: 'Optimize cleanup portfolio' }).click()
  await expect(page.getByText('VANGUARD 1')).toBeVisible()
  await expect(page.getByText(/Remaining/)).toBeVisible()
})
