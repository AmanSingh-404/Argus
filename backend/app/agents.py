import json
from google import genai
from google.genai import types
from app.security_agent import gemini_client  # reuse the same client instance
import asyncio


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


FINDING_SCHEMA = """Respond with ONLY a JSON array (no markdown fences, no prose) of findings, in this exact shape:
[
  {"file": "path/to/file.py", "line": 42, "severity": "high|medium|low", "message": "short, specific explanation"}
]
If there are no issues, respond with an empty array: []"""

LOGIC_AGENT_PROMPT = f"""You are a code logic reviewer. You will be given a unified git diff.
Identify genuine logic bugs: off-by-one errors, incorrect null/undefined handling, unreachable code,
incorrect conditional logic, race conditions in async code, and similar. Do not comment on style,
security, or missing tests.

{FINDING_SCHEMA}"""

STYLE_AGENT_PROMPT = f"""You are a code style reviewer. You will be given a unified git diff.
Identify only clear, objective style issues: inconsistent naming conventions, inconsistent
formatting, overly long functions, unclear variable names. Do not comment on logic, security,
or tests. Be conservative — only flag things that are genuinely inconsistent with common
conventions, not personal preference.

{FINDING_SCHEMA}"""

TESTS_AGENT_PROMPT = f"""You are reviewing a diff to check test coverage. You will be given a unified
git diff. Identify cases where new or changed logic (functions, conditionals, business logic) appears
to have shipped without any corresponding test file changes in the same diff. Do not flag pure
config, docs, or formatting-only changes.

{FINDING_SCHEMA}"""


async def _run_agent(prompt: str, diff_chunks: list[str], agent_name: str) -> list[dict]:
    all_findings = []
    for chunk in diff_chunks:
        response_text = None
        for attempt in range(2):
            try:
                response = await asyncio.to_thread(
                    gemini_client.models.generate_content,
                    model="gemini-3.5-flash",
                    contents=f"{prompt}\n\nDIFF:\n{chunk}",
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                response_text = response.text
                findings = json.loads(response_text)
                for f in findings:
                    f["agent"] = agent_name
                all_findings.extend(findings)
                break
            except Exception as e:
                print(f"{agent_name} agent attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    print(f"Skipping chunk after failed retry. Raw: {response_text}")
    return all_findings


async def run_logic_agent(diff_chunks: list[str]) -> list[dict]:
    return await _run_agent(LOGIC_AGENT_PROMPT, diff_chunks, "logic")


async def run_style_agent(diff_chunks: list[str]) -> list[dict]:
    return await _run_agent(STYLE_AGENT_PROMPT, diff_chunks, "style")


async def run_tests_agent(diff_chunks: list[str]) -> list[dict]:
    return await _run_agent(TESTS_AGENT_PROMPT, diff_chunks, "tests")