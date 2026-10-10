from __future__ import annotations

from datetime import UTC, datetime
from math import floor

import astropy.units as u
import numpy as np
from astropy.coordinates import CartesianDifferential, CartesianRepresentation, ITRS, TEME
from astropy.time import Time
from astropy.utils import iers
from sgp4.api import Satrec, SatrecArray
from sgp4.omm import initialize

from app.models import Frame, OrbitalObject, ScienceMetadata, StateVector

iers.conf.auto_download = False
EARTH_RADIUS_M = 6_378_137.0


def satrec_from_object(obj: OrbitalObject) -> Satrec:
    satellite = Satrec()
    fields = {key: str(value) for key, value in obj.elements.raw_omm.items()}
    initialize(satellite, fields)
    return satellite


def _julian(timestamp: datetime) -> tuple[float, float]:
    if timestamp.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    jd = Time(timestamp.astimezone(UTC)).jd
    whole = floor(jd)
    return float(whole), float(jd - whole)


def _to_itrs(position_km: np.ndarray, velocity_km_s: np.ndarray, timestamp: datetime) -> tuple[np.ndarray, np.ndarray]:
    obstime = Time(timestamp)
    representation = CartesianRepresentation(position_km * u.km, differentials=CartesianDifferential(velocity_km_s * u.km / u.s))
    transformed = TEME(representation, obstime=obstime).transform_to(ITRS(obstime=obstime))
    return transformed.cartesian.xyz.to_value(u.m), transformed.cartesian.differentials["s"].d_xyz.to_value(u.m / u.s)


def propagate_object(obj: OrbitalObject, timestamps: list[datetime], frame: Frame = Frame.TEME) -> tuple[list[StateVector], list[str]]:
    satellite = satrec_from_object(obj)
    states: list[StateVector] = []
    errors: list[str] = []
    for timestamp in timestamps:
        jd, fraction = _julian(timestamp)
        error, position, velocity = satellite.sgp4(jd, fraction)
        if error:
            errors.append(f"{timestamp.isoformat()}: SGP4 error {error}")
            continue
        position_array, velocity_array = np.asarray(position), np.asarray(velocity)
        if frame == Frame.ITRS:
            position_m, velocity_m_s = _to_itrs(position_array, velocity_array, timestamp)
        elif frame == Frame.TEME:
            position_m, velocity_m_s = position_array * 1_000, velocity_array * 1_000
        else:
            raise ValueError("SGP4 propagation supports TEME or ITRS output")
        states.append(
            StateVector(
                timestamp=timestamp,
                frame=frame,
                position_m=tuple(float(x) for x in position_m),
                velocity_m_s=tuple(float(x) for x in velocity_m_s),
                metadata=ScienceMetadata(
                    source=obj.source,
                    model="SGP4" + (" + Astropy TEME→ITRS" if frame == Frame.ITRS else ""),
                    model_version="sgp4-2.25/astropy-7.2",
                    assumptions=["IERS data bundled with Astropy; polar-motion accuracy follows available table"] if frame == Frame.ITRS else [],
                ),
            )
        )
    return states, errors


def propagate_catalog_teme(objects: list[OrbitalObject], timestamp: datetime) -> tuple[np.ndarray, np.ndarray]:
    satellites = SatrecArray([satrec_from_object(obj) for obj in objects])
    jd, fraction = _julian(timestamp)
    errors, positions, _ = satellites.sgp4(np.asarray([jd]), np.asarray([fraction]))
    return errors[:, 0], positions[:, 0, :] * 1_000


def orbital_summary(state: StateVector) -> dict[str, float]:
    radius = float(np.linalg.norm(state.position_m))
    speed = float(np.linalg.norm(state.velocity_m_s))
    return {"geocentric_radius_m": radius, "approximate_altitude_m": radius - EARTH_RADIUS_M, "speed_m_s": speed}
