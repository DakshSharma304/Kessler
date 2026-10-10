from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Callable
from uuid import uuid4


@dataclass
class Job:
    job_id: str
    status: str = "queued"
    progress: float = 0.0
    stage: str = "queued"
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    result: Any = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        result = self.result.model_dump(mode="json") if hasattr(self.result, "model_dump") else self.result
        return {
            "job_id": self.job_id, "status": self.status, "progress": self.progress,
            "started_at": self.started_at.isoformat(), "current_stage": self.stage,
            "result": result, "error": self.error, "warnings": self.warnings,
        }


class JobManager:
    def __init__(self, max_workers: int):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="kessler-job")
        self.jobs: dict[str, Job] = {}
        self.lock = Lock()

    def submit(self, operation: Callable[..., Any], *args: Any) -> Job:
        job = Job(job_id=uuid4().hex)
        with self.lock:
            self.jobs[job.job_id] = job

        def run() -> None:
            job.status, job.progress, job.stage = "running", 0.1, "computing"
            try:
                job.result = operation(*args)
                job.status, job.progress, job.stage = "complete", 1.0, "complete"
            except Exception as exc:
                job.status, job.stage, job.error = "failed", "failed", str(exc)

        self.executor.submit(run)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)
