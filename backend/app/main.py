import hashlib
import hmac
import json
import os

import time
import jwt
import httpx

from google import genai
from google.genai import types



SECURITY_AGENT_PROMPT = """You are a security-focused code reviewer. You will be given a unified git diff.
Identify only genuine security issues: hardcoded secrets/API keys, SQL/command injection risk,
unsafe deserialization, missing input validation on user-controlled data, insecure use of eval/exec,
path traversal, and similar. Do not comment on style, naming, or non-security logic issues.

Respond with ONLY a JSON array (no markdown fences, no prose) of findings, in this exact shape:
[
  {"file": "path/to/file.py", "line": 42, "severity": "high|medium|low", "message": "short, specific explanation"}
]

If there are no security issues, respond with an empty array: []
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="Argus API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

APP_ID = os.getenv("GITHUB_APP_ID")
PRIVATE_KEY_PATH = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")


def generate_jwt() -> str:
    """Creates a short-lived JWT signed with the app's private key, used to authenticate as the App itself."""
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),
        "iss": APP_ID,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    """Exchanges the app JWT for a short-lived installation access token, scoped to one repo installation."""
    app_jwt = generate_jwt()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        return resp.json()["token"]


async def post_pr_comment(installation_id: int, repo_full_name: str, pr_number: int, body: str):
    """Posts a comment on a PR, authenticated as the GitHub App installation."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"body": body},
        )
        resp.raise_for_status()
        return resp.json()

async def fetch_pr_diff(installation_id: int, repo_full_name: str, pr_number: int) -> str:
    """Fetches the raw unified diff for a PR, authenticated as the GitHub App installation."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3.diff",
            },
        )
        resp.raise_for_status()
        return resp.text

def chunk_diff(diff_text: str, max_chars_per_chunk: int = 6000) -> list[str]:
    """Splits a unified diff into per-file chunks, capping size so each chunk stays well within context limits."""
    file_sections = diff_text.split("diff --git ")
    chunks = []
    current_chunk = ""

    for section in file_sections:
        if not section.strip():
            continue
        section = "diff --git " + section

        if len(section) > max_chars_per_chunk:
            # a single file's diff is huge on its own — truncate it rather than dropping it entirely
            section = section[:max_chars_per_chunk] + "\n... (truncated, file too large)"

        if len(current_chunk) + len(section) > max_chars_per_chunk:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = section
        else:
            current_chunk += section

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

async def run_security_agent(diff_chunks: list[str]) -> list[dict]:
    """Runs the Security Agent over each diff chunk, returns a merged list of findings."""
    all_findings = []

    for chunk in diff_chunks:
        response_text = None
        for attempt in range(2):  # one retry if the model returns malformed JSON
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{SECURITY_AGENT_PROMPT}\n\nDIFF:\n{chunk}",
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                response_text = response.text
                findings = json.loads(response_text)
                all_findings.extend(findings)
                break
            except Exception as e:
                print(f"Security agent attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    print(f"Skipping this chunk after failed retry. Raw response: {response_text}")

    return all_findings

async def post_review_comments(installation_id: int, repo_full_name: str, pr_number: int, commit_id: str, findings: list[dict]):
    """Posts findings as inline comments on specific lines, via GitHub's review API."""
    token = await get_installation_token(installation_id)

    if not findings:
        body = "Argus reviewed this PR — no security issues found. 👁️"
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                json={"body": body},
            )
        return

    review_comments = []
    for f in findings:
        icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(f.get("severity", "low"), "🔵")
        review_comments.append({
            "path": f["file"],
            "line": f["line"],
            "body": f"{icon} **SECURITY · {f.get('severity', 'low')}**\n\n{f['message']}\n\n— flagged by security-agent",
        })

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/reviews",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={
                "commit_id": commit_id,
                "event": "COMMENT",
                "comments": review_comments,
            },
        )
        if resp.status_code >= 400:
            print(f"Review post failed ({resp.status_code}): {resp.text}")
        resp.raise_for_status()

def verify_signature(payload_body: bytes, signature_header: str | None) -> None:
    """Verifies GitHub's HMAC signature on the webhook payload. Raises 401 if invalid."""
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
        print(f"Action: {action} | Repo: {repo_full_name} | PR #{pr_number}")

        if action == "opened":
            commit_id = payload.get("pull_request", {}).get("head", {}).get("sha")

            diff_text = await fetch_pr_diff(installation_id, repo_full_name, pr_number)
            chunks = chunk_diff(diff_text)
            print(f"Diff split into {len(chunks)} chunk(s)")

            findings = await run_security_agent(chunks)
            print(f"Security agent found {len(findings)} issue(s)")

            await post_review_comments(installation_id, repo_full_name, pr_number, commit_id, findings)
            print(f"Posted review on PR #{pr_number}")

    return {"status": "received"}