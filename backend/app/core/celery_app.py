from celery import Celery

from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging()  # separate process from the API -- needs its own call

celery_app = Celery(
    "securify",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.scan_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_time_limit=600,
)