import numpy as np

from app.decay import assess_decay
from app.screening import targeted_secondary_screening


def test_segment_screening_detects_between_sample_encounter() -> None:
    modified = np.array([[-100.0, 0, 0], [100.0, 0, 0]])
    third = np.array([[0, -100.0, 0], [0, 100.0, 0]])
    result = targeted_secondary_screening(modified, {"THIRD": third}, threshold_m=1)
    assert result.status == "complete"
    assert len(result.encounters) == 1
    assert result.encounters[0].nominal_separation_m == 0


def test_segment_screening_does_not_flag_distant_object() -> None:
    modified = np.array([[0.0, 0, 0], [100.0, 0, 0]])
    distant = np.array([[0, 50_000.0, 0], [100, 50_000.0, 0]])
    result = targeted_secondary_screening(modified, {"FAR": distant}, threshold_m=1_000)
    assert not result.encounters


def test_decay_missing_properties_is_unavailable() -> None:
    assert assess_decay(400_000, None, 2).status == "unavailable"


def test_decay_scenarios_are_bounded_and_sensitive() -> None:
    low_area = assess_decay(500_000, 1_000, 1)
    high_area = assess_decay(500_000, 1_000, 20)
    assert len(low_area.scenarios) == 3
    assert high_area.scenarios[1].persistence_years[1] < low_area.scenarios[1].persistence_years[1]
