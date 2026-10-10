from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

from app.models import ManeuverConstraints, ManeuverResult, OptimizationResult, StateVector
from app.risk import construct_rtn_basis

MU = 3.986004418e14
J2 = 1.08262668e-3
EARTH_RADIUS_M = 6_378_137.0


def gravity_j2(_: float, state: np.ndarray) -> np.ndarray:
    position = state[:3]
    radius = np.linalg.norm(position)
    x, y, z = position
    z_ratio = (z / radius) ** 2
    factor = -MU / radius**3
    j2_factor = 1.5 * J2 * (EARTH_RADIUS_M / radius) ** 2
    acceleration = factor * np.array([
        x * (1 + j2_factor * (1 - 5 * z_ratio)),
        y * (1 + j2_factor * (1 - 5 * z_ratio)),
        z * (1 + j2_factor * (3 - 5 * z_ratio)),
    ])
    return np.concatenate((state[3:], acceleration))


def propagate_numerical(state: np.ndarray, duration_seconds: float, *, dense: bool = False):
    return solve_ivp(
        gravity_j2, (0.0, duration_seconds), state, method="DOP853",
        rtol=1e-10, atol=1e-7, max_step=max(1.0, abs(duration_seconds) / 100), dense_output=dense,
    )


def _array(state: StateVector) -> np.ndarray:
    return np.asarray((*state.position_m, *state.velocity_m_s), dtype=float)


def simulate_maneuver(
    state_1_tca: StateVector,
    state_2_tca: StateVector,
    burn_seconds_before_tca: float,
    delta_v_rtn_m_s: tuple[float, float, float],
) -> ManeuverResult:
    if state_1_tca.frame != state_2_tca.frame:
        raise ValueError("states must use the same inertial frame")
    if state_1_tca.frame.value == "ITRS":
        raise ValueError("maneuver simulation requires an inertial frame")
    state1_tca, state2_tca = _array(state_1_tca), _array(state_2_tca)
    backward1 = propagate_numerical(state1_tca, -burn_seconds_before_tca)
    backward2 = propagate_numerical(state2_tca, -burn_seconds_before_tca)
    if not backward1.success or not backward2.success:
        raise RuntimeError("failed to propagate to maneuver epoch")
    burn1, burn2 = backward1.y[:, -1], backward2.y[:, -1]
    basis = construct_rtn_basis(burn1[:3], burn1[3:])
    modified = burn1.copy()
    modified[3:] += basis @ np.asarray(delta_v_rtn_m_s)
    propagated1 = propagate_numerical(modified, burn_seconds_before_tca + 600, dense=True)
    propagated2 = propagate_numerical(burn2, burn_seconds_before_tca + 600, dense=True)
    if not propagated1.success or not propagated2.success:
        raise RuntimeError("modified propagation failed")
    lower = max(0.0, burn_seconds_before_tca - 600)
    upper = burn_seconds_before_tca + 600

    def separation_squared(time: float) -> float:
        delta = propagated2.sol(time)[:3] - propagated1.sol(time)[:3]
        return float(delta @ delta)

    minimum = minimize_scalar(separation_squared, bounds=(lower, upper), method="bounded", options={"xatol": 1e-4})
    relative = propagated2.sol(minimum.x) - propagated1.sol(minimum.x)
    baseline_separation = float(np.linalg.norm(state2_tca[:3] - state1_tca[:3]))
    magnitude = float(np.linalg.norm(delta_v_rtn_m_s))
    return ManeuverResult(
        burn_seconds_before_tca=burn_seconds_before_tca,
        delta_v_rtn_m_s=delta_v_rtn_m_s,
        delta_v_magnitude_m_s=magnitude,
        baseline_separation_m=baseline_separation,
        modified_separation_m=float(np.linalg.norm(relative[:3])),
        closest_approach_offset_seconds=float(minimum.x - burn_seconds_before_tca),
        relative_speed_m_s=float(np.linalg.norm(relative[3:])),
        warnings=[
            "Hypothetical two-body + J2 simulation; no execution error or covariance propagation.",
            "Secondary conjunction screening has not been performed.",
        ],
    )


def _nondominated(results: list[ManeuverResult]) -> list[ManeuverResult]:
    frontier = []
    for candidate in results:
        dominated = any(
            other.delta_v_magnitude_m_s <= candidate.delta_v_magnitude_m_s
            and other.modified_separation_m >= candidate.modified_separation_m
            and (other.delta_v_magnitude_m_s < candidate.delta_v_magnitude_m_s or other.modified_separation_m > candidate.modified_separation_m)
            for other in results
        )
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier, key=lambda item: (item.delta_v_magnitude_m_s, -item.modified_separation_m))


def optimize_maneuvers(state_1: StateVector, state_2: StateVector, constraints: ManeuverConstraints) -> OptimizationResult:
    earliest = min(constraints.earliest_burn_seconds_before_tca, constraints.latest_burn_seconds_before_tca)
    latest = max(constraints.earliest_burn_seconds_before_tca, constraints.latest_burn_seconds_before_tca)
    latest = min(latest, constraints.warning_time_seconds)
    if latest < earliest:
        return OptimizationResult(status="no_feasible_candidate", evaluated_candidates=0, solutions=[], warnings=["Available warning time excludes the requested maneuver window."])
    times = np.linspace(earliest, latest, max(3, min(8, constraints.candidate_count // 3)))
    magnitudes = np.linspace(constraints.max_delta_v_m_s / 4, constraints.max_delta_v_m_s, 3)
    directions = {
        "radial": np.array([1.0, 0.0, 0.0]),
        "along_track": np.array([0.0, 1.0, 0.0]),
        "normal": np.array([0.0, 0.0, 1.0]),
    }
    candidates: list[ManeuverResult] = []
    for time in times:
        for name in constraints.allowed_directions:
            for sign in (-1, 1):
                for magnitude in magnitudes:
                    if len(candidates) >= constraints.candidate_count:
                        break
                    dv = tuple(float(x) for x in directions[name] * sign * magnitude)
                    result = simulate_maneuver(state_1, state_2, float(time), dv)
                    result.feasible = result.delta_v_magnitude_m_s <= constraints.max_delta_v_m_s + 1e-12
                    if result.feasible:
                        candidates.append(result)
    feasible = [item for item in candidates if item.modified_separation_m >= constraints.minimum_separation_m]
    frontier = _nondominated(feasible or candidates)
    status = "complete" if feasible else "no_feasible_candidate"
    return OptimizationResult(
        status=status,
        evaluated_candidates=len(candidates),
        solutions=frontier[:10] if feasible else [],
        warnings=["Probability objective unavailable without covariance; optimized nominal clearance.", "Returned maneuvers are UNSCREENED against third objects."],
    )
