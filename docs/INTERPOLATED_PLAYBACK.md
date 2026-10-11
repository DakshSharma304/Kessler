# GPU-interpolated playback — 2026-10-11 UTC

This supersedes the stepwise playback repair in [PLAYBACK_REPAIR.md](PLAYBACK_REPAIR.md).
It changes display animation, not the scientific analysis algorithms.

## Implementation

- `POST /api/visualization/window` returns five real SGP4/ITRS position/velocity
  samples at 300-second intervals: a 20-minute simulation window. It preserves
  per-object provenance and propagation errors, checks catalog-version consistency,
  rejects naive timestamps, and bounds work to 20,000 objects × 5 samples.
- The compact contract avoids repeating metadata for every timestamp. Partial
  object tracks are omitted and reported; failed samples are not bridged silently.
- The frontend packs reusable Float32 GPU buffers, using the same axis mapping and
  Earth-radius scale for positions and velocities. Cubic Hermite interpolation
  respects both sampled positions and velocities instead of moving along a straight
  line or adding a constant offset forever.
- The animation clock advances at 60× in `requestAnimationFrame`; the point shader
  evaluates the current segment each rendered frame. Frame work is one clock/uniform
  update, not a per-object React state/array rewrite or a backend POST per frame.
  Four-Hz text updates and one-Hz FPS reporting are separate from marker animation.
  Four GL buffers are reused across segments and disposed on window replacement;
  segment transitions do not leave old attribute buffers accumulating in VRAM.
- Prefetch starts halfway through a window. At most one window request is active
  for the current view; current + next windows bound stored animation data. Playback
  continues during prefetch. At a coverage boundary it holds the final valid positions
  until the next window arrives; it never extrapolates beyond calculated coverage.
- Pause stops the clock; Now resets it and fetches new coverage. Catalog/filter
  changes discard obsolete tracks and abort their client requests while preserving
  the current time. Failed fetches show an error, stop retries, and can be retried
  with Now. Long background-tab frame gaps are discarded, not treated as an instruction
  to jump beyond coverage. Aborting HTTP does not cancel backend work already running.
- The selected orbit is fetched once per window, not every frame. Its existing
  90-minute partial-path limitation is unchanged; it is not the motion interpolator.
- Rendering starts at DPR 1, with cheaper Earth lighting/wireframe geometry. If
  measured rendering is below 22 FPS, visual resolution is reduced in 0.15 steps,
  down to DPR 0.5. This changes pixel sharpness only, not orbital samples. There is
  no hardware-independent minimum-FPS guarantee; the UI reports measured FPS.

No dependency changes or new upstream data download. Both frontend and backend must
be updated because the animation now uses the new window endpoint. Redeploy Modal
and the frontend if using hosted services; no hosted deployment was performed here.

## Accuracy boundary

The renderer is explicitly labeled **display interpolation only**. Scientific
positions, trajectories, encounter analysis, and maneuver calculations continue to
use their original backend methods. Do not use these GPU-interpolated Float32
positions for collision probability, miss distance, screening, or maneuver validation.

A read-only real-catalog comparison used all 16,701 loaded objects at
`2026-10-11T00:30:00Z`, `+150 s`, and `+300 s`, with zero failed objects. Hermite
midpoint positions compared with independent direct SGP4/ITRS positions had mean
error 186.09 m, median 193.83 m, 95th percentile 238.07 m, and maximum 435.15 m
(object 37818). These are one-snapshot midpoint checks, not universal error bounds,
SGP4 truth accuracy, or covariance guarantees. They exclude additional Float32 GPU
rounding. The four-object real OMM unit fixture also checks three interior fractions
against SGP4 with a fixture-specific 5 km ceiling.

## Visual/performance evidence

The standalone cloud check used Chromium, software WebGL (SwiftShader), a 1440×1000
viewport, the actual cached 16,701-object catalog, and real window API responses.
There were no mocked orbital states and no captured page exceptions.

The actual GPU interpolation-uniform stream, not merely a React clock, recorded
433 distinct fractional updates, averaging **17.42 updates/s**; median frame gap
58 ms and 95th percentile 97.9 ms. The displayed renderer rate at completion was
19 FPS. This exceeds the 15-FPS average target in this check, but does not establish
every-frame 15 FPS, hardware-independent performance, or hosted/network performance.
Adaptive resolution had reduced the drawing buffer to 524×576 (DPR 0.5).

Only two window requests were made across startup and ~24 seconds of playback,
maximum concurrent count one. All 16,701 markers remained represented; simulation
time advanced continuously across a window boundary and Pause froze it. Screenshots
[playing](audit/interpolation/playing.png) and [advanced](audit/interpolation/advanced.png)
were opened and visually inspected for retained/moving dots.

An earlier run without rendering optimizations, alongside other browser tests,
recorded 6.34 shader updates/s. It prompted the renderer tuning; it is not evidence
for meeting the target. Software rendering still has slower individual frames,
particularly during data parsing/transfer or competing workloads.

Checks: **39 backend tests passed** (2.76 s), **15 frontend unit tests passed**
(1.63 s runner duration), **8 browser tests passed** (22.5 s), final TypeScript/Vite
build passed (Vite 7.08 s). The last full-catalog visual check also exercised the
reusable GL buffers across a window transition. Existing Astropy cache/AnyIO and
runner-color warnings and the >500 kB Explore chunk warning remain.

Reproduce against a running app from `frontend`:

```bash
KESSLER_VERIFY_URL=http://127.0.0.1:5173 PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium node scripts/verify-playback.mjs
```

The executable override is optional if Playwright's Chromium is installed. This
script measures/logs FPS; it fails on page exceptions, nonmoving shader fractions,
unstable Pause, or overlapping requests, not on platform-specific FPS variation.

## Exact local test

1. Pull main, restart both backend and frontend, and reload Explore. If using Modal,
   deploy the updated backend and frontend first.
2. Wait for a nonzero Position snapshot, then press Play. Dots should move smoothly
   between requests. Read the FPS value; target at least 15 on your machine.
3. Leave it playing at least 30 seconds to cross the first 20-minute simulation
   window. Prefetch should not clear the dots. A slow server can cause a labeled
   hold at the boundary, not a blank globe or invented extrapolation.
4. Pause; the clock/dots should stop. Press Now and test search/category changes;
   excluded dots must not linger as if they were matching objects.
