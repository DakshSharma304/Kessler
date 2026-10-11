import { expect, test } from 'vitest'
import { EARTH_RADIUS_M, hermite, prepareAnimationWindow, segmentAt } from '../src/scene/interpolation'
import type { VisualizationWindow } from '../src/api/client'

test('Hermite matches endpoints and a constant-velocity path, and clamps instead of extrapolating', () => {
  expect(hermite(10, 3, 40, 3, 10, 0)).toBe(10)
  expect(hermite(10, 3, 40, 3, 10, 1)).toBe(40)
  expect(hermite(10, 3, 40, 3, 10, .25)).toBe(17.5)
  expect(hermite(10, 3, 40, 3, 10, -1)).toBe(10)
  expect(hermite(10, 3, 40, 3, 10, 2)).toBe(40)
})

test('Hermite respects endpoint velocities and curved motion rather than adding a fixed offset', () => {
  const epsilon = 1e-6
  expect((hermite(0, 2, 10, -3, 20, epsilon) - 0) / (epsilon * 20)).toBeCloseTo(2, 4)
  expect((10 - hermite(0, 2, 10, -3, 20, 1 - epsilon)) / (epsilon * 20)).toBeCloseTo(-3, 4)
  expect(hermite(0, 2, 10, -3, 20, .5)).not.toBe(5)
})

test('segment selection crosses boundaries and holds coverage endpoints', () => {
  const times = [0, 300000, 600000]
  expect(segmentAt(times, -1)).toEqual({ index: 0, duration: 300, fraction: 0 })
  expect(segmentAt(times, 150000)).toEqual({ index: 0, duration: 300, fraction: .5 })
  expect(segmentAt(times, 300000)).toEqual({ index: 1, duration: 300, fraction: 0 })
  expect(segmentAt(times, 999999)).toEqual({ index: 1, duration: 300, fraction: 1 })
})

function fixture(): VisualizationWindow {
  return {
    timestamps: ['2026-10-11T00:00:00Z', '2026-10-11T00:05:00Z'], frame: 'ITRS', catalog_version: 'test', display_only: true, interpolation: 'Test', errors: ['omitted test object'],
    tracks: [{ object_id: '1', positions_m: [[EARTH_RADIUS_M, 2 * EARTH_RADIUS_M, 3 * EARTH_RADIUS_M], [2 * EARTH_RADIUS_M, 0, 0]], velocities_m_s: [[EARTH_RADIUS_M, 2 * EARTH_RADIUS_M, 3 * EARTH_RADIUS_M], [0, 0, 0]],
      metadata: { source: 'Test', model: 'Test', model_version: '1', availability: 'available', assumptions: [], warnings: [] } }],
  }
}

test('packs reusable GPU buffers with consistent Earth radius, axis and velocity mapping', () => {
  const packed = prepareAnimationWindow(fixture())
  expect([...packed.positions[0]]).toEqual([1, 3, -2])
  expect([...packed.velocities[0]]).toEqual([1, 3, -2])
  expect(packed.ids).toEqual(['1'])
  expect(packed.errors).toEqual(['omitted test object'])
})

test('rejects invalid frame, unordered/nonfinite timestamps and incomplete/nonfinite samples', () => {
  const wrongFrame = fixture(); Object.assign(wrongFrame, { frame: 'TEME' })
  expect(() => prepareAnimationWindow(wrongFrame)).toThrow('frame')
  const unordered = fixture(); unordered.timestamps.reverse()
  expect(() => prepareAnimationWindow(unordered)).toThrow('timestamps')
  const invalidTime = fixture(); invalidTime.timestamps[0] = 'not a time'
  expect(() => prepareAnimationWindow(invalidTime)).toThrow('timestamps')
  const incomplete = fixture(); incomplete.tracks[0].positions_m.pop()
  expect(() => prepareAnimationWindow(incomplete)).toThrow('samples')
  const nonfinite = fixture(); nonfinite.tracks[0].velocities_m_s[0][0] = Infinity
  expect(() => prepareAnimationWindow(nonfinite)).toThrow('samples')
})
