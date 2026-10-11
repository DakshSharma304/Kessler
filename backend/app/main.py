from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.cleanup import optimize_cleanup
from app.catalog import CatalogLoader
from app.config import get_settings
from app.data import GCAT_URL, GP_URL, SOCRATES_URL, CatalogStore, SourceCache, parse_gcat_tsv, parse_gp_json, parse_socrates_csv
from app.jobs import JobManager
from app.maneuvers import optimize_maneuvers, simulate_maneuver
from app.models import (
    Availability, CatalogLoadingStatus, CleanupOptimizeRequest, DatasetStatus, EncounterAnalysis,
    EncounterAnalyzeRequest, Frame, ManeuverOptimizeRequest,
    ManeuverSimulationRequest, PositionRequest, PositionResult, ScienceMetadata,
    TrajectoryRequest, VisualizationWindowRequest, VisualizationWindow, VisualizationTrack,
)
from app.orbital import propagate_object, propagate_objects
from app.risk import calculate_cdm_probability, parse_cdm

settings = get_settings()
store = CatalogStore(settings.data_dir / "kessler.sqlite3")
source_cache = SourceCache(settings.data_dir / "cache", store, settings.source_timeout_seconds)
catalog_loader = CatalogLoader(store, source_cache, max(7_200, settings.cache_ttl_gp_seconds))
jobs = JobManager(settings.max_concurrent_jobs)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures"


def load_archived_fixture_if_empty() -> None:
    if store.count("objects"):
        loaded = store.objects(limit=1)
        statuses = {item.name: item for item in store.dataset_statuses()}
        gp_status = statuses.get("gp")
        if loaded and "Archived" in loaded[0].source and (not gp_status or gp_status.availability == Availability.UNAVAILABLE):
            store.set_dataset(DatasetStatus(
                name="gp", source_url=GP_URL, availability=Availability.STALE,
                dataset_timestamp=loaded[0].elements.epoch, record_count=store.count("objects"),
                parsing_status="archived_fixture", stale=True,
                error=f"Live refresh unavailable ({gp_status.error if gp_status else 'not attempted'}); archived real-data fixture remains loaded.",
            ))
        return
    fixture = FIXTURE_ROOT / "gp_sample.json"
    if not fixture.exists():
        return
    objects, errors = parse_gp_json(fixture.read_bytes(), source="Archived CelesTrak OMM fixture distributed by python-sgp4")
    store.upsert_objects(objects)
    store.set_dataset(DatasetStatus(
        name="gp", source_url=GP_URL, availability=Availability.STALE,
        dataset_timestamp=min((item.elements.epoch for item in objects), default=None),
        record_count=len(objects), parsing_status="archived_fixture",
        error="Live source has not been retrieved; archived real-data fixture loaded for offline validation.", stale=True,
    ))
    if errors:
        raise RuntimeError(f"archived OMM fixture failed to parse: {errors}")


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "cache").mkdir(parents=True, exist_ok=True)
    load_archived_fixture_if_empty()
    catalog_loader.persist = getattr(application.state, "commit_source_data", None)
    if settings.auto_refresh_catalog:
        catalog_loader.start(automatic=True)
    try:
        yield
    finally:
        await catalog_loader.close()


app = FastAPI(
    title="Kessler API", version=__version__,
    description="Orbital debris research and hypothetical intervention API. Not operational flight software.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": {"code": "INVALID_SCIENTIFIC_INPUT", "message": str(exc)}})


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [{"location": list(item["loc"]), "message": item["msg"], "type": item["type"]} for item in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "REQUEST_VALIDATION_FAILED", "message": "Request fields failed validation", "details": details}},
    )


@app.get("/api/health", tags=["system"])
async def health() -> dict:
    return {
        "status": "ok", "version": __version__, "model_version": "0.1.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "datasets": {"objects": store.count("objects"), "encounters": store.count("encounters")},
        "source_freshness": [item.model_dump(mode="json") for item in store.dataset_statuses()],
        "catalog_loading": catalog_loader.status(),
    }


@app.get("/api/data/status", tags=["data"])
async def data_status() -> list[DatasetStatus]:
    return [catalog_loader.status().source if item.name == "gp" else item for item in store.dataset_statuses()]


@app.get("/api/catalog/status", response_model=CatalogLoadingStatus, tags=["data"])
async def catalog_status() -> CatalogLoadingStatus:
    return catalog_loader.status()


@app.post("/api/catalog/refresh", response_model=CatalogLoadingStatus, tags=["data"])
async def refresh_catalog() -> CatalogLoadingStatus:
    result = await catalog_loader.refresh()
    if result.error:
        raise HTTPException(503, f"Catalog load could not finish: {result.error}")
    return result


@app.post("/api/data/refresh", tags=["data"])
async def refresh_data() -> dict:
    results: dict[str, dict] = {}
    loaded = await catalog_loader.refresh()
    if loaded.error:
        raise HTTPException(503, f"Catalog load could not finish: {loaded.error}")
    gp_status = loaded.source
    results["gp"] = gp_status.model_dump(mode="json")

    soc_payload, soc_status = await source_cache.fetch("socrates", SOCRATES_URL, settings.cache_ttl_socrates_seconds, "csv")
    if soc_payload:
        try:
            version = soc_status.checksum_sha256 or datetime.now(UTC).isoformat()
            encounters, errors = parse_socrates_csv(soc_payload, version)
            store.upsert_encounters(encounters)
            soc_status = soc_status.model_copy(update={"record_count": len(encounters), "parsing_status": "parsed", "error": "; ".join(errors[:5]) or soc_status.error})
            store.set_dataset(soc_status)
        except Exception as exc:
            soc_status = soc_status.model_copy(update={"parsing_status": "parse_failed", "error": str(exc)})
            store.set_dataset(soc_status)
    results["socrates"] = soc_status.model_dump(mode="json")

    gcat_payload, gcat_status = await source_cache.fetch("gcat", GCAT_URL, 86_400, "tsv")
    if gcat_payload:
        try:
            rows = parse_gcat_tsv(gcat_payload)
            gcat_status = gcat_status.model_copy(update={"record_count": len(rows), "parsing_status": "parsed"})
            store.set_dataset(gcat_status)
        except Exception as exc:
            gcat_status = gcat_status.model_copy(update={"parsing_status": "parse_failed", "error": str(exc)})
            store.set_dataset(gcat_status)
    results["gcat"] = gcat_status.model_dump(mode="json")
    return results


@app.get("/api/objects", tags=["catalog"])
async def list_objects(search: str = "", category: str | None = None, limit: int = Query(100, ge=1, le=1_000), offset: int = Query(0, ge=0)) -> dict:
    return {"items": [obj.model_dump(exclude={"elements": {"raw_omm"}}) for obj in store.objects(search, category, limit, offset)],
            "total": store.count("objects"), "limit": limit, "offset": offset,
            "catalog_version": catalog_loader.status().catalog_version}


@app.get("/api/objects/{catalog_id}", tags=["catalog"])
async def get_object(catalog_id: str):
    obj = store.object(catalog_id)
    if not obj:
        raise HTTPException(404, "Object not found in loaded catalog coverage")
    return obj


@app.post("/api/positions", response_model=list[PositionResult], tags=["orbital"])
async def positions(request: PositionRequest) -> list[PositionResult]:
    if len(request.object_ids) > settings.max_propagated_objects:
        raise HTTPException(413, "Too many objects requested")
    if len(request.object_ids) * len(request.timestamps) > 100_000:
        raise HTTPException(413, "Object/timestamp product exceeds 100,000 states")
    loaded = store.objects_by_ids(request.object_ids)
    results = await asyncio.to_thread(propagate_objects, list(loaded.values()), request.timestamps, request.frame)
    by_id = {item.object_id: item for item in results}
    return [by_id.get(object_id, PositionResult(object_id=object_id, states=[], errors=["Object unavailable in loaded catalog coverage"])) for object_id in request.object_ids]


@app.post("/api/visualization/window", response_model=VisualizationWindow, tags=["orbital"])
async def visualization_window(request: VisualizationWindowRequest) -> VisualizationWindow:
    # Five samples bound work to the existing 100,000-state API limit. This compact
    # response avoids repeating per-state metadata five times for the browser.
    version = catalog_loader.status().catalog_version
    timestamps = [request.start + timedelta(seconds=300 * index) for index in range(5)]
    results = await positions(PositionRequest(object_ids=request.object_ids, timestamps=timestamps, frame=Frame.ITRS))
    if catalog_loader.status().catalog_version != version:
        raise HTTPException(409, "Catalog changed while computing animation window; reload the snapshot")
    tracks, errors = [], []
    for result in results:
        errors.extend(f"{result.object_id}: {error}" for error in result.errors)
        if len(result.states) != len(timestamps):
            if not result.errors:
                errors.append(f"{result.object_id}: Incomplete animation samples; object omitted")
            continue
        tracks.append(VisualizationTrack(
            object_id=result.object_id,
            positions_m=[state.position_m for state in result.states],
            velocities_m_s=[state.velocity_m_s for state in result.states],
            metadata=result.states[0].metadata,
        ))
    return VisualizationWindow(timestamps=timestamps, catalog_version=version, tracks=tracks, errors=errors)


@app.post("/api/trajectories", tags=["orbital"])
async def trajectory(request: TrajectoryRequest) -> PositionResult:
    if request.samples > settings.max_trajectory_samples:
        raise HTTPException(413, "Trajectory sample limit exceeded")
    if request.end - request.start > timedelta(days=30):
        raise HTTPException(422, "Trajectory horizon exceeds 30 days")
    obj = store.object(request.object_id)
    if not obj:
        raise HTTPException(404, "Object not found in loaded catalog coverage")
    timestamps = [request.start + (request.end - request.start) * index / (request.samples - 1) for index in range(request.samples)]
    states, errors = propagate_object(obj, timestamps, request.frame)
    return PositionResult(object_id=request.object_id, states=states, errors=errors)


@app.get("/api/encounters", tags=["encounters"])
async def encounters(object_id: str | None = None, limit: int = Query(100, ge=1, le=1_000), offset: int = Query(0, ge=0)) -> dict:
    return {"items": store.encounters(object_id, limit, offset), "total": store.count("encounters"), "coverage": "SOCRATES candidates only; empty results do not mean zero collision risk."}


@app.post("/api/encounters/analyze", response_model=EncounterAnalysis, tags=["encounters"])
async def analyze_encounter(request: EncounterAnalyzeRequest) -> EncounterAnalysis:
    encounter = store.encounter(request.encounter_id)
    if not encounter:
        raise HTTPException(404, "Encounter not found in loaded SOCRATES coverage")
    first, second = store.object(encounter.catalog_id_1), store.object(encounter.catalog_id_2)
    if not first or not second:
        return EncounterAnalysis(
            encounter=encounter, refined_tca=None, refined_separation_m=None, refined_relative_speed_m_s=None,
            calculated_probability=None, probability_status="unavailable",
            metadata=ScienceMetadata(source="SOCRATES + CelesTrak GP", model="SGP4 local refinement", model_version="0.1.0", availability=Availability.UNAVAILABLE, warnings=["One or both current orbital records are unavailable."]),
        )
    states1, errors1 = propagate_object(first, [encounter.tca], Frame.TEME)
    states2, errors2 = propagate_object(second, [encounter.tca], Frame.TEME)
    if errors1 or errors2 or not states1 or not states2:
        raise HTTPException(422, "SGP4 refinement failed")
    delta_position = np.asarray(states2[0].position_m) - np.asarray(states1[0].position_m)
    delta_velocity = np.asarray(states2[0].velocity_m_s) - np.asarray(states1[0].velocity_m_s)
    probability = None
    probability_status = "unavailable"
    assumptions = []
    if request.assumed_position_sigma_m:
        from app.risk import calculate_collision_probability_2d
        probability = calculate_collision_probability_2d(delta_position[:2], np.eye(2) * request.assumed_position_sigma_m**2, request.hard_body_radius_m)
        probability_status = "assumption_based"
        assumptions.append(f"Isotropic position sigma of {request.assumed_position_sigma_m:g} m explicitly selected by user")
    return EncounterAnalysis(
        encounter=encounter, refined_tca=encounter.tca,
        refined_separation_m=float(np.linalg.norm(delta_position)), refined_relative_speed_m_s=float(np.linalg.norm(delta_velocity)),
        calculated_probability=probability, probability_status=probability_status,
        metadata=ScienceMetadata(source="SOCRATES + current CelesTrak GP", model="SGP4 geometry at reported TCA", model_version="0.1.0", assumptions=assumptions, warnings=["Current element epochs may differ from those used by SOCRATES."]),
    )


@app.get("/api/reference-encounters", tags=["research"])
async def reference_encounters() -> list[dict]:
    output = []
    for filename in ("terra_iridium33.cdm", "terra_sl16.cdm"):
        encounter = parse_cdm(FIXTURE_ROOT / filename)
        historical_states = [
            {
                "timestamp": encounter.tca,
                "frame": "EME2000",
                "position_m": item.position_m.tolist(),
                "velocity_m_s": item.velocity_m_s.tolist(),
                "metadata": {
                    "source": "NASA CARA historical CDM",
                    "model": "archived state vector",
                    "model_version": "CCSDS_CDM_VERS_1.0",
                    "availability": "available",
                    "assumptions": [],
                    "warnings": ["Historical validation state; never combine with the current catalog."],
                },
            }
            for item in encounter.objects
        ]
        output.append({
            "id": encounter.message_id, "mode": "historical_validation", "tca": encounter.tca,
            "participants": [item.name for item in encounter.objects],
            "published_probability": encounter.published_probability,
            "calculated_probability": calculate_cdm_probability(encounter),
            "states": historical_states,
            "source": "NASA CARA Analysis Tools CDM fixture",
        })
    return output


def _states_for_simulation(request: ManeuverSimulationRequest):
    if request.state_1 and request.state_2:
        return request.state_1, request.state_2
    if request.encounter_id:
        encounter = store.encounter(request.encounter_id)
        if not encounter:
            raise HTTPException(404, "Encounter not found")
        objects = store.object(encounter.catalog_id_1), store.object(encounter.catalog_id_2)
        if not all(objects):
            raise HTTPException(422, "Orbital records unavailable for encounter participants")
        first, errors1 = propagate_object(objects[0], [encounter.tca], Frame.TEME)
        second, errors2 = propagate_object(objects[1], [encounter.tca], Frame.TEME)
        if errors1 or errors2:
            raise HTTPException(422, "Failed to propagate encounter participants")
        return first[0], second[0]
    raise HTTPException(422, "Supply encounter_id or both state vectors")


@app.post("/api/maneuvers/simulate", tags=["maneuvers"])
async def simulate(request: ManeuverSimulationRequest):
    first, second = _states_for_simulation(request)
    return await asyncio.to_thread(simulate_maneuver, first, second, request.burn_seconds_before_tca, request.delta_v_rtn_m_s)


@app.post("/api/maneuvers/optimize", status_code=status.HTTP_202_ACCEPTED, tags=["maneuvers"])
async def optimize(request: ManeuverOptimizeRequest) -> dict:
    job = jobs.submit(optimize_maneuvers, request.state_1, request.state_2, request.constraints)
    return {"job_id": job.job_id, "status": job.status, "progress": job.progress}


@app.get("/api/jobs/{job_id}", tags=["jobs"])
async def get_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.as_dict()


@app.post("/api/cleanup/optimize", tags=["cleanup"])
async def cleanup(request: CleanupOptimizeRequest):
    return optimize_cleanup(request)


@app.get("/api/methods", tags=["system"])
async def methods() -> dict:
    return {
        "purpose": "Research and educational decision-support prototype; not operational flight software.",
        "models": [
            {"name": "SGP4", "use": "public catalog orbital propagation", "frame": "TEME; Astropy conversion to ITRS"},
            {"name": "Foster-style 2D Gaussian integral", "use": "covariance-supported historical collision probability"},
            {"name": "Earth gravity + J2", "use": "hypothetical impulsive maneuver comparisons"},
            {"name": "Greedy marginal-benefit portfolio", "use": "budget-constrained cleanup proxy selection"},
        ],
        "probability_states": ["verified_input", "assumption_based", "unavailable"],
        "limitations": [
            "SOCRATES MAX_PROB remains an external screening metric.",
            "No covariance means no calibrated Kessler collision probability unless an explicit uncertainty assumption is chosen.",
            "Maneuvers are hypothetical and omit execution error, tracking updates, propulsion feasibility, and covariance propagation.",
            "Secondary screening is currently unscreened unless explicitly reported otherwise.",
        ],
        "sources": [GP_URL, SOCRATES_URL, GCAT_URL, "https://github.com/nasa/CARA_Analysis_Tools"],
    }
