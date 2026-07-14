from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

from app.security_agent import chunk_diff, run_security_agent


class ReviewState(TypedDict):
    diff_text: str
    files_changed: list[str]
    run_security: bool
    findings: list


SECURITY_RELEVANT_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb", ".php", ".env", ".yml", ".yaml"}
SECURITY_RELEVANT_KEYWORDS = ["auth", "login", "password", "token", "secret", "key", "session", "admin", "payment", "sql", "query", "config"]


def planner_node(state: ReviewState) -> dict:
    """Decides whether the Security agent is worth running, based on which files changed."""
    files = state["files_changed"]

    if not files:
        return {"run_security": False}

    for f in files:
        f_lower = f.lower()
        has_relevant_extension = any(f_lower.endswith(ext) for ext in SECURITY_RELEVANT_EXTENSIONS)
        has_relevant_keyword = any(kw in f_lower for kw in SECURITY_RELEVANT_KEYWORDS)

        if has_relevant_extension or has_relevant_keyword:
            print(f"Planner: routing to security agent (matched file: {f})")
            return {"run_security": True}

    print(f"Planner: skipping security agent — no relevant files among {files}")
    return {"run_security": False}


def route_after_planner(state: ReviewState) -> Literal["security", "skip"]:
    return "security" if state["run_security"] else "skip"


async def security_node(state: ReviewState) -> dict:
    chunks = chunk_diff(state["diff_text"])
    findings = await run_security_agent(chunks)
    return {"findings": findings}


def skip_node(state: ReviewState) -> dict:
    return {"findings": []}


def build_graph():
    builder = StateGraph(ReviewState)
    builder.add_node("planner", planner_node)
    builder.add_node("security", security_node)
    builder.add_node("skip", skip_node)

    builder.add_edge(START, "planner")
    builder.add_conditional_edges("planner", route_after_planner, {"security": "security", "skip": "skip"})
    builder.add_edge("security", END)
    builder.add_edge("skip", END)

    return builder.compile()


review_graph = build_graph()