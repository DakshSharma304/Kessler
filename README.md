# Kessler

Kessler is a partial research and educational orbital-debris intelligence prototype, **not operational flight software**. It has real SGP4 propagation, two historical NASA probability regressions, a limited dynamic historical maneuver planner, and a budgeted cleanup selection algorithm. The required current-encounter intervention workflow is not yet complete.

The backend now starts a background CelesTrak active-group load automatically. Explore and Data & Methods show loading, catalog coverage, source errors, and a Refresh/Retry control. Fresh data is cached for at least two hours; errors stop automatic retries and retain the previous catalog or explicitly archived Vanguard fallback. The browser loads every catalog page and renders up to 20,000 matching objects with an explicit limit notice. This is active-group coverage, not the full debris catalog.

Explore automatically starts GPU-interpolated playback between real, buffered SGP4 samples,
instead of requesting/clearing catalog positions each second. It prefetches the
next window and shows measured FPS. This is a display approximation, not scientific
state interpolation. There is no Play/Pause control; Now and the orbit toggle remain.
See [implementation and measured performance](docs/INTERPOLATED_PLAYBACK.md).

The orbit display still uses a fixed 90-minute partial path. Avoidance still ignores selected current encounters, and Cleanup still uses placeholder inputs (now explicitly limited to 5,000 candidates). See the [implementation audit](docs/IMPLEMENTATION_AUDIT.md), [checkpoints](docs/CHECKPOINTS.md), and [loading verification](docs/CATALOG_LOADING.md) for evidence and remaining limitations.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci
```

Run the services in separate terminals:

```bash
cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev -- --host 0.0.0.0
```

The API is at `http://localhost:8000`, OpenAPI at `/docs`, and the Vite UI at `http://localhost:5173`.

## Validation

```bash
cd backend && ../.venv/bin/pytest
cd frontend && npm test -- --run && npm run build
```

See `docs/` for architecture, data provenance, limitations, checkpoints, performance, and deployment details.

## Deploy with Modal + Vercel

From a clone containing this implementation, install the Modal CLI and link your account:

```bash
python -m pip install -r requirements-modal.txt
python -m modal setup
python -m modal deploy modal_app.py
```

Modal prints the backend HTTPS URL. Set `VITE_API_URL` to that URL in Vercel and deploy with root directory `frontend`. Set `KESSLER_CORS_ORIGINS` to the resulting Vercel origin and redeploy Modal. Detailed commands and persistence limits are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
