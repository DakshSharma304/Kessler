from datetime import UTC, datetime

from app.cleanup import optimize_cleanup
from app.maneuvers import simulate_maneuver
from app.models import (
    CleanupCandidate, CleanupOptimizeRequest, EncounterEdge, Frame,
    ScienceMetadata, StateVector,
)


def state(position, velocity) -> StateVector:
    return StateVector(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC), frame=Frame.EME2000,
        position_m=position, velocity_m_s=velocity,
        metadata=ScienceMetadata(source="synthetic numerical regression", model="state fixture", model_version="1"),
    )


def test_nonzero_maneuver_changes_computed_trajectory() -> None:
    first = state((7_000_000, 0, 0), (0, 7_500, 0))
    second = state((7_000_100, 0, 0), (0, 7_500, 10))
    baseline = simulate_maneuver(first, second, 600, (0, 0, 0))
    positive = simulate_maneuver(first, second, 600, (0, 0.2, 0))
    negative = simulate_maneuver(first, second, 600, (0, -0.2, 0))
    assert abs(baseline.modified_separation_m - baseline.baseline_separation_m) < 1.0
    assert positive.modified_separation_m != negative.modified_separation_m
    assert positive.delta_v_magnitude_m_s == 0.2


def test_cleanup_budget_and_shared_edges() -> None:
    candidates = [
        CleanupCandidate(object_id="A", name="A", effort=2, persistence=1, exposure=1, consequence=1),
        CleanupCandidate(object_id="B", name="B", effort=2, persistence=.9, exposure=.9, consequence=.9),
        CleanupCandidate(object_id="C", name="C", effort=2, persistence=.2, exposure=.2, consequence=.2),
    ]
    request = CleanupOptimizeRequest(
        candidates=candidates,
        edges=[EncounterEdge(object_a="A", object_b="B", weight=10)],
        budget=4,
    )
    result = optimize_cleanup(request)
    assert result.total_effort <= 4
    assert len(result.selected) == 2
    # The A-B edge is consumed by the first endpoint and is not credited twice.
    assert sum(item.marginal_benefit for item in result.selected) < 20


def test_cleanup_budget_changes_portfolio_size() -> None:
    candidates = [CleanupCandidate(object_id=str(i), name=str(i), effort=1, persistence=.5, exposure=.5, consequence=.5) for i in range(4)]
    one = optimize_cleanup(CleanupOptimizeRequest(candidates=candidates, budget=1))
    three = optimize_cleanup(CleanupOptimizeRequest(candidates=candidates, budget=3))
    assert len(one.selected) == 1
    assert len(three.selected) == 3
