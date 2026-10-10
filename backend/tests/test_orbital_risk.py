from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from app.data import parse_gp_json
from app.models import Frame
from app.orbital import propagate_object
from app.risk import calculate_cdm_probability, calculate_collision_probability_2d, construct_rtn_basis, parse_cdm

FIXTURES = Path(__file__).parents[2] / "data" / "fixtures"


def test_sgp4_propagation_is_finite_deterministic_and_si() -> None:
    obj = parse_gp_json((FIXTURES / "gp_sample.json").read_bytes())[0][0]
    when = datetime(2020, 10, 13, 5, tzinfo=UTC)
    first, errors = propagate_object(obj, [when, when + timedelta(minutes=10)], Frame.TEME)
    second, _ = propagate_object(obj, [when], Frame.TEME)
    assert not errors
    assert np.all(np.isfinite(first[0].position_m))
    assert 6_000_000 < np.linalg.norm(first[0].position_m) < 20_000_000
    assert np.allclose(first[0].position_m, second[0].position_m)
    assert first[0].timestamp < first[1].timestamp


def test_rtn_basis_is_orthonormal() -> None:
    basis = construct_rtn_basis(np.array([7e6, 0, 0]), np.array([0, 7_500, 1]))
    assert np.allclose(basis.T @ basis, np.eye(3), atol=1e-12)
    assert np.linalg.det(basis) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("terra_iridium33.cdm", 0.02117), ("terra_sl16.cdm", 0.0001082)],
)
def test_nasa_cara_reference_probability(filename: str, expected: float) -> None:
    encounter = parse_cdm(FIXTURES / filename)
    calculated = calculate_cdm_probability(encounter)
    assert calculated == pytest.approx(expected, rel=7e-4)


def test_invalid_covariance_fails_safely() -> None:
    with pytest.raises(ValueError, match="positive definite"):
        calculate_collision_probability_2d(np.zeros(2), np.array([[1, 0], [0, -1]]), 10)
