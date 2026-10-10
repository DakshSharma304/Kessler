# Deployment

## Local

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci
```

Then run `../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000` from `backend/` and `npm run dev -- --host 0.0.0.0` from `frontend/`.

## Backend: Modal

The repository provides `modal_app.py`, which uploads the backend and scientific fixtures into a Python 3.12 image and serves FastAPI through `@modal.asgi_app()`. It creates a persistent Modal Volume named `kessler-data`, mounted at `/var/lib/kessler`, and commits cache/SQLite changes after data refreshes and during startup/shutdown. Dependencies are installed from the same pinned backend requirements used locally.

Run these commands **on your computer, from the root of a clone containing the implementation**:

```bash
python -m pip install -r requirements-modal.txt
python -m modal setup
python -m modal deploy modal_app.py
```

The account setup opens Modal's login flow. The deploy command prints a public HTTPS endpoint; use that exact origin as the backend URL below. For a temporary development endpoint, use `python -m modal serve modal_app.py` instead of `deploy`.

Verify the endpoint, replacing the sample hostname with the URL Modal prints:

```bash
curl --fail https://YOUR-MODAL-ENDPOINT.modal.run/api/health
curl --fail https://YOUR-MODAL-ENDPOINT.modal.run/api/reference-encounters
```

### Connect Vercel

1. Import the GitHub repository into Vercel; select `frontend` as its root directory.
2. Set `VITE_API_URL` to Modal's HTTPS origin, with no trailing slash or `/api` suffix.
3. Build with `npm run build`; use output directory `dist`.
4. Copy the frontend's production origin and redeploy Modal with it allowed by CORS:

```bash
KESSLER_CORS_ORIGINS=https://YOUR-PROJECT.vercel.app python -m modal deploy modal_app.py
```

For PowerShell, use:

```powershell
$env:KESSLER_CORS_ORIGINS = "https://YOUR-PROJECT.vercel.app"
python -m modal deploy modal_app.py
```

You can comma-separate multiple exact frontend origins, including `http://localhost:5173` for local testing against Modal. Preview deployments have different origins and need to be explicitly allowed. If `VITE_API_URL` changes, redeploy Vercel because Vite reads it at build time.

### Populate live data

After deployment, request one refresh and check the returned statuses:

```bash
curl --fail -X POST https://YOUR-MODAL-ENDPOINT.modal.run/api/data/refresh
curl --fail https://YOUR-MODAL-ENDPOINT.modal.run/api/data/status
```

This request downloads public data from Modal's runtime; cloud-onboarding network settings do not control Modal's network. An upstream rejection there must be diagnosed from that response. Refreshes are manual in this deployment. If you add a scheduler, respect the GP/SOCRATES update cadence and avoid repeated retries after non-200 responses.

### Runtime and persistence limits

The function uses two CPU cores and 2 GiB of memory, permits at most one active container, and scales down after 300 seconds idle. Concurrent HTTP requests can share the same API process. This preserves the current in-memory job lookup within an active container and avoids multiple SQLite writers across separate containers. Poll an optimization job promptly; jobs and their results do not survive container replacement or redeployment. The durable Volume preserves catalog/cache files, not the in-memory job manager. Multi-container operation requires durable shared jobs and a different database design.

The endpoint is public. The current prototype has no user authentication; do not share it as an unrestricted production service. Deploying and using Modal consumes resources under your account's plan. No deployment was performed by the agent because no Modal account credentials were configured here.

The backend remains a standard ASGI application (`app.main:app`). `backend/Dockerfile` is an optional portable container configuration; Modal uses the image declaration in `modal_app.py` directly.

Environment variables:

- `KESSLER_DATA_DIR`: persistent SQLite/cache directory.
- `KESSLER_CACHE_TTL_GP_SECONDS`: GP refresh floor, default 7,200.
- `KESSLER_CACHE_TTL_SOCRATES_SECONDS`: SOCRATES refresh floor, default 39,600.
- `KESSLER_CORS_ORIGINS`: comma-separated frontend origins.
- `KESSLER_MAX_TRAJECTORY_SAMPLES`, `KESSLER_MAX_PROPAGATED_OBJECTS`, `KESSLER_MAX_CONCURRENT_JOBS`: compute limits.

`KESSLER_CORS_ORIGINS` is captured by `modal_app.py` from the deployment command's environment. The persistent data directory is set by the Modal image. Do not put Modal tokens in Vite variables or commit account credential files.

## Frontend

`frontend/vercel.json` configures a Vite build and SPA routing. Set `VITE_API_URL` at build time to the public HTTPS backend origin, and add the Vercel origin to `KESSLER_CORS_ORIGINS`.

Modal SDK and local ASGI/persistence tests have been run. Remote image building, deployment, and the actual hosted endpoint must be verified after account setup. Local tests alone do not establish a successful Modal deployment.
