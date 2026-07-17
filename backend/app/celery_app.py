import os
# pyrefly: ignore [missing-import]
from celery import Celery
# pyrefly: ignore [missing-import]
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery(
    "argus",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL"),
    include=["app.tasks", "app.tasks_docs"],
)

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