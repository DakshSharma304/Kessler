from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.data import CatalogStore, parse_gp_json, parse_socrates_csv
from app.models import Frame, ScienceMetadata, StateVector

FIXTURES = Path(__file__).parents[2] / "data" / "fixtures"


def test_science_timestamp_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        StateVector(
            timestamp=datetime(2026, 1, 1), frame=Frame.TEME,
            position_m=(1, 2, 3), velocity_m_s=(4, 5, 6),
            metadata=ScienceMetadata(source="test", model="test", model_version="1"),
        )


def test_real_omm_fixture_parses_and_deduplicates() -> None:
    objects, errors = parse_gp_json((FIXTURES / "gp_sample.json").read_bytes())
    assert not errors
    assert len(objects) == 1
    assert objects[0].name == "VANGUARD 1"
    assert objects[0].catalog_id == "5"
    assert objects[0].elements.epoch.tzinfo is not None


def test_socrates_schema_parses_units_and_both_index_paths(tmp_path: Path) -> None:
    payload = (
        "NORAD_CAT_ID_1,OBJECT_NAME_1,DSE_1,NORAD_CAT_ID_2,OBJECT_NAME_2,DSE_2,TCA,TCA_RANGE,TCA_RELATIVE_SPEED,MAX_PROB,DILUTION\n"
        "25544,ISS,1.2,20580,HST,2.3,2026-10-12T00:00:00,0.125,14.2,1.2e-5,0.8\n"
    ).encode()
    encounters, errors = parse_socrates_csv(payload, "fixture-sha")
    assert not errors
    assert encounters[0].separation_m == 125
    assert encounters[0].relative_speed_m_s == 14_200
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    store.upsert_encounters(encounters)
    assert store.encounters("25544")[0].encounter_id == encounters[0].encounter_id
    assert store.encounters("20580")[0].encounter_id == encounters[0].encounter_id
