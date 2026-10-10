from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.models import Availability, Conjunction, DatasetStatus, OrbitalElements, OrbitalObject


GP_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=JSON"
SOCRATES_URL = "https://celestrak.org/SOCRATES/sort-minRange.csv"
GCAT_URL = "https://planet4589.org/space/gcat/tsv/cat/satcat.tsv"


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def classify_object(name: str, object_type: str | None = None) -> str:
    upper = f"{name} {object_type or ''}".upper()
    if "DEB" in upper:
        return "debris"
    if "R/B" in upper or "ROCKET" in upper:
        return "rocket_body"
    if object_type and object_type.upper() in {"PAY", "ACTIVE"}:
        return "active"
    return "unknown"


def parse_gp_json(payload: bytes, *, source: str = "CelesTrak GP") -> tuple[list[OrbitalObject], list[str]]:
    raw = json.loads(payload)
    if not isinstance(raw, list):
        raise ValueError("GP JSON must contain a list")
    objects: dict[str, OrbitalObject] = {}
    errors: list[str] = []
    for index, record in enumerate(raw):
        try:
            catalog_id = str(record["NORAD_CAT_ID"])
            obj = OrbitalObject(
                catalog_id=catalog_id,
                name=str(record["OBJECT_NAME"]),
                object_id=record.get("OBJECT_ID"),
                category=classify_object(str(record["OBJECT_NAME"]), record.get("OBJECT_TYPE")),
                source=source,
                elements=OrbitalElements(
                    epoch=_utc(str(record["EPOCH"])),
                    inclination_rad=float(record["INCLINATION"]) * 3.141592653589793 / 180,
                    raan_rad=float(record["RA_OF_ASC_NODE"]) * 3.141592653589793 / 180,
                    eccentricity=float(record["ECCENTRICITY"]),
                    argument_of_perigee_rad=float(record["ARG_OF_PERICENTER"]) * 3.141592653589793 / 180,
                    mean_anomaly_rad=float(record["MEAN_ANOMALY"]) * 3.141592653589793 / 180,
                    mean_motion_rev_day=float(record["MEAN_MOTION"]),
                    bstar=float(record["BSTAR"]),
                    raw_omm=record,
                ),
            )
            current = objects.get(catalog_id)
            if current is None or obj.elements.epoch > current.elements.epoch:
                objects[catalog_id] = obj
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"row {index}: {exc}")
    return list(objects.values()), errors


def _field(row: dict[str, str], name: str) -> str:
    for key, value in row.items():
        if key and key.strip().upper() == name:
            return (value or "").strip()
    raise KeyError(name)


def parse_socrates_csv(payload: bytes, dataset_version: str) -> tuple[list[Conjunction], list[str]]:
    text = payload.decode("utf-8-sig")
    rows = csv.DictReader(io.StringIO(text))
    encounters: list[Conjunction] = []
    errors: list[str] = []
    for index, row in enumerate(rows):
        try:
            id1, id2 = _field(row, "NORAD_CAT_ID_1"), _field(row, "NORAD_CAT_ID_2")
            tca = _utc(_field(row, "TCA"))
            raw_probability = _field(row, "MAX_PROB")
            encounters.append(
                Conjunction(
                    encounter_id=hashlib.sha256(f"{id1}:{id2}:{tca.isoformat()}".encode()).hexdigest()[:20],
                    catalog_id_1=id1,
                    object_name_1=_field(row, "OBJECT_NAME_1"),
                    catalog_id_2=id2,
                    object_name_2=_field(row, "OBJECT_NAME_2"),
                    tca=tca,
                    separation_m=float(_field(row, "TCA_RANGE")) * 1_000,
                    relative_speed_m_s=float(_field(row, "TCA_RELATIVE_SPEED")) * 1_000,
                    socrates_max_probability=float(raw_probability) if raw_probability else None,
                    source_dataset_version=dataset_version,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"row {index}: {exc}")
    return encounters, errors


def parse_gcat_tsv(payload: bytes) -> list[dict[str, Any]]:
    lines = [line for line in payload.decode("utf-8-sig").splitlines() if line and not line.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines, delimiter="\t")
    return [{(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in reader]


class CatalogStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS objects (
              catalog_id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
              epoch TEXT NOT NULL, omm_json TEXT NOT NULL, object_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS encounters (
              encounter_id TEXT PRIMARY KEY, id1 TEXT NOT NULL, id2 TEXT NOT NULL,
              tca TEXT NOT NULL, separation_m REAL NOT NULL, encounter_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS encounters_id1 ON encounters(id1);
            CREATE INDEX IF NOT EXISTS encounters_id2 ON encounters(id2);
            CREATE INDEX IF NOT EXISTS encounters_tca ON encounters(tca);
            CREATE TABLE IF NOT EXISTS datasets (
              name TEXT PRIMARY KEY, status_json TEXT NOT NULL
            );
            """
        )

    def upsert_objects(self, objects: list[OrbitalObject]) -> None:
        with self.connection:
            self.connection.executemany(
                "INSERT INTO objects VALUES(?,?,?,?,?,?) ON CONFLICT(catalog_id) DO UPDATE SET name=excluded.name, category=excluded.category, epoch=excluded.epoch, omm_json=excluded.omm_json, object_json=excluded.object_json",
                [(o.catalog_id, o.name, o.category, o.elements.epoch.isoformat(), json.dumps(o.elements.raw_omm), o.model_dump_json()) for o in objects],
            )

    def upsert_encounters(self, encounters: list[Conjunction]) -> None:
        with self.connection:
            self.connection.executemany(
                "INSERT INTO encounters VALUES(?,?,?,?,?,?) ON CONFLICT(encounter_id) DO UPDATE SET tca=excluded.tca, separation_m=excluded.separation_m, encounter_json=excluded.encounter_json",
                [(e.encounter_id, e.catalog_id_1, e.catalog_id_2, e.tca.isoformat(), e.separation_m, e.model_dump_json()) for e in encounters],
            )

    def set_dataset(self, status: DatasetStatus) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO datasets VALUES(?,?) ON CONFLICT(name) DO UPDATE SET status_json=excluded.status_json",
                (status.name, status.model_dump_json()),
            )

    def dataset_statuses(self) -> list[DatasetStatus]:
        return [DatasetStatus.model_validate_json(row[0]) for row in self.connection.execute("SELECT status_json FROM datasets ORDER BY name")]

    def count(self, table: str) -> int:
        if table not in {"objects", "encounters"}:
            raise ValueError("invalid table")
        return int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def objects(self, search: str = "", category: str | None = None, limit: int = 100, offset: int = 0) -> list[OrbitalObject]:
        clauses, values = [], []
        if search:
            clauses.append("(name LIKE ? OR catalog_id LIKE ?)")
            values.extend([f"%{search}%", f"%{search}%"])
        if category:
            clauses.append("category = ?")
            values.append(category)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.extend([limit, offset])
        rows = self.connection.execute(f"SELECT object_json FROM objects {where} ORDER BY name LIMIT ? OFFSET ?", values)
        return [OrbitalObject.model_validate_json(row[0]) for row in rows]

    def object(self, catalog_id: str) -> OrbitalObject | None:
        row = self.connection.execute("SELECT object_json FROM objects WHERE catalog_id=?", (catalog_id,)).fetchone()
        return OrbitalObject.model_validate_json(row[0]) if row else None

    def encounter(self, encounter_id: str) -> Conjunction | None:
        row = self.connection.execute("SELECT encounter_json FROM encounters WHERE encounter_id=?", (encounter_id,)).fetchone()
        return Conjunction.model_validate_json(row[0]) if row else None

    def encounters(self, object_id: str | None = None, limit: int = 100, offset: int = 0) -> list[Conjunction]:
        if object_id:
            rows = self.connection.execute(
                "SELECT encounter_json FROM encounters WHERE id1=? OR id2=? ORDER BY separation_m LIMIT ? OFFSET ?",
                (object_id, object_id, limit, offset),
            )
        else:
            rows = self.connection.execute("SELECT encounter_json FROM encounters ORDER BY separation_m LIMIT ? OFFSET ?", (limit, offset))
        return [Conjunction.model_validate_json(row[0]) for row in rows]


class SourceCache:
    def __init__(self, directory: Path, store: CatalogStore):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.store = store

    async def fetch(self, name: str, url: str, ttl_seconds: int, suffix: str) -> tuple[bytes | None, DatasetStatus]:
        data_path = self.directory / f"{name}.{suffix}"
        existing = next((item for item in self.store.dataset_statuses() if item.name == name), None)
        if data_path.exists() and existing and existing.retrieved_at:
            if datetime.now(UTC) - existing.retrieved_at < timedelta(seconds=ttl_seconds):
                return data_path.read_bytes(), existing
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30, headers={"User-Agent": "Kessler/0.1 educational-research"}) as client:
                response = await client.get(url)
                response.raise_for_status()
            payload = response.content
            checksum = hashlib.sha256(payload).hexdigest()
            data_path.write_bytes(payload)
            status = DatasetStatus(
                name=name, source_url=url, availability=Availability.AVAILABLE,
                retrieved_at=datetime.now(UTC), checksum_sha256=checksum,
                parsing_status="downloaded", record_count=0,
            )
        except Exception as exc:
            if data_path.exists():
                payload = data_path.read_bytes()
                status = (existing or DatasetStatus(name=name, source_url=url, availability=Availability.STALE)).model_copy(
                    update={"availability": Availability.STALE, "stale": True, "error": str(exc)}
                )
            else:
                payload = None
                status = DatasetStatus(name=name, source_url=url, availability=Availability.UNAVAILABLE, error=str(exc), parsing_status="download_failed")
        self.store.set_dataset(status)
        return payload, status
