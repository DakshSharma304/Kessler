# Kessler

Kessler is a research and educational orbital-debris intelligence prototype. It ingests public orbital data, propagates catalog objects with SGP4, presents current conjunction screening information, and evaluates hypothetical avoidance and cleanup decisions. It is **not operational flight software**.

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
