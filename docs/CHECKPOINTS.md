# Checkpoint log

## Playback flashing repair — 2026-10-11 UTC

- Keep completed same-catalog/filter positions and same-object orbit visible while
  fetching the next timestamp; pace playback to completed requests rather than
  accumulating timestamp queries every second. Exact-time keys repair Now within
  the same minute. A visible snapshot timestamp distinguishes displayed from
  requested time. Playback remains stepwise, not smooth or fixed wall-clock speed.
- Slow-response browser regressions and separate real 16,701-object visual checks:
  [PLAYBACK_REPAIR.md](PLAYBACK_REPAIR.md). No backend/dependency changes, no new
  upstream catalog download, and no hosted deployment.
- Final checks: **8 browser tests passed** (23.5 s), **5 frontend unit tests passed**
  (1.29 s runner duration), production build passed (Vite 4.48 s). Existing warnings
  remain; no backend retest for this frontend-only change.

## Catalog-loading repair — 2026-10-10 UTC (after the audit below)

- Automatic background GP loading, coordinated refresh/status endpoints, policy-aware
  validated GP caching, snapshot replacement, visible retry/fallback, full browser
  pagination, and batched positions API are implemented and tested.
- One real HTTP-200 active-group download yielded 16,701 objects. The same download
  was reused for runtime startup/refresh; all 16,701 ITRS states returned without
  propagation errors in the direct browser inspection. Screenshots were opened and
  visually inspected; six-digit ID search, selection, and cached refresh worked.
- Backend: **34 passed** in 2.11 s; frontend: **5 passed** (1.33 s runner duration);
  browser: **6 passed** in 12.9 s; production build passed (Vite 6.28 s). Third-party warning and
  large-chunk limitations remain. Browser tests distinguish mocked loading states
  from the separate real-catalog inspection.
- Scope remains active-group loading, not complete debris ingestion or all original
  stage acceptance. Orbit coverage, current encounter workflow, optimizer defects,
  GCAT joins, secondary screening, and scientific Cleanup inputs remain unfinished.
- Details, provenance, commands, visual evidence, and local checks:
  [CATALOG_LOADING.md](CATALOG_LOADING.md). The section below records the earlier
  documentation-only audit and its earlier test counts; it is historical evidence.

## Audit correction — 2026-10-10 UTC

This log supersedes the original completion claims. Kessler is a partial prototype,
not a completed execution of the original stages 0–12. Passing existing tests does
not establish that every requirement of a stage works.

This repair changes documentation and visual evidence only. No application,
dependency, test, or deployment behavior was changed. The single-object fallback,
partial orbit, historical-only planner, and other defects remain. See
[the feature audit](IMPLEMENTATION_AUDIT.md).

## Checks rerun for this correction

| Check | Command / working directory | Actual result | Evidence boundary |
| --- | --- | --- | --- |
| Backend | `../.venv/bin/python -m pytest -q` / `backend` | 21 passed in 1.36 s; one Starlette/AnyIO deprecation warning | Existing cases only, not all stage acceptance tests |
| Frontend unit | `npm test -- --run` / `frontend` | 1 passed; 1.60 s runner duration | Mocked shell/status, not real API or WebGL validation |
| TypeScript/production build | `npm run build` / `frontend` | Passed; Vite build 5.21 s | Compile/build only; Explore chunk 917.68 kB, >500 kB warning |
| Browser smoke | `npm run test:e2e -- --reporter=line` / `frontend` | 4 passed in 10.3 s | Archived-object shell, empty encounters/methods, historical optimizer, placeholder-input cleanup |
| Runtime API | GET `/api/health` and `/api/data/status` | Healthy; 1 object, 0 encounters; GP archived/stale, SOCRATES/GCAT unavailable | Current cloud runtime; stored previous 403 errors, not new upstream probes |
| Visual inspection | Chromium/Playwright, 1440×1000, software WebGL | Six screenshots opened and inspected; active WebGL; camera drag, orbit toggle, search-empty state, navigation, both planners exercised | Desktop archived workflow only; not mobile/full catalog/hosted deployment |

No captured page exceptions or console warnings during visual inspection. A console
resource 404 was recorded; `/favicon.ico` independently returned 404. Do not claim a
clean browser console. The E2E runner also emitted a NO_COLOR/FORCE_COLOR warning.

## Baseline stage status before the catalog-loading repair

### Stage 0 — setup: implemented and tested for this cloud checkout

Dependencies are installed, existing API/Vite services respond, and the checks
above run. Not verification of a fresh clone on every supported OS.

### Stage 1 — models/API foundation: limited; incomplete

Test evidence: state-vector timezone rejection, one invalid trajectory-window
request, structured validation, health/OpenAPI, and shell. Complete typed responses,
scientific metadata, finite-value validation, timezone checks on all request fields,
and frontend structured-error handling are incomplete.

### Stage 2 — ingestion: incomplete, with external access limitations

Real OMM fixture parsing and synthetic SOCRATES unit conversion/two-participant
lookup are tested. The test named “parses_and_deduplicates” uses one record and
does not exercise duplicates. No GCAT parser/join, source-cache recovery, or
restart-persistence test exists in the current suite.

Active-only GP coverage, incomplete classification/physical joins, pre-validation
cache writes, and retained old snapshots are code limitations independent of 403.
Previous official-source requests in this cloud returned 403, blocking live
demonstration here; local/Modal access is unknown, not proven blocked.

### Stage 3 — propagation/globe: limited; incomplete

Real SGP4, OMM, TEME-to-ITRS code, GPU points, and orbit controls exist. Tests cover
finite/deterministic TEME output, SI scale, and two ordered timestamps, not frame
roundtrips or full orbit coverage. Visual inspection confirms Earth, a marker after
rotation, camera movement, and a partial orbit. UI requests 90 minutes, not the
object's period. API batching and catalog-scale animation are not integrated.

### Stage 4 — current encounters: incomplete

Both participant indexes are tested using synthetic CSV; empty wording is
browser-tested. Time/search filters, details, trajectory integration, and local
numerical TCA refinement are missing. Analysis samples reported TCA and ignores
refinement_window_seconds. No real SOCRATES schema/current encounter flow verified.

### Stage 5 — probability: historical core tested; generic integration incomplete

Two NASA fixture integrals match published values at relative tolerance 7e-4:
approximately 0.02117381156 and 0.0001082494810. RTN orthonormality and one invalid
covariance are tested. Independent NASA numerical reference, generic CDM frames/
units, conditioning, and UI risk workflows remain incomplete/unverified. The
current-encounter assumed-Pc branch uses XY instead of the encounter plane.

### Stage 6 — maneuver simulation: limited; incomplete

DOP853 gravity+J2, RTN impulses, and modified-trajectory minimization exist. One
synthetic case checks zero-impulse separation within 1 m and distinct signed
along-track outcomes. Generic epoch/frame validity, convergence, equally refined
baseline comparison, supported modified Pc, returned comparison trajectories, and
frontend simulation controls are not verified/complete.

### Stage 7 — optimization: limited; incomplete

Browser runs a real 18-candidate historical computation, not a validation of its
search/constraints. Default enumeration exhausts the budget at the first burn time.
Sensitivity search, combined corrections, probability targets, cancellation/time
budgets, and incremental progress are absent. Worker count is bounded; queued and
stored jobs are not. No optimizer-specific correctness unit tests exist.

### Stage 8 — screening: standalone function tested; integration incomplete

Two synthetic straight-line cases exercise intersample crossing and a distant
object. They do not establish conservative curved-orbit coverage. Optimizer never
calls the function; results remain UNSCREENED. Internal “complete” status is not
evidence of complete catalog/horizon safety screening.

### Stage 9 — decay/cleanup: selection core tested; scientific pipeline incomplete

Synthetic cleanup tests cover budgets and a shared-edge non-double-counting case,
not catalog-grounded ranking or priority sensitivity. UI supplies arbitrary effort,
constant exposure/consequence, and unsupported persistence; GCAT is not joined.
Decay tests exercise missing inputs and sensitivity of hardcoded bands, not
scientific lifetime validation. Decay has no API/UI integration.

### Stage 10 — frontend integration: incomplete

Five sections render; four smoke flows pass. Avoidance ignores selected current
encounters and always uses the first historical reference. Baseline/modified
comparison, full controls, live progress, and comprehensive errors are absent.
Filters affect list, not markers. Original flows A–E are not covered end to end.
Visual source-status badges are clipped/mis-shaped.

### Stage 11 — reliability/performance: limited measurements; incomplete

Checks above pass within stated scope. Previous SGP4 numbers duplicate one OMM and
exercise a helper, not positions API or globe; benchmarks were not rerun here.
Cache recovery, simultaneous requests, full-catalog performance, optimizer
correctness/runtime limits, and the current-data end-to-end pipeline are unverified.

### Stage 12 — deployment: prepared; hosted verification unavailable

Modal/Vercel configuration and instructions exist. Two local mocked-commit tests
verify lifecycle/refresh ordering and failure reporting, not real Modal storage.
Previous SDK import was local only. No remote image build/deployment/hosted smoke
test performed; credentials are not configured here. Docker fixture layout has a
known mismatch with PROJECT_ROOT, independent of credentials. Jobs are in memory.

## Next task recorded at the baseline audit

Repair catalog loading/coverage (repair-list item 2), then snapshots (item 3).
Verify documented queries, parser fixtures, counts/categories, participant records,
and honest offline/error behavior before calling ingestion complete. This
documentation-only change does not start those repairs.
