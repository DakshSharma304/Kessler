# Playback flashing repair — 2026-10-11 UTC

Historical stepwise repair: superseded by
[GPU-interpolated playback](INTERPOLATED_PLAYBACK.md) later on 2026-10-11.

## Cause and behavior

Explore previously changed the position/trajectory query key every second, then
passed empty arrays to the globe until each new request finished. With a slow
backend, the clock could also advance before the current request completed.

Explore now retains the last completed position and orbit snapshots during a time
update. Position snapshots are retained only for the same catalog version and
same filtered IDs; an object/filter or catalog change must not show excluded dots.
Orbit snapshots are retained only for the same selected object and catalog version.
The exact timestamp is part of both query keys, so **Now** also refreshes within
the same minute instead of reusing a different timestamp's cached state.

Playback waits for positions and the enabled orbit request to settle, waits one
second, then advances simulation time by one minute. This is request-paced,
stepwise motion, not smooth animation or a guaranteed 60× wall-clock rate.
The position-snapshot text identifies the timestamp actually being rendered;
while calculating, the controls show the requested timestamp and the dots retain
the previous completed snapshot. Pausing stops future steps; an already running
request may still finish. Initial loading or a changed filter can legitimately
show no dots until its first matching snapshot arrives. Errors remain visible.

No backend scientific model, source download, dependency, or deployment changes.
The incomplete orbit coverage and other audited prototype limitations remain.

## Verification

- Browser regression tests use explicitly synthetic API fixtures with 1.8-second
  position delays: snapshots never drop to zero during playback, time/positions
  update, maximum concurrent position requests is one, Pause stops new requests,
  changing filters does not retain excluded dots, and Now makes a new request.
- Separate Chromium/software-WebGL inspection uses the actual 16,701-object cached
  live catalog and real SGP4/ITRS responses, without mocked orbital data. Images
  capture [paused](audit/playback/paused.png),
  [updating](audit/playback/updating.png), and
  [advanced](audit/playback/advanced.png) snapshots. No new upstream download.
  All images were opened and visually inspected: dots remain during calculation
  and change after the update. The rendered snapshot advanced from
  `2026-10-11T00:13:22.112000Z` to `2026-10-11T00:14:22.112000Z`, with all 16,701
  states retained while pending, one position request at a time, changed real
  position coordinates, and no captured page exceptions.
- Final frontend checks: 8 browser tests passed (23.5 s), 5 unit tests passed
  (1.29 s runner duration), TypeScript/production build passed (Vite 4.48 s).
  Existing Astropy cache/runner-color and >500 kB bundle warnings remain. Backend
  tests were not rerun because this repair changes no backend files.

## Local check

Pull main, restart the frontend dev server, and reload Explore. Wait for the first
position snapshot, then press **Play** for 15 seconds. Dots should stay on screen
while “Calculating orbital positions…” appears, and move after each completed
update. The snapshot timestamp should advance. Press **Pause**: after any in-flight
update completes, both the snapshot and clock should stop changing. Motion remains
in jumps; dots can be hidden behind Earth normally.
