import hashlib
import hmac
import json
import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.github_client import post_pr_comment  # noqa: E402
from app.tasks import review_pull_request_task  # noqa: E402
from app.routes_reviews import router as reviews_router

app = FastAPI(title="Argus API", version="0.1.0")

app.include_router(reviews_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload_body: bytes, signature_header: str | None) -> None:
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature header")

    expected = "sha256=" + hmac.new(
        key=WEBHOOK_SECRET.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


@app.get("/health")
def health():
    return {"status": "ok", "service": "argus-api"}


@app.get("/")
def root():
    return {"message": "Argus is watching."}


@app.post("/webhooks/github")
async def github_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    verify_signature(body, signature)

    event_type = request.headers.get("X-GitHub-Event", "unknown")
    payload = json.loads(body)

    print(f"\n=== Received GitHub event: {event_type} ===")

    if event_type == "pull_request":
        action = payload.get("action")
        pr_number = payload.get("pull_request", {}).get("number")
        repo_full_name = payload.get("repository", {}).get("full_name")
        installation_id = payload.get("installation", {}).get("id")
        commit_sha = payload.get("pull_request", {}).get("head", {}).get("sha")

        print(f"Action: {action} | Repo: {repo_full_name} | PR #{pr_number}")

        if action == "opened":
            review_pull_request_task.delay(installation_id, repo_full_name, pr_number, commit_sha)
            print(f"Enqueued review job for PR #{pr_number}")

    return {"status": "received"}