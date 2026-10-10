from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.integrate import quad


@dataclass
class CdmObject:
    designator: str
    name: str
    position_m: np.ndarray
    velocity_m_s: np.ndarray
    covariance_rtn_m2: np.ndarray


@dataclass
class CdmEncounter:
    message_id: str
    tca: datetime
    hard_body_radius_m: float
    published_probability: float | None
    objects: tuple[CdmObject, CdmObject]


def _number(value: str) -> float:
    return float(value.split("[")[0].strip())


def parse_cdm(path: Path) -> CdmEncounter:
    common: dict[str, str] = {}
    object_sections: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    hard_body_radius = 10.0
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        hbr = re.search(r"COMMENT HBR\s*=\s*([0-9.eE+-]+)", line)
        if hbr:
            hard_body_radius = float(hbr.group(1))
        if not line or line.startswith("COMMENT") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key == "OBJECT":
            current = {"OBJECT": value}
            object_sections.append(current)
        elif current is None:
            common[key] = value
        else:
            current[key] = value
    if len(object_sections) != 2:
        raise ValueError("CDM must contain exactly two objects")
    objects = []
    for section in object_sections:
        covariance = np.array([
            [_number(section["CR_R"]), _number(section["CT_R"]), _number(section["CN_R"])],
            [_number(section["CT_R"]), _number(section["CT_T"]), _number(section["CN_T"])],
            [_number(section["CN_R"]), _number(section["CN_T"]), _number(section["CN_N"])],
        ])
        objects.append(CdmObject(
            designator=section["OBJECT_DESIGNATOR"], name=section["OBJECT_NAME"],
            position_m=np.array([_number(section[k]) for k in ("X", "Y", "Z")]) * 1_000,
            velocity_m_s=np.array([_number(section[k]) for k in ("X_DOT", "Y_DOT", "Z_DOT")]) * 1_000,
            covariance_rtn_m2=covariance,
        ))
    probability = common.get("COLLISION_PROBABILITY")
    return CdmEncounter(
        message_id=common["MESSAGE_ID"],
        tca=datetime.fromisoformat(common["TCA"]).replace(tzinfo=UTC),
        hard_body_radius_m=hard_body_radius,
        published_probability=float(probability) if probability else None,
        objects=(objects[0], objects[1]),
    )


def construct_rtn_basis(position_m: np.ndarray, velocity_m_s: np.ndarray) -> np.ndarray:
    radial = position_m / np.linalg.norm(position_m)
    normal = np.cross(position_m, velocity_m_s)
    normal /= np.linalg.norm(normal)
    transverse = np.cross(normal, radial)
    return np.column_stack((radial, transverse, normal))


def combine_relative_covariance(encounter: CdmEncounter) -> np.ndarray:
    covariance = np.zeros((3, 3))
    for obj in encounter.objects:
        basis = construct_rtn_basis(obj.position_m, obj.velocity_m_s)
        covariance += basis @ obj.covariance_rtn_m2 @ basis.T
    return (covariance + covariance.T) / 2


def construct_encounter_plane(relative_velocity_m_s: np.ndarray) -> np.ndarray:
    velocity_axis = relative_velocity_m_s / np.linalg.norm(relative_velocity_m_s)
    seed = np.array([1.0, 0.0, 0.0]) if abs(velocity_axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    first = seed - np.dot(seed, velocity_axis) * velocity_axis
    first /= np.linalg.norm(first)
    second = np.cross(velocity_axis, first)
    return np.column_stack((first, second))


def calculate_collision_probability_2d(mean_m: np.ndarray, covariance_m2: np.ndarray, hard_body_radius_m: float) -> float:
    if covariance_m2.shape != (2, 2) or mean_m.shape != (2,):
        raise ValueError("expected a 2D mean and 2x2 covariance")
    eigenvalues = np.linalg.eigvalsh(covariance_m2)
    if np.any(eigenvalues <= 0) or not np.all(np.isfinite(eigenvalues)):
        raise ValueError("encounter-plane covariance must be positive definite")
    inverse = np.linalg.inv(covariance_m2)
    normalization = 1.0 / (2 * np.pi * np.sqrt(np.linalg.det(covariance_m2)))

    def radial_integral(theta: float) -> float:
        direction = np.array([np.cos(theta), np.sin(theta)])

        def integrand(radius: float) -> float:
            delta = radius * direction - mean_m
            return normalization * np.exp(-0.5 * delta @ inverse @ delta) * radius

        return quad(integrand, 0, hard_body_radius_m, epsabs=1e-13, epsrel=2e-8, limit=100)[0]

    probability = quad(radial_integral, 0, 2 * np.pi, epsabs=1e-12, epsrel=2e-7, limit=200)[0]
    return float(np.clip(probability, 0.0, 1.0))


def calculate_cdm_probability(encounter: CdmEncounter) -> float:
    first, second = encounter.objects
    relative_position = second.position_m - first.position_m
    relative_velocity = second.velocity_m_s - first.velocity_m_s
    plane = construct_encounter_plane(relative_velocity)
    mean = plane.T @ relative_position
    covariance = plane.T @ combine_relative_covariance(encounter) @ plane
    return calculate_collision_probability_2d(mean, covariance, encounter.hard_body_radius_m)
