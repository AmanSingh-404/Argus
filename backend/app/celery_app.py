import os
# pyrefly: ignore [missing-import]
from celery import Celery
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