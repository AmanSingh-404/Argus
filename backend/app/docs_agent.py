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
Below is your draft, and the ORIGINAL diff it was based on — this diff is the only source of truth
for what changed. Do not assume any other changes happened beyond what's shown in this diff.

Check ONLY for these two failure modes:
1. The draft describes behavior that contradicts what the diff actually shows.
2. The diff introduces a meaningful, user-visible behavior change that the draft failed to reflect.

Do not flag stylistic issues, and do not speculate about changes outside this diff.

Respond with ONLY a JSON object (no markdown fences, no prose) in this exact shape:
{"confident": true|false, "issues": ["short description of any problem found"]}

IMPORTANT: these two fields must be consistent. If "issues" contains anything, "confident" MUST be false.
If you are confident the draft is accurate, "issues" MUST be an empty array."""


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
        result = json.loads(response.text)
    except Exception:
        return {"confident": False, "issues": ["self-check response could not be parsed"]}

    # Enforce consistency ourselves — don't trust the model to have followed its own rule.
    if result.get("issues"):
        result["confident"] = False

    return result