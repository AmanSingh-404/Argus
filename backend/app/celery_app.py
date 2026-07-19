import os
# pyrefly: ignore [missing-import]
from celery import Celery
# pyrefly: ignore [missing-import]
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL", "")

celery_app = Celery(
    "argus",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks", "app.tasks_docs"],
)

import ssl

if redis_url.startswith("rediss://"):
    ssl_config = {"ssl_cert_reqs": ssl.CERT_NONE}
    celery_app.conf.broker_use_ssl = ssl_config
    celery_app.conf.redis_backend_use_ssl = ssl_config

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)

# TESTING: runs every 60 seconds so you can watch it fire.
# For real deployment, replace with: crontab(hour=2, minute=0)  — runs nightly at 2 AM.
celery_app.conf.beat_schedule = {
    "sweep-docs-drift": {
        "task": "sweep_docs_drift",
        "schedule": crontab(hour=2, minute=0),
    },
}