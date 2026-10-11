import type { VisualizationWindow } from '../api/client'

export const EARTH_RADIUS_M = 6_378_137

export type AnimationWindow = {
  times: number[]; ids: string[]; positions: Float32Array[]; velocities: Float32Array[]; errors: string[]
}

export function prepareAnimationWindow(data: VisualizationWindow): AnimationWindow {
  const times = data.timestamps.map(value => Date.parse(value))
  if (data.display_only !== true || data.frame !== 'ITRS' || times.length < 2 || times.some((value, index) => !Number.isFinite(value) || (index > 0 && value <= times[index - 1]))) {
    throw new Error('Invalid animation frame or timestamps')
  }
  for (const track of data.tracks) {
    if (track.positions_m.length !== times.length || track.velocities_m_s.length !== times.length ||
      [...track.positions_m, ...track.velocities_m_s].some(vector => vector.length !== 3 || vector.some(value => !Number.isFinite(value)))) {
      throw new Error(`Invalid animation samples for ${track.object_id}`)
    }
  }
  const mapped = (vectors: Array<[number, number, number]>) => {
    const result = new Float32Array(vectors.length * 3)
    vectors.forEach(([x, y, z], index) => result.set([x / EARTH_RADIUS_M, z / EARTH_RADIUS_M, -y / EARTH_RADIUS_M], index * 3))
    return result
  }
  return {
    times, ids: data.tracks.map(track => track.object_id), errors: data.errors,
    positions: times.map((_, index) => mapped(data.tracks.map(track => track.positions_m[index]))),
    velocities: times.map((_, index) => mapped(data.tracks.map(track => track.velocities_m_s[index]))),
  }
}

export function segmentAt(times: number[], time: number) {
  let index = 0
  while (index < times.length - 2 && time >= times[index + 1]) index++
  const duration = (times[index + 1] - times[index]) / 1000
  return { index, duration, fraction: Math.max(0, Math.min(1, (time - times[index]) / (duration * 1000))) }
}

// CPU reference for tests/accuracy checks; the display evaluates this on the GPU.
export function hermite(p0: number, v0: number, p1: number, v1: number, duration: number, fraction: number) {
  const u = Math.max(0, Math.min(1, fraction)), u2 = u * u, u3 = u2 * u
  return (2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * duration * v0 +
    (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * duration * v1
}
