import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { getVisualizationWindow, type VisualizationWindow } from '../src/api/client'
import { useOrbitalPlayback } from '../src/features/useOrbitalPlayback'

vi.mock('../src/api/client', () => ({ getVisualizationWindow: vi.fn() }))
const fetchWindow = vi.mocked(getVisualizationWindow)
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks() })

function fixture(start: number): VisualizationWindow {
  return {
    timestamps: [0, 300, 600, 900, 1200].map(value => new Date(start + value * 1000).toISOString()),
    tracks: [], frame: 'ITRS', catalog_version: 'test', display_only: true, interpolation: 'Test', errors: [],
  }
}

function frameDriver() {
  let now = 1, nextId = 0
  const callbacks = new Map<number, FrameRequestCallback>()
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => { callbacks.set(++nextId, callback); return nextId })
  vi.stubGlobal('cancelAnimationFrame', (id: number) => callbacks.delete(id))
  return (count: number, stepMs = 20) => act(() => {
    for (let index = 0; index < count; index++) {
      now += stepMs
      const pending = [...callbacks.values()]; callbacks.clear()
      pending.forEach(callback => callback(now))
    }
  })
}

test('clock starts automatically without fetching every frame, and stops on unmount', async () => {
  const step = frameDriver(), ids = ['1'], start = Date.parse('2026-10-11T00:00:00Z')
  fetchWindow.mockResolvedValue(fixture(start))
  const { result, unmount } = renderHook(() => useOrbitalPlayback(ids, 'test', start))
  await waitFor(() => expect(result.current.window).toBeDefined())
  step(101)
  expect(result.current.clock.current - start).toBeCloseTo(120_000)
  expect(fetchWindow).toHaveBeenCalledTimes(1)
  unmount()
  const stopped = result.current.clock.current
  step(100)
  expect(result.current.clock.current).toBe(stopped)
})

test('prefetches once, keeps moving during delay, holds at the boundary and resumes only inside coverage', async () => {
  const step = frameDriver(), ids = ['1'], start = Date.parse('2026-10-11T00:00:00Z')
  let resolveNext!: (data: VisualizationWindow) => void
  fetchWindow.mockResolvedValueOnce(fixture(start)).mockImplementationOnce(() => new Promise(resolve => { resolveNext = resolve }))
  const { result } = renderHook(() => useOrbitalPlayback(ids, 'test', start))
  await waitFor(() => expect(result.current.window).toBeDefined())
  step(601)
  expect(fetchWindow).toHaveBeenCalledTimes(2)
  expect(result.current.clock.current).toBe(start + 720_000)
  step(500)
  expect(result.current.clock.current).toBe(start + 1_200_000)
  expect(result.current.buffering).toBe(true)
  expect(result.current.window?.times[0]).toBe(start)
  expect(fetchWindow).toHaveBeenCalledTimes(2)
  await act(async () => resolveNext(fixture(start + 1_200_000)))
  step(20)
  expect(result.current.window?.times[0]).toBe(start + 1_200_000)
  expect(result.current.clock.current).toBeGreaterThan(start + 1_200_000)
  expect(result.current.buffering).toBe(false)
})

test('filter changes preserve time, discard old context, and abort stale fetches; Now resets time', async () => {
  const step = frameDriver(), firstIds = ['1'], nextIds = ['2'], start = Date.parse('2026-10-11T00:00:00Z')
  fetchWindow.mockImplementation(async (_, at) => fixture(at))
  const { result, rerender } = renderHook(({ ids, at }) => useOrbitalPlayback(ids, 'test', at), { initialProps: { ids: firstIds, at: start } })
  await waitFor(() => expect(result.current.window).toBeDefined())
  step(51)
  const advanced = result.current.clock.current
  const oldSignal = fetchWindow.mock.calls[0][2]
  rerender({ ids: nextIds, at: start })
  expect(oldSignal?.aborted).toBe(true)
  expect(fetchWindow.mock.calls[1].slice(0, 2)).toEqual([nextIds, advanced])
  await waitFor(() => expect(result.current.window?.times[0]).toBe(advanced))
  rerender({ ids: nextIds, at: start + 1234 })
  await waitFor(() => expect(result.current.window?.times[0]).toBe(start + 1234))
  expect(result.current.clock.current).toBe(start + 1234)
})

test('a failed prefetch is reported without retries or extrapolation', async () => {
  const step = frameDriver(), ids = ['1'], start = Date.parse('2026-10-11T00:00:00Z')
  fetchWindow.mockResolvedValueOnce(fixture(start)).mockRejectedValueOnce(new Error('Network test failure'))
  const { result } = renderHook(() => useOrbitalPlayback(ids, 'test', start))
  await waitFor(() => expect(result.current.window).toBeDefined())
  step(601)
  await waitFor(() => expect(result.current.error).toBe('Network test failure'))
  step(1500)
  expect(fetchWindow).toHaveBeenCalledTimes(2)
  expect(result.current.clock.current).toBe(start + 1_200_000)
  expect(result.current.buffering).toBe(true)
})

test('an aborted response cannot restore dots from a previous filter', async () => {
  frameDriver()
  const start = Date.parse('2026-10-11T00:00:00Z')
  let resolveOld!: (data: VisualizationWindow) => void
  fetchWindow.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
    .mockResolvedValueOnce(fixture(start))
  const { result, rerender } = renderHook(({ ids }) => useOrbitalPlayback(ids, 'test', start), { initialProps: { ids: ['old'] } })
  rerender({ ids: ['new'] })
  await waitFor(() => expect(result.current.window).toBeDefined())
  const current = result.current.window
  await act(async () => resolveOld(fixture(start + 1000)))
  expect(result.current.window).toBe(current)
  expect(result.current.window?.times[0]).toBe(start)
})
