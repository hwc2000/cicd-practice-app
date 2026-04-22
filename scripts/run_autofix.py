#!/usr/bin/env python3
"""CLI wrapper for the auto-fix loop.

Usage (from Jenkins or local shell):

    PYTHONPATH=. python scripts/run_autofix.py \
        --input debug-agent-input.md \
        --workspace . \
        --output autofix-result.json \
        --max-attempts 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_tools.autofix_graph import AutoFixState, build_result_json, run_autofix


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CI auto-fix loop.")
    parser.add_argument("--input", required=True, help="Path to debug-agent-input.md")
    parser.add_argument("--workspace", default=".", help="Project workspace root")
    parser.add_argument("--output", default="autofix-result.json", help="Result JSON path")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max retry attempts")
    parser.add_argument("--env-file", default=".env", help=".env file for OpenAI config")
    args = parser.parse_args()

    initial_state: AutoFixState = {
        "input_path": args.input,
        "workspace": args.workspace,
        "max_attempts": args.max_attempts,
        "env_file": args.env_file,
    }

    final_state = run_autofix(initial_state)
    result = build_result_json(final_state)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Auto-fix result: action={result['action']}, "
          f"test_passed={result['test_passed']}, "
          f"attempt={result['attempt'] + 1}/{result['max_attempts']}")
    print(f"Summary: {result['summary']}")
    print(f"Wrote {output_path}")

    # Exit 0 for commit_push, 1 for give_up (Jenkinsfile uses this)
    sys.exit(0 if result["action"] == "commit_push" else 1)


if __name__ == "__main__":
    main()
