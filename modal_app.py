"""Deploy from the repository root: modal deploy modal_app.py.

Set KESSLER_CORS_ORIGINS to the frontend's exact origin before deploying.
No Modal credentials or local .env files are copied into the runtime image.
"""

import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent
REMOTE_ROOT = "/opt/kessler"
DATA_DIR = "/var/lib/kessler"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements(str(ROOT / "backend" / "requirements.txt"))
    .env({
        "PYTHONPATH": f"{REMOTE_ROOT}/backend",
        "KESSLER_DATA_DIR": DATA_DIR,
        "KESSLER_CORS_ORIGINS": os.environ.get(
            "KESSLER_CORS_ORIGINS", "http://localhost:5173"
        ),
    })
    .workdir(f"{REMOTE_ROOT}/backend")
    .add_local_dir(
        ROOT / "backend" / "app",
        remote_path=f"{REMOTE_ROOT}/backend/app",
        ignore=["**/__pycache__/**", "**/*.pyc"],
    )
    .add_local_dir(ROOT / "data" / "fixtures", remote_path=f"{REMOTE_ROOT}/data/fixtures")
)

app = modal.App("kessler", image=image)
data_volume = modal.Volume.from_name("kessler-data", create_if_missing=True)


@app.function(
    volumes={DATA_DIR: data_volume},
    cpu=2,
    memory=2048,
    timeout=300,
    min_containers=0,
    max_containers=1,
    scaledown_window=300,
)
@modal.concurrent(max_inputs=16)
@modal.asgi_app()
def api():
    from app.deployment import persist_source_data
    from app.main import app as fastapi_app

    return persist_source_data(fastapi_app, data_volume.commit.aio)
