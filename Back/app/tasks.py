import os
from celery import Celery
from typing import Optional

from app.services.s7_parser import run_s7_search

BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/0"))

celery = Celery(
    "app",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery.task(name="parse_s7_flights")
def parse_s7_flights_task(origin: str, dest: str, date_out: str, date_back: Optional[str]):
    """Celery-задача для парсинга рейсов S7."""
    return run_s7_search(origin=origin, dest=dest, date_out=date_out, date_back=date_back)
