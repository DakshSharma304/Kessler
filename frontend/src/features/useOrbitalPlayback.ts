import { useEffect, useRef, useState } from 'react'
import { getVisualizationWindow } from '../api/client'
import { prepareAnimationWindow, type AnimationWindow } from '../scene/interpolation'

export const PLAYBACK_RATE = 60

export function useOrbitalPlayback(ids: string[], catalogVersion: string | undefined, start: number, playing: boolean) {
  const clock = useRef(start)
  const lastStart = useRef(start)
  const playingRef = useRef(playing)
  playingRef.current = playing
  const [window, setWindow] = useState<AnimationWindow>()
  const [time, setTime] = useState(start)
  const [loading, setLoading] = useState(false)
  const [buffering, setBuffering] = useState(false)
  const [error, setError] = useState<string>()

  useEffect(() => {
    const controller = new AbortController()
    let active: AnimationWindow | undefined, next: AnimationWindow | undefined
    let prefetchStarted = false, pending = false, frame = 0, previous = 0, lastUi = 0
    const begin = lastStart.current === start ? clock.current : start
    lastStart.current = start
    clock.current = begin
    setTime(begin); setWindow(undefined); setError(undefined); setBuffering(false)

    async function load(at: number, initial: boolean) {
      if (pending || controller.signal.aborted) return
      pending = true; setLoading(true)
      try {
        const response = await getVisualizationWindow(ids, at, controller.signal)
        if (controller.signal.aborted) return
        if (catalogVersion && response.catalog_version !== catalogVersion) throw new Error('Catalog changed; reload the catalog before playing')
        const prepared = prepareAnimationWindow(response)
        if (initial) { active = prepared; setWindow(prepared) } else next = prepared
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Animation window unavailable')
      } finally {
        pending = false
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    function animate(now: number) {
      // Discard long background-tab gaps instead of jumping beyond computed coverage.
      const elapsed = previous ? Math.min((now - previous) / 1000, .25) : 0
      previous = now
      let waiting = false
      if (playingRef.current && active) {
        const end = active.times[active.times.length - 1]
        const requested = clock.current + elapsed * PLAYBACK_RATE * 1000
        clock.current = Math.min(requested, end)
        if (!prefetchStarted && clock.current >= (active.times[0] + end) / 2) {
          prefetchStarted = true
          void load(end, false)
        }
        if (clock.current >= end) {
          if (next) {
            active = next; next = undefined; prefetchStarted = false
            clock.current = Math.min(requested, active.times[active.times.length - 1])
            setWindow(active)
          } else waiting = true // Hold the last valid position; never extrapolate.
        }
      }
      if (now - lastUi >= 250) {
        lastUi = now; setTime(clock.current); setBuffering(waiting)
      }
      frame = globalThis.requestAnimationFrame(animate)
    }
    if (ids.length) void load(begin, true)
    else setLoading(false)
    frame = globalThis.requestAnimationFrame(animate)
    return () => { controller.abort(); globalThis.cancelAnimationFrame(frame) }
  }, [ids, catalogVersion, start])

  useEffect(() => { if (!playing) setTime(clock.current) }, [playing])
  const pause = () => {
    // Stop immediately in the click handler and commit the exact frozen clock in
    // the same React update as the button, rather than a later effect/text tick.
    playingRef.current = false
    setTime(clock.current)
    setBuffering(false)
  }
  return { clock, window, time, loading, buffering, error, pause }
}
