"""Apply safe, structured patch candidates produced by the debug agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_PREFIXES = ("app/", "tests/", "agent_tools/", "scripts/")


def load_patch_candidate(report: dict[str, Any]) -> dict[str, Any] | None:
    if "patch_candidate" in report:
        return report["patch_candidate"]

    local_analysis = report.get("local_analysis")
    if isinstance(local_analysis, dict):
        return local_analysis.get("patch_candidate")

    return None


def validate_patch_candidate(candidate: dict[str, Any]) -> None:
    if candidate.get("kind") != "replace_text":
        raise ValueError("Only replace_text patch candidates are supported.")
    if not candidate.get("safe_to_apply"):
        raise ValueError("Patch candidate is not marked safe_to_apply.")

    target_file = candidate.get("target_file", "")
    if not any(target_file.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        raise ValueError(f"Refusing to edit unsupported file path: {target_file}")

    if not candidate.get("find"):
        raise ValueError("Patch candidate is missing a find string.")


def apply_patch_candidate(
    candidate: dict[str, Any],
    workspace: Path,
    apply: bool = False,
) -> dict[str, Any]:
    validate_patch_candidate(candidate)

    target_path = (workspace / candidate["target_file"]).resolve()
    workspace_root = workspace.resolve()
    if workspace_root not in target_path.parents and target_path != workspace_root:
        raise ValueError("Target file is outside the workspace.")

    original_text = target_path.read_text(encoding="utf-8")
    find_text = candidate["find"]
    replace_text = candidate["replace"]

    occurrences = original_text.count(find_text)
    if occurrences == 0:
        raise ValueError("Find string was not found in the target file.")
    if occurrences > 1:
        raise ValueError("Find string matched multiple times; refusing ambiguous edit.")

    updated_text = original_text.replace(find_text, replace_text, 1)

    if apply:
        target_path.write_text(updated_text, encoding="utf-8")

    return {
        "target_file": candidate["target_file"],
        "applied": apply,
        "occurrences": occurrences,
        "find": find_text,
        "replace": replace_text,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a safe patch candidate from a debug report JSON file.")
    parser.add_argument("--input", default="debug-openai-report.json")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    candidate = load_patch_candidate(report)
    if not candidate:
        raise SystemExit("No patch_candidate was found in the input report.")

    result = apply_patch_candidate(candidate, workspace=Path(args.workspace), apply=args.apply)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
