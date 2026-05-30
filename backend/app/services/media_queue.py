"""RQ enqueue helpers for creative media processing."""

from __future__ import annotations

from rq import Queue
from redis import Redis

from ..config import settings


def enqueue_media_ingest_job(job_id: str) -> None:
    if not settings.redis_url:
        return
    connection = Redis.from_url(settings.redis_url)
    queue = Queue("media_jobs", connection=connection)
    queue.enqueue(
        "app.worker_tasks.run_media_job",
        job_id,
        job_timeout=3600,
        result_ttl=0,
    )
