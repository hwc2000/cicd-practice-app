"""Local graph-style Debug Agent flow without LangGraph dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent_tools.failure_context import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    analyze_ci_failure,
    build_failure_report,
    read_prompt,
    render_user_prompt,
)


DebugAgentState = dict[str, Any]


def load_artifacts(state: DebugAgentState) -> DebugAgentState:
    input_path = Path(state["input_path"])
    system_prompt_path = Path(state["system_prompt_path"])
    user_prompt_path = Path(state["user_prompt_path"])

    state["ci_input"] = input_path.read_text(encoding="utf-8")
    state["system_prompt"] = read_prompt(system_prompt_path)
    state["user_prompt_template"] = read_prompt(user_prompt_path)
    return state


def render_prompt_node(state: DebugAgentState) -> DebugAgentState:
    state["rendered_user_prompt"] = render_user_prompt(
        state["user_prompt_template"],
        state["ci_input"],
    )
    return state


def analyze_failure_tool_node(state: DebugAgentState) -> DebugAgentState:
    state["analysis"] = analyze_ci_failure(
        input_text=state["ci_input"],
        system_prompt=state["system_prompt"],
        user_prompt=state["rendered_user_prompt"],
    )
    return state


def render_report_node(state: DebugAgentState) -> DebugAgentState:
    state["report_markdown"] = build_failure_report(
        input_text=state["ci_input"],
        system_prompt=state["system_prompt"],
        user_prompt=state["rendered_user_prompt"],
    )
    return state


def require_human_review_node(state: DebugAgentState) -> DebugAgentState:
    state["needs_human_review"] = True
    state["decision"] = "manual_review_required"
    return state


def run_graph(initial_state: DebugAgentState) -> DebugAgentState:
    state = initial_state
    for node in (
        load_artifacts,
        render_prompt_node,
        analyze_failure_tool_node,
        render_report_node,
        require_human_review_node,
    ):
        state = node(state)
    return state


def public_state(state: DebugAgentState) -> DebugAgentState:
    return {
        "input_path": state["input_path"],
        "system_prompt_path": state["system_prompt_path"],
        "user_prompt_path": state["user_prompt_path"],
        "analysis": state["analysis"],
        "decision": state["decision"],
        "needs_human_review": state["needs_human_review"],
        "rendered_user_prompt_preview": state["rendered_user_prompt"][:500],
        "report_markdown_preview": state["report_markdown"][:500],
    }


def write_json(path: Path, data: DebugAgentState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local graph-style Debug Agent flow.")
    parser.add_argument("--input", default="docs/debug-agent-example.md")
    parser.add_argument("--output", default="debug-graph-state.json")
    parser.add_argument("--system-prompt", default=str(DEFAULT_SYSTEM_PROMPT))
    parser.add_argument("--user-prompt", default=str(DEFAULT_USER_PROMPT))
    args = parser.parse_args()

    final_state = run_graph(
        {
            "input_path": args.input,
            "system_prompt_path": args.system_prompt,
            "user_prompt_path": args.user_prompt,
        }
    )

    output_path = Path(args.output)
    write_json(output_path, public_state(final_state))
    print(f"Wrote {output_path}")
