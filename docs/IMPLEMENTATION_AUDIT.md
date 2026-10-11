# Implementation audit

Playback update (2026-10-11): display animation now uses GPU cubic-Hermite
interpolation between buffered real SGP4/ITRS samples, with bounded prefetch and FPS
monitoring/adaptive visual resolution. This supersedes the no-interpolation/stepwise
display assessments below; scientific and partial-orbit gaps remain. See
[INTERPOLATED_PLAYBACK.md](INTERPOLATED_PLAYBACK.md).

## Current update: catalog-loading repair

Since the baseline audit below, automatic GP startup/refresh, safe validated GP
cache promotion, active-group classification, full browser pagination, batch API
positions, marker filtering, and visible error/cooldown states were repaired.
One real snapshot of 16,701 objects was loaded and inspected. Source-status badges
are no longer stretched/clipped. Backend/frontend/browser counts are now 34/5/6.
See [loading evidence and remaining scope](CATALOG_LOADING.md). The previous 403s
remain historical; current GP fetching succeeded. SOCRATES/GCAT were not retried.

All sections below are the baseline assessment before that behavioral repair, not
claims that the repaired loading features remain absent. The overall current-
encounter intervention workflow and partial-orbit defect remain incomplete.

## Baseline audit

Audited 2026-10-10 UTC against the original KESSLER attachment, source, existing
tests, running API, and directly inspected screenshots. The attachment supplies
requirements; the current request covers repair item 1 only, not all implementation
stages.

**Overall status: partial prototype. The mandatory current-encounter intervention
workflow is incomplete. This change does not fix application behavior.**

## Status vocabulary

- **Implemented and tested:** only the precise behavior exercised by cited evidence.
- **Implemented but limited:** working code with restricted inputs/functionality.
- **Incomplete:** required behavior missing, disconnected, incorrect, or unverified.
- **Externally blocked/unavailable:** demonstrated outside prerequisite prevents
  verification; this does not excuse independent code defects.

## Implemented and tested, within a narrow scope

- Health/OpenAPI, one structured invalid-window response, and state-vector timezone
  rejection; not complete scientific API validation.
- One real archived OMM parse and deterministic/finite/SI-scale TEME propagation;
  not diverse catalog, duplicate resolution, or frame roundtrip validation.
- Synthetic SOCRATES conversion and both participant indexes; not published-schema
  evidence. Two NASA probability regressions, RTN orthonormality, and one invalid
  covariance rejection; not a generic validated CDM/risk pipeline.
- Synthetic zero/signed impulse checks, budget/shared-edge cleanup tests, and
  straight-line segment crossing tests; not integrated scientific workflows.
- Mocked persistence commit ordering/failure; not a real Modal Volume test.
- Mocked frontend shell, four offline browser smoke flows, and desktop observations
  below; not all original flows A–E.

Commands, counts, timings, warnings: [checkpoint evidence](CHECKPOINTS.md).

## Feature audit

| Feature | Actual status/evidence | Remaining limitation / repair |
| --- | --- | --- |
| Catalog ingestion | Limited: real archived OMM loads; adapter code exists | Active-only query; no debris/body coverage; unreliable classification; no initial live loading or UI refresh |
| Source cache | Incomplete: TTL/checksum/disk/SQLite code | Writes bytes before parsing; no tested last-known-good recovery, concurrent coordination, or snapshot retirement |
| GCAT | Incomplete: parser returns rows | Rows discarded after counting; no normalization, physical joins, or dedicated tests |
| Globe/orbits | Limited: Earth, marker, camera drag, partial line inspected | Fixed 90-minute ITRS path; no picking/focus/reset/speed; list filters leave markers unchanged |
| Catalog-scale API | Incomplete integration: SatrecArray helper exists | Endpoint loops per object; UI first 1,000 only; no full-catalog API/browser benchmark/interpolation |
| Current encounters | Incomplete: two-ID lookup tested; empty view inspected | Real-source schema, time/search filters, geometry view, numerical TCA refinement missing |
| Probability | Limited: two historical regressions | Wrong XY projection for assumed current Pc; CDM frames/units/radius assumed; independent NASA test missing |
| Simulation | Limited: real gravity+J2; synthetic regression | Epoch/frame checks and consistent refined baseline incomplete; no comparison trajectories or modified supported Pc |
| Optimizer | Limited: real historical browser computation | Default 18 candidates at first burn time; sensitivity/combined directions/risk objectives missing; constraints/search not fully tested |
| Jobs | Limited: worker pool/polling | Queue/history unbounded; progress 0.1 then 1; UI hides intermediate polls; no cancellation/time budget/restart durability |
| Screening | Standalone function tested; product incomplete | Never invoked by optimizer; no curved-orbit error bounds/refined minima; results UNSCREENED |
| Decay | Incomplete/unsupported estimate | Hardcoded lifetime bands lack cited physical validation; no API/UI integration; needs justified model or unavailable state |
| Cleanup | Limited selection math; placeholder-input browser run | Index-based effort, constant exposure/consequence, unsupported persistence; no GCAT pipeline/horizon/validated ranking |
| Frontend workflow | Incomplete: five sections render | Avoidance ignores selected encounter, always first NASA case; no solution/trajectory comparison or full error/progress controls |
| Deployment | Prepared, not remotely verified | No hosted smoke checks; Docker root mismatch; ephemeral jobs; cloud-specific Playwright paths |

## External blockers versus code defects

Previous official GP/SOCRATES/GCAT requests in this cloud returned 403; current
source status retains those errors. This correction did not retry sources.
Runtime: 1 archived object, 0 encounters. Local/Modal access is unknown, not proven
blocked. Modal credentials are not configured here; deployment was not attempted.

Query coverage, unsafe cache promotion, missing GCAT joins, partial trajectories,
wrong encounter/risk paths, incomplete optimizer, and disconnected UI/screening are
independent code defects, not consequences of source denial. No dataset or
scientific output was fabricated to make inspection pass.

## Direct visual verification

Actual active software-WebGL Chromium context, viewport 1440×1000. Screenshots were
opened and inspected, not just generated. Archived positions at the current
simulation time are not live tracking evidence.

| Screenshot | Observed behavior / limitation |
| --- | --- |
| [Explore](audit/visual/explore.png) | Earth, partial amber trajectory, 1 OBJECTS, Vanguard with ARCHIVED DATA |
| [Rotated Explore](audit/visual/explore-rotated.png) | Camera changes view; small marker on arc; trajectory still incomplete |
| [Close Approaches](audit/visual/close-approaches.png) | Empty coverage wording does not claim zero risk; no current encounter available |
| [Avoidance](audit/visual/avoidance.png) | Historical Terra/Iridium description; 18 computed candidates, 3 solutions all at 1-hour lead, UNSCREENED; no comparison |
| [Cleanup](audit/visual/cleanup.png) | Vanguard selected, effort 1, used 1/remaining 1; API/rendering evidence, not scientific ranking |
| [Data & Methods](audit/visual/methods.png) | Stored failures/stale fixture; clipped/mis-shaped badges; UI limitations omit several defects |

Also exercised hide/show orbit, no-match search, and navigation. Captured trajectory
request: 90 samples over 90 minutes, ITRS. Full-period coverage and correct common-
frame orbit-shape visualization remain repairs.

No captured page exceptions or console warnings. A resource 404 was recorded;
favicon.ico independently returns 404. No clean-console/mobile-layout claim.
No source refresh/live demonstration/hosted deployment performed.

## User verification for this documentation-only repair

1. Read corrected checkpoint statuses and this audit: unfinished features must not
   be advertised as complete, and blockers must be separate from code defects.
2. Compare local Explore with the screenshots. Archived Vanguard/partial path may
   remain: this documentation change does not repair them.
3. Run Find Best Maneuvers; confirm historical description and UNSCREENED labels.
   Report differences from the captured result screen.
4. Check Data & Methods and report your source statuses; local access may differ
   from this cloud. No upstream refresh is needed merely to validate this audit.

No restart is needed for documentation alone. Update the local clone only to read
the new docs/screenshots there.

## Next repair

Catalog loading/coverage is repair item 2 and has not started here. Continue actual
ingestion/cache/globe/encounter/risk/simulation/search/screening/cleanup/integration
repairs with requirement-specific evidence, not unchanged smoke-test counts.
