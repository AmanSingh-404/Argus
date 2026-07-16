import json
from google.genai import types
from app.security_agent import gemini_client
from app.github_client import get_installation_token, fetch_file_content
from app.github_client import fetch_commit_diff, fetch_file_content
import httpx


DRAFT_PROMPT = """You are updating technical documentation to match a code change. You will be given
the current documentation content, and a diff showing how the source code changed.

Rewrite ONLY the section(s) of the documentation that are now inaccurate because of this diff.
Keep everything else in the document exactly as-is. Preserve the original markdown structure and style.

Respond with ONLY the full, complete updated markdown document (no fences, no prose, no explanation) —
this will be written directly as the new file content."""

SELF_CHECK_PROMPT = """You previously drafted an update to a documentation file based on a code diff.
Below is your draft, and the original diff it was based on. Check your draft for any claims that
are NOT actually supported by the diff — for example, describing behavior that isn't in the code,
or missing a change that IS in the diff.

Respond with ONLY a JSON object (no markdown fences, no prose) in this shape:
{"confident": true|false, "issues": ["short description of any problem found"]}

If the draft looks accurate, return {"confident": true, "issues": []}"""


async def draft_doc_update(current_doc_content: str, diff_text: str) -> str:
    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"{DRAFT_PROMPT}\n\nCURRENT DOC:\n{current_doc_content}\n\nDIFF:\n{diff_text}",
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=2048),
    )
    return response.text


async def self_check_draft(draft: str, diff_text: str) -> dict:
    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"{SELF_CHECK_PROMPT}\n\nDRAFT:\n{draft}\n\nDIFF:\n{diff_text}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=1024,
        ),
    )
    try:
        return json.loads(response.text)
    except Exception:
        return {"confident": False, "issues": ["self-check response could not be parsed"]}