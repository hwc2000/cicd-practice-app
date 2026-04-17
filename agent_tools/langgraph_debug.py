"""LangGraph StateGraph prototype for the Debug Agent flow."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, TypedDict

from agent_tools.debug_agent import DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT
from agent_tools.debug_graph import (
    load_artifacts,
    public_state,
    render_prompt_node,
    render_report_node,
    require_human_review_node,
    analyze_failure_tool_node,
    write_json,
)


class DebugAgentGraphState(TypedDict, total=False):
    input_path: str
    system_prompt_path: str
    user_prompt_path: str
    ci_input: str
    system_prompt: str
    user_prompt_template: str
    rendered_user_prompt: str
    analysis: dict[str, Any]
    report_markdown: str
    decision: str
    needs_human_review: bool


def build_state_graph():
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(DebugAgentGraphState)
    builder.add_node("load_artifacts", load_artifacts)
    builder.add_node("render_prompt", render_prompt_node)
    builder.add_node("analyze_failure_tool", analyze_failure_tool_node)
    builder.add_node("render_report", render_report_node)
    builder.add_node("require_human_review", require_human_review_node)

    builder.add_edge(START, "load_artifacts")
    builder.add_edge("load_artifacts", "render_prompt")
    builder.add_edge("render_prompt", "analyze_failure_tool")
    builder.add_edge("analyze_failure_tool", "render_report")
    builder.add_edge("render_report", "require_human_review")
    builder.add_edge("require_human_review", END)
    return builder.compile()


def run_langgraph(initial_state: DebugAgentGraphState) -> DebugAgentGraphState:
    graph = build_state_graph()
    return graph.invoke(initial_state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Debug Agent flow with LangGraph StateGraph.")
    parser.add_argument("--input", default="docs/debug-agent-example.md")
    parser.add_argument("--output", default="debug-langgraph-state.json")
    parser.add_argument("--system-prompt", default=str(DEFAULT_SYSTEM_PROMPT))
    parser.add_argument("--user-prompt", default=str(DEFAULT_USER_PROMPT))
    args = parser.parse_args()

    final_state = run_langgraph(
        {
            "input_path": args.input,
            "system_prompt_path": args.system_prompt,
            "user_prompt_path": args.user_prompt,
        }
    )
    write_json(Path(args.output), public_state(final_state))
    print(f"Wrote {args.output}")
