"""Compare local graph and LangGraph Debug Agent state artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_COMPARE_KEYS = (
    "analysis.failed_tests",
    "analysis.error_snippet",
    "analysis.changed_files",
    "analysis.suspected_files",
    "analysis.fix_direction",
    "decision",
    "needs_human_review",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_path(data: dict[str, Any], dotted_path: str) -> Any:
    value: Any = data
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def compare_states(
    local_state: dict[str, Any],
    langgraph_state: dict[str, Any],
    keys: tuple[str, ...] = DEFAULT_COMPARE_KEYS,
) -> dict[str, Any]:
    differences = []
    for key in keys:
        local_value = get_path(local_state, key)
        langgraph_value = get_path(langgraph_state, key)
        if local_value != langgraph_value:
            differences.append(
                {
                    "key": key,
                    "local": local_value,
                    "langgraph": langgraph_value,
                }
            )

    return {
        "matched": not differences,
        "compared_keys": list(keys),
        "differences": differences,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare local graph and LangGraph state artifacts.")
    parser.add_argument("--local", default="debug-graph-state.json")
    parser.add_argument("--langgraph", default="debug-langgraph-state.json")
    parser.add_argument("--output", default="debug-graph-compare.json")
    args = parser.parse_args()

    result = compare_states(
        read_json(Path(args.local)),
        read_json(Path(args.langgraph)),
    )
    write_json(Path(args.output), result)
    print(f"Wrote {args.output}")

