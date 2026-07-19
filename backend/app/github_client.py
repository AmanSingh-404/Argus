import os
import time
import jwt
import httpx

APP_ID = os.getenv("GITHUB_APP_ID")
PRIVATE_KEY_PATH = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")


def generate_jwt() -> str:
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
    if not private_key:
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


async def fetch_pr_diff(installation_id: int, repo_full_name: str, pr_number: int) -> str:
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

async def fetch_pr_files(installation_id: int, repo_full_name: str, pr_number: int) -> list[str]:
    """Returns just the list of changed filenames for a PR — used by the Planner to decide routing."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/files",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        return [f["filename"] for f in resp.json()]


async def post_pr_comment(installation_id: int, repo_full_name: str, pr_number: int, body: str):
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"body": body},
        )
        resp.raise_for_status()
        return resp.json()


async def post_review_comments(installation_id: int, repo_full_name: str, pr_number: int, commit_id: str, findings: list[dict]):
    token = await get_installation_token(installation_id)

    if not findings:
        await post_pr_comment(installation_id, repo_full_name, pr_number, "Argus reviewed this PR — no security issues found. 👁️")
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
            json={"commit_id": commit_id, "event": "COMMENT", "comments": review_comments},
        )
        if resp.status_code >= 400:
            print(f"Review post failed ({resp.status_code}): {resp.text}")
        resp.raise_for_status()

async def fetch_repo_tree(installation_id: int, repo_full_name: str) -> list[str]:
    """Returns every file path in the repo's default branch."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        repo_resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        repo_resp.raise_for_status()
        default_branch = repo_resp.json()["default_branch"]

        tree_resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/git/trees/{default_branch}?recursive=1",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        tree_resp.raise_for_status()
        return [item["path"] for item in tree_resp.json()["tree"] if item["type"] == "blob"]


async def fetch_file_content(installation_id: int, repo_full_name: str, path: str, ref: str = None) -> str:
    token = await get_installation_token(installation_id)
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw"},
        )
        resp.raise_for_status()
        return resp.text


async def fetch_commit_diff(installation_id: int, repo_full_name: str, base_sha: str, head_sha: str) -> str:
    """Returns the unified diff between two commits — used for push events."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/compare/{base_sha}...{head_sha}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3.diff"},
        )
        resp.raise_for_status()
        return resp.text

async def create_branch(installation_id: int, repo_full_name: str, new_branch: str, from_sha: str):
    """Creates a new branch pointing at from_sha."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/git/refs",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"ref": f"refs/heads/{new_branch}", "sha": from_sha},
        )
        resp.raise_for_status()
        return resp.json()


async def commit_file_update(installation_id: int, repo_full_name: str, branch: str, file_path: str, new_content: str, commit_message: str):
    """Commits an update to an existing file on the given branch."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        # Need the current file's sha to update it (GitHub requires this to avoid overwrite conflicts)
        get_resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}?ref={branch}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        get_resp.raise_for_status()
        current_sha = get_resp.json()["sha"]

        import base64
        encoded_content = base64.b64encode(new_content.encode()).decode()

        put_resp = await client.put(
            f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={
                "message": commit_message,
                "content": encoded_content,
                "sha": current_sha,
                "branch": branch,
            },
        )
        put_resp.raise_for_status()
        return put_resp.json()


async def open_pull_request(installation_id: int, repo_full_name: str, title: str, body: str, head_branch: str, base_branch: str = "main"):
    """Opens a PR from head_branch into base_branch."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/pulls",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"title": title, "body": body, "head": head_branch, "base": base_branch},
        )
        resp.raise_for_status()
        return resp.json()

async def fetch_default_branch_sha(installation_id: int, repo_full_name: str) -> str:
    """Returns the current HEAD commit sha of the repo's default branch."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        repo_resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        repo_resp.raise_for_status()
        default_branch = repo_resp.json()["default_branch"]

        ref_resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/git/refs/heads/{default_branch}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        ref_resp.raise_for_status()
        return ref_resp.json()["object"]["sha"]

async def fetch_installation_repos(installation_id: int) -> list[dict]:
    """Returns every repo this installation currently has access to, via the API directly."""
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/installation/repositories",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        return resp.json()["repositories"]