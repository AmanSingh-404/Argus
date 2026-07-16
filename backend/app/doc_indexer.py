import json
from google.genai import types
from app.security_agent import gemini_client
from app.github_client import get_installation_token
import httpx


INDEXING_PROMPT = """You are analyzing a code repository to map documentation files to the source
files they describe. You will be given the full content of documentation files and source files.

For each documentation file, identify which source file(s) it documents by matching function
names, class names, or module-level behavior described in the doc against what's actually
defined in each source file's content.

Respond with ONLY a JSON array (no markdown fences, no prose), in this shape:
[
  {"source_path": "path/to/source.py", "doc_path": "docs/api.md"}
]

Only include pairs you're reasonably confident about. If no clear mapping exists, return []."""


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


async def fetch_file_content(installation_id: int, repo_full_name: str, path: str) -> str:
    token = await get_installation_token(installation_id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw"},
        )
        resp.raise_for_status()
        return resp.text


async def build_doc_index(installation_id: int, repo_full_name: str) -> list[dict]:
    """Scans the repo, asks the LLM to propose source-to-doc mappings."""
    all_paths = await fetch_repo_tree(installation_id, repo_full_name)
    doc_paths = [p for p in all_paths if p.endswith(".md")]
    code_paths = [p for p in all_paths if p.endswith((".py", ".js", ".ts", ".go", ".java"))]

    doc_contents = {}
    for dp in doc_paths:
        try:
            doc_contents[dp] = await fetch_file_content(installation_id, repo_full_name, dp)
        except Exception as e:
            print(f"Could not fetch {dp}: {e}")

    code_contents = {}
    for cp in code_paths:
        try:
            code_contents[cp] = await fetch_file_content(installation_id, repo_full_name, cp)
        except Exception as e:
            print(f"Could not fetch {cp}: {e}")

    print(f"DEBUG — doc_contents keys: {list(doc_contents.keys())}")
    print(f"DEBUG — code_contents keys: {list(code_contents.keys())}")

    prompt_input = (
        f"DOC FILE CONTENTS:\n{json.dumps(doc_contents)}\n\n"
        f"SOURCE FILE CONTENTS:\n{json.dumps(code_contents)}"
    )

    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"{INDEXING_PROMPT}\n\n{prompt_input}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )

    try:
        return json.loads(response.text)
    except Exception as e:
        finish_reason = None
        try:
            finish_reason = response.candidates[0].finish_reason
        except Exception:
            pass
        print(f"Failed to parse indexing response: {e}")
        print(f"finish_reason: {finish_reason}")
        print(f"Raw: {response.text}")
        return []