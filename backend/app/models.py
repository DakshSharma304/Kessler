from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Availability(StrEnum):
    AVAILABLE = "available"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    ASSUMPTION_BASED = "assumption_based"


class Frame(StrEnum):
    TEME = "TEME"
    ITRS = "ITRS"
    EME2000 = "EME2000"


class ScienceMetadata(BaseModel):
    source: str
    model: str
    model_version: str
    availability: Availability = Availability.AVAILABLE
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StateVector(BaseModel):
    timestamp: datetime
    frame: Frame
    position_m: tuple[float, float, float]
    velocity_m_s: tuple[float, float, float]
    metadata: ScienceMetadata

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a UTC offset")
        return value


class OrbitalElements(BaseModel):
    epoch: datetime
    inclination_rad: float
    raan_rad: float
    eccentricity: float = Field(ge=0, lt=1)
    argument_of_perigee_rad: float
    mean_anomaly_rad: float
    mean_motion_rev_day: float = Field(gt=0)
    bstar: float
    raw_omm: dict[str, Any]


class PhysicalProperties(BaseModel):
    dry_mass_kg: float | None = Field(default=None, gt=0)
    dimensions_m: str | None = None
    shape: str | None = None
    status: str | None = None
    estimated: bool = False
    source: str = "GCAT"


class OrbitalObject(BaseModel):
    catalog_id: str
    name: str
    object_id: str | None = None
    category: Literal["active", "debris", "rocket_body", "unknown"] = "unknown"
    elements: OrbitalElements
    physical: PhysicalProperties | None = None
    source: str = "CelesTrak GP"


class DatasetStatus(BaseModel):
    name: str
    source_url: str
    availability: Availability
    retrieved_at: datetime | None = None
    dataset_timestamp: datetime | None = None
    checksum_sha256: str | None = None
    record_count: int = 0
    parsing_status: str = "not_loaded"
    error: str | None = None
    stale: bool = False


class Conjunction(BaseModel):
    encounter_id: str
    catalog_id_1: str
    object_name_1: str
    catalog_id_2: str
    object_name_2: str
    tca: datetime
    separation_m: float = Field(ge=0)
    relative_speed_m_s: float = Field(ge=0)
    socrates_max_probability: float | None = Field(default=None, ge=0, le=1)
    source_dataset_version: str
    source_prediction_timestamp: datetime | None = None
    coverage_note: str = "SOCRATES screening covers its published population and horizon; absence is not evidence of zero risk."


class PositionRequest(BaseModel):
    object_ids: list[str] = Field(min_length=1, max_length=20_000)
    timestamps: list[datetime] = Field(min_length=1, max_length=32)
    frame: Frame = Frame.ITRS


class PositionResult(BaseModel):
    object_id: str
    states: list[StateVector]
    errors: list[str] = Field(default_factory=list)


class TrajectoryRequest(BaseModel):
    object_id: str
    start: datetime
    end: datetime
    samples: int = Field(default=120, ge=2, le=1_000)
    frame: Frame = Frame.ITRS

    @field_validator("end")
    @classmethod
    def valid_window(cls, value: datetime, info):
        start = info.data.get("start")
        if start and value <= start:
            raise ValueError("end must be after start")
        return value


class EncounterAnalyzeRequest(BaseModel):
    encounter_id: str
    refinement_window_seconds: float = Field(default=300, gt=0, le=3_600)
    assumed_position_sigma_m: float | None = Field(default=None, gt=0, le=100_000)
    hard_body_radius_m: float = Field(default=10, gt=0, le=1_000)


class EncounterAnalysis(BaseModel):
    encounter: Conjunction
    refined_tca: datetime | None
    refined_separation_m: float | None
    refined_relative_speed_m_s: float | None
    calculated_probability: float | None
    probability_status: Literal["verified_input", "assumption_based", "unavailable"]
    metadata: ScienceMetadata


class ManeuverConstraints(BaseModel):
    max_delta_v_m_s: float = Field(default=1.0, gt=0, le=100)
    warning_time_seconds: float = Field(default=86_400, gt=60, le=30 * 86_400)
    earliest_burn_seconds_before_tca: float = Field(default=3_600, gt=0)
    latest_burn_seconds_before_tca: float = Field(default=86_400, gt=0)
    minimum_separation_m: float = Field(default=1_000, gt=0)
    allowed_directions: list[Literal["radial", "along_track", "normal"]] = Field(
        default_factory=lambda: ["radial", "along_track", "normal"]
    )
    candidate_count: int = Field(default=18, ge=3, le=100)


class ManeuverSimulationRequest(BaseModel):
    encounter_id: str | None = None
    state_1: StateVector | None = None
    state_2: StateVector | None = None
    burn_seconds_before_tca: float = Field(gt=0, le=30 * 86_400)
    delta_v_rtn_m_s: tuple[float, float, float]
    hard_body_radius_m: float = Field(default=10, gt=0)


class ManeuverResult(BaseModel):
    burn_seconds_before_tca: float
    delta_v_rtn_m_s: tuple[float, float, float]
    delta_v_magnitude_m_s: float
    baseline_separation_m: float
    modified_separation_m: float
    closest_approach_offset_seconds: float
    relative_speed_m_s: float
    calculated_probability: float | None = None
    probability_status: str = "unavailable"
    feasible: bool = True
    secondary_screening_status: Literal["unscreened", "partially_screened", "complete"] = "unscreened"
    warnings: list[str] = Field(default_factory=list)


class ManeuverOptimizeRequest(BaseModel):
    state_1: StateVector
    state_2: StateVector
    constraints: ManeuverConstraints = Field(default_factory=ManeuverConstraints)


class OptimizationResult(BaseModel):
    status: Literal["complete", "partial_results", "no_feasible_candidate", "time_budget_exceeded"]
    evaluated_candidates: int
    solutions: list[ManeuverResult]
    warnings: list[str]


class CleanupCandidate(BaseModel):
    object_id: str
    name: str
    effort: float = Field(gt=0)
    persistence: float = Field(ge=0, le=1)
    exposure: float = Field(ge=0)
    consequence: float = Field(ge=0)
    data_quality: Literal["high", "medium", "low"] = "low"


class EncounterEdge(BaseModel):
    object_a: str
    object_b: str
    weight: float = Field(ge=0)


class CleanupOptimizeRequest(BaseModel):
    candidates: list[CleanupCandidate] = Field(min_length=1, max_length=5_000)
    edges: list[EncounterEdge] = Field(default_factory=list, max_length=100_000)
    budget: float = Field(gt=0)
    priority: Literal["balanced", "persistence", "exposure", "consequence"] = "balanced"
    max_objects: int = Field(default=20, ge=1, le=100)


class CleanupSelection(BaseModel):
    candidate: CleanupCandidate
    marginal_benefit: float
    reason: str


class CleanupPortfolio(BaseModel):
    selected: list[CleanupSelection]
    alternatives: list[CleanupCandidate]
    total_effort: float
    modeled_benefit: float
    remaining_budget: float
    assumptions: list[str]
