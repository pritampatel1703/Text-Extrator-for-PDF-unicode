"""
Celery application configuration.
Manages task queues, serialization, and retry policies.
"""

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Celery configuration
celery_app = Celery(
    "pdf_worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    include=[
        "tasks.ocr_task",
        "tasks.indexing_task",
        "tasks.embedding_task",
    ],
)

# Celery settings
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Retry policy
    task_default_retry_delay=30,
    task_max_retries=3,

    # Result expiration (24 hours)
    result_expires=86400,

    # Task routes — dedicated queues for different task types
    task_routes={
        "tasks.ocr_task.*": {"queue": "ocr"},
        "tasks.indexing_task.*": {"queue": "indexing"},
        "tasks.embedding_task.*": {"queue": "embedding"},
    },

    # Task time limits
    task_soft_time_limit=600,  # 10 minutes soft limit
    task_time_limit=900,       # 15 minutes hard limit

    # Worker settings
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory leak prevention)
    worker_max_memory_per_child=2_000_000,  # 2GB memory limit per worker

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)


if __name__ == "__main__":
    celery_app.start()
