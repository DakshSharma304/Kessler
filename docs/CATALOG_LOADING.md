# Catalog loading repair

## Behavior

- Start the backend normally: its lifespan loads the previous SQLite snapshot or
  archived Vanguard immediately, then starts one background GP load. Health and UI
  remain available while the network request waits (30-second default timeout).
- Explore/Data & Methods show loading, source errors, coverage, download time, and
  Refresh/Retry. The catalog and header update without reloading the browser.
- GP query: https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=JSON
  Classification uses active-group membership, with debris/body name distinctions;
  group membership does not establish propulsion or actual maneuverability.
- Validate nonempty OMM records and initialize SGP4 before atomically promoting
  downloaded GP bytes. Replace the owned catalog snapshot transactionally only on
  valid data; retain good bytes/catalog on download or malformed-200 failures.
- Concurrent refreshes share one task. Fresh cache prevents repeat downloads for
  at least two hours. All non-200 responses stop automatic retries, do not follow
  redirects, and expose a two-hour cooldown. Restart does not repeatedly retry a
  recorded failure; an explicit retry is available after cooldown/access diagnosis.
- This is initial loading, not a recurring scheduler. Refresh after the cache ages
  uses the same policy. No new paid services or credentials are required locally.
- Browser retrieves all catalog pages and checks snapshot version consistency.
  The actual positions API uses batch SGP4 and batch TEME→ITRS conversion, preserving
  object identity/errors. Rendering is capped at 20,000 matches, visibly labeled;
  list renders 100 entries at a time with Show more. Search/filtering changes points.
- Modal's background load calls the configured Volume commit callback. Tests use
  mocks, not a remotely deployed Volume. Jobs remain ephemeral.

## Direct live and visual evidence — 2026-10-10 UTC

The documentation and live GP endpoint returned HTTP 200 this time. One actual GP
download contained 16,701 unique objects; all initialized successfully. The exact
download was validated/promoted into the ignored runtime cache and reused for
startup and refresh checks, avoiding a second upstream download within the update.
The cache promotion time is recorded as retrieved_at, slightly after the original
download. Full snapshot SHA-256:

`479737fbd3894844e3217bd1241a518ae4e22ded78d0cd26db39039bbc982d73`

The backend reported 16,694 active-category objects and 7 name-classified rocket
bodies in the active-group snapshot. The oldest element epoch was September 11,
2026; a newly fetched snapshot does not mean every element is current. Future
source results/counts can differ; this is not complete public-catalog coverage.

One warm local HTTP check retrieved all catalog pages in 1.585 s and requested/
received/parsed all ITRS positions in 1.831 s; see [performance scope](PERFORMANCE.md).
The live API and browser returned 16,701 propagated ITRS states with zero per-object
errors at the inspected timestamp. An active software-WebGL Chromium canvas was
inspected directly. Saved screenshots:

- [Loaded catalog and many real markers](audit/loading/live-catalog.png)
- [Six-digit ID 100981 search and selection](audit/loading/six-digit-search.png)
- [GP availability, coverage, and refresh control](audit/loading/methods.png)

Refreshing retained all objects without a browser reload or upstream redownload.
The selected filtered object can be occluded behind Earth in a particular camera
view; camera-focus/marker picking remains unfinished. Dense-catalog marker size is
reduced for readability; marker size is a visualization aid, not physical size.
No captured page exceptions or failed Playwright-tracked responses occurred in this
live inspection. No hosted Modal deployment or new SOCRATES/GCAT fetch was performed.

Four records from this actual download are preserved in
`data/fixtures/gp_active_sample.json` for deterministic tests; they are not a
production substitute for the live catalog. Original NASA/archived fixtures remain.

## Automated evidence

- Backend: 34 passed. New tests cover startup, concurrent coalescing, cache TTL,
  HTTP rejection/cooldown, malformed/empty/all-invalid 200 responses, cache restart,
  six-digit IDs, latest duplicate, serialized background persistence/failure, pagination/API
  integration, and batch/single propagation equivalence in TEME and ITRS.
- Frontend: 5 passed. New client tests cover all pages, snapshot-change rejection,
  object identity/errors, and structured backend errors.
- Playwright: 6 passed. Four existing offline flows plus explicit synthetic API
  tests of refresh-to-multiple-objects and rejection/fallback/cooldown. Tests use an
  isolated temporary database and disable real downloads; synthetic browser tests
  establish UI behavior, not live coverage. The separate inspection above uses real data.
- TypeScript/production build passed. The large Explore chunk warning remains;
  backend tests also report third-party Starlette and cloud Astropy-cache warnings.

Run tests:

```bash
cd backend
../.venv/bin/python -m pytest -q
```

```bash
cd frontend
npm test -- --run
npm run build
npx playwright install chromium
npm run test:e2e
```

If using an installed system Chromium, set PLAYWRIGHT_CHROMIUM_EXECUTABLE instead
of downloading a browser (the cloud run used /usr/bin/chromium). Backend launch in
Playwright still assumes a POSIX virtualenv; cross-platform launch remains limited.

## Exact local verification

1. Pull the updated main branch, stop/restart your Python backend, and reopen Explore.
2. Expect Loading live catalog, then Catalog loaded and many markers, not only
   archived Vanguard. If a source rejects access, expect an explicit error/fallback
   and next permitted retry time instead; report the exact displayed error.
3. Click Refresh catalog once. The loaded catalog should remain visible; within
   two hours it uses cached data, not a fresh upstream request.
4. Search for an object name or a six-digit ID present in your snapshot and select
   the result. Details should change. Clear search to restore the catalog markers.
5. Check Data & Methods: GP should show parsed records and a real count when loading
   succeeds. SOCRATES/GCAT may remain unavailable; this change does not load them.

No dependencies were added. KESSLER_AUTO_REFRESH_CATALOG defaults to true;
KESSLER_SOURCE_TIMEOUT_SECONDS defaults to 30. An existing environment setting of
false deliberately disables startup fetching. Partial orbits, current encounter
planning, GCAT/debris ingestion, and scientific Cleanup inputs are not repaired here.
