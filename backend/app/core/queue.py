from functools import lru_cache

from redis import Redis
from rq import Queue

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


@lru_cache
def get_queue() -> Queue:
    settings = get_settings()
    return Queue(settings.queue_name, connection=get_redis())


def enqueue_run(run_id: str) -> None:
    queue = get_queue()
    queue.enqueue(
        "app.worker.runner.execute_run_job",
        run_id,
        job_timeout=get_settings().run_timeout_seconds + 30,
    )
