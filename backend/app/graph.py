from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from app.security_agent import chunk_diff, run_security_agent


class ReviewState(TypedDict):
    diff_text: str
    findings: list


async def security_node(state: ReviewState) -> dict:
    chunks = chunk_diff(state["diff_text"])
    findings = await run_security_agent(chunks)
    return {"findings": findings}


def build_graph():
    builder = StateGraph(ReviewState)
    builder.add_node("security", security_node)
    builder.add_edge(START, "security")
    builder.add_edge("security", END)
    return builder.compile()


review_graph = build_graph()