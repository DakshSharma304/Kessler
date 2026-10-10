from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SecondaryEncounter:
    object_id: str
    interval_index: int
    time_fraction: float
    nominal_separation_m: float


@dataclass
class ScreeningResult:
    status: str
    encounters: list[SecondaryEncounter]
    screened_objects: int
    screened_intervals: int
    method: str = "piecewise-linear relative trajectory segments with analytic segment minima"


def _segment_minimum(relative_start: np.ndarray, relative_end: np.ndarray) -> tuple[float, float]:
    direction = relative_end - relative_start
    denominator = float(direction @ direction)
    fraction = 0.0 if denominator == 0 else float(np.clip(-(relative_start @ direction) / denominator, 0, 1))
    closest = relative_start + fraction * direction
    return fraction, float(np.linalg.norm(closest))


def targeted_secondary_screening(
    modified_positions_m: np.ndarray,
    catalog_trajectories_m: dict[str, np.ndarray],
    threshold_m: float,
) -> ScreeningResult:
    """Screen piecewise trajectory segments; endpoint-only sampling is deliberately avoided."""
    if modified_positions_m.ndim != 2 or modified_positions_m.shape[1] != 3 or len(modified_positions_m) < 2:
        raise ValueError("modified trajectory must contain at least two three-dimensional positions")
    encounters: list[SecondaryEncounter] = []
    complete = True
    screened = 0
    for object_id, trajectory in catalog_trajectories_m.items():
        if trajectory.shape != modified_positions_m.shape:
            complete = False
            continue
        screened += 1
        best: SecondaryEncounter | None = None
        for index in range(len(trajectory) - 1):
            relative_start = trajectory[index] - modified_positions_m[index]
            relative_end = trajectory[index + 1] - modified_positions_m[index + 1]
            fraction, separation = _segment_minimum(relative_start, relative_end)
            if separation <= threshold_m and (best is None or separation < best.nominal_separation_m):
                best = SecondaryEncounter(object_id, index, fraction, separation)
        if best:
            encounters.append(best)
    status = "complete" if complete else "partially_screened"
    return ScreeningResult(status, encounters, screened, len(modified_positions_m) - 1)
