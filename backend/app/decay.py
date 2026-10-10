from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DecayScenario:
    name: str
    persistence_years: tuple[float, float] | None
    status: str


@dataclass
class DecayAssessment:
    status: str
    scenarios: list[DecayScenario]
    assumptions: list[str]
    warning: str


def assess_decay(perigee_altitude_m: float | None, mass_kg: float | None, area_m2: float | None) -> DecayAssessment:
    """Return broad LEO persistence bands, never a precise reentry date.

    The bands are intentionally conservative scenario categories, not a time-integrated
    atmosphere model. Higher area-to-mass ratios shorten the nominal range.
    """
    if perigee_altitude_m is None or mass_kg is None or area_m2 is None or mass_kg <= 0 or area_m2 <= 0:
        return DecayAssessment("unavailable", [], [], "Altitude, positive dry mass, and cross-sectional area are required.")
    altitude_km = perigee_altitude_m / 1_000
    ratio = area_m2 / mass_kg
    if altitude_km >= 1_000:
        ranges = [(200, 1_000), (100, 1_000), (50, 1_000)]
    elif altitude_km >= 700:
        ranges = [(50, 500), (20, 300), (8, 150)]
    elif altitude_km >= 500:
        ranges = [(10, 100), (3, 40), (1, 20)]
    elif altitude_km >= 350:
        ranges = [(1, 15), (0.3, 7), (0.1, 3)]
    else:
        ranges = [(0.05, 3), (0.02, 1), (0.005, 0.5)]
    factor = max(0.35, min(2.5, 0.01 / ratio))
    scenarios = [
        DecayScenario(name, (low * factor, high * factor), "broad_scenario_range")
        for name, (low, high) in zip(("low_drag", "nominal", "high_drag"), ranges)
    ]
    return DecayAssessment(
        "modeled_estimate", scenarios,
        [f"Constant effective area-to-mass ratio {ratio:.6g} m²/kg", "Broad altitude bands; solar cycle and attitude are not propagated"],
        "Scenario bands are cleanup-priority context, not precise reentry forecasts.",
    )
