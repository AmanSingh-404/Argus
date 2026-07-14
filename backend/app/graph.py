from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

from app.security_agent import chunk_diff, run_security_agent
from app.agents import run_logic_agent, run_style_agent, run_tests_agent


class ReviewState(TypedDict):
    diff_text: str
    files_changed: list[str]
    agents_to_run: list[str]
    security_findings: list
    logic_findings: list
    style_findings: list
    tests_findings: list
    findings: list  # final, critic-arbitrated output


SECURITY_RELEVANT_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb", ".php", ".env", ".yml", ".yaml"}
SECURITY_RELEVANT_KEYWORDS = ["auth", "login", "password", "token", "secret", "key", "session", "admin", "payment", "sql", "query", "config"]
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb", ".php"}


def planner_node(state: ReviewState) -> dict:
    """Decides which specialist agents are worth running, based on which files changed."""
    files = state["files_changed"]
    agents_to_run = []

    has_code_file = any(any(f.lower().endswith(ext) for ext in CODE_EXTENSIONS) for f in files)
    has_security_signal = any(
        any(f.lower().endswith(ext) for ext in SECURITY_RELEVANT_EXTENSIONS)
        or any(kw in f.lower() for kw in SECURITY_RELEVANT_KEYWORDS)
        for f in files
    )

    if has_security_signal:
        agents_to_run.append("security")
    if has_code_file:
        agents_to_run.extend(["logic", "style", "tests"])

    if agents_to_run:
        print(f"Planner: routing to {agents_to_run} (files: {files})")
    else:
        print(f"Planner: no relevant agents for files: {files}")

    return {"agents_to_run": agents_to_run}


def route_after_planner(state: ReviewState) -> list[str]:
    """Fans out to every agent the planner selected — these run in parallel."""
    agents = state["agents_to_run"]
    return [a for a in agents] if agents else ["critic"]


async def security_node(state: ReviewState) -> dict:
    chunks = chunk_diff(state["diff_text"])
    findings = await run_security_agent(chunks)
    for f in findings:
        f["agent"] = "security"
    return {"security_findings": findings}


async def logic_node(state: ReviewState) -> dict:
    chunks = chunk_diff(state["diff_text"])
    return {"logic_findings": await run_logic_agent(chunks)}


async def style_node(state: ReviewState) -> dict:
    chunks = chunk_diff(state["diff_text"])
    return {"style_findings": await run_style_agent(chunks)}


async def tests_node(state: ReviewState) -> dict:
    chunks = chunk_diff(state["diff_text"])
    return {"tests_findings": await run_tests_agent(chunks)}


def critic_node(state: ReviewState) -> dict:
    """Merges all specialist findings, dedupes overlapping file+line flags, ranks by severity."""
    all_findings = (
        state.get("security_findings", [])
        + state.get("logic_findings", [])
        + state.get("style_findings", [])
        + state.get("tests_findings", [])
    )

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    seen = {}

    for f in all_findings:
        key = (f["file"], f["line"])
        if key not in seen:
            seen[key] = f
        else:
            # same file+line flagged by multiple agents — keep whichever has higher severity
            existing_rank = severity_rank.get(seen[key].get("severity", "low"), 2)
            new_rank = severity_rank.get(f.get("severity", "low"), 2)
            if new_rank < existing_rank:
                seen[key] = f

    deduped = list(seen.values())
    deduped.sort(key=lambda f: severity_rank.get(f.get("severity", "low"), 2))

    print(f"Critic: {len(all_findings)} raw findings -> {len(deduped)} after dedup")
    return {"findings": deduped}


def build_graph():
    builder = StateGraph(ReviewState)
    builder.add_node("planner", planner_node)
    builder.add_node("security", security_node)
    builder.add_node("logic", logic_node)
    builder.add_node("style", style_node)
    builder.add_node("tests", tests_node)
    builder.add_node("critic", critic_node)

    builder.add_edge(START, "planner")
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        ["security", "logic", "style", "tests", "critic"],
    )
    builder.add_edge("security", "critic")
    builder.add_edge("logic", "critic")
    builder.add_edge("style", "critic")
    builder.add_edge("tests", "critic")
    builder.add_edge("critic", END)

    return builder.compile()


review_graph = build_graph()