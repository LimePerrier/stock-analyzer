from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import List, Optional
import uuid


@dataclass
class AnalysisJob:
    ticker: str
    urls: List[str]
    analysis_type: str
    model: str
    txt_path: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    status: str = "queued"  # queued, running, done, failed


class QueueService:
    def __init__(self, max_jobs: int = 25):
        self.max_jobs = max_jobs
        self._jobs: List[AnalysisJob] = []
        self._lock = Lock()

    def add_job(self, job: AnalysisJob) -> None:
        with self._lock:
            if self.pending_count() >= self.max_jobs:
                raise ValueError(f"Maximum {self.max_jobs} queued jobs.")
            self._jobs.append(job)

    def has_duplicate(self, ticker: str, analysis_type: str, txt_path: str = "") -> bool:
        normalized_path = (txt_path or "").strip()
        with self._lock:
            return any(
                job.status == "queued"
                and job.ticker == ticker
                and job.analysis_type == analysis_type
                and (job.txt_path or "").strip() == normalized_path
                for job in self._jobs
            )

    def pending_count(self) -> int:
        return sum(1 for job in self._jobs if job.status == "queued")

    def snapshot(self) -> List[AnalysisJob]:
        with self._lock:
            return list(self._jobs)

    def get_next_job(self) -> Optional[AnalysisJob]:
        with self._lock:
            for job in self._jobs:
                if job.status == "queued":
                    job.status = "running"
                    return job
        return None

    def mark_done(self, job_id: str) -> None:
        with self._lock:
            self._remove_or_mark(job_id, remove=True, fallback_status="done")

    def mark_failed(self, job_id: str) -> None:
        with self._lock:
            self._remove_or_mark(job_id, remove=True, fallback_status="failed")

    def remove_queued_at_index(self, queued_index: int) -> bool:
        with self._lock:
            queued_jobs = [job for job in self._jobs if job.status == "queued"]
            if 0 <= queued_index < len(queued_jobs):
                target = queued_jobs[queued_index]
                self._jobs = [job for job in self._jobs if job.id != target.id]
                return True
        return False

    def clear_pending(self) -> None:
        with self._lock:
            self._jobs = [job for job in self._jobs if job.status != "queued"]

    def has_pending(self) -> bool:
        with self._lock:
            return any(job.status == "queued" for job in self._jobs)

    def has_running(self) -> bool:
        with self._lock:
            return any(job.status == "running" for job in self._jobs)

    def _remove_or_mark(self, job_id: str, remove: bool, fallback_status: str) -> None:
        for idx, job in enumerate(self._jobs):
            if job.id == job_id:
                if remove:
                    self._jobs.pop(idx)
                else:
                    job.status = fallback_status
                return
