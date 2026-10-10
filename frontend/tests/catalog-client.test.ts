import { afterEach, expect, test, vi } from 'vitest'
import { api, getObjects, getPositions } from '../src/api/client'

afterEach(() => vi.unstubAllGlobals())

test('loads all catalog pages rather than silently stopping at the first page', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ items: [{ catalog_id: '1' }, { catalog_id: '2' }], total: 3, limit: 2, offset: 0, catalog_version: 'v1' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [{ catalog_id: '100981' }], total: 3, limit: 2, offset: 2, catalog_version: 'v1' }) })
  vi.stubGlobal('fetch', fetchMock)
  expect((await getObjects()).items.map(item => item.catalog_id)).toEqual(['1', '2', '100981'])
  expect(fetchMock.mock.calls[1][0]).toContain('offset=2')
})

test('rejects a changed snapshot instead of silently combining catalogs', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ items: [{ catalog_id: '1' }], total: 2, catalog_version: 'v1' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [{ catalog_id: '2' }], total: 2, catalog_version: 'v2' }) }))
  await expect(getObjects()).rejects.toThrow('Catalog changed')
})

test('preserves per-object propagation errors and identity', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [
    { object_id: '1', states: [{ position_m: [1, 2, 3] }], errors: [] },
    { object_id: '2', states: [], errors: ['SGP4 failed'] },
  ] }))
  const result = await getPositions(['1', '2'], new Date())
  expect(result.states[0].object_id).toBe('1')
  expect(result.errors).toEqual(['2: SGP4 failed'])
})

test('displays structured backend errors', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422, statusText: 'Invalid', json: async () => ({ error: { message: 'Specific validation error' } }) }))
  await expect(api('/api/catalog/refresh')).rejects.toThrow('Specific validation error')
})
