# Architecture

Current loading update: app.catalog coordinates background initial GP loading,
status, and explicit refresh. GP payloads are validated before atomic cache
promotion, then replace the SQLite snapshot. The positions API now calls batched
SGP4/ITRS; the UI retrieves all pages, refreshes by catalog checksum, filters markers,
and reports coverage/errors. The module assessment below is the earlier baseline;
its loading/API/filtering gaps have been repaired. Other gaps remain. See
[the loading implementation](CATALOG_LOADING.md).

Kessler has a FastAPI backend and React/Vite frontend. Intended design: source
ingestion/science in backend, visualization in frontend. Current implementation is
partial: Cleanup constructs arbitrary proxy inputs in frontend, animation lacks
interpolation, and current selection does not flow into Avoidance. See
[the audit](IMPLEMENTATION_AUDIT.md).

SI-named fields and frames exist, but timezone, finite-value, provenance, and
frame/unit validation are incomplete across contracts.

## Existing modules and actual integration

- app.data: parsers, TTL downloads, checksums, SQLite objects/encounters/status,
  both-participant indexes. Cache writes precede validation, old rows accumulate,
  and GCAT rows are not joined.
- app.orbital: actual OMM/SGP4 and Astropy TEME→ITRS. SatrecArray is used by benchmark
  helper, not the looping positions API. Frontend trajectory window is 90 minutes.
- app.risk: per-object RTN rotation, independent covariance sum, encounter plane,
  Gaussian disk integral for two NASA fixtures. Generic frames/units incomplete;
  assumed-current Pc uses XY instead of encounter-plane calculation.
- app.maneuvers: gravity+J2 DOP853, RTN impulse, modified minimum. Baseline is not
  equivalently refined. Axis-candidate optimizer consumes default budget at first time.
- app.screening: standalone straight-line segment minima, never called by optimizer;
  no conservative curved-orbit error bounds.
- app.decay: hardcoded lifetime bands without physical validation/API/UI integration.
- app.cleanup: budgeted marginal-benefit/shared-edge math, synthetic-case tested.
  Frontend inputs arbitrary, not a GCAT/persistence/exposure pipeline.
- app.jobs: fixed worker count, in-memory jobs, unbounded queue/history, coarse
  progress, no cancellation or computation timeout.
- app.deployment: Modal commit middleware/lifecycle; tests use mock storage.

Frontend uses Zustand selection, TanStack Query, lazy sections, GPU points.
Selection survives navigation, but Avoidance ignores selectedEncounterId and chooses
first NASA reference. Filters affect list only; client discards position identity/
errors. Comparison trajectories are not integrated. Section-local time/controls
are not globally shared.
