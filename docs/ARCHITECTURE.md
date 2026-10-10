# Architecture

Kessler is split into a FastAPI backend and a React/Vite frontend. The backend owns source retrieval, SQLite-backed caching, orbital mechanics, risk analysis, intervention optimization, and scientific provenance. The frontend owns interaction and visualization; visual interpolation is never used for scientific calculations.

Canonical backend units are UTC, meters, meters per second, kilograms, radians, and unit-interval probability. Reference-frame conversions are explicit at module boundaries.

## Processing paths

- `app.data`: rate-conscious source retrieval, checksum metadata, parsers, deduplication, and an indexed SQLite store. Both conjunction participants are indexed.
- `app.orbital`: OMM initialization through `sgp4`, vectorized `SatrecArray` catalog propagation, and time-aware Astropy TEME→ITRS conversion.
- `app.risk`: CCSDS CDM parsing, per-object RTN covariance rotation, inertial covariance combination under independence, encounter-plane projection, and numerical hard-body-disk integration.
- `app.maneuvers`: backward/forward DOP853 propagation with Earth gravity + J2, RTN impulses, local closest-approach refinement, constraint evaluation, and nondominated selection.
- `app.screening`: analytic minima across piecewise relative-trajectory segments so close passes between time samples are not missed by endpoint checks.
- `app.decay` and `app.cleanup`: bounded persistence scenarios and deterministic, budgeted marginal-benefit selection with shared-edge deduplication.
- `app.jobs`: bounded worker pool and observable optimization lifecycle.

The React app uses shared Zustand selection state, TanStack Query caching, lazy-loaded functional sections, and one GPU point buffer for catalog objects. The browser never calculates safety-critical geometry.
