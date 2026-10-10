# Checkpoint log

Recorded from commands actually run on 2026-10-10 UTC.

## Stage 0 — repository and setup: complete

- Detected Python 3.12.14 and Node 24.19.0; installed pinned backend dependencies into `.venv` and 223 npm packages.
- Backend, Vite, HTTP health, pytest, Vitest, and TypeScript production build all ran successfully.
- npm's unwritable default cache was corrected with a writable cache without disabling TLS or integrity checks.

## Stage 1 — shared models and API foundation: complete

- Added UTC-aware typed scientific models, SI units, explicit frames, provenance, settings, CORS, structured validation errors, OpenAPI, frontend API client, persistent selection, and five-section navigation.
- Validation tests reject naive timestamps and invalid windows. API/OpenAPI and frontend shell tests pass.

## Stage 2 — real-data ingestion: implemented but externally limited

- Added GP OMM, SOCRATES CSV, and GCAT TSV adapters; SHA-256/status cache metadata; TTLs; last-known-good behavior; deduplication; SQLite persistence; and two-participant encounter indexes.
- Live requests to all three official sources returned HTTP 403, including direct approved retries. Counts are not fabricated.
- Archived real Vanguard 1 OMM is loaded and explicitly marked stale; current encounters remain empty with correct coverage wording.

## Stage 3 — SGP4 and globe: complete for loaded coverage

- Actual `sgp4` OMM propagation, vectorized `SatrecArray`, Astropy TEME→ITRS conversion, trajectory API, and React Three Fiber Earth/GPU points/orbit controls are implemented.
- Determinism, finite values, SI scale, and monotonic trajectory timestamps pass.
- Benchmarks: 100 / 1,000 / 10,000 propagators in 0.00210 / 0.01450 / 0.21798 s; zero errors.

## Stage 4 — current close approaches: implemented but no live dataset

- Indexed lookup, filtering/pagination, SOCRATES external metric labeling, encounter view, empty coverage state, and current-element analysis path are implemented.
- Parser/unit/index tests pass. Live SOCRATES data is unavailable due HTTP 403, so current encounter refinement cannot be demonstrated truthfully.

## Stage 5 — collision probability: complete for historical validation

- Implemented CCSDS CDM parser, separate RTN bases, covariance rotation/combination, encounter plane, conditioning validation, and numerical 2D Gaussian hard-body integration.
- Terra / Iridium-33 debris: calculated `0.02117381156`, published `0.02117`.
- Terra / SL-16 debris: calculated `0.0001082494810`, published `0.0001082`.
- Invalid covariance fails safely; ordinary encounters without covariance return unavailable unless an assumption is explicit.

## Stage 6 — dynamic maneuver simulation: complete with documented force-model limits

- Added DOP853 Earth-gravity + J2 propagation, RTN impulses, backward burn timing, forward propagation, and bounded closest-approach refinement.
- Tests verify zero-delta-v baseline reproduction and distinguish positive/negative along-track interventions.

## Stage 7 — maneuver optimization: complete for nominal-clearance objective

- Dynamic timing/direction/magnitude candidates, hard constraints, numerical refinement, nondominated selection, bounded asynchronous jobs, progress/status, and frontend polling are integrated.
- Fresh 18-candidate historical-state run completed in 1.54 s with three nondominated solutions.
- Probability optimization remains unavailable because maneuver covariance propagation is not implemented; UI states this explicitly.

## Stage 8 — targeted secondary screening: implemented but not applied to historical UI case

- Piecewise relative-trajectory segments use analytic segment minima instead of endpoint-only checks.
- Synthetic between-sample collision and distant-object rejection tests pass.
- Historical NASA cases are correctly not mixed with today's catalog; interactive results are labeled `UNSCREENED`.

## Stage 9 — decay and cleanup: implemented with proxy limits

- Added bounded low/nominal/high drag persistence bands with unavailable states for missing mass/area.
- Added deterministic budgeted marginal-benefit cleanup optimization and shared-edge deduplication.
- Budget response, priority machinery, missing-input, scenario sensitivity, and edge double-counting tests pass.

## Stage 10 — frontend integration: complete for available data

- Explore, Close Approaches, Avoidance Planner, Cleanup Planner, and Data & Methods call real APIs; primary actions report errors and no control is intentionally inert.
- Chromium E2E: 4 passed—catalog/globe shell, navigation and empty coverage, fresh maneuver optimization, and cleanup optimization.

## Stage 11 — reliability and performance: complete for offline coverage

- Backend: 19 passed, one third-party Starlette deprecation warning.
- Frontend unit: 1 passed. Browser: 4 passed. Production build passed.
- Optimizer, batch SGP4, SQLite restart behavior, stale/unavailable source states, and deterministic scientific regressions were exercised.
- Full live-catalog benchmark is blocked by upstream access and is not claimed.

## Stage 12 — deployment readiness: complete, not deployed

- Standard ASGI startup, Dockerfile, Vercel SPA config, environment examples, CORS/API URL, cache persistence, and refresh cadence are documented.
- Added a concrete Modal deployment in `modal_app.py` with Python 3.12, two CPUs, 2 GiB RAM, a persistent `kessler-data` Volume, and a single backend container for the current in-memory job manager.
- Installed the pinned Modal SDK (`requirements-modal.txt`, 1.6.1) and verified the deployment definition imports successfully without cloud calls.
- Added persistence lifecycle/refresh tests: full backend suite now reports **21 passed**. Tests verify a failed Volume commit cannot be reported as a successful refresh.
- Modal remote image build and hosted smoke checks remain unrun: this environment has no Modal token bindings or credential configuration. This implementation is being committed and published to GitHub at the user's request so it can be deployed from a clone.
- Deployment was not authorized and no paid service was provisioned.

## Feature audit

### Implemented and tested

- Typed API/OpenAPI, SQLite/cache foundation, OMM/SOCRATES/GCAT parsers, SGP4 and frame conversion, WebGL Earth, NASA-validated collision probability, dynamic J2 maneuvers, asynchronous optimizer, targeted screening algorithm, decay scenarios, cleanup optimizer, and all five frontend sections.

### Implemented but limited

- Globe/catalog: one archived real object because live GP is blocked.
- Close approaches: complete path but no live SOCRATES rows in this environment.
- Maneuver risk: nominal clearance only after intervention; fixed covariance is not presented as calibrated propagated risk.
- Secondary screening: algorithm tested, but historical UI results remain unscreened by design.
- Decay and cleanup: broad transparent proxies only.

### Unavailable or blocked

- Live CelesTrak/GCAT refresh and full-catalog counts (HTTP 403).
- Operational covariance feeds, full covariance propagation, global all-pairs screening, precise reentry prediction, and real mission costs/vehicle availability.
- Cloud deployment, because authorization and provider credentials were not supplied.
