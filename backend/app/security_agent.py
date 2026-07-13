import os
import json
from google import genai
from google.genai import types

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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


def chunk_diff(diff_text: str, max_chars_per_chunk: int = 6000) -> list[str]:
    file_sections = diff_text.split("diff --git ")
    chunks = []
    current_chunk = ""

    for section in file_sections:
        if not section.strip():
            continue
        section = "diff --git " + section

        if len(section) > max_chars_per_chunk:
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
    all_findings = []

    for chunk in diff_chunks:
        response_text = None
        for attempt in range(2):
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-3.5-flash",
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